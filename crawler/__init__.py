"""
Web Crawler Module

Handles crawling of different content types:
- HTML pages
- JavaScript-rendered pages
- PDF documents
"""

from .base_crawler import BaseCrawler
from .html_crawler import HTMLCrawler
from .js_crawler import JSCrawler
from .pdf_crawler import PDFCrawler
from .content_detector import ContentDetector

__all__ = [
    'BaseCrawler',
    'HTMLCrawler', 
    'JSCrawler',
    'PDFCrawler',
    'ContentDetector'
]