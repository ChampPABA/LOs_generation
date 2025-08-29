"""
Structural Chunker Service for processing native PDFs with selectable text.
Uses LangChain's text splitters for hierarchical chunking (Late Chunking strategy).
"""

import logging
from typing import List, Dict, Any, Optional
import hashlib
import time

import fitz  # PyMuPDF
from langchain.text_splitter import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from markdownify import markdownify as md

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class StructuralChunkData(BaseModel):
    """Data structure for structural chunk before database storage."""
    content: str
    page_number: Optional[int] = None
    chapter_title: Optional[str] = None
    section_title: Optional[str] = None
    chunk_size: int
    overlap_size: Optional[int] = None


class StructuralChunkingResult(BaseModel):
    """Result of structural chunking process."""
    parent_chunks: List[StructuralChunkData]
    child_chunks: List[List[StructuralChunkData]]  # Child chunks grouped by parent
    processing_metadata: Dict[str, Any]


class StructuralChunker:
    """Service for structural chunking of native PDF documents."""
    
    def __init__(self):
        # Configuration for chunking
        self.parent_chunk_size = 1000      # Target size for parent chunks
        self.child_chunk_size = 300        # Target size for child chunks  
        self.chunk_overlap = 50            # Overlap between child chunks
        
        # Headers to split on (Markdown style)
        self.headers_to_split_on = [
            ("#", "Header 1"),
            ("##", "Header 2"), 
            ("###", "Header 3"),
            ("####", "Header 4"),
        ]
        
        # Configure text splitters
        self.markdown_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=self.headers_to_split_on
        )
        
        self.recursive_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.child_chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
    
    async def process_document(self, pdf_path: str, textbook_id: int) -> StructuralChunkingResult:
        """
        Process a native PDF document through structural chunking.
        
        Args:
            pdf_path: Path to the PDF file
            textbook_id: ID of the source textbook
            
        Returns:
            StructuralChunkingResult with parent and child chunks
        """
        logger.info(f"Starting structural chunking for: {pdf_path}")
        start_time = time.time()
        
        try:
            # Step 1: Extract structured text from PDF
            structured_content = await self._extract_structured_content(pdf_path)
            
            if not structured_content:
                raise Exception("No structured content could be extracted from PDF")
            
            logger.info(f"Extracted {len(structured_content)} characters of structured content")
            
            # Step 2: Convert to markdown for better structure recognition
            markdown_content = await self._convert_to_markdown(structured_content)
            
            # Step 3: Create parent chunks using header-based splitting
            parent_chunks = await self._create_parent_chunks(markdown_content)
            logger.info(f"Created {len(parent_chunks)} parent chunks")
            
            # Step 4: Create child chunks from each parent
            child_chunks_grouped = []
            for parent_chunk in parent_chunks:
                child_chunks = await self._create_child_chunks(parent_chunk.content)
                child_chunks_grouped.append(child_chunks)
                logger.debug(f"Parent chunk split into {len(child_chunks)} child chunks")
            
            total_child_chunks = sum(len(group) for group in child_chunks_grouped)
            processing_time = time.time() - start_time
            
            logger.info(f"Structural chunking completed: {len(parent_chunks)} parent, {total_child_chunks} child chunks in {processing_time:.1f}s")
            
            return StructuralChunkingResult(
                parent_chunks=parent_chunks,
                child_chunks=child_chunks_grouped,
                processing_metadata={
                    'method': 'structural',
                    'processing_time_seconds': processing_time,
                    'total_parent_chunks': len(parent_chunks),
                    'total_child_chunks': total_child_chunks,
                    'average_parent_size': sum(chunk.chunk_size for chunk in parent_chunks) / len(parent_chunks) if parent_chunks else 0,
                    'textbook_id': textbook_id
                }
            )
            
        except Exception as e:
            logger.error(f"Structural chunking failed: {str(e)}")
            raise
    
    async def _extract_structured_content(self, pdf_path: str) -> str:
        """Extract structured text content from native PDF."""
        try:
            doc = fitz.open(pdf_path)
            content_parts = []
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                
                # Get text with layout information
                text = page.get_text("text")  # Basic text extraction
                
                if text.strip():
                    # Add page separator for multi-page documents
                    if page_num > 0:
                        content_parts.append(f"\n\n--- Page {page_num + 1} ---\n\n")
                    
                    content_parts.append(text)
            
            doc.close()
            return ''.join(content_parts)
            
        except Exception as e:
            logger.error(f"Text extraction failed: {str(e)}")
            raise
    
    async def _convert_to_markdown(self, content: str) -> str:
        """
        Convert extracted text to markdown format for better structure recognition.
        This helps the MarkdownHeaderTextSplitter identify hierarchical structure.
        """
        lines = content.split('\n')
        markdown_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                markdown_lines.append('')
                continue
            
            # Detect headers based on text characteristics
            if self._is_header_line(line):
                # Convert to markdown header based on detected level
                header_level = self._detect_header_level(line)
                markdown_lines.append(f"{'#' * header_level} {line}")
            else:
                markdown_lines.append(line)
        
        return '\n'.join(markdown_lines)
    
    def _is_header_line(self, line: str) -> bool:
        """Detect if a line is likely a header."""
        if not line or len(line) > 100:  # Headers are usually not too long
            return False
        
        # Check for header indicators
        header_indicators = [
            line.isupper(),                          # ALL CAPS
            line.endswith(':'),                      # Ends with colon
            len(line.split()) <= 8,                  # Short (8 words or less)
            line[0].isupper() and not line.endswith('.'),  # Starts with capital, no period
            any(keyword in line.lower() for keyword in ['chapter', 'section', 'part', 'introduction', 'conclusion'])
        ]
        
        # Header if multiple indicators are true
        return sum(header_indicators) >= 2
    
    def _detect_header_level(self, line: str) -> int:
        """Detect the hierarchical level of a header (1-4)."""
        if any(word in line.lower() for word in ['chapter', 'part']):
            return 1  # Top level
        elif any(word in line.lower() for word in ['section']):
            return 2  # Second level
        elif line.isupper():
            return 2  # ALL CAPS are usually important
        elif any(word in line.lower() for word in ['introduction', 'conclusion', 'summary']):
            return 3  # Third level
        else:
            return 3  # Default to third level
    
    async def _create_parent_chunks(self, markdown_content: str) -> List[StructuralChunkData]:
        """Create parent chunks using markdown header-based splitting."""
        try:
            # Split by headers first
            header_splits = self.markdown_splitter.split_text(markdown_content)
            
            if not header_splits:
                # Fallback to size-based splitting if no headers found
                logger.warning("No headers detected, falling back to size-based splitting")
                return await self._create_size_based_parent_chunks(markdown_content)
            
            parent_chunks = []
            
            for i, split in enumerate(header_splits):
                content = split.page_content if hasattr(split, 'page_content') else str(split)
                metadata = split.metadata if hasattr(split, 'metadata') else {}
                
                # Extract structure information from metadata
                chapter_title = None
                section_title = None
                
                # Parse metadata for hierarchical information
                for key, value in metadata.items():
                    if 'Header 1' in key or 'Header 2' in key:
                        chapter_title = value
                    elif 'Header 3' in key or 'Header 4' in key:
                        section_title = value
                
                # If chunk is too large, split it further
                if len(content) > self.parent_chunk_size * 1.5:
                    sub_chunks = await self._split_large_chunk(content, chapter_title, section_title)
                    parent_chunks.extend(sub_chunks)
                else:
                    chunk_data = StructuralChunkData(
                        content=content.strip(),
                        chapter_title=chapter_title,
                        section_title=section_title,
                        chunk_size=len(content)
                    )
                    parent_chunks.append(chunk_data)
            
            return parent_chunks
            
        except Exception as e:
            logger.warning(f"Header-based splitting failed: {str(e)}, using size-based fallback")
            return await self._create_size_based_parent_chunks(markdown_content)
    
    async def _split_large_chunk(self, content: str, chapter_title: Optional[str], section_title: Optional[str]) -> List[StructuralChunkData]:
        """Split large chunks into smaller parent chunks."""
        # Use recursive splitter for large chunks
        large_chunk_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.parent_chunk_size,
            chunk_overlap=100,  # Larger overlap for parent chunks
            length_function=len
        )
        
        splits = large_chunk_splitter.split_text(content)
        
        sub_chunks = []
        for i, split_content in enumerate(splits):
            chunk_data = StructuralChunkData(
                content=split_content.strip(),
                chapter_title=chapter_title,
                section_title=f"{section_title} (Part {i+1})" if section_title else f"Part {i+1}",
                chunk_size=len(split_content)
            )
            sub_chunks.append(chunk_data)
        
        return sub_chunks
    
    async def _create_size_based_parent_chunks(self, content: str) -> List[StructuralChunkData]:
        """Fallback method for creating parent chunks based on size only."""
        parent_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.parent_chunk_size,
            chunk_overlap=100,
            length_function=len
        )
        
        splits = parent_splitter.split_text(content)
        
        parent_chunks = []
        for i, split_content in enumerate(splits):
            chunk_data = StructuralChunkData(
                content=split_content.strip(),
                section_title=f"Section {i+1}",
                chunk_size=len(split_content)
            )
            parent_chunks.append(chunk_data)
        
        return parent_chunks
    
    async def _create_child_chunks(self, parent_content: str) -> List[StructuralChunkData]:
        """Create child chunks from parent chunk content."""
        try:
            child_splits = self.recursive_splitter.split_text(parent_content)
            
            child_chunks = []
            for split_content in child_splits:
                chunk_data = StructuralChunkData(
                    content=split_content.strip(),
                    chunk_size=len(split_content),
                    overlap_size=self.chunk_overlap
                )
                child_chunks.append(chunk_data)
            
            return child_chunks
            
        except Exception as e:
            logger.error(f"Child chunk creation failed: {str(e)}")
            # Fallback to simple sentence splitting
            return await self._create_simple_child_chunks(parent_content)
    
    async def _create_simple_child_chunks(self, content: str) -> List[StructuralChunkData]:
        """Fallback method for creating child chunks using simple sentence splitting."""
        # Split by sentences
        sentences = content.split('. ')
        
        child_chunks = []
        current_chunk = []
        current_size = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            # Ensure sentence ends with period
            if not sentence.endswith('.'):
                sentence += '.'
            
            # Check if adding this sentence exceeds chunk size
            if current_size + len(sentence) > self.child_chunk_size and current_chunk:
                # Create chunk from current sentences
                chunk_content = ' '.join(current_chunk)
                chunk_data = StructuralChunkData(
                    content=chunk_content,
                    chunk_size=len(chunk_content),
                    overlap_size=0  # No overlap in simple splitting
                )
                child_chunks.append(chunk_data)
                
                # Start new chunk
                current_chunk = [sentence]
                current_size = len(sentence)
            else:
                current_chunk.append(sentence)
                current_size += len(sentence)
        
        # Add final chunk
        if current_chunk:
            chunk_content = ' '.join(current_chunk)
            chunk_data = StructuralChunkData(
                content=chunk_content,
                chunk_size=len(chunk_content),
                overlap_size=0
            )
            child_chunks.append(chunk_data)
        
        return child_chunks
    
    def generate_chunk_hash(self, content: str) -> str:
        """Generate unique hash for chunk content."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    async def validate_chunks(self, parent_chunks: List[StructuralChunkData]) -> Dict[str, Any]:
        """Validate the quality of created chunks."""
        if not parent_chunks:
            return {'valid': False, 'reason': 'no_chunks_created'}
        
        # Check chunk sizes
        sizes = [chunk.chunk_size for chunk in parent_chunks]
        avg_size = sum(sizes) / len(sizes)
        
        # Check for reasonable size distribution
        too_small = len([s for s in sizes if s < 100])  # Less than 100 chars
        too_large = len([s for s in sizes if s > 2000])  # More than 2000 chars
        
        validation_result = {
            'valid': True,
            'total_chunks': len(parent_chunks),
            'average_size': avg_size,
            'min_size': min(sizes),
            'max_size': max(sizes),
            'chunks_too_small': too_small,
            'chunks_too_large': too_large,
            'size_distribution': 'good' if too_small + too_large < len(sizes) * 0.2 else 'poor'
        }
        
        # Mark as invalid if too many problematic chunks
        if too_small + too_large > len(sizes) * 0.3:
            validation_result['valid'] = False
            validation_result['reason'] = 'poor_size_distribution'
        
        return validation_result