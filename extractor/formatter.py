"""
Content formatter for preserving special formatting like subscripts, superscripts, and math symbols.
"""

import re
import html
import unicodedata
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)


class ContentFormatter:
    """Handles preservation and conversion of special formatting in extracted content."""
    
    def __init__(self):
        # Mapping between different notation systems
        self.subscript_map = {
            '0': '₀', '1': '₁', '2': '₂', '3': '₃', '4': '₄',
            '5': '₅', '6': '₆', '7': '₇', '8': '₈', '9': '₉',
            '+': '₊', '-': '₋', '=': '₌', '(': '₍', ')': '₎'
        }
        
        self.superscript_map = {
            '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴',
            '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹',
            '+': '⁺', '-': '⁻', '=': '⁼', '(': '⁽', ')': '⁾',
            'n': 'ⁿ', 'i': 'ⁱ'
        }
        
        self.reverse_subscript_map = {v: k for k, v in self.subscript_map.items()}
        self.reverse_superscript_map = {v: k for k, v in self.superscript_map.items()}
        
        # Common math symbols and their alternatives
        self.math_symbols = {
            'alpha': 'α', 'beta': 'β', 'gamma': 'γ', 'delta': 'δ',
            'epsilon': 'ε', 'zeta': 'ζ', 'eta': 'η', 'theta': 'θ',
            'iota': 'ι', 'kappa': 'κ', 'lambda': 'λ', 'mu': 'μ',
            'nu': 'ν', 'xi': 'ξ', 'omicron': 'ο', 'pi': 'π',
            'rho': 'ρ', 'sigma': 'σ', 'tau': 'τ', 'upsilon': 'υ',
            'phi': 'φ', 'chi': 'χ', 'psi': 'ψ', 'omega': 'ω',
            'Alpha': 'Α', 'Beta': 'Β', 'Gamma': 'Γ', 'Delta': 'Δ',
            'Epsilon': 'Ε', 'Zeta': 'Ζ', 'Eta': 'Η', 'Theta': 'Θ',
            'Iota': 'Ι', 'Kappa': 'Κ', 'Lambda': 'Λ', 'Mu': 'Μ',
            'Nu': 'Ν', 'Xi': 'Ξ', 'Omicron': 'Ο', 'Pi': 'Π',
            'Rho': 'Ρ', 'Sigma': 'Σ', 'Tau': 'Τ', 'Upsilon': 'Υ',
            'Phi': 'Φ', 'Chi': 'Χ', 'Psi': 'Ψ', 'Omega': 'Ω',
            'degree': '°', 'celsius': '℃', 'fahrenheit': '℉',
            'plus_minus': '±', 'multiply': '×', 'divide': '÷',
            'le': '≤', 'ge': '≥', 'ne': '≠', 'approx': '≈',
            'infinity': '∞', 'sum': '∑', 'product': '∏', 'integral': '∫'
        }
    
    def preserve_formatting(self, text: str, source_content: Dict[str, Any], formatting_type: str = 'auto') -> str:
        """
        Preserve formatting from source content in the extracted text.
        
        Args:
            text: Extracted text to format
            source_content: Original content with formatting information
            formatting_type: Type of formatting to preserve ('auto', 'html', 'unicode', 'latex', 'markdown')
            
        Returns:
            Formatted text with preserved formatting
        """
        if formatting_type == 'auto':
            formatting_type = self._detect_best_format_type(source_content)
        
        formatted_text = text
        
        # Apply formatting based on type
        if formatting_type == 'html':
            formatted_text = self._apply_html_formatting(formatted_text, source_content)
        elif formatting_type == 'unicode':
            formatted_text = self._apply_unicode_formatting(formatted_text, source_content)
        elif formatting_type == 'latex':
            formatted_text = self._apply_latex_formatting(formatted_text, source_content)
        elif formatting_type == 'markdown':
            formatted_text = self._apply_markdown_formatting(formatted_text, source_content)
        
        return formatted_text
    
    def _detect_best_format_type(self, source_content: Dict[str, Any]) -> str:
        """Detect the best formatting type based on source content."""
        content_data = source_content.get('content', {})
        
        # Check if we have PDF with formatting info
        if 'pages' in content_data and any('formatting' in page for page in content_data.get('pages', [])):
            return 'unicode'
        
        # Check if we have HTML content
        if 'raw_html' in content_data:
            return 'html'
        
        # Default to unicode for best compatibility
        return 'unicode'
    
    def _apply_html_formatting(self, text: str, source_content: Dict[str, Any]) -> str:
        """Apply HTML-based formatting preservation."""
        formatted_text = text
        
        # Convert common patterns to HTML
        # Subscripts: H2O -> H<sub>2</sub>O
        formatted_text = re.sub(r'([A-Za-z])(\d+)', r'\1<sub>\2</sub>', formatted_text)
        
        # Superscripts: E=mc^2 -> E=mc<sup>2</sup>
        formatted_text = re.sub(r'\^(\d+)', r'<sup>\1</sup>', formatted_text)
        
        # Degree symbol
        formatted_text = formatted_text.replace('°', '&deg;')
        
        return formatted_text
    
    def _apply_unicode_formatting(self, text: str, source_content: Dict[str, Any]) -> str:
        """Apply Unicode-based formatting preservation."""
        formatted_text = text
        
        # Check for PDF formatting information
        content_data = source_content.get('content', {})
        if 'pages' in content_data:
            formatted_text = self._apply_pdf_formatting(formatted_text, content_data)
        
        # Convert common notation to Unicode
        formatted_text = self._convert_to_unicode_subscripts(formatted_text)
        formatted_text = self._convert_to_unicode_superscripts(formatted_text)
        formatted_text = self._convert_math_symbols(formatted_text)
        
        return formatted_text
    
    def _apply_latex_formatting(self, text: str, source_content: Dict[str, Any]) -> str:
        """Apply LaTeX-based formatting preservation."""
        formatted_text = text
        
        # Convert to LaTeX notation
        # Subscripts: H2O -> H_{2}O
        formatted_text = re.sub(r'([A-Za-z])(\d+)', r'\1_{\\2}', formatted_text)
        
        # Superscripts: E=mc^2 -> E=mc^{2}
        formatted_text = re.sub(r'\^(\d+)', r'^{\\1}', formatted_text)
        
        # Greek letters
        for name, symbol in self.math_symbols.items():
            if symbol in formatted_text:
                formatted_text = formatted_text.replace(symbol, f'\\{name}')
        
        return formatted_text
    
    def _apply_markdown_formatting(self, text: str, source_content: Dict[str, Any]) -> str:
        """Apply Markdown-based formatting preservation."""
        formatted_text = text
        
        # Markdown doesn't have native sub/superscript, use HTML tags
        formatted_text = re.sub(r'([A-Za-z])(\d+)', r'\1<sub>\2</sub>', formatted_text)
        formatted_text = re.sub(r'\^(\d+)', r'<sup>\1</sup>', formatted_text)
        
        return formatted_text
    
    def _apply_pdf_formatting(self, text: str, content_data: Dict[str, Any]) -> str:
        """Apply formatting based on PDF character-level information."""
        formatted_text = text
        
        # Process each page's formatting information
        for page in content_data.get('pages', []):
            formatting_info = page.get('formatting', [])
            
            if not formatting_info:
                continue
            
            # Apply formatting based on character positions
            for fmt in formatting_info:
                char_text = fmt.get('text', '')
                fmt_type = fmt.get('type', '')
                
                if fmt_type == 'subscript' and char_text in self.subscript_map:
                    unicode_char = self.subscript_map[char_text]
                    formatted_text = formatted_text.replace(char_text, unicode_char)
                elif fmt_type == 'superscript' and char_text in self.superscript_map:
                    unicode_char = self.superscript_map[char_text]
                    formatted_text = formatted_text.replace(char_text, unicode_char)
        
        return formatted_text
    
    def _convert_to_unicode_subscripts(self, text: str) -> str:
        """Convert numeric subscripts to Unicode subscript characters."""
        # Pattern for chemical formulas like H2O, CO2, etc.
        def replace_subscript(match):
            element = match.group(1)
            numbers = match.group(2)
            unicode_numbers = ''.join(self.subscript_map.get(d, d) for d in numbers)
            return element + unicode_numbers
        
        # Match element followed by numbers
        pattern = r'([A-Z][a-z]?)(\d+)'
        return re.sub(pattern, replace_subscript, text)
    
    def _convert_to_unicode_superscripts(self, text: str) -> str:
        """Convert caret notation to Unicode superscript characters."""
        def replace_superscript(match):
            base = match.group(1)
            exponent = match.group(2)
            unicode_exponent = ''.join(self.superscript_map.get(c, c) for c in exponent)
            return base + unicode_exponent
        
        # Match base^exponent pattern
        pattern = r'([A-Za-z0-9)]+)\^([0-9+-]+)'
        return re.sub(pattern, replace_superscript, text)
    
    def _convert_math_symbols(self, text: str) -> str:
        """Convert text representations to Unicode math symbols."""
        converted_text = text
        
        # Replace named symbols
        for name, symbol in self.math_symbols.items():
            # Replace patterns like 'alpha', '[alpha]', '&alpha;'
            patterns = [
                f'\\b{name}\\b',
                f'\\[{name}\\]',
                f'&{name};'
            ]
            
            for pattern in patterns:
                converted_text = re.sub(pattern, symbol, converted_text, flags=re.IGNORECASE)
        
        return converted_text
    
    def normalize_formatting(self, text: str) -> str:
        """Normalize various formatting to a consistent form."""
        normalized = text
        
        # Convert HTML entities
        normalized = html.unescape(normalized)
        
        # Normalize Unicode
        normalized = unicodedata.normalize('NFKC', normalized)
        
        # Clean up whitespace
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        return normalized
    
    def convert_between_formats(self, text: str, from_format: str, to_format: str) -> str:
        """Convert text from one formatting system to another."""
        
        if from_format == to_format:
            return text
        
        converted = text
        
        # First, normalize to a standard form
        if from_format == 'html':
            converted = self._html_to_unicode(converted)
        elif from_format == 'latex':
            converted = self._latex_to_unicode(converted)
        
        # Then convert to target format
        if to_format == 'html':
            converted = self._unicode_to_html(converted)
        elif to_format == 'latex':
            converted = self._unicode_to_latex(converted)
        elif to_format == 'markdown':
            converted = self._unicode_to_markdown(converted)
        
        return converted
    
    def _html_to_unicode(self, text: str) -> str:
        """Convert HTML formatting to Unicode."""
        # Convert subscripts
        text = re.sub(r'<sub>(.*?)</sub>', lambda m: ''.join(self.subscript_map.get(c, c) for c in m.group(1)), text)
        
        # Convert superscripts
        text = re.sub(r'<sup>(.*?)</sup>', lambda m: ''.join(self.superscript_map.get(c, c) for c in m.group(1)), text)
        
        # Convert entities
        text = html.unescape(text)
        
        return text
    
    def _latex_to_unicode(self, text: str) -> str:
        """Convert LaTeX formatting to Unicode."""
        # Convert subscripts: _{text} -> unicode
        text = re.sub(r'_\{([^}]+)\}', lambda m: ''.join(self.subscript_map.get(c, c) for c in m.group(1)), text)
        
        # Convert superscripts: ^{text} -> unicode
        text = re.sub(r'\^\{([^}]+)\}', lambda m: ''.join(self.superscript_map.get(c, c) for c in m.group(1)), text)
        
        # Convert Greek letters
        for name, symbol in self.math_symbols.items():
            text = text.replace(f'\\{name}', symbol)
        
        return text
    
    def _unicode_to_html(self, text: str) -> str:
        """Convert Unicode formatting to HTML."""
        converted = text
        
        # Convert subscript characters to HTML
        for unicode_char, regular_char in self.reverse_subscript_map.items():
            converted = converted.replace(unicode_char, f'<sub>{regular_char}</sub>')
        
        # Convert superscript characters to HTML
        for unicode_char, regular_char in self.reverse_superscript_map.items():
            converted = converted.replace(unicode_char, f'<sup>{regular_char}</sup>')
        
        return converted
    
    def _unicode_to_latex(self, text: str) -> str:
        """Convert Unicode formatting to LaTeX."""
        converted = text
        
        # Convert subscript characters to LaTeX
        for unicode_char, regular_char in self.reverse_subscript_map.items():
            converted = converted.replace(unicode_char, f'_{{{regular_char}}}')
        
        # Convert superscript characters to LaTeX
        for unicode_char, regular_char in self.reverse_superscript_map.items():
            converted = converted.replace(unicode_char, f'^{{{regular_char}}}')
        
        # Convert math symbols to LaTeX commands
        for name, symbol in self.math_symbols.items():
            if symbol in converted:
                converted = converted.replace(symbol, f'\\{name}')
        
        return converted
    
    def _unicode_to_markdown(self, text: str) -> str:
        """Convert Unicode formatting to Markdown (using HTML tags)."""
        return self._unicode_to_html(text)
    
    def extract_formatting_metadata(self, text: str) -> Dict[str, Any]:
        """Extract metadata about formatting present in text."""
        metadata = {
            'has_subscripts': False,
            'has_superscripts': False,
            'has_greek_letters': False,
            'has_math_symbols': False,
            'subscript_chars': [],
            'superscript_chars': [],
            'greek_letters': [],
            'math_symbols_found': [],
            'formatting_complexity': 0
        }
        
        # Check for subscripts
        for char in text:
            if char in self.reverse_subscript_map:
                metadata['has_subscripts'] = True
                metadata['subscript_chars'].append(char)
        
        # Check for superscripts
        for char in text:
            if char in self.reverse_superscript_map:
                metadata['has_superscripts'] = True
                metadata['superscript_chars'].append(char)
        
        # Check for Greek letters and math symbols
        for name, symbol in self.math_symbols.items():
            if symbol in text:
                if 'alpha' <= name.lower() <= 'omega':
                    metadata['has_greek_letters'] = True
                    metadata['greek_letters'].append(symbol)
                else:
                    metadata['has_math_symbols'] = True
                    metadata['math_symbols_found'].append(symbol)
        
        # Calculate complexity score
        complexity = 0
        complexity += len(metadata['subscript_chars']) * 2
        complexity += len(metadata['superscript_chars']) * 2
        complexity += len(metadata['greek_letters']) * 3
        complexity += len(metadata['math_symbols_found']) * 3
        
        metadata['formatting_complexity'] = complexity
        
        return metadata