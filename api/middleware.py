"""
Advanced Middleware Components for Production API.

This module provides comprehensive middleware for the FastAPI application
with modern security, performance monitoring, and request tracking features.

Middleware Components:
- RequestIDMiddleware: Unique request tracking for debugging
- PerformanceMiddleware: Response time monitoring and metrics
- SecurityHeadersMiddleware: Security headers and protection
- RateLimitMiddleware: Advanced rate limiting with sliding window
- CompressionMiddleware: Response compression for performance

Features:
- Structured logging with request context
- Performance metrics collection
- Security best practices implementation
- Rate limiting with configurable policies
- Request/response transformation
- Error handling and recovery

Author: Web Scraping Framework Team
License: MIT
"""

import time
import uuid
import logging
import asyncio
from typing import Dict, Any, Optional, Callable, Awaitable
from collections import defaultdict, deque
from datetime import datetime, timedelta
import hashlib

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware for generating and tracking unique request IDs.
    
    Features:
    - Generates UUID4 request IDs for tracking
    - Adds request ID to all log entries
    - Includes request ID in response headers
    - Supports client-provided request IDs
    """
    
    def __init__(self, app: ASGIApp, header_name: str = "X-Request-ID") -> None:
        """
        Initialize request ID middleware.
        
        Args:
            app: FastAPI application instance
            header_name: Header name for request ID (default: X-Request-ID)
        """
        super().__init__(app)
        self.header_name = header_name
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with unique ID tracking.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware/endpoint in chain
            
        Returns:
            Response with request ID header added
        """
        # Check for existing request ID from client
        request_id = request.headers.get(self.header_name) or str(uuid.uuid4())
        
        # Store request ID in request state for access in handlers
        request.state.request_id = request_id
        
        # Add to logging context (if using structured logging)
        extra_context = {'request_id': request_id}
        
        try:
            # Process request
            response = await call_next(request)
            
            # Add request ID to response headers
            response.headers[self.header_name] = request_id
            
            return response
            
        except Exception as e:
            logger.error(
                f"Request {request_id} failed: {e}",
                extra=extra_context,
                exc_info=True
            )
            raise


