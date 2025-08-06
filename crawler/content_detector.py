"""
Content type detector to automatically choose the appropriate crawler.
"""

import asyncio
import aiohttp
from typing import Dict, Any, Optional, Type
import logging
from urllib.parse import urlparse
import re

from .base_crawler import BaseCrawler
from .html_crawler import HTMLCrawler
from .js_crawler import JSCrawler
from .pdf_crawler import PDFCrawler

logger = logging.getLogger(__name__)


class ContentDetector:
    """Detects content type and selects appropriate crawler."""
    
    def __init__(self, proxy_manager=None):
        self.proxy_manager = proxy_manager
        self.crawlers = {
            'html': HTMLCrawler,
            'js': JSCrawler,
            'pdf': PDFCrawler
        }
        
        # JavaScript frameworks and indicators
        self.js_indicators = [
            'react', 'angular', 'vue', 'ember', 'backbone',
            'knockout', 'meteor', 'polymer', 'aurelia',
            'app.js', 'bundle.js', 'main.js', 'spa'
        ]
        
        # File extensions that typically indicate content type
        self.pdf_extensions = ['.pdf']
        self.html_extensions = ['.html', '.htm', '.php', '.asp', '.aspx', '.jsp']
        
    async def detect_content_type(self, url: str, **kwargs) -> str:
        """Detect the content type of a URL."""
        
        # First, check URL for obvious indicators
        parsed_url = urlparse(url.lower())
        path = parsed_url.path
        
        # Check file extension
        for ext in self.pdf_extensions:
            if path.endswith(ext):
                return 'pdf'
        
        # Check for SPA/JS framework indicators in URL
        for indicator in self.js_indicators:
            if indicator in url.lower():
                return 'js'
        
        # If no clear indicators, make a HEAD request to check headers
        try:
            content_type = await self._check_headers(url)
            if content_type:
                return content_type
        except Exception as e:
            logger.warning(f"Could not check headers for {url}: {e}")
        
        # If still unclear, make a partial GET request to check content
        try:
            return await self._analyze_partial_content(url, **kwargs)
        except Exception as e:
            logger.warning(f"Could not analyze content for {url}: {e}")
            
        # Default to HTML if detection fails
        return 'html'
    
    async def _check_headers(self, url: str) -> Optional[str]:
        """Check HTTP headers to determine content type."""
        timeout = aiohttp.ClientTimeout(total=10)
        
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.head(url) as response:
                    content_type = response.headers.get('content-type', '').lower()
                    
                    if 'pdf' in content_type:
                        return 'pdf'
                    elif any(t in content_type for t in ['text/html', 'application/xhtml']):
                        # Could be HTML or JS-rendered, need further analysis
                        return None
                    else:
                        return 'html'  # Default for unknown text content
                        
        except Exception as e:
            logger.debug(f"HEAD request failed for {url}: {e}")
            return None
    
    async def _analyze_partial_content(self, url: str, **kwargs) -> str:
        """Analyze partial content to detect if JavaScript rendering is needed."""
        timeout = aiohttp.ClientTimeout(total=15)
        
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                # Get first 8KB of content
                async with session.get(url) as response:
                    # Read partial content
                    partial_content = await response.content.read(8192)
                    content_str = partial_content.decode('utf-8', errors='ignore').lower()
                    
                    # Check for PDF magic bytes
                    if partial_content.startswith(b'%PDF'):
                        return 'pdf'
                    
                    # Check for JavaScript framework indicators
                    js_patterns = [
                        r'<div[^>]+id=["\']root["\']',  # React root
                        r'<div[^>]+id=["\']app["\']',   # Vue/other SPA root
                        r'ng-app',                      # AngularJS
                        r'data-ng-app',                 # Angular
                        r'v-app',                       # Vue
                        r'ember-application',           # Ember
                        r'window\.app\s*=',             # Generic SPA
                        r'document\.ready.*\$',         # jQuery heavy sites
                        r'<script[^>]*type=["\']module["\']',  # ES6 modules
                    ]
                    
                    for pattern in js_patterns:
                        if re.search(pattern, content_str):
                            return 'js'
                    
                    # Check for heavy JavaScript usage
                    script_count = content_str.count('<script')
                    if script_count > 5:  # Lots of scripts might indicate JS rendering
                        return 'js'
                    
                    # Check for minimal content (common in SPAs)
                    body_match = re.search(r'<body[^>]*>(.*?)</body>', content_str, re.DOTALL)
                    if body_match:
                        body_content = body_match.group(1)
                        # Remove scripts and styles
                        body_content = re.sub(r'<script[^>]*>.*?</script>', '', body_content, flags=re.DOTALL | re.IGNORECASE)
                        body_content = re.sub(r'<style[^>]*>.*?</style>', '', body_content, flags=re.DOTALL | re.IGNORECASE)
                        
                        # Check if there's meaningful content
                        text_content = re.sub(r'<[^>]+>', '', body_content).strip()
                        if len(text_content) < 100:  # Very little content might indicate SPA
                            return 'js'
                    
                    # Default to HTML
                    return 'html'
                    
        except Exception as e:
            logger.debug(f"Content analysis failed for {url}: {e}")
            return 'html'  # Default fallback
    
    async def get_crawler(self, url: str, **kwargs) -> BaseCrawler:
        """Get the appropriate crawler for the given URL."""
        content_type = await self.detect_content_type(url, **kwargs)
        
        # Force specific crawler type if requested
        if 'force_crawler' in kwargs:
            forced_type = kwargs['force_crawler']
            if forced_type in self.crawlers:
                content_type = forced_type
                logger.info(f"Forcing crawler type: {forced_type}")
        
        crawler_class = self.crawlers.get(content_type, HTMLCrawler)
        
        # Initialize crawler with proxy manager
        crawler_kwargs = {
            'proxy_manager': self.proxy_manager,
            'max_retries': kwargs.get('max_retries', 3),
            'delay': kwargs.get('delay', 1.0)
        }
        
        # Add crawler-specific options
        if content_type == 'js':
            crawler_kwargs.update({
                'headless': kwargs.get('headless', True),
                'browser_type': kwargs.get('browser_type', 'chromium')
            })
        elif content_type == 'pdf':
            crawler_kwargs.update({
                'extract_images': kwargs.get('extract_images', True),
                'extract_tables': kwargs.get('extract_tables', True)
            })
        
        logger.info(f"Selected {content_type} crawler for {url}")
        return crawler_class(**crawler_kwargs)
    
    async def crawl_auto(self, url: str, **kwargs) -> Dict[str, Any]:
        """Automatically detect content type and crawl with appropriate crawler."""
        crawler = await self.get_crawler(url, **kwargs)
        
        try:
            result = await crawler.crawl(url, **kwargs)
            return result
        finally:
            await crawler.close()