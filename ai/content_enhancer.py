"""
AI-powered content enhancement and validation.
"""

import logging
from typing import Dict, Any, List, Optional
import json

logger = logging.getLogger(__name__)


class ContentEnhancer:
    """AI-powered content enhancement and validation."""
    
    def __init__(self, openai_api_key: Optional[str] = None, model: str = "gpt-3.5-turbo"):
        self.openai_api_key = openai_api_key
        self.model = model
        self.client = None
        
        if openai_api_key:
            try:
                import openai
                self.client = openai.OpenAI(api_key=openai_api_key)
                logger.info("OpenAI client initialized successfully")
            except ImportError:
                logger.warning("OpenAI library not available. Install with: pip install openai")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
    
    async def enhance_extraction_results(
        self, 
        extracted_data: Dict[str, Any], 
        original_content: str,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Enhance extraction results using AI validation and improvement.
        
        Args:
            extracted_data: Originally extracted field data
            original_content: Source content that was scraped
            context: Additional context about the extraction task
            
        Returns:
            Enhanced extraction results with improved accuracy
        """
        if not self.client:
            logger.debug("AI enhancement not available - returning original data")
            return extracted_data
        
        try:
            enhanced_data = extracted_data.copy()
            
            # Enhance each field
            for field_name, field_value in extracted_data.items():
                if field_value and isinstance(field_value, (str, list)):
                    enhanced_value = await self._enhance_field_value(
                        field_name, field_value, original_content, context
                    )
                    if enhanced_value != field_value:
                        enhanced_data[field_name] = enhanced_value
                        logger.debug(f"Enhanced field '{field_name}': {field_value} -> {enhanced_value}")
            
            return enhanced_data
            
        except Exception as e:
            logger.error(f"AI enhancement failed: {e}")
            return extracted_data
    
    async def _enhance_field_value(
        self,
        field_name: str,
        field_value: Any,
        original_content: str,
        context: Optional[str] = None
    ) -> Any:
        """Enhance a specific field value using AI."""
        
        try:
            # Create enhancement prompt
            prompt = self._create_enhancement_prompt(
                field_name, field_value, original_content, context
            )
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert data extraction assistant. Validate and improve extracted field values."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=200,
                temperature=0.1
            )
            
            enhanced_value = response.choices[0].message.content.strip()
            
            # Try to parse as JSON if it looks like structured data
            if enhanced_value.startswith('[') or enhanced_value.startswith('{'):
                try:
                    enhanced_value = json.loads(enhanced_value)
                except json.JSONDecodeError:
                    pass
            
            return enhanced_value
            
        except Exception as e:
            logger.error(f"Failed to enhance field '{field_name}': {e}")
            return field_value
    
    def _create_enhancement_prompt(
        self,
        field_name: str,
        field_value: Any,
        original_content: str,
        context: Optional[str] = None
    ) -> str:
        """Create a prompt for AI enhancement."""
        
        # Truncate content if too long
        content_preview = original_content[:1000] + "..." if len(original_content) > 1000 else original_content
        
        prompt = f"""
Field Name: {field_name}
Extracted Value: {field_value}
Context: {context or 'General web scraping'}

Source Content Preview:
{content_preview}

Task: Validate and improve the extracted value for the field '{field_name}'. 

Guidelines:
1. Check if the extracted value makes sense given the field name
2. Correct obvious errors in formatting or content
3. For chemical formulas, ensure proper formatting with subscripts/superscripts
4. For dates, use standard formats
5. For lists, ensure proper JSON array format
6. If the value is clearly wrong, try to find the correct value in the source content
7. Return only the improved value, no explanation

Improved Value:"""
        
        return prompt
    
    async def validate_chemical_formulas(self, formulas: List[str]) -> Dict[str, Any]:
        """Validate chemical formulas using AI knowledge."""
        if not self.client or not formulas:
            return {"valid": [], "invalid": [], "suggestions": []}
        
        try:
            prompt = f"""
Validate these chemical formulas and provide corrections if needed:
{', '.join(formulas)}

Return a JSON object with:
- "valid": list of valid formulas
- "invalid": list of invalid formulas with corrections
- "suggestions": list of possible improvements

Focus on:
1. Proper element symbols (capitalization)
2. Correct subscript/superscript notation
3. Balanced equations
4. Common compound recognition

JSON Response:"""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a chemistry expert. Validate chemical formulas and provide corrections."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=500,
                temperature=0.1
            )
            
            result = json.loads(response.choices[0].message.content.strip())
            return result
            
        except Exception as e:
            logger.error(f"Chemical formula validation failed: {e}")
            return {"valid": formulas, "invalid": [], "suggestions": []}
    
    async def suggest_missing_fields(
        self, 
        content: str, 
        existing_fields: List[str],
        domain: Optional[str] = None
    ) -> List[str]:
        """Suggest additional fields that could be extracted from content."""
        if not self.client:
            return []
        
        try:
            content_preview = content[:1500] + "..." if len(content) > 1500 else content
            
            prompt = f"""
Content Preview:
{content_preview}

Currently Extracted Fields: {', '.join(existing_fields)}
Domain: {domain or 'General'}

Analyze the content and suggest 3-5 additional fields that could be extracted. 
Consider the domain context and look for commonly missed but valuable data.

Return only a JSON array of field names:
["field1", "field2", "field3"]

Suggested Fields:"""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a data extraction expert. Identify valuable fields that can be extracted from content."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=200,
                temperature=0.3
            )
            
            suggestions = json.loads(response.choices[0].message.content.strip())
            return suggestions if isinstance(suggestions, list) else []
            
        except Exception as e:
            logger.error(f"Field suggestion failed: {e}")
            return []
    
    async def improve_confidence_scores(
        self,
        field_results: Dict[str, Any],
        content: str
    ) -> Dict[str, float]:
        """Use AI to improve confidence scores for extracted fields."""
        if not self.client:
            return {}
        
        try:
            # Analyze each field for context relevance
            improved_scores = {}
            
            for field_name, field_value in field_results.items():
                if field_value:
                    score = await self._assess_field_confidence(
                        field_name, field_value, content
                    )
                    improved_scores[field_name] = score
            
            return improved_scores
            
        except Exception as e:
            logger.error(f"Confidence score improvement failed: {e}")
            return {}
    
    async def _assess_field_confidence(
        self,
        field_name: str,
        field_value: Any,
        content: str
    ) -> float:
        """Assess confidence for a specific field using AI."""
        try:
            content_preview = content[:800] + "..." if len(content) > 800 else content
            
            prompt = f"""
Field: {field_name}
Value: {field_value}
Content: {content_preview}

Rate the confidence (0.0-1.0) that this extracted value is correct for this field name given the source content.

Consider:
1. Does the value match the field name semantically?
2. Is the value present in the content?
3. Is the formatting appropriate?
4. Does the context support this extraction?

Return only a number between 0.0 and 1.0:"""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a data quality expert. Assess extraction confidence scores."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=50,
                temperature=0.1
            )
            
            score_str = response.choices[0].message.content.strip()
            score = float(score_str)
            return max(0.0, min(1.0, score))
            
        except Exception as e:
            logger.error(f"Failed to assess confidence for {field_name}: {e}")
            return 0.5  # Default moderate confidence