"""
Health check and monitoring endpoints.
"""

import time
import logging
from typing import Dict, Any

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from ..models import HealthCheck
from ..dependencies import get_scraping_service, get_job_manager
from ..scraping_service import ScrapingService
from ..job_manager import JobManager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health", response_model=HealthCheck)
async def health_check():
    """Basic health check endpoint."""
    return HealthCheck(
        status="healthy",
        timestamp=time.time(),
        version="1.0.0",
        dependencies={
            "api": "operational",
            "database": "not_configured",
            "external_services": "not_configured"
        }
    )


@router.get("/health/detailed")
async def detailed_health_check(
    scraping_service: ScrapingService = Depends(get_scraping_service),
    job_manager: JobManager = Depends(get_job_manager)
):
    """Detailed health check with component status."""
    
    health_status = {
        "status": "healthy",
        "timestamp": time.time(),
        "version": "1.0.0",
        "components": {}
    }
    
    overall_healthy = True
    
    try:
        # Check scraping service
        if scraping_service.is_initialized:
            health_status["components"]["scraping_service"] = {
                "status": "healthy",
                "details": "Service initialized and ready"
            }
        else:
            health_status["components"]["scraping_service"] = {
                "status": "initializing",
                "details": "Service not yet initialized"
            }
            overall_healthy = False
        
        # Check job manager
        if job_manager.is_running:
            job_stats = await job_manager.get_stats()
            health_status["components"]["job_manager"] = {
                "status": "healthy",
                "details": f"Running with {job_stats.get('running_jobs', 0)} active jobs"
            }
        else:
            health_status["components"]["job_manager"] = {
                "status": "unhealthy",
                "details": "Job manager not running"
            }
            overall_healthy = False
        
        # Check proxy manager
        if scraping_service.proxy_manager and scraping_service.proxy_manager.is_running:
            proxy_stats = scraping_service.proxy_manager.get_stats()
            health_status["components"]["proxy_manager"] = {
                "status": "healthy",
                "details": f"{proxy_stats.get('active_count', 0)} active proxies"
            }
        else:
            health_status["components"]["proxy_manager"] = {
                "status": "disabled",
                "details": "Proxy manager not running"
            }
        
        # Check external dependencies
        try:
            import requests
            import beautifulsoup4
            import playwright
            
            health_status["components"]["dependencies"] = {
                "status": "healthy",
                "details": "All required packages available"
            }
        except ImportError as e:
            health_status["components"]["dependencies"] = {
                "status": "unhealthy",
                "details": f"Missing dependency: {e}"
            }
            overall_healthy = False
        
        # Set overall status
        health_status["status"] = "healthy" if overall_healthy else "degraded"
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        health_status["status"] = "unhealthy"
        health_status["error"] = str(e)
    
    return health_status


@router.get("/health/readiness")
async def readiness_check(
    scraping_service: ScrapingService = Depends(get_scraping_service),
    job_manager: JobManager = Depends(get_job_manager)
):
    """Readiness check for Kubernetes/container orchestration."""
    
    try:
        # Check if core services are ready to handle requests
        ready = (
            scraping_service.is_initialized and
            job_manager.is_running
        )
        
        if ready:
            return JSONResponse(
                status_code=200,
                content={"status": "ready", "timestamp": time.time()}
            )
        else:
            return JSONResponse(
                status_code=503,
                content={"status": "not_ready", "timestamp": time.time()}
            )
            
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={"status": "error", "error": str(e), "timestamp": time.time()}
        )


@router.get("/health/liveness")
async def liveness_check():
    """Liveness check for Kubernetes/container orchestration."""
    
    try:
        # Basic liveness check - just ensure the API is responding
        return JSONResponse(
            status_code=200,
            content={"status": "alive", "timestamp": time.time()}
        )
        
    except Exception as e:
        logger.error(f"Liveness check failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "error": str(e), "timestamp": time.time()}
        )


@router.get("/health/metrics")
async def get_metrics(
    job_manager: JobManager = Depends(get_job_manager)
):
    """Get basic metrics in Prometheus format."""
    
    try:
        job_stats = await job_manager.get_stats()
        
        # Simple Prometheus-style metrics
        metrics = f"""# HELP web_scraper_jobs_total Total number of jobs
# TYPE web_scraper_jobs_total counter
web_scraper_jobs_total{{{job_stats.get('total_jobs', 0)}}}

# HELP web_scraper_jobs_running Currently running jobs
# TYPE web_scraper_jobs_running gauge
web_scraper_jobs_running {job_stats.get('running_jobs', 0)}

# HELP web_scraper_jobs_completed Completed jobs
# TYPE web_scraper_jobs_completed counter
web_scraper_jobs_completed {job_stats.get('completed_jobs', 0)}

# HELP web_scraper_jobs_failed Failed jobs
# TYPE web_scraper_jobs_failed counter
web_scraper_jobs_failed {job_stats.get('failed_jobs', 0)}
"""
        
        return JSONResponse(
            status_code=200,
            content=metrics,
            media_type="text/plain"
        )
        
    except Exception as e:
        logger.error(f"Metrics collection failed: {e}")
        return JSONResponse(
            status_code=500,
            content=f"# Error collecting metrics: {e}",
            media_type="text/plain"
        )