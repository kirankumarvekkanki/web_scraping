"""
Advanced pattern matching with regex and context analysis.
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple
import unicodedata

logger = logging.getLogger(__name__)


class PatternMatcher:
    """Advanced pattern matching with context awareness and confidence scoring."""
    
    def __init__(self):
        self.context_window = 100  # Characters around match for context
        
        # Unicode patterns for special characters common in scientific texts
        self.unicode_patterns = {
            'subscripts': r'[₀₁₂₃₄₅₆₇₈₉]',
            'superscripts': r'[⁰¹²³⁴⁵⁶⁷⁸⁹]',
            'greek_letters': r'[αβγδεζηθικλμνξοπρστυφχψω]',
            'math_symbols': r'[±×÷≤≥≠≈∞∑∏∫∂∇∆∀∃∈∉⊂⊃∪∩]',
            'arrows': r'[←→↑↓↔↕⇐⇒⇑⇓⇔⇕]',
            'chemical_bonds': r'[–—≡]',
            'degrees': r'[°℃℉]'
        }
    
    def find_matches(self, text: str, pattern: str, flags: int = 0, max_matches: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Find all matches of a pattern in text with context and confidence.
        
        Args:
            text: Text to search in
            pattern: Regex pattern to match
            flags: Regex flags
            max_matches: Maximum number of matches to return
            
        Returns:
            List of match dictionaries with metadata
        """
        matches = []
        
        try:
            # Compile regex with flags
            regex = re.compile(pattern, flags | re.UNICODE)
            
            # Find all matches with positions
            for match_obj in regex.finditer(text):
                match_info = {
                    'match': match_obj.group(0),
                    'groups': match_obj.groups(),
                    'named_groups': match_obj.groupdict(),
                    'start': match_obj.start(),
                    'end': match_obj.end(),
                    'pattern': pattern,
                    'context': self._extract_context(text, match_obj.start(), match_obj.end()),
                    'confidence': self._calculate_match_confidence(match_obj, text, pattern),
                    'position': match_obj.start()
                }
                
                # Add formatting analysis
                match_info['formatting'] = self._analyze_formatting(match_obj.group(0))
                
                matches.append(match_info)
                
                # Stop if we've reached max matches
                if max_matches and len(matches) >= max_matches:
                    break
                    
        except re.error as e:
            logger.error(f"Invalid regex pattern '{pattern}': {e}")
            return []
        
        return matches
    
    def find_fuzzy_matches(self, text: str, target: str, threshold: float = 0.8) -> List[Dict[str, Any]]:
        """
        Find fuzzy matches using similarity scoring.
        
        Args:
            text: Text to search in
            target: Target string to find similar matches for
            threshold: Minimum similarity score (0.0 to 1.0)
            
        Returns:
            List of fuzzy match dictionaries
        """
        import difflib
        
        matches = []
        words = text.split()
        target_words = target.split()
        
        # Create sliding windows of same length as target
        window_size = len(target_words)
        
        for i in range(len(words) - window_size + 1):
            window = ' '.join(words[i:i + window_size])
            similarity = difflib.SequenceMatcher(None, target.lower(), window.lower()).ratio()
            
            if similarity >= threshold:
                # Find position in original text
                start_pos = text.lower().find(window.lower())
                if start_pos != -1:
                    end_pos = start_pos + len(window)
                    
                    matches.append({
                        'match': window,
                        'similarity': similarity,
                        'start': start_pos,
                        'end': end_pos,
                        'context': self._extract_context(text, start_pos, end_pos),
                        'confidence': similarity
                    })
        
        # Sort by similarity score
        matches.sort(key=lambda x: x['similarity'], reverse=True)
        return matches
    
    def extract_structured_data(self, text: str, patterns: Dict[str, str]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Extract multiple structured fields at once.
        
        Args:
            text: Text to extract from
            patterns: Dictionary of field_name -> pattern
            
        Returns:
            Dictionary of field_name -> list of matches
        """
        results = {}
        
        for field_name, pattern in patterns.items():
            matches = self.find_matches(text, pattern)
            results[field_name] = matches
        
        return results
    
    def find_chemical_formulas(self, text: str) -> List[Dict[str, Any]]:
        """Specialized method for finding chemical formulas with proper formatting."""
        
        # Enhanced chemical formula patterns
        patterns = {
            'simple_formula': r'[A-Z][a-z]?(?:\d+)?(?:[A-Z][a-z]?(?:\d+)?)*',
            'subscript_formula': r'[A-Z][a-z]?[₀-₉]*(?:[A-Z][a-z]?[₀-₉]*)*',
            'complex_formula': r'(?:[A-Z][a-z]?(?:\d+|[₀-₉]+)?)+(?:[-·](?:[A-Z][a-z]?(?:\d+|[₀-₉]+)?)+)*',
            'ionic_formula': r'\[(?:[A-Z][a-z]?(?:\d+|[₀-₉]+)?)+\](?:\d+|[₀-₉]+)?[-+]',
            'hydrated_formula': r'[A-Z][a-z]?(?:\d+|[₀-₉]+)?(?:[A-Z][a-z]?(?:\d+|[₀-₉]+)?)*·(?:\d+|[₀-₉]+)?H(?:\d+|[₀-₉]+)?O'
        }
        
        all_formulas = []
        
        for formula_type, pattern in patterns.items():
            matches = self.find_matches(text, pattern)
            for match in matches:
                match['formula_type'] = formula_type
                match['normalized'] = self._normalize_chemical_formula(match['match'])
                all_formulas.append(match)
        
        # Remove duplicates and sort by confidence
        unique_formulas = []
        seen_formulas = set()
        
        for formula in sorted(all_formulas, key=lambda x: x['confidence'], reverse=True):
            normalized = formula['normalized']
            if normalized not in seen_formulas and len(normalized) > 1:
                seen_formulas.add(normalized)
                unique_formulas.append(formula)
        
        return unique_formulas
    
    def find_scientific_notation(self, text: str) -> List[Dict[str, Any]]:
        """Find numbers in scientific notation."""
        patterns = {
            'standard': r'[-+]?\d(?:\.\d+)?[eE][-+]?\d+',
            'unicode_super': r'[-+]?\d(?:\.\d+)?\s*[×x]\s*10[⁰¹²³⁴⁵⁶⁷⁸⁹-]+',
            'caret_notation': r'[-+]?\d(?:\.\d+)?\s*[×x]\s*10\^[-+]?\d+'
        }
        
        all_matches = []
        for notation_type, pattern in patterns.items():
            matches = self.find_matches(text, pattern)
            for match in matches:
                match['notation_type'] = notation_type
                match['numeric_value'] = self._parse_scientific_notation(match['match'])
                all_matches.append(match)
        
        return all_matches
    
    def _extract_context(self, text: str, start: int, end: int) -> str:
        """Extract context around a match."""
        context_start = max(0, start - self.context_window)
        context_end = min(len(text), end + self.context_window)
        
        context = text[context_start:context_end]
        
        # Mark the actual match within context
        match_start_in_context = start - context_start
        match_end_in_context = end - context_start
        
        return {
            'full_context': context,
            'before': context[:match_start_in_context],
            'match': context[match_start_in_context:match_end_in_context],
            'after': context[match_end_in_context:],
            'match_position_in_context': (match_start_in_context, match_end_in_context)
        }
    
    def _calculate_match_confidence(self, match_obj: re.Match, text: str, pattern: str) -> float:
        """Calculate confidence score for a match."""
        confidence = 1.0
        
        # Pattern complexity factor
        pattern_complexity = len(pattern) / 100.0  # Normalize
        confidence *= (1.0 + min(pattern_complexity, 0.5))
        
        # Match length factor
        match_length = len(match_obj.group(0))
        if match_length < 2:
            confidence *= 0.5
        elif match_length > 10:
            confidence *= 1.2
        
        # Context quality factor
        context = self._extract_context(text, match_obj.start(), match_obj.end())
        before_words = len(context['before'].split())
        after_words = len(context['after'].split())
        
        if before_words > 0 and after_words > 0:
            confidence *= 1.1
        
        # Position factor (matches near beginning might be more important)
        position_factor = 1.0 - (match_obj.start() / len(text)) * 0.1
        confidence *= position_factor
        
        return min(confidence, 1.0)
    
    def _analyze_formatting(self, match_text: str) -> Dict[str, Any]:
        """Analyze formatting characteristics of matched text."""
        formatting = {
            'has_subscripts': bool(re.search(self.unicode_patterns['subscripts'], match_text)),
            'has_superscripts': bool(re.search(self.unicode_patterns['superscripts'], match_text)),
            'has_greek_letters': bool(re.search(self.unicode_patterns['greek_letters'], match_text)),
            'has_math_symbols': bool(re.search(self.unicode_patterns['math_symbols'], match_text)),
            'has_special_chars': bool(re.search(r'[^\w\s]', match_text)),
            'is_uppercase': match_text.isupper(),
            'is_lowercase': match_text.islower(),
            'is_title_case': match_text.istitle(),
            'char_count': len(match_text),
            'unicode_categories': list(set(unicodedata.category(c) for c in match_text))
        }
        
        return formatting
    
    def _normalize_chemical_formula(self, formula: str) -> str:
        """Normalize chemical formula for comparison."""
        # Convert subscript numbers to regular numbers
        subscript_map = str.maketrans('₀₁₂₃₄₅₆₇₈₉', '0123456789')
        normalized = formula.translate(subscript_map)
        
        # Remove extra whitespace
        normalized = re.sub(r'\s+', '', normalized)
        
        return normalized
    
    def _parse_scientific_notation(self, notation: str) -> float:
        """Parse scientific notation string to float."""
        try:
            # Clean up the notation
            clean_notation = notation.replace('×', 'e').replace('x', 'e')
            
            # Handle unicode superscripts
            if '10' in clean_notation and any(c in clean_notation for c in '⁰¹²³⁴⁵⁶⁷⁸⁹'):
                # Convert unicode superscripts to regular notation
                superscript_map = str.maketrans('⁰¹²³⁴⁵⁶⁷⁸⁹', '0123456789')
                clean_notation = clean_notation.translate(superscript_map)
                clean_notation = re.sub(r'10([0-9-]+)', r'e\1', clean_notation)
            
            # Handle caret notation
            clean_notation = re.sub(r'10\^', 'e', clean_notation)
            
            # Remove spaces around 'e'
            clean_notation = re.sub(r'\s*e\s*', 'e', clean_notation)
            
            return float(clean_notation)
        except (ValueError, TypeError):
            return 0.0
    
    def get_unicode_pattern(self, pattern_name: str) -> str:
        """Get a unicode pattern by name."""
        return self.unicode_patterns.get(pattern_name, '')
    
    def add_unicode_pattern(self, name: str, pattern: str) -> None:
        """Add a custom unicode pattern."""
        self.unicode_patterns[name] = pattern