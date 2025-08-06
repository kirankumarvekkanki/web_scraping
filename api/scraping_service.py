"""
Core scraping service that coordinates all components.
"""

import asyncio
import logging
from typing import Dict, Any

from ..crawler import ContentDetector
from ..extractor import FieldExtractor
from ..proxy import ProxyManager
from .models import ScrapeRequest

logger = logging.getLogger(__name__)


class ScrapingService:
    """Main service that coordinates crawling, extraction, and processing."""
    
    def __init__(self):
        self.content_detector = None
        self.field_extractor = None
        self.proxy_manager = None
        self.is_initialized = False
    
    async def initialize(self):
        """Initialize the scraping service."""
        if self.is_initialized:
            return
        
        logger.info("Initializing scraping service...")
        
        # Initialize components
        self.field_extractor = FieldExtractor(ai_enabled=True)
        self.content_detector = ContentDetector()
        
        # Initialize proxy manager if needed
        self.proxy_manager = ProxyManager()
        
        self.is_initialized = True
        logger.info("Scraping service initialized")
    
    async def cleanup(self):
        """Clean up resources."""
        if self.proxy_manager:
            await self.proxy_manager.stop()
        
        logger.info("Scraping service cleaned up")
    
    async def scrape(self, request: ScrapeRequest) -> Dict[str, Any]:
        """
        Perform scraping operation based on request.
        
        Args:
            request: Scraping request with URL and field specifications
            
        Returns:
            Scraping results with extracted data
        """
        if not self.is_initialized:
            await self.initialize()
        
        try:
            # Setup proxy manager if requested
            if request.use_proxy:
                if not self.proxy_manager.is_running:
                    if request.proxy_sources:
                        self.proxy_manager.proxy_sources = request.proxy_sources
                    await self.proxy_manager.start()
                
                self.content_detector.proxy_manager = self.proxy_manager
            
            # Prepare crawling options
            crawl_options = {
                'max_retries': request.max_retries,
                'delay': request.delay,
                'timeout': request.timeout
            }
            
            # Add JavaScript crawler options
            if request.crawler_type in ['js', 'auto']:
                crawl_options.update({
                    'headless': request.headless,
                    'browser_type': request.browser_type,
                    'wait_for_selector': request.wait_for_selector,
                    'wait_for_function': request.wait_for_function,
                    'additional_wait': request.additional_wait
                })
            
            # Add PDF crawler options
            if request.crawler_type in ['pdf', 'auto']:
                crawl_options.update({
                    'extract_images': request.extract_images,
                    'extract_tables': request.extract_tables
                })
            
            # Force specific crawler type if not auto
            if request.crawler_type != 'auto':
                crawl_options['force_crawler'] = request.crawler_type
            
            # Add custom headers
            if request.custom_headers:
                crawl_options['headers'] = request.custom_headers
            
            # Perform crawling
            logger.info(f"Crawling URL: {request.url}")
            crawl_result = await self.content_detector.crawl_auto(str(request.url), **crawl_options)
            
            if not crawl_result.get('success', False):
                return {
                    'success': False,
                    'error': crawl_result.get('error', 'Crawling failed'),
                    'fields': {},
                    'metadata': crawl_result.get('metadata', {})
                }
            
            # Prepare field specifications for extraction
            field_specs = {}
            for field_name, field_spec in request.fields.items():
                if isinstance(field_spec, str):
                    field_specs[field_name] = field_spec
                else:
                    # Convert FieldSpec object to dict
                    field_specs[field_name] = {
                        'pattern': field_spec.pattern,
                        'multiple': field_spec.multiple,
                        'max_matches': field_spec.max_matches,
                        'preserve_formatting': field_spec.preserve_formatting,
                        'formatting_type': field_spec.formatting_type,
                        'transform': field_spec.transform,
                        'context_keywords': field_spec.context_keywords,
                        'unique': field_spec.unique,
                        'include_alternatives': field_spec.include_alternatives,
                        'max_alternatives': field_spec.max_alternatives
                    }
            
            # Add schema validation if specified
            if request.schema_name:
                field_specs['schema'] = request.schema_name
            
            # Perform field extraction
            logger.info(f"Extracting fields: {list(field_specs.keys())}")
            
            if request.use_ai_enhancement:
                extraction_result = await self.field_extractor.extract_with_ai_enhancement(
                    crawl_result, field_specs, request.ai_prompt
                )
            else:
                extraction_result = await self.field_extractor.extract_fields(
                    crawl_result, field_specs
                )
            
            # Process output format
            result = self._format_output(extraction_result, request.output_format)
            
            # Add performance metadata
            result['metadata']['scraping_service'] = 'ScrapingService v1.0'
            result['metadata']['crawler_used'] = crawl_result.get('crawler_type', 'unknown')
            result['metadata']['proxy_used'] = request.use_proxy
            result['metadata']['ai_enhanced'] = request.use_ai_enhancement
            
            logger.info(f"Successfully scraped {request.url}")
            return result
            
        except Exception as e:
            logger.error(f"Scraping failed for {request.url}: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'fields': {},
                'metadata': {
                    'url': str(request.url),
                    'error_type': type(e).__name__
                }
            }
    
    def _format_output(self, extraction_result: Dict[str, Any], output_format: str) -> Dict[str, Any]:
        """Format extraction results based on requested output format."""
        
        if output_format == 'raw':
            return extraction_result
        
        elif output_format == 'text':
            # Convert to text format
            text_output = []
            for field_name, value in extraction_result.get('fields', {}).items():
                if value is not None:
                    text_output.append(f"{field_name}: {value}")
            
            return {
                'success': True,
                'text_content': '\n'.join(text_output),
                'metadata': extraction_result.get('metadata', {})
            }
        
        elif output_format == 'json':
            # Clean JSON format
            return {
                'success': extraction_result.get('metadata', {}).get('success', True),
                'url': extraction_result.get('metadata', {}).get('source_url', ''),
                'data': extraction_result.get('fields', {}),
                'extracted_at': extraction_result.get('metadata', {}).get('extraction_timestamp')
            }
        
        else:  # structured (default)
            return extraction_result
    
    async def validate_url(self, url: str) -> Dict[str, Any]:
        """Validate if a URL is accessible and determine content type."""
        try:
            content_type = await self.content_detector.detect_content_type(url)
            
            return {
                'valid': True,
                'content_type': content_type,
                'url': url
            }
        except Exception as e:
            return {
                'valid': False,
                'error': str(e),
                'url': url
            }
    
    async def get_available_patterns(self) -> Dict[str, str]:
        """Get all available built-in patterns."""
        if not self.field_extractor:
            self.field_extractor = FieldExtractor()
        
        return self.field_extractor.get_builtin_patterns()
    
    async def test_pattern(self, pattern: str, test_text: str) -> Dict[str, Any]:
        """Test a regex pattern against sample text."""
        if not self.field_extractor:
            self.field_extractor = FieldExtractor()
        
        try:
            matches = self.field_extractor.pattern_matcher.find_matches(test_text, pattern)
            
            return {
                'success': True,
                'pattern': pattern,
                'matches_found': len(matches),
                'matches': [
                    {
                        'value': match['match'],
                        'position': (match['start'], match['end']),
                        'confidence': match['confidence']
                    }
                    for match in matches[:10]  # Limit to first 10 matches
                ]
            }
        except Exception as e:
            return {
                'success': False,
                'pattern': pattern,
                'error': str(e)
            }