"""
Proxy Management Module

Handles proxy rotation, validation, and headers spoofing:
- Proxy pool management
- Automatic rotation on failures
- Headers randomization
- Health checking
"""

from .proxy_manager import ProxyManager
from .proxy_validator import ProxyValidator
from .headers_spoofing import HeadersSpoofing

__all__ = [
    'ProxyManager',
    'ProxyValidator',
    'HeadersSpoofing'
]