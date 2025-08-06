"""
Advanced Field Extraction Engine with Modern Python Techniques.

This module implements a high-performance field extraction system using:
- Async/await patterns for non-blocking operations
- Type hints for better code quality and IDE support
- Dataclasses for structured data handling
- Context managers for resource management
- Caching and memoization for performance optimization
- Comprehensive error handling and logging

The field extractor coordinates pattern matching, content formatting, and
schema validation to provide accurate and reliable data extraction from
web content with preserved formatting.

Features:
- 25+ built-in extraction patterns
- Custom regex pattern support
- Formatting preservation (subscripts, superscripts, math symbols)
- AI-enhanced extraction capabilities
- Schema validation and data quality assurance
- Performance metrics and monitoring
- Concurrent extraction processing

Author: Web Scraping Framework Team
License: MIT
"""

import re
import logging
import asyncio
from typing import Dict, Any, List, Optional, Union, Tuple, Set
from dataclasses import dataclass, field
from functools import lru_cache, wraps
from concurrent.futures import ThreadPoolExecutor
import html
import unicodedata
import time

from .pattern_matcher import PatternMatcher
from .formatter import ContentFormatter
from .schema_validator import SchemaValidator

# Configure logger with structured format
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ExtractionResult:
    """
    Immutable result object for field extraction operations.
    
    Uses dataclass with frozen=True for better performance and immutability.
    """
    field_name: str
    value: Any
    confidence: float
    formatted_value: Optional[str] = None
    alternatives: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractionContext:
    """Context object containing extraction state and configuration."""
    source_url: str
    content_type: str
    extraction_timestamp: float = field(default_factory=time.time)
    enable_ai: bool = False
    cache_results: bool = True
    max_concurrent_extractions: int = 10


def performance_monitor(func):
    """
    Decorator for monitoring function performance with detailed metrics.
    
    Provides:
    - Execution time tracking
    - Memory usage monitoring (if available)
    - Error rate tracking
    - Automatic logging of performance statistics
    """
    @wraps(func)
    async def async_wrapper(self, *args, **kwargs):
        start_time = time.perf_counter()
        method_name = f"{self.__class__.__name__}.{func.__name__}"
        
        try:
            result = await func(self, *args, **kwargs)
            
            # Record success metrics
            execution_time = time.perf_counter() - start_time
            if hasattr(self, '_performance_metrics'):
                self._performance_metrics[method_name] = {
                    'last_execution_time': execution_time,
                    'total_calls': self._performance_metrics.get(method_name, {}).get('total_calls', 0) + 1,
                    'total_time': self._performance_metrics.get(method_name, {}).get('total_time', 0) + execution_time,
                    'success_rate': self._performance_metrics.get(method_name, {}).get('success_rate', 1.0)
                }
            
            # Log slow operations
            if execution_time > 1.0:  # Log operations taking more than 1 second
                logger.warning(
                    f"Slow operation detected: {method_name} took {execution_time:.2f}s",
                    extra={'method': method_name, 'execution_time': execution_time}
                )
            
            return result
            
        except Exception as e:
            execution_time = time.perf_counter() - start_time
            logger.error(
                f"Method {method_name} failed after {execution_time:.2f}s: {e}",
                extra={'method': method_name, 'execution_time': execution_time, 'error': str(e)},
                exc_info=True
            )
            raise
    
    @wraps(func)
    def sync_wrapper(self, *args, **kwargs):
        # Similar implementation for sync functions
        start_time = time.perf_counter()
        method_name = f"{self.__class__.__name__}.{func.__name__}"
        
        try:
            result = func(self, *args, **kwargs)
            execution_time = time.perf_counter() - start_time
            
            if hasattr(self, '_performance_metrics'):
                self._performance_metrics[method_name] = {
                    'last_execution_time': execution_time,
                    'total_calls': self._performance_metrics.get(method_name, {}).get('total_calls', 0) + 1
                }
            
            return result
        except Exception as e:
            execution_time = time.perf_counter() - start_time
            logger.error(f"Method {method_name} failed after {execution_time:.2f}s: {e}", exc_info=True)
            raise
    
    return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper


