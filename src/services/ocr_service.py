"""
OCR Service for processing scanned PDF documents using Tesseract.
Handles image preprocessing, text extraction, and quality validation.
"""

import asyncio
import tempfile
import os
from typing import List, Optional, Dict, Any
from pathlib import Path
import logging

import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import cv2
import numpy as np
import fitz  # PyMuPDF
from pdf2image import convert_from_path

from pydantic import BaseModel
from src.core.config import settings

logger = logging.getLogger(__name__)


class OCRResult(BaseModel):
    """OCR processing result with confidence and metadata."""
    
    text: str
    confidence: float
    language_detected: str
    page_number: int
    processing_time_ms: int
    preprocessing_applied: Dict[str, bool]
    raw_confidence_data: Optional[Dict[str, Any]] = None


class OCRService:
    """Service for OCR processing of scanned PDF documents."""
    
    def __init__(self):
        self.tesseract_cmd = settings.ocr.tesseract_command if hasattr(settings, 'ocr') else 'tesseract'
        self.languages = getattr(settings.ocr, 'supported_languages', ['eng', 'tha']) if hasattr(settings, 'ocr') else ['eng', 'tha']
        self.min_confidence = getattr(settings.ocr, 'minimum_confidence', 60) if hasattr(settings, 'ocr') else 60
        
        # Set Tesseract command path
        if self.tesseract_cmd != 'tesseract':
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd
    
    async def extract_text_from_pdf(self, pdf_path: str) -> List[OCRResult]:
        """
        Extract text from all pages of a scanned PDF using OCR.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            List of OCRResult objects for each page
        """
        logger.info(f"Starting OCR processing for PDF: {pdf_path}")
        
        try:
            # Convert PDF pages to images
            images = await self._pdf_to_images(pdf_path)
            
            # Process each page with OCR
            ocr_results = []
            for page_num, image in enumerate(images, 1):
                result = await self._process_page_with_ocr(image, page_num)
                if result and result.confidence >= self.min_confidence:
                    ocr_results.append(result)
                    logger.info(f"Page {page_num} processed successfully, confidence: {result.confidence:.2f}")
                else:
                    logger.warning(f"Page {page_num} skipped due to low confidence: {result.confidence if result else 0:.2f}")
            
            logger.info(f"OCR processing completed. {len(ocr_results)} pages processed successfully")
            return ocr_results
            
        except Exception as e:
            logger.error(f"OCR processing failed for {pdf_path}: {str(e)}")
            raise
    
    async def _pdf_to_images(self, pdf_path: str, dpi: int = 300) -> List[Image.Image]:
        """Convert PDF pages to PIL Images."""
        try:
            # Use pdf2image for better quality conversion
            images = convert_from_path(pdf_path, dpi=dpi)
            logger.info(f"Converted {len(images)} pages to images at {dpi} DPI")
            return images
        except Exception as e:
            logger.error(f"PDF to image conversion failed: {str(e)}")
            # Fallback to PyMuPDF
            return await self._pdf_to_images_pymupdf(pdf_path)
    
    async def _pdf_to_images_pymupdf(self, pdf_path: str) -> List[Image.Image]:
        """Fallback method using PyMuPDF for PDF to image conversion."""
        images = []
        doc = fitz.open(pdf_path)
        
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            # Render page as image with high resolution
            mat = fitz.Matrix(2.0, 2.0)  # 2x zoom for better quality
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("png")
            
            # Convert to PIL Image
            import io
            image = Image.open(io.BytesIO(img_data))
            images.append(image)
        
        doc.close()
        return images
    
    async def _process_page_with_ocr(self, image: Image.Image, page_number: int) -> Optional[OCRResult]:
        """Process a single page image with OCR."""
        import time
        start_time = time.time()
        
        try:
            # Apply image preprocessing
            processed_image, preprocessing_applied = await self._preprocess_image(image)
            
            # Configure Tesseract
            config = self._get_tesseract_config()
            
            # Perform OCR with confidence data
            ocr_data = pytesseract.image_to_data(
                processed_image, 
                lang='+'.join(self.languages),
                config=config,
                output_type=pytesseract.Output.DICT
            )
            
            # Extract text and calculate confidence
            text = self._extract_text_from_data(ocr_data)
            confidence = self._calculate_confidence(ocr_data)
            detected_lang = self._detect_language(text)
            
            processing_time = int((time.time() - start_time) * 1000)
            
            return OCRResult(
                text=text,
                confidence=confidence,
                language_detected=detected_lang,
                page_number=page_number,
                processing_time_ms=processing_time,
                preprocessing_applied=preprocessing_applied,
                raw_confidence_data=self._extract_confidence_stats(ocr_data)
            )
            
        except Exception as e:
            logger.error(f"OCR processing failed for page {page_number}: {str(e)}")
            return None
    
    async def _preprocess_image(self, image: Image.Image) -> tuple[Image.Image, Dict[str, bool]]:
        """
        Apply image preprocessing to improve OCR accuracy.
        
        Returns:
            Tuple of (processed_image, preprocessing_applied)
        """
        processed_image = image.copy()
        preprocessing_applied = {}
        
        try:
            # Convert to grayscale if needed
            if processed_image.mode != 'L':
                processed_image = processed_image.convert('L')
                preprocessing_applied['grayscale_conversion'] = True
            
            # Apply sharpening
            processed_image = processed_image.filter(ImageFilter.SHARPEN)
            preprocessing_applied['sharpening'] = True
            
            # Enhance contrast
            enhancer = ImageEnhance.Contrast(processed_image)
            processed_image = enhancer.enhance(1.5)
            preprocessing_applied['contrast_enhancement'] = True
            
            # Apply noise reduction using OpenCV
            if self._should_apply_advanced_preprocessing(processed_image):
                processed_image = await self._apply_opencv_preprocessing(processed_image)
                preprocessing_applied['noise_reduction'] = True
                preprocessing_applied['morphological_operations'] = True
            
            return processed_image, preprocessing_applied
            
        except Exception as e:
            logger.warning(f"Image preprocessing failed: {str(e)}, using original image")
            return image, {'preprocessing_failed': True}
    
    def _should_apply_advanced_preprocessing(self, image: Image.Image) -> bool:
        """Determine if advanced preprocessing should be applied based on image quality."""
        # Simple heuristic: apply if image is small or potentially low quality
        width, height = image.size
        return width < 1500 or height < 2000
    
    async def _apply_opencv_preprocessing(self, image: Image.Image) -> Image.Image:
        """Apply OpenCV-based preprocessing for better OCR results."""
        try:
            # Convert PIL to OpenCV format
            cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            
            # Apply Gaussian blur to reduce noise
            cv_image = cv2.GaussianBlur(cv_image, (1, 1), 0)
            
            # Apply morphological operations
            kernel = np.ones((1, 1), np.uint8)
            cv_image = cv2.morphologyEx(cv_image, cv2.MORPH_CLOSE, kernel)
            cv_image = cv2.morphologyEx(cv_image, cv2.MORPH_OPEN, kernel)
            
            # Convert back to PIL
            cv_image_rgb = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)
            return Image.fromarray(cv_image_rgb)
            
        except Exception as e:
            logger.warning(f"OpenCV preprocessing failed: {str(e)}")
            return image
    
    def _get_tesseract_config(self) -> str:
        """Get Tesseract configuration string."""
        return '--psm 3 --oem 3 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.,!?;:()[]{}"-/กขคฆงจฉชซฌญฎฏฐฑฒณดตถทธนบปผฝพฟภมยรลวศษสหฬอฮะาิีึืุูเแโใไๅๆ็่้๊๋์'
    
    def _extract_text_from_data(self, ocr_data: Dict) -> str:
        """Extract clean text from Tesseract output data."""
        words = []
        confidences = ocr_data.get('conf', [])
        texts = ocr_data.get('text', [])
        
        for i, (conf, text) in enumerate(zip(confidences, texts)):
            if conf > 30 and text.strip():  # Filter low-confidence words
                words.append(text.strip())
        
        return ' '.join(words)
    
    def _calculate_confidence(self, ocr_data: Dict) -> float:
        """Calculate overall confidence score from OCR data."""
        confidences = [conf for conf in ocr_data.get('conf', []) if conf > 0]
        
        if not confidences:
            return 0.0
        
        # Calculate weighted average confidence
        total_conf = sum(confidences)
        avg_confidence = total_conf / len(confidences)
        
        return round(avg_confidence, 2)
    
    def _detect_language(self, text: str) -> str:
        """Simple language detection based on character patterns."""
        if not text:
            return 'unknown'
        
        # Count Thai characters
        thai_chars = sum(1 for char in text if '\u0e00' <= char <= '\u0e7f')
        english_chars = sum(1 for char in text if char.isalpha() and ord(char) < 128)
        
        total_alpha = thai_chars + english_chars
        if total_alpha == 0:
            return 'unknown'
        
        thai_ratio = thai_chars / total_alpha
        
        if thai_ratio > 0.7:
            return 'tha'
        elif thai_ratio < 0.3:
            return 'eng'
        else:
            return 'mixed'
    
    def _extract_confidence_stats(self, ocr_data: Dict) -> Dict[str, Any]:
        """Extract detailed confidence statistics."""
        confidences = [conf for conf in ocr_data.get('conf', []) if conf > 0]
        
        if not confidences:
            return {}
        
        return {
            'mean_confidence': round(sum(confidences) / len(confidences), 2),
            'min_confidence': min(confidences),
            'max_confidence': max(confidences),
            'total_words': len(confidences),
            'high_confidence_words': len([c for c in confidences if c > 80]),
            'low_confidence_words': len([c for c in confidences if c < 50])
        }
    
    async def validate_ocr_setup(self) -> Dict[str, bool]:
        """Validate that OCR system is properly configured."""
        validation_results = {}
        
        try:
            # Test Tesseract installation
            version = pytesseract.get_tesseract_version()
            validation_results['tesseract_installed'] = True
            validation_results['tesseract_version'] = str(version)
            logger.info(f"Tesseract version: {version}")
        except Exception as e:
            validation_results['tesseract_installed'] = False
            validation_results['tesseract_error'] = str(e)
            logger.error(f"Tesseract validation failed: {str(e)}")
        
        try:
            # Test language packs
            available_langs = pytesseract.get_languages()
            validation_results['available_languages'] = available_langs
            
            missing_langs = [lang for lang in self.languages if lang not in available_langs]
            validation_results['missing_languages'] = missing_langs
            validation_results['all_languages_available'] = len(missing_langs) == 0
            
        except Exception as e:
            validation_results['language_check_error'] = str(e)
            logger.error(f"Language pack validation failed: {str(e)}")
        
        return validation_results