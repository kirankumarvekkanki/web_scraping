"""
JavaScript-rendered page crawler using Playwright for dynamic content.
"""

import asyncio
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from typing import Dict, Any, Optional, List
import logging
import json

from .base_crawler import BaseCrawler

logger = logging.getLogger(__name__)


class JSCrawler(BaseCrawler):
    """Crawler for JavaScript-rendered pages using Playwright."""
    
    def __init__(self, headless: bool = True, browser_type: str = 'chromium', **kwargs):
        super().__init__(**kwargs)
        self.headless = headless
        self.browser_type = browser_type
        self.playwright = None
        self.browser = None
        self.context = None
        self.stealth_enabled = True
    
    async def _setup_browser(self):
        """Initialize Playwright browser."""
        if not self.playwright:
            self.playwright = await async_playwright().start()
            
            # Choose browser type
            if self.browser_type == 'firefox':
                browser_launcher = self.playwright.firefox
            elif self.browser_type == 'webkit':
                browser_launcher = self.playwright.webkit
            else:
                browser_launcher = self.playwright.chromium
            
            # Launch browser with stealth settings
            self.browser = await browser_launcher.launch(
                headless=self.headless,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor'
                ]
            )
            
            # Create context with stealth settings
            self.context = await self.browser.new_context(
                user_agent=self.user_agent.random,
                viewport={'width': 1920, 'height': 1080},
                extra_http_headers=self.get_headers()
            )
            
            # Add stealth scripts
            if self.stealth_enabled:
                await self._add_stealth_scripts()
    
    async def _add_stealth_scripts(self):
        """Add stealth scripts to avoid detection."""
        stealth_script = """
        // Overwrite the `plugins` property to use a custom getter.
        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5]
        });
        
        // Overwrite the `languages` property to use a custom getter.
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en']
        });
        
        // Overwrite the `webdriver` property to remove it.
        delete navigator.__proto__.webdriver;
        
        // Mock chrome object
        window.chrome = {
            runtime: {}
        };
        
        // Mock permissions
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
        );
        """
        
        await self.context.add_init_script(stealth_script)
    
    async def _fetch_content(self, url: str, **kwargs) -> Dict[str, Any]:
        """Fetch content using Playwright."""
        await self._setup_browser()
        
        page = await self.context.new_page()
        
        try:
            # Set proxy if available
            if self.proxy_manager:
                proxy_url = await self.proxy_manager.get_proxy()
                if proxy_url:
                    # Note: Playwright proxy setting needs to be done at browser launch
                    # This is a simplified approach
                    pass
            
            # Configure page settings
            await page.set_extra_http_headers(self.get_headers())
            
            # Navigate to page with options
            wait_until = kwargs.get('wait_until', 'networkidle')
            timeout = kwargs.get('timeout', 30000)
            
            await page.goto(url, wait_until=wait_until, timeout=timeout)
            
            # Wait for additional loading if specified
            if 'wait_for_selector' in kwargs:
                await page.wait_for_selector(kwargs['wait_for_selector'], timeout=timeout)
            
            if 'wait_for_function' in kwargs:
                await page.wait_for_function(kwargs['wait_for_function'], timeout=timeout)
            
            # Additional wait time
            additional_wait = kwargs.get('additional_wait', 2)
            await asyncio.sleep(additional_wait)
            
            # Extract page content
            content = {
                'html': await page.content(),
                'title': await page.title(),
                'url': page.url,
                'cookies': await self.context.cookies(),
                'local_storage': await page.evaluate('() => JSON.stringify(localStorage)'),
                'session_storage': await page.evaluate('() => JSON.stringify(sessionStorage)'),
                'page_metrics': await self._get_page_metrics(page),
                'console_logs': [],  # Will be populated by listener
                'network_requests': []  # Will be populated by listener
            }
            
            return content
            
        except Exception as e:
            logger.error(f"Error fetching content from {url}: {e}")
            raise
        finally:
            await page.close()
    
    async def _get_page_metrics(self, page: Page) -> Dict[str, Any]:
        """Get page performance metrics."""
        try:
            metrics = await page.evaluate("""
                () => {
                    const navigation = performance.getEntriesByType('navigation')[0];
                    return {
                        load_time: navigation ? navigation.loadEventEnd - navigation.loadEventStart : 0,
                        dom_content_loaded: navigation ? navigation.domContentLoadedEventEnd - navigation.domContentLoadedEventStart : 0,
                        first_paint: performance.getEntriesByName('first-paint')[0]?.startTime || 0,
                        first_contentful_paint: performance.getEntriesByName('first-contentful-paint')[0]?.startTime || 0
                    }
                }
            """)
            return metrics
        except Exception as e:
            logger.warning(f"Could not get page metrics: {e}")
            return {}
    
    async def parse_content(self, content: Dict[str, Any], url: str) -> Dict[str, Any]:
        """Parse JavaScript-rendered content."""
        from bs4 import BeautifulSoup
        
        html_content = content.get('html', '')
        soup = BeautifulSoup(html_content, 'lxml')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.extract()
        
        parsed_data = {
            'title': content.get('title', ''),
            'url': content.get('url', url),
            'cookies': content.get('cookies', []),
            'local_storage': self._parse_storage(content.get('local_storage', '{}')),
            'session_storage': self._parse_storage(content.get('session_storage', '{}')),
            'page_metrics': content.get('page_metrics', {}),
            'headings': self._extract_headings(soup),
            'links': self._extract_links(soup, url),
            'images': self._extract_images(soup, url),
            'text_content': self._extract_text_content(soup),
            'tables': self._extract_tables(soup),
            'forms': self._extract_forms(soup),
            'lists': self._extract_lists(soup),
            'interactive_elements': self._extract_interactive_elements(soup),
            'raw_html': html_content
        }
        
        return parsed_data
    
    def _parse_storage(self, storage_json: str) -> Dict[str, Any]:
        """Parse localStorage/sessionStorage JSON."""
        try:
            return json.loads(storage_json)
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def _extract_headings(self, soup: BeautifulSoup) -> Dict[str, list]:
        """Extract all headings (h1-h6)."""
        headings = {}
        for i in range(1, 7):
            tag = f'h{i}'
            headings[tag] = [h.get_text().strip() for h in soup.find_all(tag)]
        return headings
    
    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> list:
        """Extract all links from the page."""
        links = []
        for link in soup.find_all('a', href=True):
            href = link['href']
            text = link.get_text().strip()
            absolute_url = self.resolve_url(base_url, href)
            
            links.append({
                'url': absolute_url,
                'text': text,
                'title': link.get('title', ''),
                'rel': link.get('rel', [])
            })
        
        return links
    
    def _extract_images(self, soup: BeautifulSoup, base_url: str) -> list:
        """Extract all images from the page."""
        images = []
        for img in soup.find_all('img'):
            src = img.get('src')
            if src:
                absolute_url = self.resolve_url(base_url, src)
                images.append({
                    'url': absolute_url,
                    'alt': img.get('alt', ''),
                    'title': img.get('title', ''),
                    'width': img.get('width'),
                    'height': img.get('height')
                })
        
        return images
    
    def _extract_text_content(self, soup: BeautifulSoup) -> str:
        """Extract clean text content preserving formatting."""
        # Preserve line breaks for block elements
        for br in soup.find_all("br"):
            br.replace_with("\n")
        
        for p in soup.find_all(["p", "div", "li", "td", "th"]):
            p.append("\n")
        
        text = soup.get_text()
        
        # Clean up multiple newlines and spaces
        lines = [line.strip() for line in text.splitlines()]
        return '\n'.join(line for line in lines if line)
    
    def _extract_tables(self, soup: BeautifulSoup) -> list:
        """Extract table data."""
        tables = []
        for table in soup.find_all('table'):
            headers = []
            rows = []
            
            # Extract headers
            header_row = table.find('tr')
            if header_row:
                headers = [th.get_text().strip() for th in header_row.find_all(['th', 'td'])]
            
            # Extract data rows
            for row in table.find_all('tr')[1:]:  # Skip header row
                cells = [td.get_text().strip() for td in row.find_all(['td', 'th'])]
                if cells:
                    rows.append(cells)
            
            if headers or rows:
                tables.append({
                    'headers': headers,
                    'rows': rows
                })
        
        return tables
    
    def _extract_forms(self, soup: BeautifulSoup) -> list:
        """Extract form information."""
        forms = []
        for form in soup.find_all('form'):
            fields = []
            for input_field in form.find_all(['input', 'select', 'textarea']):
                field_info = {
                    'tag': input_field.name,
                    'type': input_field.get('type', ''),
                    'name': input_field.get('name', ''),
                    'id': input_field.get('id', ''),
                    'placeholder': input_field.get('placeholder', ''),
                    'required': input_field.has_attr('required')
                }
                fields.append(field_info)
            
            forms.append({
                'action': form.get('action', ''),
                'method': form.get('method', 'GET'),
                'fields': fields
            })
        
        return forms
    
    def _extract_lists(self, soup: BeautifulSoup) -> Dict[str, list]:
        """Extract list items."""
        lists = {'ul': [], 'ol': []}
        
        for ul in soup.find_all('ul'):
            items = [li.get_text().strip() for li in ul.find_all('li')]
            if items:
                lists['ul'].append(items)
        
        for ol in soup.find_all('ol'):
            items = [li.get_text().strip() for li in ol.find_all('li')]
            if items:
                lists['ol'].append(items)
        
        return lists
    
    def _extract_interactive_elements(self, soup: BeautifulSoup) -> Dict[str, list]:
        """Extract interactive elements specific to JS pages."""
        elements = {
            'buttons': [],
            'inputs': [],
            'selects': [],
            'textareas': []
        }
        
        # Extract buttons
        for button in soup.find_all(['button', 'input']):
            if button.name == 'input' and button.get('type') not in ['button', 'submit', 'reset']:
                continue
            
            elements['buttons'].append({
                'text': button.get_text().strip(),
                'type': button.get('type', ''),
                'id': button.get('id', ''),
                'class': button.get('class', [])
            })
        
        # Extract input fields
        for input_field in soup.find_all('input'):
            if input_field.get('type') in ['button', 'submit', 'reset']:
                continue
                
            elements['inputs'].append({
                'type': input_field.get('type', 'text'),
                'name': input_field.get('name', ''),
                'id': input_field.get('id', ''),
                'placeholder': input_field.get('placeholder', ''),
                'value': input_field.get('value', '')
            })
        
        # Extract select elements
        for select in soup.find_all('select'):
            options = [opt.get_text().strip() for opt in select.find_all('option')]
            elements['selects'].append({
                'name': select.get('name', ''),
                'id': select.get('id', ''),
                'options': options
            })
        
        # Extract textareas
        for textarea in soup.find_all('textarea'):
            elements['textareas'].append({
                'name': textarea.get('name', ''),
                'id': textarea.get('id', ''),
                'placeholder': textarea.get('placeholder', ''),
                'text': textarea.get_text().strip()
            })
        
        return elements
    
    async def close(self):
        """Clean up Playwright resources."""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()