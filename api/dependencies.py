"""
FastAPI dependencies for dependency injection.
"""

from fastapi import Depends, HTTPException, Request
from typing import Optional

from .scraping_service import ScrapingService
from .job_manager import JobManager


async def get_scraping_service() -> ScrapingService:
    """Dependency to get scraping service instance."""
    service = ScrapingService()
    await service.initialize()
    return service


async def get_job_manager(request: Request) -> JobManager:
    """Dependency to get job manager instance."""
    job_manager = getattr(request.app.state, 'job_manager', None)
    if not job_manager:
        raise HTTPException(status_code=503, detail="Job manager not available")
    return job_manager


async def validate_api_key(api_key: Optional[str] = None) -> bool:
    """Validate API key if authentication is required."""
    # For now, return True (no authentication)
    # In production, implement proper API key validation
    return True


async def rate_limit_check(request: Request) -> bool:
    """Check rate limiting."""
    # For now, return True (no rate limiting)
    # In production, implement proper rate limiting
    return True