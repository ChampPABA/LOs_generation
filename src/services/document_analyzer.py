"""
Document Analyzer Service for detecting PDF type (native vs scanned).
Determines the appropriate processing path for the hybrid chunking pipeline.
"""

import logging
from typing import Dict, List, Optional, Tuple
from enum import Enum
from pathlib import Path
import re

import fitz  # PyMuPDF
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class DocumentType(str, Enum):
    """Document type classification."""
    NATIVE = "native"      # PDF with selectable text
    SCANNED = "scanned"    # Image-based PDF requiring OCR
    MIXED = "mixed"        # Contains both native and scanned pages


class ProcessingPath(str, Enum):
    """Processing path determination."""
    STRUCTURAL = "structural"      # Use structural chunking (MarkdownHeaderTextSplitter)
    OCR_AGENTIC = "ocr_agentic"   # Use OCR + agentic chunking


class PageAnalysis(BaseModel):
    """Analysis result for a single page."""
    page_number: int
    has_text: bool
    text_density: float        # Characters per square unit
    text_length: int
    estimated_readability: float  # 0-1, based on text structure
    requires_ocr: bool


class DocumentAnalysisResult(BaseModel):
    """Complete document analysis result."""
    document_type: DocumentType
    processing_path: ProcessingPath
    confidence: float          # 0-1, confidence in the classification
    total_pages: int
    pages_with_text: int
    pages_requiring_ocr: int
    page_analyses: List[PageAnalysis]
    analysis_method: str
    decision_factors: List[str]


