"""
AI Integration Module

Provides AI-enhanced features for content extraction and generation:
- Content validation and improvement
- Natural language generation from extracted data
- Context-aware field extraction
- Intelligent pattern suggestions
"""

from .content_enhancer import ContentEnhancer
from .text_generator import TextGenerator
from .pattern_suggester import PatternSuggester

__all__ = [
    'ContentEnhancer',
    'TextGenerator',
    'PatternSuggester'
]