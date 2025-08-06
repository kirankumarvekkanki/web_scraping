"""
Retry utilities with exponential backoff and jitter.
"""

import asyncio
import functools
import logging
import random
import time
from typing import Callable, Optional, Union, List, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    retry_on_exceptions: tuple = (Exception,)
    stop_on_exceptions: tuple = ()


class ExponentialBackoff:
    """Exponential backoff calculator with jitter."""
    
    def __init__(self, config: RetryConfig):
        self.config = config
        self.attempt = 0
    
    def reset(self):
        """Reset attempt counter."""
        self.attempt = 0
    
    def get_delay(self) -> float:
        """Calculate delay for current attempt."""
        if self.attempt == 0:
            return 0
        
        # Calculate exponential delay
        delay = self.config.base_delay * (self.config.exponential_base ** (self.attempt - 1))
        
        # Apply maximum delay limit
        delay = min(delay, self.config.max_delay)
        
        # Add jitter to avoid thundering herd
        if self.config.jitter:
            jitter_range = delay * 0.1  # 10% jitter
            delay += random.uniform(-jitter_range, jitter_range)
        
        return max(0, delay)
    
    def next_attempt(self) -> float:
        """Increment attempt and return delay."""
        self.attempt += 1
        return self.get_delay()


def retry_sync(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retry_on: tuple = (Exception,),
    stop_on: tuple = (),
    on_retry: Optional[Callable] = None
):
    """
    Decorator for synchronous functions with retry logic.
    
    Args:
        max_attempts: Maximum number of retry attempts
        base_delay: Base delay between retries in seconds
        max_delay: Maximum delay between retries
        exponential_base: Base for exponential backoff
        jitter: Whether to add random jitter to delays
        retry_on: Tuple of exceptions to retry on
        stop_on: Tuple of exceptions to immediately stop on
        on_retry: Callback function called on each retry
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            config = RetryConfig(
                max_attempts=max_attempts,
                base_delay=base_delay,
                max_delay=max_delay,
                exponential_base=exponential_base,
                jitter=jitter,
                retry_on_exceptions=retry_on,
                stop_on_exceptions=stop_on
            )
            
            backoff = ExponentialBackoff(config)
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                    
                except stop_on as e:
                    logger.debug(f"Stopping retry for {func.__name__} due to {type(e).__name__}: {e}")
                    raise
                    
                except retry_on as e:
                    last_exception = e
                    
                    if attempt == max_attempts - 1:
                        logger.error(f"Function {func.__name__} failed after {max_attempts} attempts: {e}")
                        raise
                    
                    delay = backoff.next_attempt()
                    
                    logger.warning(
                        f"Attempt {attempt + 1}/{max_attempts} failed for {func.__name__}: {e}. "
                        f"Retrying in {delay:.2f}s"
                    )
                    
                    if on_retry:
                        try:
                            on_retry(attempt + 1, e, delay)
                        except Exception as callback_error:
                            logger.error(f"Retry callback failed: {callback_error}")
                    
                    if delay > 0:
                        time.sleep(delay)
                
                except Exception as e:
                    logger.error(f"Function {func.__name__} failed with non-retryable exception: {e}")
                    raise
            
            # This should never be reached, but just in case
            if last_exception:
                raise last_exception
        
        return wrapper
    return decorator


def retry_async(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retry_on: tuple = (Exception,),
    stop_on: tuple = (),
    on_retry: Optional[Callable] = None
):
    """
    Decorator for asynchronous functions with retry logic.
    
    Args:
        max_attempts: Maximum number of retry attempts
        base_delay: Base delay between retries in seconds
        max_delay: Maximum delay between retries
        exponential_base: Base for exponential backoff
        jitter: Whether to add random jitter to delays
        retry_on: Tuple of exceptions to retry on
        stop_on: Tuple of exceptions to immediately stop on
        on_retry: Async callback function called on each retry
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            config = RetryConfig(
                max_attempts=max_attempts,
                base_delay=base_delay,
                max_delay=max_delay,
                exponential_base=exponential_base,
                jitter=jitter,
                retry_on_exceptions=retry_on,
                stop_on_exceptions=stop_on
            )
            
            backoff = ExponentialBackoff(config)
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                    
                except stop_on as e:
                    logger.debug(f"Stopping retry for {func.__name__} due to {type(e).__name__}: {e}")
                    raise
                    
                except retry_on as e:
                    last_exception = e
                    
                    if attempt == max_attempts - 1:
                        logger.error(f"Async function {func.__name__} failed after {max_attempts} attempts: {e}")
                        raise
                    
                    delay = backoff.next_attempt()
                    
                    logger.warning(
                        f"Attempt {attempt + 1}/{max_attempts} failed for {func.__name__}: {e}. "
                        f"Retrying in {delay:.2f}s"
                    )
                    
                    if on_retry:
                        try:
                            if asyncio.iscoroutinefunction(on_retry):
                                await on_retry(attempt + 1, e, delay)
                            else:
                                on_retry(attempt + 1, e, delay)
                        except Exception as callback_error:
                            logger.error(f"Retry callback failed: {callback_error}")
                    
                    if delay > 0:
                        await asyncio.sleep(delay)
                
                except Exception as e:
                    logger.error(f"Async function {func.__name__} failed with non-retryable exception: {e}")
                    raise
            
            # This should never be reached, but just in case
            if last_exception:
                raise last_exception
        
        return wrapper
    return decorator


