"""
Job management endpoints for asynchronous operations.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse

from ..models import *
from ..dependencies import get_job_manager, rate_limit_check
from ..job_manager import JobManager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/jobs", response_model=Dict[str, str])
async def submit_job(
    request: ScrapeRequest,
    job_manager: JobManager = Depends(get_job_manager),
    rate_limit_ok: bool = Depends(rate_limit_check)
):
    """
    Submit a scraping job for asynchronous processing.
    
    Returns a job ID that can be used to track the job status.
    """
    try:
        job_id = await job_manager.submit_job(request)
        return {"job_id": job_id, "status": "submitted"}
    except Exception as e:
        logger.error(f"Failed to submit job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/{job_id}", response_model=ScrapeJob)
async def get_job(
    job_id: str,
    job_manager: JobManager = Depends(get_job_manager)
):
    """Get job status and results by job ID."""
    job = await job_manager.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return job


@router.delete("/jobs/{job_id}")
async def cancel_job(
    job_id: str,
    job_manager: JobManager = Depends(get_job_manager)
):
    """Cancel a running or pending job."""
    success = await job_manager.cancel_job(job_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {"message": f"Job {job_id} cancelled successfully"}


@router.get("/jobs", response_model=List[ScrapeJob])
async def list_jobs(
    status: Optional[JobStatus] = None,
    limit: int = 100,
    job_manager: JobManager = Depends(get_job_manager)
):
    """
    List jobs with optional status filter.
    
    Args:
        status: Filter by job status (pending, running, completed, failed, cancelled)
        limit: Maximum number of jobs to return (default: 100, max: 1000)
    """
    if limit > 1000:
        limit = 1000
    
    jobs = await job_manager.list_jobs(status=status, limit=limit)
    return jobs


@router.get("/jobs/stats", response_model=Dict[str, Any])
async def get_job_stats(
    job_manager: JobManager = Depends(get_job_manager)
):
    """Get job manager statistics."""
    stats = await job_manager.get_stats()
    return stats


@router.post("/jobs/batch", response_model=List[Dict[str, str]])
async def submit_batch_jobs(
    requests: List[ScrapeRequest],
    job_manager: JobManager = Depends(get_job_manager),
    rate_limit_ok: bool = Depends(rate_limit_check)
):
    """
    Submit multiple scraping jobs for asynchronous processing.
    
    Returns a list of job IDs for tracking each job.
    """
    if len(requests) > 50:  # Limit batch job submissions
        raise HTTPException(status_code=400, detail="Maximum 50 jobs allowed per batch submission")
    
    try:
        job_ids = []
        for request in requests:
            job_id = await job_manager.submit_job(request)
            job_ids.append({"job_id": job_id, "url": str(request.url)})
        
        return job_ids
        
    except Exception as e:
        logger.error(f"Failed to submit batch jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/batch/{job_ids}")
async def get_batch_jobs(
    job_ids: str,  # Comma-separated job IDs
    job_manager: JobManager = Depends(get_job_manager)
):
    """Get status and results for multiple jobs."""
    
    # Parse job IDs
    job_id_list = [job_id.strip() for job_id in job_ids.split(',') if job_id.strip()]
    
    if len(job_id_list) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 job IDs allowed per request")
    
    results = []
    for job_id in job_id_list:
        job = await job_manager.get_job(job_id)
        if job:
            results.append(job)
        else:
            results.append({
                "job_id": job_id,
                "status": "not_found",
                "error": "Job not found"
            })
    
    return results