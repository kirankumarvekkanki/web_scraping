"""
Error handling utilities and custom exceptions.
"""

import logging
import traceback
import sys
from typing import Dict, Any, Optional, Callable, List
from enum import Enum
import time

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ScrapingError(Exception):
    """Base exception for scraping-related errors."""
    
    def __init__(self, message: str, error_code: str = None, details: Dict[str, Any] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or "SCRAPING_ERROR"
        self.details = details or {}
        self.timestamp = time.time()


class CrawlerError(ScrapingError):
    """Exception for crawler-related errors."""
    
    def __init__(self, message: str, url: str = None, crawler_type: str = None, **kwargs):
        super().__init__(message, error_code="CRAWLER_ERROR", **kwargs)
        self.url = url
        self.crawler_type = crawler_type


class ExtractionError(ScrapingError):
    """Exception for field extraction errors."""
    
    def __init__(self, message: str, field_name: str = None, pattern: str = None, **kwargs):
        super().__init__(message, error_code="EXTRACTION_ERROR", **kwargs)
        self.field_name = field_name
        self.pattern = pattern


class ProxyError(ScrapingError):
    """Exception for proxy-related errors."""
    
    def __init__(self, message: str, proxy_url: str = None, **kwargs):
        super().__init__(message, error_code="PROXY_ERROR", **kwargs)
        self.proxy_url = proxy_url


class ValidationError(ScrapingError):
    """Exception for validation errors."""
    
    def __init__(self, message: str, field_name: str = None, value: Any = None, **kwargs):
        super().__init__(message, error_code="VALIDATION_ERROR", **kwargs)
        self.field_name = field_name
        self.value = value


class TimeoutError(ScrapingError):
    """Exception for timeout errors."""
    
    def __init__(self, message: str, timeout_duration: float = None, **kwargs):
        super().__init__(message, error_code="TIMEOUT_ERROR", **kwargs)
        self.timeout_duration = timeout_duration


class RateLimitError(ScrapingError):
    """Exception for rate limiting errors."""
    
    def __init__(self, message: str, retry_after: float = None, **kwargs):
        super().__init__(message, error_code="RATE_LIMIT_ERROR", **kwargs)
        self.retry_after = retry_after


class ErrorHandler:
    """Centralized error handling and reporting."""
    
    def __init__(self):
        self.error_counts = {}
        self.error_callbacks = {}
        self.suppressed_errors = set()
        self.error_history = []
        self.max_history = 1000
    
    def register_callback(self, error_type: type, callback: Callable):
        """Register a callback for specific error types."""
        self.error_callbacks[error_type] = callback
    
    def suppress_error(self, error_code: str):
        """Suppress specific error types from being logged."""
        self.suppressed_errors.add(error_code)
    
    def handle_error(
        self, 
        error: Exception, 
        context: Dict[str, Any] = None,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        log_traceback: bool = True
    ) -> Dict[str, Any]:
        """
        Handle an error with logging, callbacks, and statistics.
        
        Args:
            error: The exception that occurred
            context: Additional context information
            severity: Error severity level
            log_traceback: Whether to log the full traceback
            
        Returns:
            Error information dictionary
        """
        error_info = {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'severity': severity.value,
            'timestamp': time.time(),
            'context': context or {}
        }
        
        # Add custom error details if available
        if isinstance(error, ScrapingError):
            error_info.update({
                'error_code': error.error_code,
                'details': error.details
            })
        
        # Update error counts
        error_type = type(error).__name__
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        
        # Add to error history
        self.error_history.append(error_info)
        if len(self.error_history) > self.max_history:
            self.error_history.pop(0)
        
        # Check if error should be suppressed
        error_code = getattr(error, 'error_code', error_type)
        if error_code not in self.suppressed_errors:
            # Log the error
            self._log_error(error, error_info, log_traceback)
        
        # Execute callbacks
        self._execute_callbacks(error, error_info)
        
        return error_info
    
    def _log_error(self, error: Exception, error_info: Dict[str, Any], log_traceback: bool):
        """Log error based on severity."""
        severity = ErrorSeverity(error_info['severity'])
        message = f"{error_info['error_type']}: {error_info['error_message']}"
        
        if error_info['context']:
            context_str = ', '.join([f"{k}={v}" for k, v in error_info['context'].items()])
            message += f" | Context: {context_str}"
        
        if severity == ErrorSeverity.LOW:
            logger.debug(message)
        elif severity == ErrorSeverity.MEDIUM:
            logger.warning(message)
        elif severity == ErrorSeverity.HIGH:
            logger.error(message)
        elif severity == ErrorSeverity.CRITICAL:
            logger.critical(message)
        
        # Log traceback for high severity errors or when explicitly requested
        if log_traceback and severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            logger.error("Traceback:", exc_info=True)
    
    def _execute_callbacks(self, error: Exception, error_info: Dict[str, Any]):
        """Execute registered callbacks for error type."""
        error_type = type(error)
        
        # Execute specific callback
        if error_type in self.error_callbacks:
            try:
                self.error_callbacks[error_type](error, error_info)
            except Exception as callback_error:
                logger.error(f"Error callback failed: {callback_error}")
        
        # Execute base class callbacks
        for registered_type, callback in self.error_callbacks.items():
            if registered_type != error_type and isinstance(error, registered_type):
                try:
                    callback(error, error_info)
                except Exception as callback_error:
                    logger.error(f"Error callback failed: {callback_error}")
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics."""
        total_errors = sum(self.error_counts.values())
        
        return {
            'total_errors': total_errors,
            'error_counts': self.error_counts.copy(),
            'unique_error_types': len(self.error_counts),
            'recent_errors': len([
                e for e in self.error_history 
                if time.time() - e['timestamp'] < 3600  # Last hour
            ])
        }
    
    def get_recent_errors(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent errors."""
        return self.error_history[-limit:]
    
    def clear_error_history(self):
        """Clear error history."""
        self.error_history.clear()
        self.error_counts.clear()
    
    def create_error_summary(self) -> str:
        """Create a human-readable error summary."""
        if not self.error_counts:
            return "No errors recorded."
        
        total_errors = sum(self.error_counts.values())
        most_common = max(self.error_counts.items(), key=lambda x: x[1])
        
        summary = f"Total errors: {total_errors}\n"
        summary += f"Most common: {most_common[0]} ({most_common[1]} occurrences)\n"
        summary += "Error breakdown:\n"
        
        for error_type, count in sorted(self.error_counts.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total_errors) * 100
            summary += f"  - {error_type}: {count} ({percentage:.1f}%)\n"
        
        return summary


def safe_execute(func: Callable, *args, error_handler: ErrorHandler = None, **kwargs) -> Dict[str, Any]:
    """
    Safely execute a function with error handling.
    
    Args:
        func: Function to execute
        error_handler: Error handler instance
        *args, **kwargs: Function arguments
        
    Returns:
        Dictionary with success status and result or error
    """
    try:
        result = func(*args, **kwargs)
        return {
            'success': True,
            'result': result,
            'error': None
        }
    except Exception as e:
        error_info = None
        if error_handler:
            error_info = error_handler.handle_error(e)
        
        return {
            'success': False,
            'result': None,
            'error': str(e),
            'error_info': error_info
        }


async def safe_execute_async(func: Callable, *args, error_handler: ErrorHandler = None, **kwargs) -> Dict[str, Any]:
    """
    Safely execute an async function with error handling.
    
    Args:
        func: Async function to execute
        error_handler: Error handler instance
        *args, **kwargs: Function arguments
        
    Returns:
        Dictionary with success status and result or error
    """
    try:
        result = await func(*args, **kwargs)
        return {
            'success': True,
            'result': result,
            'error': None
        }
    except Exception as e:
        error_info = None
        if error_handler:
            error_info = error_handler.handle_error(e)
        
        return {
            'success': False,
            'result': None,
            'error': str(e),
            'error_info': error_info
        }


def error_context(**context_data):
    """Decorator to add context to errors."""
    def decorator(func: Callable) -> Callable:
        import functools
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Add context to exception
                if hasattr(e, 'details'):
                    e.details.update(context_data)
                else:
                    e.context = context_data
                raise
        
        return wrapper
    return decorator


def create_error_response(error: Exception, request_id: str = None) -> Dict[str, Any]:
    """Create a standardized error response."""
    response = {
        'success': False,
        'error': {
            'type': type(error).__name__,
            'message': str(error),
            'timestamp': time.time()
        }
    }
    
    if request_id:
        response['request_id'] = request_id
    
    if isinstance(error, ScrapingError):
        response['error'].update({
            'code': error.error_code,
            'details': error.details
        })
    
    return response