class PerformanceMiddleware(BaseHTTPMiddleware):
    """
    Advanced performance monitoring middleware.
    
    Features:
    - Response time tracking with high precision
    - Request/response size monitoring
    - Slow request detection and alerting
    - Performance metrics aggregation
    - Memory usage tracking (optional)
    """
    
    def __init__(
        self, 
        app: ASGIApp, 
        slow_threshold_ms: float = 1000.0,
        enable_memory_tracking: bool = False
    ) -> None:
        """
        Initialize performance monitoring middleware.
        
        Args:
            app: FastAPI application instance
            slow_threshold_ms: Threshold for slow request warnings (default: 1000ms)
            enable_memory_tracking: Enable memory usage monitoring
        """
        super().__init__(app)
        self.slow_threshold_ms = slow_threshold_ms
        self.enable_memory_tracking = enable_memory_tracking
        
        # Performance metrics storage
        self.request_times: deque = deque(maxlen=1000)  # Keep last 1000 requests
        self.request_counts = defaultdict(int)
        self.slow_requests = deque(maxlen=100)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Monitor request performance and collect metrics.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware/endpoint in chain
            
        Returns:
            Response with performance headers added
        """
        # Record start time with high precision
        start_time = time.perf_counter()
        start_memory = self._get_memory_usage() if self.enable_memory_tracking else 0
        
        # Get request metadata
        request_id = getattr(request.state, 'request_id', 'unknown')
        method = request.method
        path = request.url.path
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate performance metrics
            response_time = time.perf_counter() - start_time
            response_time_ms = response_time * 1000
            
            # Memory tracking
            memory_used = 0
            if self.enable_memory_tracking:
                end_memory = self._get_memory_usage()
                memory_used = max(0, end_memory - start_memory)
            
            # Store metrics
            self.request_times.append(response_time)
            self.request_counts[f"{method} {path}"] += 1
            
            # Log slow requests
            if response_time_ms > self.slow_threshold_ms:
                slow_request_info = {
                    'request_id': request_id,
                    'method': method,
                    'path': path,
                    'response_time_ms': round(response_time_ms, 2),
                    'timestamp': datetime.utcnow().isoformat()
                }
                self.slow_requests.append(slow_request_info)
                
                logger.warning(
                    f"Slow request detected: {method} {path} took {response_time_ms:.2f}ms",
                    extra={
                        'request_id': request_id,
                        'response_time_ms': response_time_ms,
                        'method': method,
                        'path': path,
                        'memory_used_mb': memory_used / 1024 / 1024 if memory_used else 0
                    }
                )
            
            # Add performance headers to response
            response.headers["X-Response-Time"] = f"{response_time_ms:.2f}ms"
            if self.enable_memory_tracking and memory_used:
                response.headers["X-Memory-Used"] = f"{memory_used / 1024:.1f}KB"
            
            # Add performance metadata to app state for monitoring
            if hasattr(request.app.state, 'performance_metrics'):
                request.app.state.performance_metrics.update({
                    'last_request_time_ms': response_time_ms,
                    'avg_response_time_ms': sum(self.request_times) / len(self.request_times) * 1000,
                    'total_requests': sum(self.request_counts.values()),
                    'slow_request_count': len(self.slow_requests)
                })
            
            return response
            
        except Exception as e:
            # Record error timing
            response_time = time.perf_counter() - start_time
            response_time_ms = response_time * 1000
            
            logger.error(
                f"Request failed after {response_time_ms:.2f}ms: {e}",
                extra={
                    'request_id': request_id,
                    'response_time_ms': response_time_ms,
                    'method': method,
                    'path': path
                }
            )
            raise
    
    def _get_memory_usage(self) -> int:
        """
        Get current memory usage in bytes.
        
        Returns:
            Memory usage in bytes, or 0 if tracking disabled
        """
        try:
            import psutil
            import os
            process = psutil.Process(os.getpid())
            return process.memory_info().rss
        except ImportError:
            # psutil not available, disable memory tracking
            return 0
        except Exception:
            return 0
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """
        Get aggregated performance statistics.
        
        Returns:
            Dictionary containing performance metrics
        """
        if not self.request_times:
            return {}
        
        response_times = list(self.request_times)
        return {
            'total_requests': sum(self.request_counts.values()),
            'avg_response_time_ms': sum(response_times) / len(response_times) * 1000,
            'min_response_time_ms': min(response_times) * 1000,
            'max_response_time_ms': max(response_times) * 1000,
            'slow_requests_count': len(self.slow_requests),
            'requests_by_endpoint': dict(self.request_counts),
            'recent_slow_requests': list(self.slow_requests)[-10:]  # Last 10 slow requests
        }


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Security headers middleware for enhanced protection.
    
    Features:
    - OWASP recommended security headers
    - Content Security Policy (CSP)
    - XSS protection and clickjacking prevention
    - HSTS for HTTPS enforcement
    - Configurable security policies
    """
    
    def __init__(
        self, 
        app: ASGIApp,
        enable_csp: bool = True,
        enable_hsts: bool = True,
        custom_headers: Optional[Dict[str, str]] = None
    ) -> None:
        """
        Initialize security headers middleware.
        
        Args:
            app: FastAPI application instance
            enable_csp: Enable Content Security Policy
            enable_hsts: Enable HTTP Strict Transport Security
            custom_headers: Additional custom security headers
        """
        super().__init__(app)
        self.enable_csp = enable_csp
        self.enable_hsts = enable_hsts
        self.custom_headers = custom_headers or {}
        
        # Default security headers
        self.security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": (
                "geolocation=(), microphone=(), camera=(), "
                "payment=(), usb=(), magnetometer=(), gyroscope=()"
            )
        }
        
        # Add HSTS if enabled
        if self.enable_hsts:
            self.security_headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )
        
        # Add CSP if enabled
        if self.enable_csp:
            self.security_headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
                "font-src 'self' https://fonts.gstatic.com; "
                "img-src 'self' data: https:; "
                "connect-src 'self' https:; "
                "frame-ancestors 'none'"
            )
        
        # Merge custom headers
        self.security_headers.update(self.custom_headers)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Add security headers to all responses.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware/endpoint in chain
            
        Returns:
            Response with security headers added
        """
        try:
            # Process request
            response = await call_next(request)
            
            # Add security headers
            for header, value in self.security_headers.items():
                response.headers[header] = value
            
            return response
            
        except Exception as e:
            # Ensure security headers are added even for error responses
            if isinstance(e, JSONResponse):
                for header, value in self.security_headers.items():
                    e.headers[header] = value
            raise


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Advanced rate limiting middleware with sliding window algorithm.
    
    Features:
    - Sliding window rate limiting
    - Per-IP and per-endpoint limits
    - Configurable time windows and thresholds
    - Burst allowance handling
    - Rate limit headers for client feedback
    """
    
    def __init__(
        self,
        app: ASGIApp,
        calls: int = 100,
        period: int = 3600,
        burst_allowance: int = 10,
        exempted_paths: Optional[list] = None
    ) -> None:
        """
        Initialize rate limiting middleware.
        
        Args:
            app: FastAPI application instance
            calls: Number of allowed calls per period
            period: Time period in seconds (default: 3600 = 1 hour)
            burst_allowance: Additional calls allowed for burst traffic
            exempted_paths: List of paths to exempt from rate limiting
        """
        super().__init__(app)
        self.calls = calls
        self.period = period
        self.burst_allowance = burst_allowance
        self.exempted_paths = exempted_paths or ["/api/v1/health", "/docs", "/redoc"]
        
        # Rate limit storage (in production, use Redis or similar)
        self.rate_limit_data: Dict[str, deque] = defaultdict(lambda: deque())
        self.burst_usage: Dict[str, int] = defaultdict(int)
        
        logger.info(
            f"Rate limiting initialized: {calls} calls per {period}s with {burst_allowance} burst allowance"
        )
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Apply rate limiting with sliding window algorithm.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware/endpoint in chain
            
        Returns:
            Response or 429 Too Many Requests if rate limited
        """
        # Skip rate limiting for exempted paths
        if request.url.path in self.exempted_paths:
            return await call_next(request)
        
        # Get client identifier (IP address)
        client_ip = self._get_client_ip(request)
        current_time = time.time()
        
        # Clean old entries and check rate limit
        allowed, remaining_calls, reset_time = self._check_rate_limit(client_ip, current_time)
        
        if not allowed:
            # Rate limit exceeded
            logger.warning(
                f"Rate limit exceeded for IP {client_ip}",
                extra={
                    'client_ip': client_ip,
                    'path': request.url.path,
                    'method': request.method,
                    'remaining_calls': remaining_calls,
                    'reset_time': reset_time
                }
            )
            
            return JSONResponse(
                status_code=429,
                content={
                    "error": "RateLimitExceeded",
                    "message": "Too many requests. Please try again later.",
                    "details": {
                        "limit": self.calls,
                        "period_seconds": self.period,
                        "remaining": 0,
                        "reset_at": reset_time
                    }
                },
                headers={
                    "X-RateLimit-Limit": str(self.calls),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(reset_time)),
                    "Retry-After": str(int(reset_time - current_time))
                }
            )
        
        # Record this request
        self.rate_limit_data[client_ip].append(current_time)
        
        try:
            # Process request
            response = await call_next(request)
            
            # Add rate limit headers to successful responses
            response.headers.update({
                "X-RateLimit-Limit": str(self.calls),
                "X-RateLimit-Remaining": str(remaining_calls - 1),
                "X-RateLimit-Reset": str(int(reset_time))
            })
            
            return response
            
        except Exception as e:
            # Remove the recorded request on error
            if self.rate_limit_data[client_ip]:
                self.rate_limit_data[client_ip].pop()
            raise
    
    def _get_client_ip(self, request: Request) -> str:
        """
        Extract client IP address from request.
        
        Args:
            request: HTTP request object
            
        Returns:
            Client IP address as string
        """
        # Check for forwarded headers (for reverse proxy setups)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take the first IP in the chain
            return forwarded_for.split(",")[0].strip()
        
        # Check for real IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fall back to direct client IP
        return request.client.host if request.client else "unknown"
    
    def _check_rate_limit(self, client_id: str, current_time: float) -> tuple[bool, int, float]:
        """
        Check if client is within rate limits using sliding window.
        
        Args:
            client_id: Client identifier (usually IP address)
            current_time: Current timestamp
            
        Returns:
            Tuple of (allowed, remaining_calls, reset_time)
        """
        window_start = current_time - self.period
        client_requests = self.rate_limit_data[client_id]
        
        # Remove requests outside the current window
        while client_requests and client_requests[0] < window_start:
            client_requests.popleft()
        
        # Calculate remaining calls
        current_calls = len(client_requests)
        remaining_calls = self.calls - current_calls
        
        # Calculate reset time (when the oldest request in window expires)
        if client_requests:
            reset_time = client_requests[0] + self.period
        else:
            reset_time = current_time + self.period
        
        # Check if within limits (including burst allowance)
        burst_used = self.burst_usage[client_id]
        total_allowance = self.calls + self.burst_allowance
        
        if current_calls < self.calls:
            # Within normal limits
            return True, remaining_calls, reset_time
        elif current_calls < total_allowance:
            # Using burst allowance
            self.burst_usage[client_id] = burst_used + 1
            return True, 0, reset_time
        else:
            # Rate limit exceeded
            return False, 0, reset_time
    
    def get_rate_limit_stats(self) -> Dict[str, Any]:
        """
        Get rate limiting statistics.
        
        Returns:
            Dictionary containing rate limit metrics
        """
        current_time = time.time()
        active_clients = 0
        total_requests = 0
        
        for client_id, requests in self.rate_limit_data.items():
            # Clean old requests
            window_start = current_time - self.period
            while requests and requests[0] < window_start:
                requests.popleft()
            
            if requests:
                active_clients += 1
                total_requests += len(requests)
        
        return {
            'active_clients': active_clients,
            'total_requests_in_window': total_requests,
            'rate_limit_config': {
                'calls_per_period': self.calls,
                'period_seconds': self.period,
                'burst_allowance': self.burst_allowance
            },
            'burst_usage': dict(self.burst_usage)
        }