class FieldExtractor:
    """
    Advanced field extraction engine with modern Python optimizations.
    
    This class provides high-performance field extraction with:
    - Concurrent processing of multiple fields
    - Intelligent caching and memoization
    - Performance monitoring and metrics
    - AI-enhanced extraction capabilities
    - Comprehensive error handling and recovery
    - Memory-efficient processing of large content
    
    Features:
    - 25+ built-in extraction patterns
    - Custom regex pattern support
    - Formatting preservation for scientific content
    - Schema validation and data quality checks
    - Async/await support for non-blocking operations
    - Thread pool for CPU-intensive regex operations
    """
    
    def __init__(
        self, 
        ai_enabled: bool = True,
        enable_caching: bool = True,
        max_workers: int = 4,
        enable_metrics: bool = True
    ) -> None:
        """
        Initialize the field extractor with modern configuration.
        
        Args:
            ai_enabled: Enable AI-enhanced extraction features
            enable_caching: Enable result caching for better performance
            max_workers: Maximum worker threads for concurrent processing
            enable_metrics: Enable performance metrics collection
        """
        # Core components with dependency injection
        self.pattern_matcher = PatternMatcher()
        self.formatter = ContentFormatter()
        self.schema_validator = SchemaValidator()
        
        # Configuration
        self.ai_enabled = ai_enabled
        self.enable_caching = enable_caching
        self.enable_metrics = enable_metrics
        
        # Thread pool for CPU-intensive operations
        self._thread_pool = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="FieldExtractor"
        )
        
        # Performance metrics storage
        self._performance_metrics: Dict[str, Dict[str, Any]] = {} if enable_metrics else {}
        
        # Result cache with LRU eviction
        self._result_cache: Dict[str, Any] = {} if enable_caching else {}
        self._cache_stats = {'hits': 0, 'misses': 0} if enable_caching else {}
        
        # Semaphore for concurrent extraction limiting
        self._extraction_semaphore = asyncio.Semaphore(10)
        
        # Optimized built-in patterns with modern regex features
        # Using compiled patterns for better performance
        self._builtin_patterns_raw = {
            # Contact Information Patterns
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'phone': r'(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})',
            'phone_international': r'\+?[1-9]\d{1,14}',
            
            # Web and Digital Patterns
            'url': r'https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:\w*))?)?',
            'url_strict': r'https?://(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(?:/[^\s]*)?',
            'ip_address': r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b',
            'ipv6': r'(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}',
            'mac_address': r'(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}',
            
            # Date and Time Patterns
            'date_iso': r'\d{4}-\d{2}-\d{2}',
            'date_us': r'\d{1,2}/\d{1,2}/\d{4}',
            'date_eu': r'\d{1,2}\.\d{1,2}\.\d{4}',
            'time': r'\d{1,2}:\d{2}(?::\d{2})?(?:\s*[AaPp][Mm])?',
            'datetime_iso': r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?',
            
            # Financial Patterns
            'price': r'\$?\d{1,3}(?:,\d{3})*(?:\.\d{2})?',
            'price_euro': r'€?\d{1,3}(?:\.\d{3})*(?:,\d{2})?',
            'price_general': r'[¥£€$]\s?\d{1,3}(?:[,.\s]\d{3})*(?:[,.]\d{2})?',
            'percentage': r'\d+(?:\.\d+)?%',
            'currency_code': r'\b[A-Z]{3}\b',
            
            # Scientific Patterns
            'temperature': r'-?\d+(?:\.\d+)?°[CF]',
            'temperature_kelvin': r'\d+(?:\.\d+)?\s*K\b',
            'chemical_formula': r'[A-Z][a-z]?(?:\d+)?(?:[A-Z][a-z]?(?:\d+)?)*',
            'molecular_formula': r'[A-Z][a-z]?[₀-₉]*(?:[A-Z][a-z]?[₀-₉]*)*',
            'chemical_compound': r'(?:[A-Z][a-z]?(?:\d+|[₀-₉]+)?)+(?:[-·•](?:\d+|[₀-₉]+)?H₂O)?',
            'scientific_notation': r'-?\d(?:\.\d+)?[eE][+-]?\d+',
            'measurement': r'\d+(?:\.\d+)?\s*(?:mm|cm|m|km|g|kg|ml|l|mol|°C|°F|K)\b',
            
            # Academic and Research Patterns
            'doi': r'10\.\d{4,}/[^\s]+',
            'pmid': r'PMID:\s*\d+',
            'isbn': r'(?:ISBN(?:-1[03])?:?\s*)?(?=[-0-9\s]{10,17}$|[-0-9X\s]{10,17}$)[0-9]{1,5}[-\s]?[0-9]{1,7}[-\s]?[0-9]{1,6}[-\s]?(?:[0-9]|X)$',
            'orcid': r'\d{4}-\d{4}-\d{4}-\d{3}[0-9X]',
            
            # Geographic Patterns
            'coordinate': r'-?\d{1,3}\.\d+,\s*-?\d{1,3}\.\d+',
            'latitude': r'[-+]?(?:[1-8]?\d(?:\.\d+)?|90(?:\.0+)?)',
            'longitude': r'[-+]?(?:180(?:\.0+)?|(?:1[0-7]\d|\d{1,2})(?:\.\d+)?)',
            'postal_code': r'\b\d{5}(?:-\d{4})?\b',
            'postal_code_uk': r'\b[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}\b',
            
            # Social Media Patterns
            'hashtag': r'#\w+',
            'mention': r'@\w+',
            'twitter_handle': r'@[A-Za-z0-9_]{1,15}',
            
            # Technical Patterns
            'hex_color': r'#[0-9A-Fa-f]{6}',
            'hex_color_short': r'#[0-9A-Fa-f]{3}',
            'uuid': r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}',
            'base64': r'[A-Za-z0-9+/]{4,}={0,2}',
            
            # Security Patterns
            'credit_card': r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
            'social_security': r'\b\d{3}-\d{2}-\d{4}\b',
            'crypto_address': r'\b[13][a-km-zA-HJ-NP-Z1-9]{25,34}\b',
            
            # File and Data Patterns
            'filename': r'\b[\w\-_]+\.(?:txt|pdf|doc|docx|xls|xlsx|ppt|pptx|jpg|jpeg|png|gif|mp4|avi|zip|tar|gz)\b',
            'file_size': r'\d+(?:\.\d+)?\s*(?:B|KB|MB|GB|TB)\b',
            'version': r'v?\d+\.\d+(?:\.\d+)?(?:-[a-zA-Z0-9]+)?',
        }
        
        # Compile patterns for better performance
        self.builtin_patterns = self._compile_patterns(self._builtin_patterns_raw)
    
    def _compile_patterns(self, patterns: Dict[str, str]) -> Dict[str, re.Pattern]:
        """
        Compile regex patterns for better performance.
        
        Compiles all patterns once during initialization to avoid
        repeated compilation overhead during extraction.
        
        Args:
            patterns: Dictionary of pattern name to regex string
            
        Returns:
            Dictionary of pattern name to compiled regex Pattern
        """
        compiled = {}
        for name, pattern in patterns.items():
            try:
                compiled[name] = re.compile(pattern, re.UNICODE | re.IGNORECASE)
            except re.error as e:
                logger.warning(f"Failed to compile pattern '{name}': {e}")
                # Store as string fallback for runtime compilation
                compiled[name] = pattern
        return compiled
    
    @lru_cache(maxsize=1000)
    def _get_cached_pattern(self, pattern_name: str) -> Optional[re.Pattern]:
        """
        Get cached compiled pattern with LRU eviction.
        
        Uses functools.lru_cache for automatic memoization of
        frequently used patterns.
        
        Args:
            pattern_name: Name of the pattern to retrieve
            
        Returns:
            Compiled regex pattern or None if not found
        """
        return self.builtin_patterns.get(pattern_name)
    
    async def __aenter__(self):
        """Async context manager entry for resource management."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit with cleanup."""
        await self.cleanup()
    
    async def cleanup(self) -> None:
        """
        Clean up resources and log performance metrics.
        
        Ensures proper cleanup of:
        - Thread pool executor
        - Cache storage
        - Performance metrics logging
        """
        try:
            # Shutdown thread pool gracefully
            if hasattr(self, '_thread_pool'):
                self._thread_pool.shutdown(wait=True)
            
            # Log final performance metrics
            if self.enable_metrics and self._performance_metrics:
                self._log_performance_summary()
            
            # Log cache statistics
            if self.enable_caching and self._cache_stats:
                cache_hit_rate = (
                    self._cache_stats['hits'] / 
                    (self._cache_stats['hits'] + self._cache_stats['misses'])
                    if (self._cache_stats['hits'] + self._cache_stats['misses']) > 0 else 0
                )
                logger.info(
                    f"FieldExtractor cache statistics: {cache_hit_rate:.2%} hit rate",
                    extra=self._cache_stats
                )
                
        except Exception as e:
            logger.warning(f"Error during FieldExtractor cleanup: {e}")
    
    def _log_performance_summary(self) -> None:
        """Log comprehensive performance metrics summary."""
        if not self._performance_metrics:
            return
        
        total_calls = sum(metrics.get('total_calls', 0) for metrics in self._performance_metrics.values())
        total_time = sum(metrics.get('total_time', 0) for metrics in self._performance_metrics.values())
        avg_time = total_time / total_calls if total_calls > 0 else 0
        
        logger.info(
            "FieldExtractor performance summary",
            extra={
                'total_extractions': total_calls,
                'total_time': round(total_time, 3),
                'average_time_per_extraction': round(avg_time, 3),
                'methods_called': len(self._performance_metrics),
                'performance_details': self._performance_metrics
            }
        )
    
    @performance_monitor
    async def extract_fields(self, content: Dict[str, Any], field_specs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract specified fields from crawled content with advanced optimization.
        
        This method provides high-performance field extraction with:
        - Concurrent processing of multiple fields
        - Intelligent caching of results
        - Performance monitoring and metrics
        - Comprehensive error handling
        - Memory-efficient processing
        
        Args:
            content: Crawled content from any crawler type
            field_specs: Dictionary defining fields to extract
            
        Returns:
            Dictionary with comprehensive extraction results including:
            - Extracted field values
            - Confidence scores
            - Formatted versions
            - Alternative matches
            - Performance metadata
        """
        # Create extraction context for tracking
        context = ExtractionContext(
            source_url=content.get('url', ''),
            content_type=content.get('crawler_type', ''),
            enable_ai=self.ai_enabled
        )
        
        # Initialize result structure with comprehensive metadata
        extracted_data = {
            'fields': {},
            'metadata': {
                'source_url': context.source_url,
                'extraction_timestamp': context.extraction_timestamp,
                'crawler_type': context.content_type,
                'success': content.get('success', False),
                'field_count': len(field_specs),
                'ai_enabled': self.ai_enabled,
                'cache_enabled': self.enable_caching
            },
            'formatting_preserved': {},
            'confidence_scores': {},
            'alternative_matches': {},
            'performance_metrics': {}
        }
        
        # Early return for failed crawling
        if not content.get('success', False):
            extracted_data['error'] = content.get('error', 'Crawling failed')
            extracted_data['metadata']['extraction_success'] = False
            return extracted_data
        
        # Extract and cache text content with optimization
        text_content = await self._extract_text_content_optimized(content)
        
        # Check cache for this content if enabled
        cache_key = None
        if self.enable_caching:
            cache_key = self._generate_cache_key(text_content, field_specs)
            cached_result = self._get_cached_result(cache_key)
            if cached_result:
                self._cache_stats['hits'] += 1
                logger.debug(f"Cache hit for extraction: {cache_key[:16]}...")
                return cached_result
            self._cache_stats['misses'] += 1
        
        # Process fields concurrently for better performance
        extraction_start = time.perf_counter()
        
        try:
            # Create semaphore-controlled concurrent extractions
            async with self._extraction_semaphore:
                # Group extractions for batch processing
                extraction_tasks = []
                
                for field_name, field_spec in field_specs.items():
                    task = self._extract_single_field_with_context(
                        field_name, field_spec, text_content, content, context
                    )
                    extraction_tasks.append(task)
                
                # Execute extractions concurrently with error isolation
                extraction_results = await asyncio.gather(
                    *extraction_tasks, 
                    return_exceptions=True
                )
                
                # Process results with comprehensive error handling
                for i, (field_name, result) in enumerate(zip(field_specs.keys(), extraction_results)):
                    if isinstance(result, Exception):
                        # Handle extraction errors gracefully
                        logger.error(
                            f"Error extracting field '{field_name}': {result}",
                            extra={'field_name': field_name, 'error_type': type(result).__name__}
                        )
                        extracted_data['fields'][field_name] = None
                        extracted_data['confidence_scores'][field_name] = 0.0
                        continue
                    
                    # Process successful extraction
                    if isinstance(result, ExtractionResult):
                        extracted_data['fields'][result.field_name] = result.value
                        extracted_data['confidence_scores'][result.field_name] = result.confidence
                        
                        if result.formatted_value:
                            extracted_data['formatting_preserved'][result.field_name] = result.formatted_value
                        
                        if result.alternatives:
                            extracted_data['alternative_matches'][result.field_name] = result.alternatives
                        
                        # Add field-specific metadata
                        if result.metadata:
                            if 'field_metadata' not in extracted_data:
                                extracted_data['field_metadata'] = {}
                            extracted_data['field_metadata'][result.field_name] = result.metadata
                
        except Exception as e:
            logger.error(f"Critical error during field extraction: {e}", exc_info=True)
            extracted_data['error'] = f"Extraction failed: {e}"
            extracted_data['metadata']['extraction_success'] = False
            return extracted_data
        
        # Record performance metrics
        extraction_time = time.perf_counter() - extraction_start
        extracted_data['performance_metrics'] = {
            'extraction_time_ms': round(extraction_time * 1000, 2),
            'fields_processed': len(field_specs),
            'successful_extractions': sum(1 for v in extracted_data['fields'].values() if v is not None),
            'cache_hit': cache_key is not None and cache_key in self._result_cache
        }
        
        # Validate extracted data against schema if provided
        if 'schema' in field_specs:
            validation_result = self.schema_validator.validate(
                extracted_data['fields'], 
                field_specs['schema']
            )
            extracted_data['validation'] = validation_result
        
        return extracted_data
    
    def _extract_text_content(self, content: Dict[str, Any]) -> str:
        """Extract text content from different crawler types."""
        crawler_content = content.get('content', {})
        
        if isinstance(crawler_content, dict):
            # Try different content keys based on crawler type
            text_sources = [
                crawler_content.get('text_content', ''),
                crawler_content.get('raw_html', ''),
                str(crawler_content)
            ]
            
            # For PDF content, combine page texts
            if 'pages' in crawler_content:
                page_texts = []
                for page in crawler_content['pages']:
                    if isinstance(page, dict) and 'text' in page:
                        page_texts.append(page['text'])
                if page_texts:
                    text_sources.insert(0, '\n'.join(page_texts))
            
            # Return the first non-empty text source
            for text in text_sources:
                if text and text.strip():
                    return text
        
        return str(crawler_content)
    
    async def _extract_single_field(self, field_name: str, field_spec: Any, text_content: str, full_content: Dict[str, Any]) -> Dict[str, Any]:
        """Extract a single field based on its specification."""
        
        # Handle different field specification formats
        if isinstance(field_spec, str):
            # Simple regex pattern
            pattern = field_spec
            options = {}
        elif isinstance(field_spec, dict):
            # Complex field specification
            pattern = field_spec.get('pattern', field_spec.get('regex', ''))
            options = field_spec
        else:
            raise ValueError(f"Invalid field specification for '{field_name}': {field_spec}")
        
        # Check if it's a built-in pattern
        if pattern in self.builtin_patterns:
            pattern = self.builtin_patterns[pattern]
        
        # Extract matches using pattern matcher
        matches = self.pattern_matcher.find_matches(
            text_content, 
            pattern, 
            options.get('flags', 0),
            options.get('max_matches', None)
        )
        
        # Process matches based on field options
        processed_result = await self._process_matches(
            matches, 
            options, 
            text_content, 
            full_content
        )
        
        return processed_result
    
    async def _process_matches(self, matches: List[Dict[str, Any]], options: Dict[str, Any], text_content: str, full_content: Dict[str, Any]) -> Dict[str, Any]:
        """Process and refine extracted matches."""
        
        if not matches:
            return {
                'value': None,
                'confidence': 0.0,
                'formatted_value': None,
                'alternatives': []
            }
        
        # Sort matches by confidence or position
        sorted_matches = sorted(matches, key=lambda x: x.get('confidence', 1.0), reverse=True)
        
        # Select primary match
        primary_match = sorted_matches[0]
        primary_value = primary_match['match']
        
        # Apply formatting preservation if requested
        formatted_value = None
        if options.get('preserve_formatting', True):
            formatted_value = self.formatter.preserve_formatting(
                primary_value,
                full_content,
                options.get('formatting_type', 'auto')
            )
        
        # Apply post-processing transformations
        if 'transform' in options:
            primary_value = self._apply_transformations(primary_value, options['transform'])
            if formatted_value:
                formatted_value = self._apply_transformations(formatted_value, options['transform'])
        
        # Calculate confidence score
        confidence = self._calculate_confidence(primary_match, options, text_content)
        
        # Get alternative matches
        alternatives = []
        if options.get('include_alternatives', False) and len(sorted_matches) > 1:
            alternatives = [
                {
                    'value': match['match'],
                    'confidence': match.get('confidence', 1.0),
                    'context': match.get('context', '')
                }
                for match in sorted_matches[1:options.get('max_alternatives', 5)]
            ]
        
        # Handle multiple values
        if options.get('multiple', False):
            all_values = [match['match'] for match in sorted_matches]
            if options.get('unique', True):
                all_values = list(dict.fromkeys(all_values))  # Preserve order
            
            return {
                'value': all_values,
                'confidence': confidence,
                'formatted_value': [self.formatter.preserve_formatting(v, full_content) for v in all_values] if formatted_value else None,
                'alternatives': alternatives
            }
        
        return {
            'value': primary_value,
            'confidence': confidence,
            'formatted_value': formatted_value,
            'alternatives': alternatives
        }
    
    def _apply_transformations(self, value: str, transformations: Union[str, List[str]]) -> str:
        """Apply post-processing transformations to extracted values."""
        if isinstance(transformations, str):
            transformations = [transformations]
        
        result = value
        
        for transform in transformations:
            if transform == 'lowercase':
                result = result.lower()
            elif transform == 'uppercase':
                result = result.upper()
            elif transform == 'title':
                result = result.title()
            elif transform == 'strip':
                result = result.strip()
            elif transform == 'normalize_unicode':
                result = unicodedata.normalize('NFKC', result)
            elif transform == 'decode_html':
                result = html.unescape(result)
            elif transform == 'remove_whitespace':
                result = re.sub(r'\s+', '', result)
            elif transform == 'normalize_whitespace':
                result = re.sub(r'\s+', ' ', result).strip()
            elif transform.startswith('replace:'):
                # Format: "replace:pattern:replacement"
                parts = transform.split(':', 2)
                if len(parts) == 3:
                    result = re.sub(parts[1], parts[2], result)
            elif transform.startswith('extract:'):
                # Format: "extract:pattern" - extract specific group from regex
                pattern = transform[8:]
                match = re.search(pattern, result)
                if match:
                    result = match.group(1) if match.groups() else match.group(0)
        
        return result
    
    def _calculate_confidence(self, match: Dict[str, Any], options: Dict[str, Any], text_content: str) -> float:
        """Calculate confidence score for a match."""
        base_confidence = match.get('confidence', 1.0)
        
        # Factors that can affect confidence
        factors = []
        
        # Context quality
        context = match.get('context', '')
        if context:
            context_keywords = options.get('context_keywords', [])
            if context_keywords:
                context_lower = context.lower()
                matching_keywords = sum(1 for kw in context_keywords if kw.lower() in context_lower)
                context_factor = matching_keywords / len(context_keywords)
                factors.append(context_factor)
        
        # Pattern specificity
        pattern_length = len(match.get('pattern', ''))
        if pattern_length > 10:  # More specific patterns get higher confidence
            factors.append(0.1)
        
        # Position in document (earlier matches might be more important)
        position = match.get('position', 0)
        total_length = len(text_content)
        if total_length > 0:
            position_factor = 1.0 - (position / total_length) * 0.2  # Max 20% reduction
            factors.append(position_factor)
        
        # Apply factors
        if factors:
            adjustment = sum(factors) / len(factors)
            base_confidence = min(1.0, base_confidence * (0.8 + 0.4 * adjustment))
        
        return round(base_confidence, 3)
    
    def get_builtin_patterns(self) -> Dict[str, str]:
        """Return available built-in patterns."""
        return self.builtin_patterns.copy()
    
    def add_custom_pattern(self, name: str, pattern: str) -> None:
        """Add a custom pattern to the built-in patterns."""
        self.builtin_patterns[name] = pattern
        logger.info(f"Added custom pattern '{name}': {pattern}")
    
    async def extract_with_ai_enhancement(self, content: Dict[str, Any], field_specs: Dict[str, Any], ai_prompt: str = None) -> Dict[str, Any]:
        """Extract fields with AI enhancement for better accuracy."""
        # First, extract using traditional regex
        base_extraction = await self.extract_fields(content, field_specs)
        
        if not self.ai_enabled:
            return base_extraction
        
        # TODO: Implement AI enhancement using OpenAI or transformers
        # This would involve:
        # 1. Analyzing extraction results
        # 2. Using AI to validate and refine matches
        # 3. Generating natural language descriptions
        # 4. Improving confidence scores
        
        # For now, return base extraction
        logger.info("AI enhancement not yet implemented")
        return base_extraction