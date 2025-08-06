"""
Main proxy manager for handling proxy rotation and validation.
"""

import asyncio
import logging
import random
from typing import List, Dict, Any, Optional
import aiohttp
import time
from urllib.parse import urlparse

from .proxy_validator import ProxyValidator
from .headers_spoofing import HeadersSpoofing

logger = logging.getLogger(__name__)


class ProxyManager:
    """Manages proxy pools with automatic rotation and health checking."""
    
    def __init__(self, 
                 proxy_sources: Optional[List[str]] = None,
                 max_failures: int = 3,
                 health_check_interval: int = 300,
                 rotation_strategy: str = 'round_robin'):
        """
        Initialize proxy manager.
        
        Args:
            proxy_sources: List of proxy URLs or sources
            max_failures: Maximum failures before marking proxy as bad
            health_check_interval: Seconds between health checks
            rotation_strategy: 'round_robin', 'random', 'least_used'
        """
        self.proxy_sources = proxy_sources or []
        self.max_failures = max_failures
        self.health_check_interval = health_check_interval
        self.rotation_strategy = rotation_strategy
        
        self.proxy_validator = ProxyValidator()
        self.headers_spoofing = HeadersSpoofing()
        
        # Proxy pools
        self.active_proxies = []
        self.inactive_proxies = []
        self.proxy_stats = {}  # Track usage and failure stats
        
        # Current proxy tracking
        self.current_proxy_index = 0
        self.current_proxy = None
        
        # Health check task
        self.health_check_task = None
        self.is_running = False
        
        # Built-in free proxy sources (for demo purposes)
        self.free_proxy_sources = [
            'https://api.proxyscrape.com/v2/?request=get&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all',
            'https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt',
            'https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt'
        ]
    
    async def start(self):
        """Start the proxy manager."""
        if self.is_running:
            return
        
        self.is_running = True
        logger.info("Starting proxy manager...")
        
        # Load initial proxies
        await self.load_proxies()
        
        # Start health check task
        self.health_check_task = asyncio.create_task(self._health_check_loop())
        
        logger.info(f"Proxy manager started with {len(self.active_proxies)} active proxies")
    
    async def stop(self):
        """Stop the proxy manager."""
        if not self.is_running:
            return
        
        self.is_running = False
        
        if self.health_check_task:
            self.health_check_task.cancel()
            try:
                await self.health_check_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Proxy manager stopped")
    
    async def load_proxies(self):
        """Load proxies from sources."""
        all_proxies = []
        
        # Load from provided sources
        for source in self.proxy_sources:
            if source.startswith('http'):
                # URL source
                proxies = await self._fetch_proxies_from_url(source)
                all_proxies.extend(proxies)
            else:
                # Assume it's a proxy URL directly
                all_proxies.append(source)
        
        # Load from free sources if no proxies provided
        if not all_proxies and not self.proxy_sources:
            logger.info("No proxy sources provided, loading from free sources...")
            for source in self.free_proxy_sources:
                try:
                    proxies = await self._fetch_proxies_from_url(source)
                    all_proxies.extend(proxies[:10])  # Limit free proxies
                except Exception as e:
                    logger.warning(f"Failed to load from {source}: {e}")
        
        # Validate and add proxies
        valid_proxies = []
        for proxy_url in all_proxies:
            try:
                # Basic URL validation
                parsed = urlparse(proxy_url)
                if not parsed.netloc:
                    # Assume it's in format IP:PORT
                    proxy_url = f"http://{proxy_url}"
                
                # Initialize proxy stats
                self.proxy_stats[proxy_url] = {
                    'failures': 0,
                    'successes': 0,
                    'last_used': 0,
                    'response_times': [],
                    'is_healthy': True
                }
                
                valid_proxies.append(proxy_url)
                
            except Exception as e:
                logger.warning(f"Invalid proxy URL {proxy_url}: {e}")
        
        self.active_proxies = valid_proxies
        logger.info(f"Loaded {len(self.active_proxies)} proxies")
        
        # Validate proxies in background
        if self.active_proxies:
            asyncio.create_task(self._validate_all_proxies())
    
    async def _fetch_proxies_from_url(self, url: str) -> List[str]:
        """Fetch proxy list from URL."""
        proxies = []
        
        try:
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        content = await response.text()
                        
                        # Parse different formats
                        lines = content.strip().split('\n')
                        for line in lines:
                            line = line.strip()
                            
                            # Skip empty lines and comments
                            if not line or line.startswith('#'):
                                continue
                            
                            # Handle JSON format
                            if line.startswith('{') and 'ip' in line:
                                try:
                                    import json
                                    proxy_data = json.loads(line)
                                    ip = proxy_data.get('ip')
                                    port = proxy_data.get('port')
                                    if ip and port:
                                        proxies.append(f"http://{ip}:{port}")
                                except:
                                    pass
                            
                            # Handle IP:PORT format
                            elif ':' in line:
                                parts = line.split(':')
                                if len(parts) >= 2:
                                    ip = parts[0]
                                    port = parts[1]
                                    
                                    # Basic IP validation
                                    if self._is_valid_ip(ip) and port.isdigit():
                                        proxies.append(f"http://{ip}:{port}")
                        
        except Exception as e:
            logger.error(f"Failed to fetch proxies from {url}: {e}")
        
        return proxies
    
    def _is_valid_ip(self, ip: str) -> bool:
        """Basic IP address validation."""
        try:
            parts = ip.split('.')
            return len(parts) == 4 and all(0 <= int(part) <= 255 for part in parts)
        except:
            return False
    
    async def get_proxy(self) -> Optional[str]:
        """Get the current proxy URL."""
        if not self.active_proxies:
            return None
        
        if self.rotation_strategy == 'round_robin':
            proxy = self.active_proxies[self.current_proxy_index]
            self.current_proxy = proxy
            
        elif self.rotation_strategy == 'random':
            proxy = random.choice(self.active_proxies)
            self.current_proxy = proxy
            
        elif self.rotation_strategy == 'least_used':
            # Find proxy with least usage
            proxy = min(self.active_proxies, 
                       key=lambda p: self.proxy_stats[p]['successes'] + self.proxy_stats[p]['failures'])
            self.current_proxy = proxy
        
        else:
            proxy = self.active_proxies[0]
            self.current_proxy = proxy
        
        # Update last used time
        if proxy in self.proxy_stats:
            self.proxy_stats[proxy]['last_used'] = time.time()
        
        return proxy
    
    async def rotate_proxy(self):
        """Rotate to the next proxy."""
        if not self.active_proxies:
            return
        
        # Mark current proxy as having a failure
        if self.current_proxy and self.current_proxy in self.proxy_stats:
            self.proxy_stats[self.current_proxy]['failures'] += 1
            
            # Move to inactive if too many failures
            if self.proxy_stats[self.current_proxy]['failures'] >= self.max_failures:
                await self._mark_proxy_inactive(self.current_proxy)
        
        # Move to next proxy
        if self.rotation_strategy == 'round_robin':
            self.current_proxy_index = (self.current_proxy_index + 1) % len(self.active_proxies)
        
        # Get new proxy
        await self.get_proxy()
        
        logger.info(f"Rotated to proxy: {self.current_proxy}")
    
    async def mark_proxy_success(self, proxy_url: str, response_time: float = 0):
        """Mark a proxy as successful."""
        if proxy_url in self.proxy_stats:
            stats = self.proxy_stats[proxy_url]
            stats['successes'] += 1
            stats['response_times'].append(response_time)
            
            # Keep only last 10 response times
            if len(stats['response_times']) > 10:
                stats['response_times'] = stats['response_times'][-10:]
    
    async def _mark_proxy_inactive(self, proxy_url: str):
        """Move proxy from active to inactive."""
        if proxy_url in self.active_proxies:
            self.active_proxies.remove(proxy_url)
            self.inactive_proxies.append(proxy_url)
            self.proxy_stats[proxy_url]['is_healthy'] = False
            
            logger.warning(f"Moved proxy to inactive: {proxy_url}")
            
            # Adjust current index if needed
            if self.current_proxy_index >= len(self.active_proxies) and self.active_proxies:
                self.current_proxy_index = 0
    
    async def _validate_all_proxies(self):
        """Validate all proxies in the background."""
        tasks = []
        for proxy_url in self.active_proxies[:]:  # Copy list to avoid modification during iteration
            task = asyncio.create_task(self._validate_single_proxy(proxy_url))
            tasks.append(task)
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _validate_single_proxy(self, proxy_url: str):
        """Validate a single proxy."""
        try:
            is_valid = await self.proxy_validator.validate_proxy(proxy_url)
            if not is_valid:
                await self._mark_proxy_inactive(proxy_url)
        except Exception as e:
            logger.warning(f"Error validating proxy {proxy_url}: {e}")
    
    async def _health_check_loop(self):
        """Background task for periodic health checks."""
        while self.is_running:
            try:
                await asyncio.sleep(self.health_check_interval)
                
                if not self.is_running:
                    break
                
                logger.info("Running proxy health check...")
                
                # Check inactive proxies for recovery
                recovered_proxies = []
                for proxy_url in self.inactive_proxies[:]:
                    try:
                        is_valid = await self.proxy_validator.validate_proxy(proxy_url)
                        if is_valid:
                            recovered_proxies.append(proxy_url)
                    except Exception as e:
                        logger.debug(f"Proxy still inactive {proxy_url}: {e}")
                
                # Move recovered proxies back to active
                for proxy_url in recovered_proxies:
                    self.inactive_proxies.remove(proxy_url)
                    self.active_proxies.append(proxy_url)
                    self.proxy_stats[proxy_url]['is_healthy'] = True
                    self.proxy_stats[proxy_url]['failures'] = 0  # Reset failures
                    logger.info(f"Recovered proxy: {proxy_url}")
                
                # Validate random sample of active proxies
                if self.active_proxies:
                    sample_size = min(5, len(self.active_proxies))
                    sample_proxies = random.sample(self.active_proxies, sample_size)
                    
                    for proxy_url in sample_proxies:
                        try:
                            is_valid = await self.proxy_validator.validate_proxy(proxy_url)
                            if not is_valid:
                                await self._mark_proxy_inactive(proxy_url)
                        except Exception as e:
                            logger.debug(f"Health check failed for {proxy_url}: {e}")
                
                logger.info(f"Health check complete. Active: {len(self.active_proxies)}, Inactive: {len(self.inactive_proxies)}")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get proxy statistics."""
        stats = {
            'active_count': len(self.active_proxies),
            'inactive_count': len(self.inactive_proxies),
            'current_proxy': self.current_proxy,
            'rotation_strategy': self.rotation_strategy,
            'proxy_details': {}
        }
        
        for proxy_url, proxy_stats in self.proxy_stats.items():
            avg_response_time = 0
            if proxy_stats['response_times']:
                avg_response_time = sum(proxy_stats['response_times']) / len(proxy_stats['response_times'])
            
            stats['proxy_details'][proxy_url] = {
                'successes': proxy_stats['successes'],
                'failures': proxy_stats['failures'],
                'avg_response_time': avg_response_time,
                'is_healthy': proxy_stats['is_healthy'],
                'last_used': proxy_stats['last_used']
            }
        
        return stats
    
    async def add_proxy(self, proxy_url: str):
        """Add a new proxy to the pool."""
        try:
            # Validate the proxy first
            is_valid = await self.proxy_validator.validate_proxy(proxy_url)
            if is_valid:
                self.active_proxies.append(proxy_url)
                self.proxy_stats[proxy_url] = {
                    'failures': 0,
                    'successes': 0,
                    'last_used': 0,
                    'response_times': [],
                    'is_healthy': True
                }
                logger.info(f"Added new proxy: {proxy_url}")
                return True
            else:
                logger.warning(f"Proxy validation failed: {proxy_url}")
                return False
        except Exception as e:
            logger.error(f"Error adding proxy {proxy_url}: {e}")
            return False
    
    async def remove_proxy(self, proxy_url: str):
        """Remove a proxy from the pool."""
        removed = False
        
        if proxy_url in self.active_proxies:
            self.active_proxies.remove(proxy_url)
            removed = True
        
        if proxy_url in self.inactive_proxies:
            self.inactive_proxies.remove(proxy_url)
            removed = True
        
        if proxy_url in self.proxy_stats:
            del self.proxy_stats[proxy_url]
        
        if removed:
            logger.info(f"Removed proxy: {proxy_url}")
            
            # Adjust current index if needed
            if self.current_proxy_index >= len(self.active_proxies) and self.active_proxies:
                self.current_proxy_index = 0
        
        return removed