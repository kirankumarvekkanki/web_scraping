"""
PDF Crawler for extracting content from PDF documents.
"""

import asyncio
import aiohttp
import io
from typing import Dict, Any, Optional, List
import logging
import re

try:
    import pdfplumber
    import fitz  # PyMuPDF
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    logger.warning("PDF libraries not available. Install pdfplumber and PyMuPDF.")

from .base_crawler import BaseCrawler

logger = logging.getLogger(__name__)


class PDFCrawler(BaseCrawler):
    """Crawler for PDF documents using pdfplumber and PyMuPDF."""
    
    def __init__(self, extract_images: bool = True, extract_tables: bool = True, **kwargs):
        super().__init__(**kwargs)
        self.extract_images = extract_images
        self.extract_tables = extract_tables
        self.timeout = aiohttp.ClientTimeout(total=60)  # PDFs might be large
        
        if not PDF_AVAILABLE:
            raise ImportError("PDF processing libraries not available. Please install pdfplumber and PyMuPDF.")
    
    async def _fetch_content(self, url: str, **kwargs) -> bytes:
        """Download PDF content."""
        headers = self.get_headers()
        headers.update({
            'Accept': 'application/pdf,application/octet-stream,*/*'
        })
        
        # Add custom headers if provided
        if 'headers' in kwargs:
            headers.update(kwargs['headers'])
        
        connector_kwargs = {}
        if self.proxy_manager:
            proxy_url = await self.proxy_manager.get_proxy()
            if proxy_url:
                connector_kwargs['connector'] = aiohttp.ProxyConnector.from_url(proxy_url)
        
        if not self.session:
            self.session = aiohttp.ClientSession(
                timeout=self.timeout,
                headers=headers,
                **connector_kwargs
            )
        
        async with self.session.get(url) as response:
            if response.status == 403:
                logger.warning(f"Access forbidden for {url}, rotating proxy")
                if self.proxy_manager:
                    await self.proxy_manager.rotate_proxy()
                raise aiohttp.ClientResponseError(
                    request_info=response.request_info,
                    history=response.history,
                    status=response.status,
                    message="Access forbidden"
                )
            
            response.raise_for_status()
            
            # Verify content type
            content_type = response.headers.get('content-type', '').lower()
            if 'pdf' not in content_type and not url.lower().endswith('.pdf'):
                logger.warning(f"Content may not be PDF: {content_type}")
            
            content = await response.read()
            
            # Add delay to be respectful
            await asyncio.sleep(self.delay)
            
            return content
    
    async def parse_content(self, content: bytes, url: str) -> Dict[str, Any]:
        """Parse PDF content and extract structured data."""
        parsed_data = {
            'url': url,
            'pages': [],
            'metadata': {},
            'text_content': '',
            'tables': [],
            'images': [],
            'toc': [],  # Table of contents
            'annotations': [],
            'forms': []
        }
        
        # Use both libraries for comprehensive extraction
        try:
            # Extract with pdfplumber (better for tables and layout)
            plumber_data = await self._extract_with_pdfplumber(content)
            
            # Extract with PyMuPDF (better for metadata and images)
            pymupdf_data = await self._extract_with_pymupdf(content)
            
            # Combine results
            parsed_data.update({
                'pages': plumber_data.get('pages', []),
                'text_content': plumber_data.get('text_content', ''),
                'tables': plumber_data.get('tables', []),
                'metadata': pymupdf_data.get('metadata', {}),
                'images': pymupdf_data.get('images', []),
                'toc': pymupdf_data.get('toc', []),
                'annotations': pymupdf_data.get('annotations', []),
                'forms': pymupdf_data.get('forms', [])
            })
            
        except Exception as e:
            logger.error(f"Error parsing PDF content: {e}")
            parsed_data['error'] = str(e)
        
        return parsed_data
    
    async def _extract_with_pdfplumber(self, content: bytes) -> Dict[str, Any]:
        """Extract content using pdfplumber."""
        data = {
            'pages': [],
            'text_content': '',
            'tables': []
        }
        
        try:
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    page_data = {
                        'page_number': page_num + 1,
                        'text': '',
                        'tables': [],
                        'layout': {},
                        'formatting': []
                    }
                    
                    # Extract text
                    text = page.extract_text()
                    if text:
                        page_data['text'] = text
                        data['text_content'] += f"\n--- Page {page_num + 1} ---\n{text}\n"
                    
                    # Extract tables if enabled
                    if self.extract_tables:
                        tables = page.extract_tables()
                        if tables:
                            for table_idx, table in enumerate(tables):
                                table_data = {
                                    'page': page_num + 1,
                                    'table_index': table_idx,
                                    'headers': table[0] if table else [],
                                    'rows': table[1:] if len(table) > 1 else [],
                                    'raw_table': table
                                }
                                page_data['tables'].append(table_data)
                                data['tables'].append(table_data)
                    
                    # Extract layout information
                    page_data['layout'] = {
                        'width': page.width,
                        'height': page.height,
                        'bbox': page.bbox
                    }
                    
                    # Extract character-level formatting for preserving subscripts/superscripts
                    chars = page.chars
                    if chars:
                        formatting_info = self._analyze_character_formatting(chars)
                        page_data['formatting'] = formatting_info
                    
                    data['pages'].append(page_data)
                    
        except Exception as e:
            logger.error(f"Error with pdfplumber extraction: {e}")
            data['error'] = str(e)
        
        return data
    
    async def _extract_with_pymupdf(self, content: bytes) -> Dict[str, Any]:
        """Extract content using PyMuPDF (fitz)."""
        data = {
            'metadata': {},
            'images': [],
            'toc': [],
            'annotations': [],
            'forms': []
        }
        
        try:
            doc = fitz.open(stream=content, filetype="pdf")
            
            # Extract metadata
            data['metadata'] = doc.metadata
            
            # Extract table of contents
            toc = doc.get_toc()
            if toc:
                data['toc'] = [{'level': item[0], 'title': item[1], 'page': item[2]} for item in toc]
            
            # Extract images and annotations from each page
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                
                # Extract images if enabled
                if self.extract_images:
                    image_list = page.get_images()
                    for img_index, img in enumerate(image_list):
                        try:
                            xref = img[0]
                            pix = fitz.Pixmap(doc, xref)
                            if pix.n - pix.alpha < 4:  # GRAY or RGB
                                img_data = {
                                    'page': page_num + 1,
                                    'index': img_index,
                                    'xref': xref,
                                    'width': pix.width,
                                    'height': pix.height,
                                    'colorspace': pix.colorspace.name if pix.colorspace else 'unknown',
                                    'size': len(pix.pil_tobytes("PNG"))
                                }
                                data['images'].append(img_data)
                            pix = None
                        except Exception as e:
                            logger.warning(f"Could not extract image {img_index} from page {page_num + 1}: {e}")
                
                # Extract annotations
                annotations = page.annots()
                for annot in annotations:
                    try:
                        annot_data = {
                            'page': page_num + 1,
                            'type': annot.type[1],
                            'content': annot.info.get('content', ''),
                            'rect': list(annot.rect),
                            'author': annot.info.get('title', ''),
                            'subject': annot.info.get('subject', '')
                        }
                        data['annotations'].append(annot_data)
                    except Exception as e:
                        logger.warning(f"Could not extract annotation from page {page_num + 1}: {e}")
                
                # Extract form fields
                if page.first_widget:
                    widget = page.first_widget
                    while widget:
                        try:
                            field_data = {
                                'page': page_num + 1,
                                'field_name': widget.field_name,
                                'field_type': widget.field_type,
                                'field_value': widget.field_value,
                                'rect': list(widget.rect)
                            }
                            data['forms'].append(field_data)
                            widget = widget.next
                        except Exception as e:
                            logger.warning(f"Could not extract form field from page {page_num + 1}: {e}")
                            break
            
            doc.close()
            
        except Exception as e:
            logger.error(f"Error with PyMuPDF extraction: {e}")
            data['error'] = str(e)
        
        return data
    
    def _analyze_character_formatting(self, chars: List[Dict]) -> List[Dict]:
        """Analyze character-level formatting to detect subscripts/superscripts."""
        formatting_info = []
        
        if not chars:
            return formatting_info
        
        # Group characters by line and analyze vertical positions
        lines = {}
        for char in chars:
            y_pos = round(char.get('y0', 0), 1)  # Round to avoid floating point issues
            if y_pos not in lines:
                lines[y_pos] = []
            lines[y_pos].append(char)
        
        # Analyze each line for formatting
        for y_pos, line_chars in lines.items():
            if not line_chars:
                continue
                
            # Calculate baseline (most common y position)
            y_positions = [char.get('y0', 0) for char in line_chars]
            baseline = max(set(y_positions), key=y_positions.count)
            
            # Detect super/subscripts based on vertical offset and font size
            for char in line_chars:
                char_y = char.get('y0', 0)
                char_size = char.get('size', 0)
                char_text = char.get('text', '')
                
                formatting_type = 'normal'
                
                # Detect subscript (below baseline, often smaller)
                if char_y > baseline + 1:  # Allow small tolerance
                    formatting_type = 'subscript'
                # Detect superscript (above baseline, often smaller)
                elif char_y < baseline - 1:
                    formatting_type = 'superscript'
                
                # Additional check for font size
                if char_size > 0:
                    avg_size = sum(c.get('size', 0) for c in line_chars) / len(line_chars)
                    if char_size < avg_size * 0.8:  # Significantly smaller
                        if formatting_type == 'normal':
                            # Determine if it's super or sub based on position
                            if char_y < baseline:
                                formatting_type = 'superscript'
                            else:
                                formatting_type = 'subscript'
                
                if formatting_type != 'normal':
                    formatting_info.append({
                        'text': char_text,
                        'type': formatting_type,
                        'x': char.get('x0', 0),
                        'y': char_y,
                        'size': char_size,
                        'font': char.get('fontname', '')
                    })
        
        return formatting_info
    
    def extract_chemical_formulas(self, text: str) -> List[str]:
        """Extract chemical formulas from text using regex patterns."""
        # Pattern for chemical formulas (basic)
        chemical_pattern = r'[A-Z][a-z]?(?:\d+)?(?:[A-Z][a-z]?(?:\d+)?)*'
        
        # More specific patterns for common chemical notations
        patterns = [
            r'H[₀-₉]+',  # Hydrogen with subscripts
            r'[A-Z][a-z]?[₀-₉]+',  # Element with subscript numbers
            r'[A-Z][a-z]?₂[A-Z][a-z]?[₀-₉]*',  # Common compounds
            chemical_pattern
        ]
        
        formulas = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            formulas.extend(matches)
        
        # Remove duplicates and filter out single letters
        unique_formulas = list(set(f for f in formulas if len(f) > 1))
        return unique_formulas
    
    def preserve_formatting_in_text(self, text: str, formatting_info: List[Dict]) -> str:
        """Apply formatting markers to preserve subscripts/superscripts in plain text."""
        if not formatting_info:
            return text
        
        # Sort by position to maintain order
        formatting_info.sort(key=lambda x: (x.get('y', 0), x.get('x', 0)))
        
        formatted_text = text
        offset = 0
        
        for fmt in formatting_info:
            char_text = fmt['text']
            fmt_type = fmt['type']
            
            # Find the character in the text
            char_pos = formatted_text.find(char_text, offset)
            if char_pos != -1:
                if fmt_type == 'subscript':
                    replacement = f"_{char_text}"
                elif fmt_type == 'superscript':
                    replacement = f"^{char_text}"
                else:
                    replacement = char_text
                
                formatted_text = (formatted_text[:char_pos] + 
                                replacement + 
                                formatted_text[char_pos + len(char_text):])
                offset = char_pos + len(replacement)
        
        return formatted_text