"""
Processing Service for content ingestion, PDF processing, and hybrid chunking operations.
Coordinates the hybrid chunking pipeline (structural vs OCR+agentic processing).
"""

import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import fitz  # PyMuPDF
from langchain.text_splitter import RecursiveCharacterTextSplitter
import structlog

from .base import BaseService
from .chunking_service import ChunkingService, HybridChunkingResult
from .document_analyzer import ProcessingPath


class ProcessingService(BaseService):
    """Service for content processing and chunking operations."""
    
    def __init__(self):
        super().__init__("ProcessingService")
        self.text_splitter = None
        self.chunking_service = None
    
    async def _initialize(self) -> None:
        """Initialize processing service components."""
        try:
            # Initialize hybrid chunking service
            self.chunking_service = ChunkingService()
            
            # Initialize fallback text splitter for legacy compatibility
            self.text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=getattr(self.settings, 'chunk_size', 500),
                chunk_overlap=getattr(self.settings, 'overlap_size', 50),
                length_function=len,
                separators=[
                    "\n\n",  # Paragraph breaks
                    "\n",    # Line breaks
                    ". ",    # Sentence endings
                    " ",     # Word boundaries
                    ""       # Character level
                ]
            )
            
            # Ensure required directories exist
            input_dir = getattr(self.settings, 'input_data_dir', './data/input')
            output_dir = getattr(self.settings, 'output_data_dir', './data/output')
            Path(input_dir).mkdir(parents=True, exist_ok=True)
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            
            self.logger.info("Processing service with hybrid chunking initialized successfully")
            
        except Exception as e:
            self.logger.error("Failed to initialize processing service", error=str(e))
            raise
    
    async def _shutdown(self) -> None:
        """Shutdown processing service."""
        self.text_splitter = None
    
    def detect_language(self, text: str) -> Tuple[str, float]:
        """
        Detect language of text content.
        
        Args:
            text: Text to analyze
            
        Returns:
            Tuple of (language_code, confidence)
        """
        # Simple character-based language detection
        if len(text.strip()) == 0:
            return "en", 0.0
        
        # Count different character types
        thai_chars = sum(1 for char in text if '\u0e00' <= char <= '\u0e7f')
        english_chars = sum(1 for char in text if char.isascii() and char.isalpha())
        total_chars = len(text)
        
        if total_chars == 0:
            return "en", 0.0
        
        thai_ratio = thai_chars / total_chars
        english_ratio = english_chars / total_chars
        
        # Determine language based on character ratios
        if thai_ratio > 0.3:
            if english_ratio > 0.2:
                return "mixed", max(thai_ratio, english_ratio)
            else:
                return "th", thai_ratio
        elif english_ratio > 0.5:
            return "en", english_ratio
        else:
            return "en", 0.5  # Default to English with moderate confidence
    
    async def extract_text_from_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extract text content from PDF file.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Dictionary with extracted text and metadata
        """
        try:
            pdf_path = Path(pdf_path)
            if not pdf_path.exists():
                raise FileNotFoundError(f"PDF file not found: {pdf_path}")
            
            self.logger.info("Extracting text from PDF", pdf_path=str(pdf_path))
            
            # Open PDF document
            doc = fitz.open(pdf_path)
            
            extracted_data = {
                "filename": pdf_path.name,
                "total_pages": doc.page_count,
                "pages": [],
                "full_text": "",
                "metadata": {
                    "title": doc.metadata.get("title", ""),
                    "author": doc.metadata.get("author", ""),
                    "subject": doc.metadata.get("subject", ""),
                    "creator": doc.metadata.get("creator", ""),
                }
            }
            
            # Extract text from each page
            for page_num in range(doc.page_count):
                page = doc.load_page(page_num)
                
                # Extract text
                text = page.get_text()
                
                if text.strip():  # Only include pages with content
                    # Detect language
                    language, confidence = self.detect_language(text)
                    
                    page_data = {
                        "page_number": page_num + 1,
                        "text": text.strip(),
                        "language": language,
                        "language_confidence": confidence,
                        "char_count": len(text.strip())
                    }
                    
                    extracted_data["pages"].append(page_data)
                    extracted_data["full_text"] += f"\n\n--- Page {page_num + 1} ---\n{text.strip()}"
            
            doc.close()
            
            # Overall document language detection
            doc_language, doc_confidence = self.detect_language(extracted_data["full_text"])
            extracted_data["document_language"] = doc_language
            extracted_data["document_language_confidence"] = doc_confidence
            
            self.logger.info(
                "PDF text extraction completed",
                pages_processed=len(extracted_data["pages"]),
                total_chars=len(extracted_data["full_text"]),
                detected_language=doc_language
            )
            
            return extracted_data
            
        except Exception as e:
            self.logger.error("PDF text extraction failed", pdf_path=pdf_path, error=str(e))
            raise
    
    def preprocess_text(self, text: str) -> str:
        """
        Preprocess text content for better chunking.
        
        Args:
            text: Raw text to preprocess
            
        Returns:
            Preprocessed text
        """
        # Basic text preprocessing
        # Remove excessive whitespace
        text = ' '.join(text.split())
        
        # Remove common PDF artifacts
        text = text.replace('\x0c', '')  # Form feed characters
        text = text.replace('\u00a0', ' ')  # Non-breaking spaces
        
        # Normalize line endings
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        # Clean up multiple consecutive newlines
        while '\n\n\n' in text:
            text = text.replace('\n\n\n', '\n\n')
        
        return text.strip()
    
    def generate_chunk_id(self, text: str, source: str, page: int, index: int) -> str:
        """
        Generate unique chunk ID based on content hash.
        
        Args:
            text: Chunk text content
            source: Source document name
            page: Page number
            index: Chunk index on page
            
        Returns:
            Unique chunk identifier
        """
        content = f"{source}:{page}:{index}:{text[:100]}"
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def calculate_quality_score(self, chunk: str, metadata: Dict[str, Any]) -> float:
        """
        Calculate basic quality score for a chunk.
        
        Args:
            chunk: Text chunk to evaluate
            metadata: Chunk metadata
            
        Returns:
            Quality score between 0.0 and 1.0
        """
        score = 0.0
        
        # Length score (0.3 weight)
        length = len(chunk)
        if length >= 100 and length <= 1500:
            length_score = 1.0
        elif length < 50 or length > 2000:
            length_score = 0.3
        else:
            length_score = 0.7
        score += length_score * 0.3
        
        # Content quality (0.4 weight)
        # Check for educational indicators
        educational_terms = [
            "physics", "force", "energy", "motion", "velocity", "acceleration",
            "ฟิสิกส์", "แรง", "พลังงาน", "การเคลื่อนที่", "ความเร็ว", "ความเร่ง"
        ]
        
        content_score = min(
            sum(1 for term in educational_terms if term.lower() in chunk.lower()) / 3,
            1.0
        )
        score += content_score * 0.4
        
        # Language confidence (0.2 weight)
        lang_confidence = metadata.get("language_confidence", 0.5)
        score += lang_confidence * 0.2
        
        # Completeness (0.1 weight)
        completeness_score = 1.0 if chunk.endswith('.') or chunk.endswith('?') or chunk.endswith('!') else 0.7
        score += completeness_score * 0.1
        
        return min(score, 1.0)
    
    async def create_chunks(
        self,
        extracted_data: Dict[str, Any],
        min_quality_score: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Create chunks from extracted text data.
        
        Args:
            extracted_data: Text data from PDF extraction
            min_quality_score: Minimum quality threshold for chunks
            
        Returns:
            List of chunk dictionaries with metadata
        """
        try:
            chunks = []
            full_text = self.preprocess_text(extracted_data["full_text"])
            
            self.logger.info(
                "Creating chunks",
                full_text_length=len(full_text),
                chunk_size=self.settings.chunk_size,
                overlap_size=self.settings.overlap_size
            )
            
            # Split text into chunks
            text_chunks = self.text_splitter.split_text(full_text)
            
            for i, chunk_text in enumerate(text_chunks):
                if len(chunk_text.strip()) < 50:  # Skip very short chunks
                    continue
                
                # Detect chunk language
                language, lang_confidence = self.detect_language(chunk_text)
                
                # Create chunk metadata
                metadata = {
                    "source_document": extracted_data["filename"],
                    "chunk_index": i,
                    "language_code": language,
                    "language_confidence": lang_confidence,
                    "char_count": len(chunk_text),
                    "word_count": len(chunk_text.split()),
                    "document_language": extracted_data.get("document_language", "en")
                }
                
                # Calculate quality score
                quality_score = self.calculate_quality_score(chunk_text, metadata)
                
                # Only include chunks that meet quality threshold
                if quality_score >= min_quality_score:
                    chunk_id = self.generate_chunk_id(
                        chunk_text,
                        extracted_data["filename"],
                        1,  # Page number (simplified for now)
                        i
                    )
                    
                    chunk = {
                        "chunk_id": chunk_id,
                        "content": chunk_text.strip(),
                        "quality_score": quality_score,
                        "metadata": metadata
                    }
                    
                    chunks.append(chunk)
            
            self.logger.info(
                "Chunk creation completed",
                total_chunks=len(chunks),
                filtered_chunks=len([c for c in chunks if c["quality_score"] >= min_quality_score])
            )
            
            return chunks
            
        except Exception as e:
            self.logger.error("Chunk creation failed", error=str(e))
            raise
    
    async def process_pdf_file(
        self,
        pdf_path: str,
        textbook_id: int,
        min_quality_score: float = 0.5,
        force_processing_path: Optional[ProcessingPath] = None
    ) -> Dict[str, Any]:
        """
        Complete PDF processing pipeline using hybrid chunking.
        
        Args:
            pdf_path: Path to PDF file
            textbook_id: ID of the source textbook
            min_quality_score: Minimum quality threshold (deprecated in hybrid mode)
            force_processing_path: Force specific processing path
            
        Returns:
            Processing results with chunks and metadata
        """
        try:
            self.logger.info("Starting hybrid PDF processing", 
                            pdf_path=pdf_path, textbook_id=textbook_id,
                            force_path=force_processing_path)
            
            # Ensure chunking service is initialized
            if not self.chunking_service:
                self.logger.warning("Chunking service not initialized, falling back to legacy")
                return await self.process_pdf_file_legacy(pdf_path, min_quality_score)
            
            # Use hybrid chunking service
            hybrid_result = await self.chunking_service.process_document(
                pdf_path=pdf_path,
                textbook_id=textbook_id,
                force_processing_path=force_processing_path
            )
            
            # Convert to legacy format for compatibility
            results = self._convert_hybrid_result_to_legacy_format(hybrid_result)
            
            self.logger.info(
                "Hybrid PDF processing completed successfully",
                processing_path=hybrid_result.processing_path_used,
                total_parent_chunks=len(hybrid_result.parent_chunks),
                total_child_chunks=len(hybrid_result.child_chunks),
                quality_score=hybrid_result.quality_score,
                processing_time=hybrid_result.processing_time_seconds,
                fallback_occurred=hybrid_result.fallback_occurred
            )
            
            return results
            
        except Exception as e:
            self.logger.error("Hybrid PDF processing failed", pdf_path=pdf_path, error=str(e))
            
            # Fallback to legacy processing if hybrid fails
            try:
                self.logger.info("Attempting fallback to legacy processing")
                return await self.process_pdf_file_legacy(pdf_path, min_quality_score)
            except Exception as fallback_error:
                self.logger.error("Fallback processing also failed", error=str(fallback_error))
                return {
                    "source_file": pdf_path,
                    "processing_successful": False,
                    "error": f"Hybrid: {str(e)}, Fallback: {str(fallback_error)}",
                    "chunks": [],
                    "processing_method": "failed"
                }
    
    async def process_pdf_file_legacy(
        self,
        pdf_path: str,
        min_quality_score: float = 0.5
    ) -> Dict[str, Any]:
        """
        Legacy PDF processing pipeline using simple text splitting.
        Maintained for backward compatibility.
        
        Args:
            pdf_path: Path to PDF file
            min_quality_score: Minimum quality threshold
            
        Returns:
            Processing results with chunks and metadata
        """
        try:
            self.logger.info("Starting legacy PDF processing", pdf_path=pdf_path)
            
            # Extract text from PDF
            extracted_data = await self.extract_text_from_pdf(pdf_path)
            
            # Create chunks using legacy method
            chunks = await self.create_chunks(extracted_data, min_quality_score)
            
            # Compile results
            results = {
                "source_file": pdf_path,
                "processing_successful": True,
                "processing_method": "legacy",
                "document_metadata": extracted_data["metadata"],
                "document_stats": {
                    "total_pages": extracted_data["total_pages"],
                    "total_chars": len(extracted_data["full_text"]),
                    "document_language": extracted_data.get("document_language", "en"),
                    "language_confidence": extracted_data.get("document_language_confidence", 0.5)
                },
                "chunks": chunks,
                "chunk_stats": {
                    "total_chunks": len(chunks),
                    "avg_quality_score": sum(c["quality_score"] for c in chunks) / len(chunks) if chunks else 0,
                    "language_distribution": self._calculate_language_distribution(chunks)
                }
            }
            
            self.logger.info(
                "Legacy PDF processing completed successfully",
                total_chunks=len(chunks),
                avg_quality=results["chunk_stats"]["avg_quality_score"]
            )
            
            return results
            
        except Exception as e:
            self.logger.error("Legacy PDF processing failed", pdf_path=pdf_path, error=str(e))
            return {
                "source_file": pdf_path,
                "processing_successful": False,
                "error": str(e),
                "chunks": [],
                "processing_method": "legacy_failed"
            }
    
    def _convert_hybrid_result_to_legacy_format(self, hybrid_result: HybridChunkingResult) -> Dict[str, Any]:
        """Convert hybrid chunking result to legacy format for compatibility."""
        
        # Convert chunks to legacy format
        legacy_chunks = []
        for i, parent_chunk in enumerate(hybrid_result.parent_chunks):
            # Create legacy chunk from parent chunk
            chunk_data = {
                "chunk_id": f"hybrid_{i}",
                "content": parent_chunk.get('content', ''),
                "quality_score": hybrid_result.quality_score,
                "metadata": {
                    "source_document": f"textbook_{parent_chunk.get('textbook_id', 0)}",
                    "chunk_index": i,
                    "language_code": parent_chunk.get('ocr_language_detected', 'en'),
                    "language_confidence": parent_chunk.get('ocr_confidence', 100) / 100.0 if parent_chunk.get('ocr_confidence') else 1.0,
                    "char_count": parent_chunk.get('chunk_size', 0),
                    "word_count": len(parent_chunk.get('content', '').split()),
                    "document_type": parent_chunk.get('document_type', 'native'),
                    "processing_path": parent_chunk.get('processing_path', 'structural'),
                    "hybrid_processing": True
                }
            }
            legacy_chunks.append(chunk_data)
        
        return {
            "source_file": "hybrid_processed",
            "processing_successful": not hybrid_result.fallback_occurred or hybrid_result.quality_score > 0.3,
            "processing_method": "hybrid",
            "processing_path": hybrid_result.processing_path_used,
            "document_analysis": hybrid_result.document_analysis.dict() if hybrid_result.document_analysis else {},
            "document_stats": {
                "total_pages": hybrid_result.document_analysis.total_pages if hybrid_result.document_analysis else 1,
                "document_type": hybrid_result.document_analysis.document_type if hybrid_result.document_analysis else "unknown",
                "confidence": hybrid_result.confidence_score,
                "processing_time": hybrid_result.processing_time_seconds
            },
            "chunks": legacy_chunks,
            "chunk_stats": {
                "total_chunks": len(legacy_chunks),
                "avg_quality_score": hybrid_result.quality_score,
                "parent_chunks": len(hybrid_result.parent_chunks),
                "child_chunks": len(hybrid_result.child_chunks)
            },
            "hybrid_metadata": {
                "fallback_occurred": hybrid_result.fallback_occurred,
                "fallback_reason": hybrid_result.fallback_reason,
                "ocr_metrics": hybrid_result.ocr_metrics,
                "agentic_metrics": hybrid_result.agentic_metrics,
                "processing_metadata": hybrid_result.metadata
            }
        }
    
    def _calculate_language_distribution(self, chunks: List[Dict[str, Any]]) -> Dict[str, int]:
        """Calculate language distribution across chunks."""
        distribution = {}
        for chunk in chunks:
            lang = chunk["metadata"]["language_code"]
            distribution[lang] = distribution.get(lang, 0) + 1
        return distribution
    
    async def health_check(self) -> Dict[str, Any]:
        """Check processing service health."""
        try:
            if not self.is_initialized():
                return {
                    "status": "unhealthy",
                    "message": "Service not initialized"
                }
            
            # Test text splitter
            test_text = "This is a test sentence. This is another test sentence."
            test_chunks = self.text_splitter.split_text(test_text)
            
            # Check directories
            input_dir_exists = Path(self.settings.input_data_dir).exists()
            output_dir_exists = Path(self.settings.output_data_dir).exists()
            
            # Check hybrid chunking service
            chunking_service_status = "initialized" if self.chunking_service else "not_initialized"
            
            return {
                "status": "healthy",
                "message": "Processing service operational with hybrid chunking",
                "capabilities": {
                    "hybrid_chunking": chunking_service_status == "initialized",
                    "legacy_processing": True,
                    "ocr_processing": chunking_service_status == "initialized",
                    "structural_chunking": chunking_service_status == "initialized",
                    "agentic_chunking": chunking_service_status == "initialized"
                },
                "text_splitter": {
                    "chunk_size": self.settings.chunk_size,
                    "overlap_size": self.settings.overlap_size,
                    "test_chunks_count": len(test_chunks)
                },
                "directories": {
                    "input_dir_exists": input_dir_exists,
                    "output_dir_exists": output_dir_exists
                },
                "services": {
                    "chunking_service": chunking_service_status
                }
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "message": f"Health check failed: {str(e)}"
            }