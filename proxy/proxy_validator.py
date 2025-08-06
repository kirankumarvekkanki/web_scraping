"""
Proxy validation and testing functionality.
"""

import asyncio
import aiohttp
import time
import logging
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class ProxyValidator:
    """Validates proxy functionality and performance."""
    
    def __init__(self, 
                 test_urls: Optional[List[str]] = None,
                 timeout: int = 10,
                 max_response_time: float = 5.0):
        """
        Initialize proxy validator.
        
        Args:
            test_urls: URLs to test proxy against
            timeout: Request timeout in seconds
            max_response_time: Maximum acceptable response time
        """
        self.test_urls = test_urls or [
            'http://httpbin.org/ip',
            'https://httpbin.org/user-agent',
            'http://ipinfo.io/json',
            'https://api.ipify.org?format=json'
        ]
        self.timeout = timeout
        self.max_response_time = max_response_time
    
    async def validate_proxy(self, proxy_url: str) -> bool:
        """
        Validate a proxy by testing it against test URLs.
        
        Args:
            proxy_url: Proxy URL to validate
            
        Returns:
            True if proxy is working, False otherwise
        """
        try:
            # Test basic connectivity
            basic_test = await self._test_basic_connectivity(proxy_url)
            if not basic_test:
                return False
            
            # Test against multiple URLs
            success_count = 0
            total_tests = min(2, len(self.test_urls))  # Test with first 2 URLs
            
            for test_url in self.test_urls[:total_tests]:
                try:
                    if await self._test_url(proxy_url, test_url):
                        success_count += 1
                except Exception as e:
                    logger.debug(f"Test failed for {proxy_url} on {test_url}: {e}")
            
            # Require at least 50% success rate
            success_rate = success_count / total_tests
            return success_rate >= 0.5
            
        except Exception as e:
            logger.debug(f"Proxy validation failed for {proxy_url}: {e}")
            return False
    
    async def _test_basic_connectivity(self, proxy_url: str) -> bool:
        """Test basic proxy connectivity."""
        try:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            
            # Parse proxy URL
            parsed_proxy = urlparse(proxy_url)
            if not parsed_proxy.netloc:
                return False
            
            # Test with a simple HTTP request
            async with aiohttp.ClientSession(timeout=timeout) as session:
                proxy_connector = aiohttp.ProxyConnector.from_url(proxy_url)
                
                async with session.get(
                    'http://httpbin.org/ip',
                    connector=proxy_connector
                ) as response:
                    return response.status == 200
                    
        except Exception as e:
            logger.debug(f"Basic connectivity test failed for {proxy_url}: {e}")
            return False
    
    async def _test_url(self, proxy_url: str, test_url: str) -> bool:
        """Test proxy against a specific URL."""
        try:
            start_time = time.time()
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                proxy_connector = aiohttp.ProxyConnector.from_url(proxy_url)
                
                async with session.get(
                    test_url,
                    connector=proxy_connector,
                    headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    }
                ) as response:
                    response_time = time.time() - start_time
                    
                    # Check response status and time
                    if response.status != 200:
                        return False
                    
                    if response_time > self.max_response_time:
                        logger.debug(f"Proxy {proxy_url} too slow: {response_time:.2f}s")
                        return False
                    
                    return True
                    
        except Exception as e:
            logger.debug(f"URL test failed for {proxy_url} on {test_url}: {e}")
            return False
    
    async def get_proxy_info(self, proxy_url: str) -> Dict[str, Any]:
        """Get detailed information about a proxy."""
        info = {
            'proxy_url': proxy_url,
            'is_working': False,
            'response_time': None,
            'ip_address': None,
            'location': None,
            'anonymity_level': None,
            'supports_https': False,
            'last_tested': time.time()
        }
        
        try:
            start_time = time.time()
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                proxy_connector = aiohttp.ProxyConnector.from_url(proxy_url)
                
                # Test IP detection
                try:
                    async with session.get(
                        'http://httpbin.org/ip',
                        connector=proxy_connector
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            info['ip_address'] = data.get('origin', '').split(',')[0].strip()
                            info['is_working'] = True
                            info['response_time'] = time.time() - start_time
                except Exception as e:
                    logger.debug(f"IP test failed for {proxy_url}: {e}")
                
                # Test HTTPS support
                if info['is_working']:
                    try:
                        async with session.get(
                            'https://httpbin.org/ip',
                            connector=proxy_connector
                        ) as response:
                            if response.status == 200:
                                info['supports_https'] = True
                    except Exception as e:
                        logger.debug(f"HTTPS test failed for {proxy_url}: {e}")
                
                # Test anonymity level
                if info['is_working']:
                    info['anonymity_level'] = await self._check_anonymity(session, proxy_connector)
                
                # Get location info
                if info['ip_address']:
                    info['location'] = await self._get_ip_location(info['ip_address'])
        
        except Exception as e:
            logger.debug(f"Failed to get proxy info for {proxy_url}: {e}")
        
        return info
    
    async def _check_anonymity(self, session: aiohttp.ClientSession, proxy_connector) -> str:
        """Check proxy anonymity level."""
        try:
            # Get headers as seen by the target server
            async with session.get(
                'http://httpbin.org/headers',
                connector=proxy_connector
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    headers = data.get('headers', {})
                    
                    # Check for proxy-related headers
                    proxy_headers = [
                        'X-Forwarded-For',
                        'X-Real-IP',
                        'Via',
                        'X-Proxy-Id',
                        'HTTP_X_FORWARDED_FOR'
                    ]
                    
                    found_proxy_headers = [h for h in proxy_headers if h in headers]
                    
                    if not found_proxy_headers:
                        return 'elite'  # High anonymity
                    elif len(found_proxy_headers) < 2:
                        return 'anonymous'  # Medium anonymity
                    else:
                        return 'transparent'  # Low anonymity
        
        except Exception as e:
            logger.debug(f"Anonymity check failed: {e}")
        
        return 'unknown'
    
    async def _get_ip_location(self, ip_address: str) -> Optional[Dict[str, Any]]:
        """Get location information for an IP address."""
        try:
            timeout = aiohttp.ClientTimeout(total=5)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                # Use free IP geolocation service
                async with session.get(f'http://ip-api.com/json/{ip_address}') as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('status') == 'success':
                            return {
                                'country': data.get('country'),
                                'country_code': data.get('countryCode'),
                                'region': data.get('regionName'),
                                'city': data.get('city'),
                                'timezone': data.get('timezone'),
                                'isp': data.get('isp')
                            }
        
        except Exception as e:
            logger.debug(f"Failed to get location for IP {ip_address}: {e}")
        
        return None
    
    async def validate_proxy_list(self, proxy_urls: List[str]) -> List[Dict[str, Any]]:
        """Validate a list of proxies and return detailed results."""
        tasks = []
        
        for proxy_url in proxy_urls:
            task = asyncio.create_task(self.get_proxy_info(proxy_url))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and return valid results
        valid_results = []
        for result in results:
            if isinstance(result, dict):
                valid_results.append(result)
            else:
                logger.warning(f"Proxy validation error: {result}")
        
        return valid_results
    
    async def benchmark_proxy(self, proxy_url: str, num_requests: int = 10) -> Dict[str, Any]:
        """Benchmark a proxy with multiple requests."""
        benchmark_results = {
            'proxy_url': proxy_url,
            'total_requests': num_requests,
            'successful_requests': 0,
            'failed_requests': 0,
            'average_response_time': 0,
            'min_response_time': float('inf'),
            'max_response_time': 0,
            'success_rate': 0,
            'errors': []
        }
        
        response_times = []
        
        for i in range(num_requests):
            try:
                start_time = time.time()
                
                if await self._test_url(proxy_url, 'http://httpbin.org/ip'):
                    response_time = time.time() - start_time
                    response_times.append(response_time)
                    benchmark_results['successful_requests'] += 1
                    
                    # Update min/max times
                    benchmark_results['min_response_time'] = min(
                        benchmark_results['min_response_time'], 
                        response_time
                    )
                    benchmark_results['max_response_time'] = max(
                        benchmark_results['max_response_time'], 
                        response_time
                    )
                else:
                    benchmark_results['failed_requests'] += 1
                
            except Exception as e:
                benchmark_results['failed_requests'] += 1
                benchmark_results['errors'].append(str(e))
            
            # Small delay between requests
            await asyncio.sleep(0.1)
        
        # Calculate statistics
        if response_times:
            benchmark_results['average_response_time'] = sum(response_times) / len(response_times)
        else:
            benchmark_results['min_response_time'] = 0
        
        benchmark_results['success_rate'] = benchmark_results['successful_requests'] / num_requests
        
        return benchmark_results
    
    def add_test_url(self, url: str):
        """Add a custom test URL."""
        if url not in self.test_urls:
            self.test_urls.append(url)
            logger.info(f"Added test URL: {url}")
    
    def remove_test_url(self, url: str):
        """Remove a test URL."""
        if url in self.test_urls:
            self.test_urls.remove(url)
            logger.info(f"Removed test URL: {url}")
    
    def get_test_urls(self) -> List[str]:
        """Get current test URLs."""
        return self.test_urls.copy()