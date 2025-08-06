"""
Headers spoofing and randomization for avoiding detection.
"""

import random
import logging
from typing import Dict, List, Any, Optional
import time
from fake_useragent import UserAgent

logger = logging.getLogger(__name__)


class HeadersSpoofing:
    """Generates realistic and randomized HTTP headers to avoid detection."""
    
    def __init__(self):
        self.user_agent = UserAgent()
        
        # Common browser versions and their characteristics
        self.browser_profiles = {
            'chrome': {
                'versions': ['120.0.0.0', '119.0.0.0', '118.0.0.0', '117.0.0.0'],
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'accept_encoding': 'gzip, deflate, br',
                'accept_language': 'en-US,en;q=0.9',
                'cache_control': 'max-age=0',
                'sec_ch_ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                'sec_ch_ua_mobile': '?0',
                'sec_ch_ua_platform': '"Windows"',
                'sec_fetch_dest': 'document',
                'sec_fetch_mode': 'navigate',
                'sec_fetch_site': 'none',
                'sec_fetch_user': '?1',
                'upgrade_insecure_requests': '1'
            },
            'firefox': {
                'versions': ['121.0', '120.0', '119.0', '118.0'],
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'accept_encoding': 'gzip, deflate, br',
                'accept_language': 'en-US,en;q=0.5',
                'cache_control': 'max-age=0',
                'upgrade_insecure_requests': '1'
            },
            'safari': {
                'versions': ['17.1', '17.0', '16.6', '16.5'],
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'accept_encoding': 'gzip, deflate, br',
                'accept_language': 'en-US,en;q=0.9',
                'cache_control': 'max-age=0'
            }
        }
        
        # Operating systems and their characteristics
        self.os_profiles = {
            'windows': {
                'platforms': ['Windows NT 10.0; Win64; x64', 'Windows NT 10.0; WOW64', 'Windows NT 6.1; Win64; x64'],
                'weight': 0.7
            },
            'macos': {
                'platforms': ['Macintosh; Intel Mac OS X 10_15_7', 'Macintosh; Intel Mac OS X 10_14_6'],
                'weight': 0.2
            },
            'linux': {
                'platforms': ['X11; Linux x86_64', 'X11; Ubuntu; Linux x86_64'],
                'weight': 0.1
            }
        }
        
        # Common screen resolutions
        self.screen_resolutions = [
            '1920x1080', '1366x768', '1536x864', '1440x900', 
            '1280x720', '1600x900', '2560x1440', '3840x2160'
        ]
        
        # Time zones for realistic headers
        self.timezones = [
            'America/New_York', 'America/Los_Angeles', 'Europe/London',
            'Europe/Berlin', 'Asia/Tokyo', 'Australia/Sydney',
            'America/Chicago', 'Europe/Paris'
        ]
        
        # Common languages
        self.languages = [
            'en-US,en;q=0.9',
            'en-GB,en;q=0.9',
            'en-US,en;q=0.8,es;q=0.6',
            'de-DE,de;q=0.9,en;q=0.8',
            'fr-FR,fr;q=0.9,en;q=0.8',
            'ja-JP,ja;q=0.9,en;q=0.8'
        ]
    
    def generate_headers(self, 
                        browser: Optional[str] = None,
                        mobile: bool = False,
                        referer: Optional[str] = None,
                        custom_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """
        Generate realistic HTTP headers.
        
        Args:
            browser: Specific browser to emulate ('chrome', 'firefox', 'safari')
            mobile: Whether to generate mobile headers
            referer: Custom referer header
            custom_headers: Additional custom headers to include
            
        Returns:
            Dictionary of HTTP headers
        """
        
        # Select browser profile
        if not browser:
            browser = random.choice(list(self.browser_profiles.keys()))
        
        if browser not in self.browser_profiles:
            browser = 'chrome'  # Default fallback
        
        profile = self.browser_profiles[browser]
        
        # Select OS
        os_choice = self._weighted_choice(self.os_profiles)
        os_platform = random.choice(self.os_profiles[os_choice]['platforms'])
        
        # Generate User-Agent
        user_agent = self._generate_user_agent(browser, profile, os_platform, mobile)
        
        # Base headers
        headers = {
            'User-Agent': user_agent,
            'Accept': profile['accept'],
            'Accept-Language': random.choice(self.languages),
            'Accept-Encoding': profile['accept_encoding'],
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'DNT': random.choice(['1', '0']),  # Do Not Track
        }
        
        # Add browser-specific headers
        if browser == 'chrome':
            headers.update({
                'sec-ch-ua': profile['sec_ch_ua'],
                'sec-ch-ua-mobile': '?1' if mobile else '?0',
                'sec-ch-ua-platform': f'"{os_choice.title()}"',
                'Sec-Fetch-Dest': profile.get('sec_fetch_dest', 'document'),
                'Sec-Fetch-Mode': profile.get('sec_fetch_mode', 'navigate'),
                'Sec-Fetch-Site': profile.get('sec_fetch_site', 'none'),
                'Sec-Fetch-User': profile.get('sec_fetch_user', '?1')
            })
        
        # Add cache control occasionally
        if random.random() < 0.7:
            headers['Cache-Control'] = profile.get('cache_control', 'max-age=0')
        
        # Add referer if provided or generate one occasionally
        if referer:
            headers['Referer'] = referer
        elif random.random() < 0.3:  # 30% chance of having a referer
            headers['Referer'] = self._generate_referer()
        
        # Add mobile-specific headers
        if mobile:
            headers.update(self._get_mobile_headers())
        
        # Add custom headers
        if custom_headers:
            headers.update(custom_headers)
        
        return headers
    
    def _generate_user_agent(self, browser: str, profile: Dict, os_platform: str, mobile: bool) -> str:
        """Generate a realistic User-Agent string."""
        
        version = random.choice(profile['versions'])
        
        if mobile:
            if browser == 'chrome':
                return f"Mozilla/5.0 (Linux; Android 12; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version} Mobile Safari/537.36"
            elif browser == 'firefox':
                return f"Mozilla/5.0 (Mobile; rv:{version}) Gecko/{version} Firefox/{version}"
            elif browser == 'safari':
                return f"Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/{version} Mobile/15E148 Safari/604.1"
        else:
            if browser == 'chrome':
                return f"Mozilla/5.0 ({os_platform}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version} Safari/537.36"
            elif browser == 'firefox':
                return f"Mozilla/5.0 ({os_platform}; rv:{version}) Gecko/20100101 Firefox/{version}"
            elif browser == 'safari':
                return f"Mozilla/5.0 ({os_platform}) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/{version} Safari/605.1.15"
        
        # Fallback to fake-useragent
        try:
            return self.user_agent.random
        except:
            return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    
    def _weighted_choice(self, choices: Dict[str, Dict]) -> str:
        """Make a weighted random choice."""
        weights = [info.get('weight', 1.0) for info in choices.values()]
        return random.choices(list(choices.keys()), weights=weights)[0]
    
    def _generate_referer(self) -> str:
        """Generate a realistic referer URL."""
        referers = [
            'https://www.google.com/',
            'https://www.bing.com/',
            'https://duckduckgo.com/',
            'https://search.yahoo.com/',
            'https://www.reddit.com/',
            'https://twitter.com/',
            'https://www.linkedin.com/',
            'https://www.facebook.com/'
        ]
        return random.choice(referers)
    
    def _get_mobile_headers(self) -> Dict[str, str]:
        """Get additional headers for mobile devices."""
        return {
            'X-Requested-With': random.choice(['XMLHttpRequest', '']),
            'Viewport-Width': str(random.randint(360, 428)),
            'Device-Memory': random.choice(['2', '4', '8']),
        }
    
    def generate_session_headers(self, base_url: str, page_type: str = 'general') -> Dict[str, str]:
        """
        Generate headers for a browsing session that appear to navigate naturally.
        
        Args:
            base_url: Base URL being browsed
            page_type: Type of page ('search', 'product', 'article', 'general')
            
        Returns:
            Session-appropriate headers
        """
        headers = self.generate_headers()
        
        # Modify headers based on page type
        if page_type == 'search':
            headers['Referer'] = random.choice([
                'https://www.google.com/search?q=',
                'https://www.bing.com/search?q=',
                'https://duckduckgo.com/?q='
            ])
            
        elif page_type == 'product':
            headers['Sec-Fetch-Dest'] = 'document'
            headers['Sec-Fetch-Mode'] = 'navigate'
            
        elif page_type == 'article':
            headers['Accept'] = 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        
        # Add realistic session timing
        headers['X-Session-Time'] = str(int(time.time()))
        
        return headers
    
    def generate_api_headers(self, api_type: str = 'rest') -> Dict[str, str]:
        """Generate headers for API requests."""
        base_headers = {
            'Accept': 'application/json, text/plain, */*',
            'Content-Type': 'application/json',
            'User-Agent': self.user_agent.random
        }
        
        if api_type == 'graphql':
            base_headers['Content-Type'] = 'application/json'
            base_headers['Accept'] = 'application/json'
            
        elif api_type == 'soap':
            base_headers['Content-Type'] = 'text/xml; charset=utf-8'
            base_headers['SOAPAction'] = '""'
        
        return base_headers
    
    def add_anti_detection_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Add headers specifically designed to avoid detection."""
        anti_detection = headers.copy()
        
        # Remove or modify headers that might indicate automation
        automation_headers = [
            'X-Automated',
            'X-Bot',
            'Selenium',
            'PhantomJS',
            'HeadlessChrome'
        ]
        
        for header in automation_headers:
            anti_detection.pop(header, None)
        
        # Add headers that make requests look more human
        if random.random() < 0.8:  # 80% chance
            anti_detection['Accept-CH'] = 'Sec-CH-UA, Sec-CH-UA-Mobile, Sec-CH-UA-Platform'
        
        if random.random() < 0.6:  # 60% chance
            anti_detection['Sec-GPC'] = '1'  # Global Privacy Control
        
        # Randomize header order (some implementations preserve order)
        header_items = list(anti_detection.items())
        random.shuffle(header_items)
        
        return dict(header_items)
    
    def get_headers_for_site(self, domain: str) -> Dict[str, str]:
        """Get headers optimized for specific website domains."""
        
        # Site-specific optimizations
        site_configs = {
            'amazon.com': {
                'browser': 'chrome',
                'additional_headers': {
                    'x-amz-user-agent': 'aws-sdk-js/2.1.0 promise',
                    'X-Amz-Content-Sha256': 'UNSIGNED-PAYLOAD'
                }
            },
            'google.com': {
                'browser': 'chrome',
                'additional_headers': {
                    'X-Client-Data': 'CKa1yQEIpbbJAQiptskBCMS2yQEIqZ3KAQioo8oBCKijygEI2qPKAQjLqMoBCLGrygEI2K3KAQ=='
                }
            },
            'facebook.com': {
                'browser': 'chrome',
                'additional_headers': {
                    'X-FB-Connection-Quality': 'GOOD',
                    'X-FB-LSD': 'AVqbxe_T'
                }
            },
            'linkedin.com': {
                'browser': 'chrome',
                'additional_headers': {
                    'X-Li-Track': '{"clientVersion":"1.0.0","osName":"web","timezoneOffset":300,"timezone":"America/New_York"}'
                }
            }
        }
        
        # Extract domain from URL if needed
        if '://' in domain:
            from urllib.parse import urlparse
            domain = urlparse(domain).netloc
        
        # Remove www. prefix
        domain = domain.replace('www.', '')
        
        # Get site-specific config
        config = site_configs.get(domain, {'browser': None, 'additional_headers': {}})
        
        # Generate headers
        headers = self.generate_headers(browser=config['browser'])
        
        # Add site-specific headers
        headers.update(config['additional_headers'])
        
        return headers
    
    def randomize_headers_timing(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Add timing-based randomization to headers."""
        timed_headers = headers.copy()
        
        # Add timestamp-based headers
        current_time = int(time.time())
        
        # Some sites check for reasonable timing
        if random.random() < 0.3:
            timed_headers['X-Request-Time'] = str(current_time)
        
        # Random delay simulation
        if random.random() < 0.2:
            timed_headers['X-Processing-Time'] = str(random.randint(10, 200))
        
        return timed_headers