class DocumentAnalyzer:
    """Service for analyzing PDF documents and determining processing strategy."""
    
    def __init__(self):
        self.text_density_threshold = 50      # chars per 1000 sq pixels
        self.native_page_threshold = 0.8      # 80% of pages must have text
        self.mixed_threshold = 0.3            # 30-70% creates mixed classification
        self.min_text_length = 50             # Minimum chars to consider "has text"
        self.sample_size_limit = 5            # Max pages to analyze for large docs
    
    async def analyze_pdf_type(self, pdf_path: str) -> DocumentAnalysisResult:
        """
        Analyze PDF to determine document type and processing path.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            DocumentAnalysisResult with classification and recommendations
        """
        logger.info(f"Starting document analysis for: {pdf_path}")
        
        try:
            # Open PDF document
            doc = fitz.open(pdf_path)
            total_pages = len(doc)
            
            # Determine sampling strategy
            pages_to_analyze = self._determine_sample_pages(total_pages)
            logger.info(f"Analyzing {len(pages_to_analyze)} pages out of {total_pages}")
            
            # Analyze each sampled page
            page_analyses = []
            for page_num in pages_to_analyze:
                analysis = await self._analyze_page(doc, page_num)
                page_analyses.append(analysis)
            
            doc.close()
            
            # Make classification decision
            result = self._classify_document(page_analyses, total_pages)
            
            logger.info(f"Document classified as {result.document_type.value} with {result.confidence:.2f} confidence")
            return result
            
        except Exception as e:
            logger.error(f"Document analysis failed for {pdf_path}: {str(e)}")
            # Return fallback classification
            return self._create_fallback_result(str(e))
    
    def _determine_sample_pages(self, total_pages: int) -> List[int]:
        """Determine which pages to sample for analysis."""
        if total_pages <= self.sample_size_limit:
            # Analyze all pages for small documents
            return list(range(total_pages))
        
        # For larger documents, sample strategically
        sample_pages = []
        
        # Always include first and last page
        sample_pages.extend([0, total_pages - 1])
        
        # Add evenly spaced middle pages
        remaining_samples = self.sample_size_limit - 2
        if remaining_samples > 0:
            step = max(1, total_pages // (remaining_samples + 1))
            for i in range(1, remaining_samples + 1):
                page_num = min(i * step, total_pages - 2)
                if page_num not in sample_pages:
                    sample_pages.append(page_num)
        
        return sorted(list(set(sample_pages)))
    
    async def _analyze_page(self, doc: fitz.Document, page_num: int) -> PageAnalysis:
        """Analyze a single page to determine text content quality."""
        page = doc.load_page(page_num)
        
        # Extract text content
        text = page.get_text().strip()
        text_length = len(text)
        
        # Calculate page dimensions for density calculation
        rect = page.rect
        page_area = rect.width * rect.height
        
        # Calculate text density (characters per 1000 sq pixels)
        text_density = (text_length * 1000) / page_area if page_area > 0 else 0
        
        # Determine if page has meaningful text
        has_meaningful_text = self._has_meaningful_text(text)
        
        # Estimate readability based on text structure
        readability = self._estimate_readability(text)
        
        # Decide if OCR is required
        requires_ocr = not has_meaningful_text
        
        return PageAnalysis(
            page_number=page_num + 1,  # 1-based page numbering
            has_text=has_meaningful_text,
            text_density=round(text_density, 2),
            text_length=text_length,
            estimated_readability=readability,
            requires_ocr=requires_ocr
        )
    
    def _has_meaningful_text(self, text: str) -> bool:
        """Determine if extracted text is meaningful (not OCR artifacts)."""
        if len(text) < self.min_text_length:
            return False
        
        # Check for common OCR artifacts and gibberish
        if self._is_ocr_artifact(text):
            return False
        
        # Check for reasonable word-like patterns
        words = text.split()
        if len(words) < 5:  # Too few words
            return False
        
        # Check average word length (reasonable range)
        avg_word_length = sum(len(word) for word in words) / len(words)
        if avg_word_length < 2 or avg_word_length > 15:
            return False
        
        return True
    
    def _is_ocr_artifact(self, text: str) -> bool:
        """Check if text appears to be OCR artifacts or gibberish."""
        # Check for excessive special characters
        special_char_ratio = sum(1 for char in text if not char.isalnum() and not char.isspace()) / len(text)
        if special_char_ratio > 0.3:
            return True
        
        # Check for repetitive character patterns (OCR errors)
        if re.search(r'(.)\1{4,}', text):  # 5+ repeated characters
            return True
        
        # Check for excessive single characters
        single_chars = [word for word in text.split() if len(word) == 1 and word.isalpha()]
        if len(single_chars) > len(text.split()) * 0.4:  # >40% single character words
            return True
        
        return False
    
    def _estimate_readability(self, text: str) -> float:
        """Estimate text readability score (0-1)."""
        if not text:
            return 0.0
        
        score = 0.0
        
        # Check for sentence structure
        sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
        if sentences:
            score += 0.3
            
            # Reasonable sentence length
            avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences)
            if 5 <= avg_sentence_length <= 30:
                score += 0.2
        
        # Check for proper capitalization
        words = text.split()
        capitalized_words = sum(1 for word in words if word and word[0].isupper())
        if capitalized_words > 0:
            cap_ratio = capitalized_words / len(words)
            if 0.1 <= cap_ratio <= 0.4:  # Reasonable capitalization
                score += 0.2
        
        # Check for punctuation variety
        punctuation_types = len(set(char for char in text if char in '.,!?;:()[]{}'))
        if punctuation_types >= 3:
            score += 0.15
        
        # Check for reasonable character distribution
        if self._has_reasonable_char_distribution(text):
            score += 0.15
        
        return min(1.0, score)
    
    def _has_reasonable_char_distribution(self, text: str) -> bool:
        """Check if text has reasonable character distribution (not random)."""
        if len(text) < 100:
            return True  # Too short to analyze meaningfully
        
        # Check vowel-consonant ratio for English/Thai mixed content
        vowels = 'aeiouAEIOUเแโใไะาิีึืุูอ'
        vowel_count = sum(1 for char in text if char in vowels)
        alpha_count = sum(1 for char in text if char.isalpha())
        
        if alpha_count > 0:
            vowel_ratio = vowel_count / alpha_count
            return 0.2 <= vowel_ratio <= 0.6  # Reasonable vowel ratio
        
        return True
    
    def _classify_document(self, page_analyses: List[PageAnalysis], total_pages: int) -> DocumentAnalysisResult:
        """Classify document based on page analyses."""
        pages_with_text = sum(1 for analysis in page_analyses if analysis.has_text)
        pages_requiring_ocr = sum(1 for analysis in page_analyses if analysis.requires_ocr)
        
        # Calculate ratios
        text_page_ratio = pages_with_text / len(page_analyses) if page_analyses else 0
        ocr_page_ratio = pages_requiring_ocr / len(page_analyses) if page_analyses else 1
        
        # Decision factors
        decision_factors = []
        
        # Classify document type
        if text_page_ratio >= self.native_page_threshold:
            doc_type = DocumentType.NATIVE
            processing_path = ProcessingPath.STRUCTURAL
            confidence = min(0.95, 0.5 + text_page_ratio * 0.5)
            decision_factors.append(f"{text_page_ratio:.1%} of pages have meaningful text")
            
        elif text_page_ratio <= self.mixed_threshold:
            doc_type = DocumentType.SCANNED
            processing_path = ProcessingPath.OCR_AGENTIC
            confidence = min(0.95, 0.5 + ocr_page_ratio * 0.5)
            decision_factors.append(f"{ocr_page_ratio:.1%} of pages require OCR")
            
        else:
            doc_type = DocumentType.MIXED
            # For mixed documents, prefer OCR path for comprehensive processing
            processing_path = ProcessingPath.OCR_AGENTIC
            confidence = 0.7  # Lower confidence for mixed documents
            decision_factors.append(f"Mixed document: {text_page_ratio:.1%} text, {ocr_page_ratio:.1%} OCR")
        
        # Add quality-based decision factors
        if page_analyses:
            avg_readability = sum(p.estimated_readability for p in page_analyses) / len(page_analyses)
            avg_text_density = sum(p.text_density for p in page_analyses) / len(page_analyses)
            
            decision_factors.append(f"Average readability: {avg_readability:.2f}")
            decision_factors.append(f"Average text density: {avg_text_density:.1f}")
            
            # Adjust confidence based on text quality
            if avg_readability > 0.8:
                confidence = min(0.98, confidence + 0.1)
            elif avg_readability < 0.3:
                confidence = max(0.5, confidence - 0.1)
        
        # Extrapolate to full document
        estimated_text_pages = int(pages_with_text * total_pages / len(page_analyses)) if page_analyses else 0
        estimated_ocr_pages = total_pages - estimated_text_pages
        
        return DocumentAnalysisResult(
            document_type=doc_type,
            processing_path=processing_path,
            confidence=round(confidence, 3),
            total_pages=total_pages,
            pages_with_text=estimated_text_pages,
            pages_requiring_ocr=estimated_ocr_pages,
            page_analyses=page_analyses,
            analysis_method="sampling" if len(page_analyses) < total_pages else "complete",
            decision_factors=decision_factors
        )
    
    def _create_fallback_result(self, error_message: str) -> DocumentAnalysisResult:
        """Create fallback result when analysis fails."""
        logger.warning(f"Using fallback classification due to error: {error_message}")
        
        return DocumentAnalysisResult(
            document_type=DocumentType.SCANNED,  # Safe fallback - assume OCR needed
            processing_path=ProcessingPath.OCR_AGENTIC,
            confidence=0.3,  # Low confidence
            total_pages=1,
            pages_with_text=0,
            pages_requiring_ocr=1,
            page_analyses=[],
            analysis_method="fallback",
            decision_factors=[f"Analysis failed: {error_message}", "Defaulting to OCR processing"]
        )
    
    async def get_detailed_page_analysis(self, pdf_path: str, page_numbers: Optional[List[int]] = None) -> List[PageAnalysis]:
        """Get detailed analysis for specific pages."""
        try:
            doc = fitz.open(pdf_path)
            
            if page_numbers is None:
                page_numbers = list(range(len(doc)))
            
            analyses = []
            for page_num in page_numbers:
                if 0 <= page_num < len(doc):
                    analysis = await self._analyze_page(doc, page_num)
                    analyses.append(analysis)
            
            doc.close()
            return analyses
            
        except Exception as e:
            logger.error(f"Detailed page analysis failed: {str(e)}")
            return []