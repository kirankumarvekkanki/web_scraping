"""
API Module

FastAPI-based REST API for the web scraping framework:
- Endpoint for submitting scraping jobs
- Field specification input
- Structured data output
- Job status tracking
"""

from .main import app
from .models import *
from .endpoints import *

__all__ = ['app']