"""
Base Crawler class providing common functionality for all crawler types.

This module implements the abstract base class for all web crawlers in the framework.
It provides common functionality like retry logic, proxy management, and URL handling
using modern Python async/await patterns and type hints.

Features:
- Async/await support for non-blocking operations
- Automatic retry with exponential backoff
- Proxy rotation and management
- Realistic headers generation
- URL resolution and validation
- Performance monitoring and logging

Author: Web Scraping Framework Team
License: MIT
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Union, Protocol
from urllib.parse import urljoin, urlparse
import time
from dataclasses import dataclass, field
from contextlib import asynccontextmanager

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from fake_useragent import UserAgent

# Modern type hints for better IDE support and runtime validation
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CrawlResult:
    """Immutable data class for crawler results using modern dataclass features."""
    url: str
    success: bool
    content: Dict[str, Any]
    timestamp: float
    crawler_type: str
    response_time: Optional[float] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class ProxyManagerProtocol(Protocol):
    """Protocol for type checking proxy manager interface."""
    async def get_proxy(self) -> Optional[str]: ...
    async def rotate_proxy(self) -> None: ...
    async def mark_proxy_success(self, proxy_url: str, response_time: float) -> None: ...


class BaseCrawler(ABC):
    """
    Abstract base class for all web crawlers.
    
    This class provides the foundation for all crawler implementations with:
    - Modern async/await patterns
    - Configurable retry logic with exponential backoff
    - Proxy management integration
    - Performance monitoring and metrics
    - Resource cleanup with context managers
    
    Attributes:
        proxy_manager: Optional proxy manager for request routing
        max_retries: Maximum number of retry attempts (default: 3)
        delay: Base delay between requests in seconds (default: 1.0)
        user_agent: UserAgent generator for realistic headers
        session: Reusable session for connection pooling
    """
    
    def __init__(
        self, 
        proxy_manager: Optional[ProxyManagerProtocol] = None, 
        max_retries: int = 3, 
        delay: float = 1.0,
        timeout: float = 30.0,
        enable_metrics: bool = True
    ) -> None:
        """
        Initialize the base crawler with modern configuration.
        
        Args:
            proxy_manager: Optional proxy manager implementing ProxyManagerProtocol
            max_retries: Maximum retry attempts for failed requests
            delay: Base delay between requests to respect rate limits
            timeout: Request timeout in seconds
            enable_metrics: Whether to collect performance metrics
        """
        self.proxy_manager = proxy_manager
        self.max_retries = max_retries
        self.delay = delay
        self.timeout = timeout
        self.enable_metrics = enable_metrics
        
        # Use lazy initialization for better performance
        self._user_agent: Optional[UserAgent] = None
        self._session: Optional[Any] = None
        
        # Performance metrics using modern collections
        self._metrics: Dict[str, List[float]] = {
            'response_times': [],
            'success_count': [],
            'error_count': []
        } if enable_metrics else {}
    
    @property
    def user_agent(self) -> UserAgent:
        """Lazy-loaded UserAgent instance for better performance."""
        if self._user_agent is None:
            self._user_agent = UserAgent()
        return self._user_agent
    
    @property
    def session(self) -> Optional[Any]:
        """Get the current session instance."""
        return self._session
    
    @session.setter
    def session(self, value: Any) -> None:
        """Set the session instance."""
        self._session = value
        
    def get_headers(self) -> Dict[str, str]:
        """
        Generate realistic HTTP headers with rotating user agents.
        
        Uses modern browser characteristics to avoid detection:
        - Recent user agent strings
        - Realistic Accept headers
        - Standard security headers
        - Connection optimization headers
        
        Returns:
            Dictionary of HTTP headers optimized for modern browsers
        """
        # Cache headers for better performance (rotate every 100 requests)
        if not hasattr(self, '_headers_cache') or getattr(self, '_request_count', 0) % 100 == 0:
            self._headers_cache = {
                'User-Agent': self.user_agent.random,
                'Accept': (
                    'text/html,application/xhtml+xml,application/xml;q=0.9,'
                    'image/avif,image/webp,image/apng,*/*;q=0.8,'
                    'application/signed-exchange;v=b3;q=0.7'
                ),
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Cache-Control': 'max-age=0',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"'
            }
            self._request_count = getattr(self, '_request_count', 0) + 1
        
        return self._headers_cache.copy()
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((
            asyncio.TimeoutError,
            ConnectionError,
            Exception  # Can be made more specific based on needs
        ))
    )
    async def fetch_with_retry(self, url: str, **kwargs) -> Any:
        """
        Fetch content with intelligent retry logic and proxy rotation.
        
        Features:
        - Exponential backoff with jitter
        - Automatic proxy rotation on failures
        - Performance metrics collection
        - Detailed error logging with context
        
        Args:
            url: Target URL to fetch
            **kwargs: Additional parameters for the fetch operation
            
        Returns:
            Fetched content from the URL
            
        Raises:
            Exception: After all retry attempts are exhausted
        """
        start_time = time.perf_counter()  # More precise timing
        
        try:
            # Execute the actual fetch with timing
            result = await self._fetch_content(url, **kwargs)
            
            # Record success metrics
            response_time = time.perf_counter() - start_time
            if self.enable_metrics:
                self._metrics['response_times'].append(response_time)
                self._metrics['success_count'].append(1)
            
            # Mark proxy as successful if using proxy manager
            if self.proxy_manager:
                current_proxy = await self.proxy_manager.get_proxy()
                if current_proxy:
                    await self.proxy_manager.mark_proxy_success(current_proxy, response_time)
            
            return result
            
        except Exception as e:
            # Record failure metrics
            if self.enable_metrics:
                self._metrics['error_count'].append(1)
            
            # Enhanced error logging with context
            logger.warning(
                f"Fetch attempt failed for {url}: {type(e).__name__}: {e}",
                extra={
                    'url': url,
                    'error_type': type(e).__name__,
                    'attempt_duration': time.perf_counter() - start_time,
                    'proxy_enabled': self.proxy_manager is not None
                }
            )
            
            # Intelligent proxy rotation based on error type
            if self.proxy_manager and self._should_rotate_proxy(e):
                await self.proxy_manager.rotate_proxy()
            
            raise
    
    def _should_rotate_proxy(self, error: Exception) -> bool:
        """
        Determine if proxy should be rotated based on error type.
        
        Args:
            error: The exception that occurred
            
        Returns:
            True if proxy should be rotated, False otherwise
        """
        # Rotate on connection issues, timeouts, and HTTP errors
        rotation_triggers = (
            ConnectionError,
            asyncio.TimeoutError,
            # Add specific HTTP status errors here
        )
        
        # Check error message for specific indicators
        error_str = str(error).lower()
        message_triggers = ['forbidden', '403', '429', 'blocked', 'captcha']
        
        return (
            isinstance(error, rotation_triggers) or
            any(trigger in error_str for trigger in message_triggers)
        )
    
    @abstractmethod
    async def _fetch_content(self, url: str, **kwargs) -> Any:
        """Implement specific fetching logic for each crawler type."""
        pass
    
    @abstractmethod
    async def parse_content(self, content: Any, url: str) -> Dict[str, Any]:
        """Parse the fetched content and return structured data."""
        pass
    
    async def crawl(self, url: str, **kwargs) -> CrawlResult:
        """
        Main crawling orchestration method with comprehensive error handling.
        
        This method coordinates the entire crawling process:
        1. Validates the URL
        2. Fetches content with retry logic
        3. Parses the content
        4. Collects performance metrics
        5. Returns structured results
        
        Args:
            url: Target URL to crawl
            **kwargs: Additional crawling parameters
            
        Returns:
            CrawlResult dataclass with all crawling information
        """
        start_time = time.perf_counter()
        timestamp = time.time()
        
        # Validate URL before processing
        if not self._is_valid_url(url):
            return CrawlResult(
                url=url,
                success=False,
                content={},
                timestamp=timestamp,
                crawler_type=self.__class__.__name__,
                error="Invalid URL format",
                response_time=0.0
            )
        
        try:
            # Use context manager for better resource management
            async with self._crawl_context():
                # Fetch content with retry logic
                content = await self.fetch_with_retry(url, **kwargs)
                
                # Parse content with error isolation
                parsed_data = await self.parse_content(content, url)
                
                response_time = time.perf_counter() - start_time
                
                return CrawlResult(
                    url=url,
                    success=True,
                    content=parsed_data,
                    timestamp=timestamp,
                    crawler_type=self.__class__.__name__,
                    response_time=response_time,
                    metadata=self._get_crawl_metadata(url, response_time)
                )
                
        except Exception as e:
            response_time = time.perf_counter() - start_time
            
            # Enhanced error logging with full context
            logger.error(
                f"Crawling failed for {url}: {type(e).__name__}: {e}",
                extra={
                    'url': url,
                    'crawler_type': self.__class__.__name__,
                    'response_time': response_time,
                    'error_type': type(e).__name__,
                    'kwargs': {k: v for k, v in kwargs.items() if k not in ['headers', 'auth']}
                },
                exc_info=True
            )
            
            return CrawlResult(
                url=url,
                success=False,
                content={},
                timestamp=timestamp,
                crawler_type=self.__class__.__name__,
                response_time=response_time,
                error=f"{type(e).__name__}: {e}",
                metadata=self._get_crawl_metadata(url, response_time)
            )
    
    @asynccontextmanager
    async def _crawl_context(self):
        """
        Async context manager for crawling operations.
        
        Provides:
        - Resource initialization
        - Cleanup on exit
        - Exception handling context
        """
        try:
            # Pre-crawl setup
            if hasattr(self, '_pre_crawl_setup'):
                await self._pre_crawl_setup()
            
            yield
            
        finally:
            # Post-crawl cleanup
            if hasattr(self, '_post_crawl_cleanup'):
                await self._post_crawl_cleanup()
    
    def _is_valid_url(self, url: str) -> bool:
        """
        Validate URL format and scheme.
        
        Args:
            url: URL to validate
            
        Returns:
            True if URL is valid, False otherwise
        """
        try:
            parsed = urlparse(url)
            return bool(parsed.netloc) and parsed.scheme in {'http', 'https', 'ftp'}
        except Exception:
            return False
    
    def _get_crawl_metadata(self, url: str, response_time: float) -> Dict[str, Any]:
        """
        Generate metadata for crawl results.
        
        Args:
            url: Crawled URL
            response_time: Time taken for the crawl
            
        Returns:
            Dictionary containing crawl metadata
        """
        metadata = {
            'response_time_ms': round(response_time * 1000, 2),
            'url_domain': urlparse(url).netloc,
            'proxy_used': self.proxy_manager is not None,
        }
        
        # Add performance metrics if enabled
        if self.enable_metrics and self._metrics:
            metadata['avg_response_time'] = (
                sum(self._metrics['response_times']) / len(self._metrics['response_times'])
                if self._metrics['response_times'] else 0
            )
            metadata['total_requests'] = (
                len(self._metrics['success_count']) + len(self._metrics['error_count'])
            )
        
        return metadata
    
    def is_absolute_url(self, url: str) -> bool:
        """Check if URL is absolute."""
        return bool(urlparse(url).netloc)
    
    def resolve_url(self, base_url: str, relative_url: str) -> str:
        """Resolve relative URL against base URL."""
        if self.is_absolute_url(relative_url):
            return relative_url
        return urljoin(base_url, relative_url)
    
    async def close(self) -> None:
        """
        Clean up crawler resources with comprehensive cleanup.
        
        This method ensures proper resource cleanup:
        - Closes network sessions
        - Clears caches
        - Logs performance statistics
        - Handles cleanup errors gracefully
        """
        try:
            # Close network session if exists
            if hasattr(self, '_session') and self._session:
                await self._session.close()
                self._session = None
            
            # Log performance metrics before cleanup
            if self.enable_metrics and self._metrics:
                self._log_performance_summary()
            
            # Clear caches
            if hasattr(self, '_headers_cache'):
                delattr(self, '_headers_cache')
            
            # Subclass-specific cleanup
            if hasattr(self, '_cleanup_resources'):
                await self._cleanup_resources()
                
        except Exception as e:
            logger.warning(f"Error during crawler cleanup: {e}", exc_info=True)
    
    def _log_performance_summary(self) -> None:
        """Log performance metrics summary for monitoring."""
        if not self._metrics:
            return
        
        response_times = self._metrics.get('response_times', [])
        success_count = len(self._metrics.get('success_count', []))
        error_count = len(self._metrics.get('error_count', []))
        
        if response_times:
            avg_time = sum(response_times) / len(response_times)
            min_time = min(response_times)
            max_time = max(response_times)
            
            logger.info(
                f"Crawler {self.__class__.__name__} performance summary",
                extra={
                    'crawler_type': self.__class__.__name__,
                    'total_requests': success_count + error_count,
                    'success_rate': success_count / (success_count + error_count) if (success_count + error_count) > 0 else 0,
                    'avg_response_time_ms': round(avg_time * 1000, 2),
                    'min_response_time_ms': round(min_time * 1000, 2),
                    'max_response_time_ms': round(max_time * 1000, 2),
                }
            )
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get current performance metrics.
        
        Returns:
            Dictionary containing performance statistics
        """
        if not self.enable_metrics or not self._metrics:
            return {}
        
        response_times = self._metrics.get('response_times', [])
        success_count = len(self._metrics.get('success_count', []))
        error_count = len(self._metrics.get('error_count', []))
        
        return {
            'total_requests': success_count + error_count,
            'successful_requests': success_count,
            'failed_requests': error_count,
            'success_rate': success_count / (success_count + error_count) if (success_count + error_count) > 0 else 0,
            'average_response_time': sum(response_times) / len(response_times) if response_times else 0,
            'min_response_time': min(response_times) if response_times else 0,
            'max_response_time': max(response_times) if response_times else 0,
        }
    
    # Context manager support for automatic cleanup
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit with cleanup."""
        await self.close()