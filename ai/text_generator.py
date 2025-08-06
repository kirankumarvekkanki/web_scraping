"""
AI-powered text generation from extracted data.
"""

import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class TextGenerator:
    """Generate natural language text from extracted data."""
    
    def __init__(self, openai_api_key: Optional[str] = None, model: str = "gpt-3.5-turbo"):
        self.openai_api_key = openai_api_key
        self.model = model
        self.client = None
        
        if openai_api_key:
            try:
                import openai
                self.client = openai.OpenAI(api_key=openai_api_key)
                logger.info("OpenAI client for text generation initialized")
            except ImportError:
                logger.warning("OpenAI library not available")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
    
    async def generate_summary(
        self, 
        extracted_data: Dict[str, Any],
        template: Optional[str] = None,
        style: str = "professional"
    ) -> str:
        """
        Generate a natural language summary from extracted data.
        
        Args:
            extracted_data: Dictionary of extracted field values
            template: Optional template for the summary format
            style: Writing style (professional, casual, technical, scientific)
            
        Returns:
            Generated summary text
        """
        if not self.client:
            return self._generate_simple_summary(extracted_data)
        
        try:
            prompt = self._create_summary_prompt(extracted_data, template, style)
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": f"You are a skilled writer. Generate clear, {style} summaries from structured data."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=300,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"AI summary generation failed: {e}")
            return self._generate_simple_summary(extracted_data)
    
    def _generate_simple_summary(self, extracted_data: Dict[str, Any]) -> str:
        """Generate a simple summary without AI."""
        summary_parts = []
        
        for field, value in extracted_data.items():
            if value:
                if isinstance(value, list):
                    if len(value) == 1:
                        summary_parts.append(f"The {field} is {value[0]}")
                    elif len(value) > 1:
                        summary_parts.append(f"The {field} include {', '.join(map(str, value[:3]))}")
                else:
                    summary_parts.append(f"The {field} is {value}")
        
        return ". ".join(summary_parts) + "."
    
    def _create_summary_prompt(
        self,
        extracted_data: Dict[str, Any],
        template: Optional[str],
        style: str
    ) -> str:
        """Create a prompt for summary generation."""
        
        data_str = "\n".join([f"- {field}: {value}" for field, value in extracted_data.items() if value])
        
        if template:
            prompt = f"""
Template: {template}
Data:
{data_str}

Using the above template and data, generate a {style} summary. Fill in the template with the extracted data where appropriate.

Summary:"""
        else:
            prompt = f"""
Extracted Data:
{data_str}

Generate a coherent, {style} summary paragraph from this extracted data. Make it flow naturally and include all relevant information.

Summary:"""
        
        return prompt
    
    async def generate_sentences(
        self,
        extracted_data: Dict[str, Any],
        sentence_count: int = 3,
        focus_fields: Optional[List[str]] = None
    ) -> List[str]:
        """
        Generate individual sentences from extracted data.
        
        Args:
            extracted_data: Dictionary of extracted field values
            sentence_count: Number of sentences to generate
            focus_fields: Specific fields to focus on
            
        Returns:
            List of generated sentences
        """
        if not self.client:
            return self._generate_simple_sentences(extracted_data, sentence_count)
        
        try:
            # Filter data if focus fields specified
            if focus_fields:
                filtered_data = {k: v for k, v in extracted_data.items() if k in focus_fields}
            else:
                filtered_data = extracted_data
            
            data_str = "\n".join([f"- {field}: {value}" for field, value in filtered_data.items() if value])
            
            prompt = f"""
Data:
{data_str}

Generate {sentence_count} clear, informative sentences from this data. Each sentence should focus on different aspects of the information.

Requirements:
1. Make each sentence self-contained
2. Use proper formatting for chemical formulas, temperatures, etc.
3. Vary sentence structure
4. Be factual and precise

Sentences:"""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a technical writer. Create clear, factual sentences from structured data."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=400,
                temperature=0.6
            )
            
            content = response.choices[0].message.content.strip()
            sentences = [s.strip() for s in content.split('\n') if s.strip()]
            
            # Remove numbered prefixes if present
            sentences = [self._clean_sentence(s) for s in sentences]
            
            return sentences[:sentence_count]
            
        except Exception as e:
            logger.error(f"AI sentence generation failed: {e}")
            return self._generate_simple_sentences(extracted_data, sentence_count)
    
    def _generate_simple_sentences(self, extracted_data: Dict[str, Any], count: int) -> List[str]:
        """Generate simple sentences without AI."""
        sentences = []
        
        for field, value in list(extracted_data.items())[:count]:
            if value:
                if isinstance(value, list) and value:
                    sentences.append(f"The {field} found include {', '.join(map(str, value[:2]))}.")
                else:
                    sentences.append(f"The {field} is {value}.")
        
        return sentences
    
    def _clean_sentence(self, sentence: str) -> str:
        """Clean up a generated sentence."""
        # Remove numbered prefixes (1. 2. etc.)
        import re
        sentence = re.sub(r'^\d+\.\s*', '', sentence)
        sentence = re.sub(r'^\-\s*', '', sentence)
        
        # Ensure sentence ends with period
        if sentence and not sentence.endswith('.'):
            sentence += '.'
        
        return sentence
    
    async def generate_scientific_description(
        self,
        chemical_data: Dict[str, Any]
    ) -> str:
        """Generate a scientific description for chemical/scientific data."""
        if not self.client:
            return self._generate_simple_scientific_description(chemical_data)
        
        try:
            prompt = f"""
Chemical/Scientific Data:
{chemical_data}

Generate a scientific description that includes:
1. Chemical formula with proper formatting
2. Physical properties (temperature, concentration, etc.)
3. Scientific context and significance
4. Proper chemical nomenclature

Write in a professional scientific style suitable for academic or research contexts.

Description:"""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a scientific writer with expertise in chemistry and research documentation."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=400,
                temperature=0.5
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Scientific description generation failed: {e}")
            return self._generate_simple_scientific_description(chemical_data)
    
    def _generate_simple_scientific_description(self, chemical_data: Dict[str, Any]) -> str:
        """Generate a simple scientific description without AI."""
        description_parts = []
        
        # Handle chemical formulas
        if 'chemical_formula' in chemical_data or 'molecular_formula' in chemical_data:
            formula = chemical_data.get('chemical_formula') or chemical_data.get('molecular_formula')
            description_parts.append(f"The compound {formula}")
        
        # Handle temperatures
        if 'temperature' in chemical_data:
            temp = chemical_data['temperature']
            description_parts.append(f"at {temp}")
        
        # Handle concentrations
        if 'concentration' in chemical_data:
            conc = chemical_data['concentration']
            description_parts.append(f"with concentration {conc}")
        
        if description_parts:
            return " ".join(description_parts) + " represents the chemical system under study."
        else:
            return "Chemical data extracted from the source material."