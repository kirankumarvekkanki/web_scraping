"""
AI-powered pattern suggestion for field extraction.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
import re

logger = logging.getLogger(__name__)


class PatternSuggester:
    """Suggest regex patterns for field extraction using AI assistance."""
    
    def __init__(self, openai_api_key: Optional[str] = None, model: str = "gpt-3.5-turbo"):
        self.openai_api_key = openai_api_key
        self.model = model
        self.client = None
        
        if openai_api_key:
            try:
                import openai
                self.client = openai.OpenAI(api_key=openai_api_key)
                logger.info("OpenAI client for pattern suggestion initialized")
            except ImportError:
                logger.warning("OpenAI library not available")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
    
    async def suggest_pattern(
        self,
        field_name: str,
        sample_values: List[str],
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Suggest a regex pattern for extracting a specific field.
        
        Args:
            field_name: Name of the field to extract
            sample_values: Example values that should match the pattern
            context: Additional context about the field
            
        Returns:
            Dictionary with suggested pattern and metadata
        """
        if not self.client:
            return self._suggest_simple_pattern(field_name, sample_values)
        
        try:
            prompt = self._create_pattern_prompt(field_name, sample_values, context)
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a regex expert. Create precise patterns for text extraction."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=300,
                temperature=0.2
            )
            
            content = response.choices[0].message.content.strip()
            return self._parse_pattern_response(content, sample_values)
            
        except Exception as e:
            logger.error(f"AI pattern suggestion failed: {e}")
            return self._suggest_simple_pattern(field_name, sample_values)
    
    def _create_pattern_prompt(
        self,
        field_name: str,
        sample_values: List[str],
        context: Optional[str]
    ) -> str:
        """Create a prompt for pattern suggestion."""
        
        samples_str = "\n".join([f"- {value}" for value in sample_values])
        
        prompt = f"""
Field Name: {field_name}
Context: {context or 'General field extraction'}

Sample Values to Match:
{samples_str}

Create a regex pattern that will match these sample values. 

Requirements:
1. The pattern should be precise but not overly restrictive
2. Consider common variations of the field type
3. Use proper regex syntax
4. Explain the pattern components
5. Provide confidence level (0.0-1.0)

Format your response as:
Pattern: [regex pattern]
Explanation: [brief explanation]
Confidence: [0.0-1.0]
Flags: [regex flags if needed]

Response:"""
        
        return prompt
    
    def _parse_pattern_response(self, response: str, sample_values: List[str]) -> Dict[str, Any]:
        """Parse the AI response and validate the pattern."""
        
        result = {
            'pattern': '',
            'explanation': '',
            'confidence': 0.5,
            'flags': [],
            'validated': False,
            'matches': []
        }
        
        try:
            lines = response.split('\n')
            
            for line in lines:
                line = line.strip()
                if line.startswith('Pattern:'):
                    result['pattern'] = line.replace('Pattern:', '').strip()
                elif line.startswith('Explanation:'):
                    result['explanation'] = line.replace('Explanation:', '').strip()
                elif line.startswith('Confidence:'):
                    try:
                        result['confidence'] = float(line.replace('Confidence:', '').strip())
                    except ValueError:
                        pass
                elif line.startswith('Flags:'):
                    flags_str = line.replace('Flags:', '').strip()
                    if flags_str and flags_str.lower() != 'none':
                        result['flags'] = [f.strip() for f in flags_str.split(',')]
            
            # Validate pattern against sample values
            if result['pattern']:
                result['validated'], result['matches'] = self._validate_pattern(
                    result['pattern'], sample_values, result['flags']
                )
            
        except Exception as e:
            logger.error(f"Failed to parse pattern response: {e}")
        
        return result
    
    def _validate_pattern(
        self,
        pattern: str,
        sample_values: List[str],
        flags: List[str]
    ) -> Tuple[bool, List[str]]:
        """Validate a pattern against sample values."""
        
        try:
            # Convert flag names to regex flags
            regex_flags = 0
            for flag in flags:
                if flag.upper() == 'IGNORECASE' or flag.upper() == 'I':
                    regex_flags |= re.IGNORECASE
                elif flag.upper() == 'MULTILINE' or flag.upper() == 'M':
                    regex_flags |= re.MULTILINE
                elif flag.upper() == 'DOTALL' or flag.upper() == 'S':
                    regex_flags |= re.DOTALL
            
            compiled_pattern = re.compile(pattern, regex_flags)
            matches = []
            successful_matches = 0
            
            for value in sample_values:
                match = compiled_pattern.search(value)
                if match:
                    matches.append(match.group(0))
                    successful_matches += 1
                else:
                    matches.append(None)
            
            # Consider it validated if at least 80% of samples match
            validation_threshold = max(1, len(sample_values) * 0.8)
            is_validated = successful_matches >= validation_threshold
            
            return is_validated, matches
            
        except re.error as e:
            logger.error(f"Invalid regex pattern '{pattern}': {e}")
            return False, []
        except Exception as e:
            logger.error(f"Pattern validation failed: {e}")
            return False, []
    
    def _suggest_simple_pattern(
        self,
        field_name: str,
        sample_values: List[str]
    ) -> Dict[str, Any]:
        """Create a simple pattern suggestion without AI."""
        
        # Analyze sample values to create a basic pattern
        if not sample_values:
            return {
                'pattern': r'.+',
                'explanation': 'Generic pattern - matches any text',
                'confidence': 0.3,
                'flags': [],
                'validated': False,
                'matches': []
            }
        
        # Look for common patterns
        field_lower = field_name.lower()
        
        if 'email' in field_lower:
            pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            explanation = 'Email address pattern'
        elif 'phone' in field_lower:
            pattern = r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b'
            explanation = 'Phone number pattern'
        elif 'date' in field_lower:
            pattern = r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b'
            explanation = 'Date pattern'
        elif 'price' in field_lower or 'cost' in field_lower:
            pattern = r'\$?\d{1,3}(?:,\d{3})*(?:\.\d{2})?'
            explanation = 'Price pattern'
        elif 'temperature' in field_lower:
            pattern = r'-?\d+(?:\.\d+)?°[CF]'
            explanation = 'Temperature pattern'
        else:
            # Create pattern based on sample characteristics
            pattern = self._analyze_samples_for_pattern(sample_values)
            explanation = 'Pattern based on sample analysis'
        
        validated, matches = self._validate_pattern(pattern, sample_values, [])
        
        return {
            'pattern': pattern,
            'explanation': explanation,
            'confidence': 0.7 if validated else 0.4,
            'flags': [],
            'validated': validated,
            'matches': matches
        }
    
    def _analyze_samples_for_pattern(self, sample_values: List[str]) -> str:
        """Analyze sample values to create a basic pattern."""
        
        if not sample_values:
            return r'.+'
        
        # Check if all samples are numeric
        all_numeric = all(value.replace('.', '').replace('-', '').isdigit() for value in sample_values)
        if all_numeric:
            return r'-?\d+(?:\.\d+)?'
        
        # Check if all samples are uppercase
        all_uppercase = all(value.isupper() for value in sample_values if value.isalpha())
        if all_uppercase:
            return r'[A-Z]+'
        
        # Check for common length
        lengths = [len(value) for value in sample_values]
        if len(set(lengths)) == 1:  # All same length
            length = lengths[0]
            return f'.{{{length}}}'
        
        # Default: flexible pattern
        return r'.+'
    
    async def suggest_multiple_patterns(
        self,
        content: str,
        target_fields: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Suggest patterns for multiple fields based on content analysis.
        
        Args:
            content: Source content to analyze
            target_fields: List of field names to create patterns for
            
        Returns:
            Dictionary mapping field names to pattern suggestions
        """
        suggestions = {}
        
        for field_name in target_fields:
            # Extract potential sample values from content
            sample_values = self._extract_sample_values(content, field_name)
            
            if sample_values:
                suggestion = await self.suggest_pattern(field_name, sample_values)
                suggestions[field_name] = suggestion
            else:
                # No samples found, create a generic suggestion
                suggestions[field_name] = self._suggest_simple_pattern(field_name, [])
        
        return suggestions
    
    def _extract_sample_values(self, content: str, field_name: str) -> List[str]:
        """Extract potential sample values for a field from content."""
        
        field_lower = field_name.lower()
        samples = []
        
        # Use simple heuristics to find relevant values
        if 'email' in field_lower:
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            samples = re.findall(email_pattern, content, re.IGNORECASE)
        elif 'phone' in field_lower:
            phone_pattern = r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b'
            samples = re.findall(phone_pattern, content)
        elif 'date' in field_lower:
            date_pattern = r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b'
            samples = re.findall(date_pattern, content)
        elif 'price' in field_lower:
            price_pattern = r'\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?'
            samples = re.findall(price_pattern, content)
        elif 'temperature' in field_lower:
            temp_pattern = r'-?\d+(?:\.\d+)?°[CF]'
            samples = re.findall(temp_pattern, content)
        
        # Limit to first 5 samples
        return samples[:5]