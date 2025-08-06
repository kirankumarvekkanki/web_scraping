"""
HTML Crawler for static web pages using requests and BeautifulSoup.
"""

import asyncio
import aiohttp
from bs4 import BeautifulSoup
from typing import Dict, Any, Optional
import logging

from .base_crawler import BaseCrawler

logger = logging.getLogger(__name__)


class HTMLCrawler(BaseCrawler):
    """Crawler for HTML content using aiohttp and BeautifulSoup."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.timeout = aiohttp.ClientTimeout(total=30)
    
    async def _fetch_content(self, url: str, **kwargs) -> str:
        """Fetch HTML content using aiohttp."""
        headers = self.get_headers()
        
        # Add custom headers if provided
        if 'headers' in kwargs:
            headers.update(kwargs['headers'])
        
        connector_kwargs = {}
        if self.proxy_manager:
            proxy_url = await self.proxy_manager.get_proxy()
            if proxy_url:
                connector_kwargs['connector'] = aiohttp.ProxyConnector.from_url(proxy_url)
        
        if not self.session:
            self.session = aiohttp.ClientSession(
                timeout=self.timeout,
                headers=headers,
                **connector_kwargs
            )
        
        async with self.session.get(url) as response:
            if response.status == 403:
                logger.warning(f"Access forbidden for {url}, rotating proxy")
                if self.proxy_manager:
                    await self.proxy_manager.rotate_proxy()
                raise aiohttp.ClientResponseError(
                    request_info=response.request_info,
                    history=response.history,
                    status=response.status,
                    message="Access forbidden"
                )
            
            response.raise_for_status()
            content = await response.text()
            
            # Add delay to be respectful
            await asyncio.sleep(self.delay)
            
            return content
    
    async def parse_content(self, content: str, url: str) -> Dict[str, Any]:
        """Parse HTML content and extract structured data."""
        soup = BeautifulSoup(content, 'lxml')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.extract()
        
        # Extract basic page information
        parsed_data = {
            'title': soup.title.string.strip() if soup.title else '',
            'meta_description': self._get_meta_description(soup),
            'meta_keywords': self._get_meta_keywords(soup),
            'headings': self._extract_headings(soup),
            'links': self._extract_links(soup, url),
            'images': self._extract_images(soup, url),
            'text_content': self._extract_text_content(soup),
            'raw_html': str(soup),
            'tables': self._extract_tables(soup),
            'forms': self._extract_forms(soup),
            'lists': self._extract_lists(soup)
        }
        
        return parsed_data
    
    def _get_meta_description(self, soup: BeautifulSoup) -> str:
        """Extract meta description."""
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        return meta_desc.get('content', '') if meta_desc else ''
    
    def _get_meta_keywords(self, soup: BeautifulSoup) -> str:
        """Extract meta keywords."""
        meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
        return meta_keywords.get('content', '') if meta_keywords else ''
    
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