class RetryManager:
    """Manages retry behavior for multiple operations."""
    
    def __init__(self, default_config: Optional[RetryConfig] = None):
        self.default_config = default_config or RetryConfig()
        self.operation_configs = {}
        self.retry_stats = {}
    
    def configure_operation(self, operation_name: str, config: RetryConfig):
        """Configure retry behavior for a specific operation."""
        self.operation_configs[operation_name] = config
        self.retry_stats[operation_name] = {
            'total_attempts': 0,
            'successful_attempts': 0,
            'failed_attempts': 0,
            'average_attempts': 0.0
        }
    
    async def execute_with_retry(
        self, 
        operation_name: str, 
        func: Callable, 
        *args, 
        **kwargs
    ) -> Any:
        """Execute a function with retry logic for a named operation."""
        
        config = self.operation_configs.get(operation_name, self.default_config)
        backoff = ExponentialBackoff(config)
        last_exception = None
        
        stats = self.retry_stats.setdefault(operation_name, {
            'total_attempts': 0,
            'successful_attempts': 0,
            'failed_attempts': 0,
            'average_attempts': 0.0
        })
        
        attempts_made = 0
        
        for attempt in range(config.max_attempts):
            attempts_made += 1
            stats['total_attempts'] += 1
            
            try:
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                
                stats['successful_attempts'] += 1
                stats['average_attempts'] = (
                    stats['average_attempts'] * (stats['successful_attempts'] - 1) + attempts_made
                ) / stats['successful_attempts']
                
                logger.debug(f"Operation {operation_name} succeeded on attempt {attempts_made}")
                return result
                
            except config.stop_on_exceptions as e:
                stats['failed_attempts'] += 1
                logger.debug(f"Stopping retry for {operation_name} due to {type(e).__name__}: {e}")
                raise
                
            except config.retry_on_exceptions as e:
                last_exception = e
                
                if attempt == config.max_attempts - 1:
                    stats['failed_attempts'] += 1
                    logger.error(f"Operation {operation_name} failed after {config.max_attempts} attempts: {e}")
                    raise
                
                delay = backoff.next_attempt()
                
                logger.warning(
                    f"Operation {operation_name} attempt {attempt + 1}/{config.max_attempts} failed: {e}. "
                    f"Retrying in {delay:.2f}s"
                )
                
                if delay > 0:
                    await asyncio.sleep(delay)
            
            except Exception as e:
                stats['failed_attempts'] += 1
                logger.error(f"Operation {operation_name} failed with non-retryable exception: {e}")
                raise
        
        # This should never be reached
        if last_exception:
            raise last_exception
    
    def get_stats(self, operation_name: Optional[str] = None) -> dict:
        """Get retry statistics for operations."""
        if operation_name:
            return self.retry_stats.get(operation_name, {})
        return self.retry_stats.copy()
    
    def reset_stats(self, operation_name: Optional[str] = None):
        """Reset statistics for operations."""
        if operation_name:
            if operation_name in self.retry_stats:
                self.retry_stats[operation_name] = {
                    'total_attempts': 0,
                    'successful_attempts': 0,
                    'failed_attempts': 0,
                    'average_attempts': 0.0
                }
        else:
            for op_name in self.retry_stats:
                self.retry_stats[op_name] = {
                    'total_attempts': 0,
                    'successful_attempts': 0,
                    'failed_attempts': 0,
                    'average_attempts': 0.0
                }


def create_retry_decorator(operation_name: str, retry_manager: RetryManager):
    """Create a retry decorator for a specific operation using RetryManager."""
    def decorator(func: Callable) -> Callable:
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                return await retry_manager.execute_with_retry(operation_name, func, *args, **kwargs)
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                return asyncio.run(retry_manager.execute_with_retry(operation_name, func, *args, **kwargs))
            return sync_wrapper
    
    return decorator