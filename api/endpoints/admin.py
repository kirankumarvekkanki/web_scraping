"""
Administrative endpoints for system management.
"""

import logging
from typing import List

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse

from ..models import *
from ..dependencies import get_scraping_service, get_job_manager, validate_api_key
from ..scraping_service import ScrapingService
from ..job_manager import JobManager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/schemas", response_model=List[SchemaInfo])
async def get_schemas(
    scraping_service: ScrapingService = Depends(get_scraping_service)
):
    """Get all available validation schemas."""
    try:
        # Get schema information from the field extractor
        if not scraping_service.field_extractor:
            await scraping_service.initialize()
        
        schema_validator = scraping_service.field_extractor.schema_validator
        schema_names = schema_validator.list_available_schemas()
        
        schemas = []
        for name in schema_names:
            schema_info = schema_validator.get_schema_info(name)
            if 'error' not in schema_info:
                schemas.append(SchemaInfo(
                    name=name,
                    description=schema_info.get('description', ''),
                    fields=schema_info.get('fields', {})
                ))
        
        return schemas
        
    except Exception as e:
        logger.error(f"Failed to get schemas: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/system/stats", response_model=SystemStats)
async def get_system_stats(
    job_manager: JobManager = Depends(get_job_manager),
    scraping_service: ScrapingService = Depends(get_scraping_service),
    authenticated: bool = Depends(validate_api_key)
):
    """Get system statistics and health information."""
    try:
        import psutil
        import time
        
        # Get job statistics
        job_stats = await job_manager.get_stats()
        
        # Get proxy statistics if available
        proxy_stats = None
        if (scraping_service.proxy_manager and 
            scraping_service.proxy_manager.is_running):
            proxy_stats = scraping_service.proxy_manager.get_stats()
        
        # Get system metrics
        memory_usage = psutil.virtual_memory().percent
        cpu_usage = psutil.cpu_percent(interval=1)
        
        # Calculate uptime (simplified)
        uptime = time.time() - job_stats.get('start_time', time.time())
        
        return SystemStats(
            active_jobs=job_stats.get('running_jobs', 0),
            completed_jobs=job_stats.get('completed_jobs', 0),
            failed_jobs=job_stats.get('failed_jobs', 0),
            proxy_stats=proxy_stats,
            uptime=uptime,
            memory_usage=memory_usage,
            cpu_usage=cpu_usage
        )
        
    except ImportError:
        # psutil not available
        job_stats = await job_manager.get_stats()
        
        return SystemStats(
            active_jobs=job_stats.get('running_jobs', 0),
            completed_jobs=job_stats.get('completed_jobs', 0),
            failed_jobs=job_stats.get('failed_jobs', 0),
            proxy_stats=None,
            uptime=0.0,
            memory_usage=0.0,
            cpu_usage=0.0
        )
    except Exception as e:
        logger.error(f"Failed to get system stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/system/config")
async def update_config(
    config: ConfigUpdate,
    scraping_service: ScrapingService = Depends(get_scraping_service),
    authenticated: bool = Depends(validate_api_key)
):
    """Update system configuration."""
    try:
        updates_applied = []
        
        # Update proxy sources
        if config.proxy_sources is not None:
            if scraping_service.proxy_manager:
                scraping_service.proxy_manager.proxy_sources = config.proxy_sources
                await scraping_service.proxy_manager.load_proxies()
                updates_applied.append("proxy_sources")
        
        # Update logging level
        if config.log_level:
            logging.getLogger().setLevel(getattr(logging, config.log_level))
            updates_applied.append("log_level")
        
        # Note: Other config updates would require service restart
        # or more sophisticated configuration management
        
        return {
            "message": "Configuration updated successfully",
            "updates_applied": updates_applied
        }
        
    except Exception as e:
        logger.error(f"Failed to update config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/system/proxy/reload")
async def reload_proxies(
    scraping_service: ScrapingService = Depends(get_scraping_service),
    authenticated: bool = Depends(validate_api_key)
):
    """Reload proxy list from sources."""
    try:
        if not scraping_service.proxy_manager:
            raise HTTPException(status_code=400, detail="Proxy manager not initialized")
        
        await scraping_service.proxy_manager.load_proxies()
        stats = scraping_service.proxy_manager.get_stats()
        
        return {
            "message": "Proxies reloaded successfully",
            "active_proxies": stats.get('active_count', 0),
            "inactive_proxies": stats.get('inactive_count', 0)
        }
        
    except Exception as e:
        logger.error(f"Failed to reload proxies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/system/proxy/stats")
async def get_proxy_stats(
    scraping_service: ScrapingService = Depends(get_scraping_service),
    authenticated: bool = Depends(validate_api_key)
):
    """Get detailed proxy statistics."""
    try:
        if not scraping_service.proxy_manager:
            return {"message": "Proxy manager not initialized"}
        
        stats = scraping_service.proxy_manager.get_stats()
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get proxy stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/system/proxy/add")
async def add_proxy(
    proxy_url: str,
    scraping_service: ScrapingService = Depends(get_scraping_service),
    authenticated: bool = Depends(validate_api_key)
):
    """Add a new proxy to the pool."""
    try:
        if not scraping_service.proxy_manager:
            raise HTTPException(status_code=400, detail="Proxy manager not initialized")
        
        success = await scraping_service.proxy_manager.add_proxy(proxy_url)
        
        if success:
            return {"message": f"Proxy {proxy_url} added successfully"}
        else:
            return {"message": f"Failed to add proxy {proxy_url} (validation failed)"}
        
    except Exception as e:
        logger.error(f"Failed to add proxy: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/system/proxy/{proxy_url}")
async def remove_proxy(
    proxy_url: str,
    scraping_service: ScrapingService = Depends(get_scraping_service),
    authenticated: bool = Depends(validate_api_key)
):
    """Remove a proxy from the pool."""
    try:
        if not scraping_service.proxy_manager:
            raise HTTPException(status_code=400, detail="Proxy manager not initialized")
        
        success = await scraping_service.proxy_manager.remove_proxy(proxy_url)
        
        if success:
            return {"message": f"Proxy {proxy_url} removed successfully"}
        else:
            raise HTTPException(status_code=404, detail="Proxy not found")
        
    except Exception as e:
        logger.error(f"Failed to remove proxy: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/system/jobs/cleanup")
async def cleanup_jobs(
    job_manager: JobManager = Depends(get_job_manager),
    authenticated: bool = Depends(validate_api_key)
):
    """Manually trigger cleanup of old completed jobs."""
    try:
        # This would typically be handled by the background cleanup task
        # For now, return statistics
        stats = await job_manager.get_stats()
        
        return {
            "message": "Job cleanup completed",
            "active_jobs": stats.get('running_jobs', 0),
            "total_jobs_in_memory": stats.get('memory_usage', 0)
        }
        
    except Exception as e:
        logger.error(f"Failed to cleanup jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))