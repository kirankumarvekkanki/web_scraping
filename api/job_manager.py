"""
Background job manager for asynchronous scraping operations.
"""

import asyncio
import logging
import time
import uuid
from typing import Dict, Optional, List
from concurrent.futures import ThreadPoolExecutor
import threading

from .models import ScrapeJob, ScrapeRequest, ScrapeResponse, JobStatus
from .scraping_service import ScrapingService

logger = logging.getLogger(__name__)


class JobManager:
    """Manages background scraping jobs."""
    
    def __init__(self, max_concurrent_jobs: int = 10):
        self.max_concurrent_jobs = max_concurrent_jobs
        self.jobs: Dict[str, ScrapeJob] = {}
        self.running_jobs: Dict[str, asyncio.Task] = {}
        self.scraping_service = ScrapingService()
        self.is_running = False
        self.cleanup_task = None
        self.lock = threading.Lock()
        
        # Job statistics
        self.stats = {
            'total_jobs': 0,
            'completed_jobs': 0,
            'failed_jobs': 0,
            'cancelled_jobs': 0
        }
    
    async def start(self):
        """Start the job manager."""
        if self.is_running:
            return
        
        self.is_running = True
        logger.info("Starting job manager...")
        
        # Initialize scraping service
        await self.scraping_service.initialize()
        
        # Start cleanup task
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        logger.info(f"Job manager started with max {self.max_concurrent_jobs} concurrent jobs")
    
    async def stop(self):
        """Stop the job manager."""
        if not self.is_running:
            return
        
        self.is_running = False
        logger.info("Stopping job manager...")
        
        # Cancel all running jobs
        for job_id, task in self.running_jobs.items():
            if not task.done():
                task.cancel()
                logger.info(f"Cancelled job {job_id}")
        
        # Wait for tasks to complete or cancel
        if self.running_jobs:
            await asyncio.gather(*self.running_jobs.values(), return_exceptions=True)
        
        # Stop cleanup task
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Cleanup scraping service
        await self.scraping_service.cleanup()
        
        logger.info("Job manager stopped")
    
    async def submit_job(self, request: ScrapeRequest) -> str:
        """
        Submit a new scraping job.
        
        Args:
            request: Scraping request
            
        Returns:
            Job ID
        """
        if not self.is_running:
            raise RuntimeError("Job manager is not running")
        
        # Generate unique job ID
        job_id = str(uuid.uuid4())
        
        # Create job
        job = ScrapeJob(
            job_id=job_id,
            status=JobStatus.PENDING,
            request=request,
            created_at=time.time(),
            progress=0.0
        )
        
        with self.lock:
            self.jobs[job_id] = job
            self.stats['total_jobs'] += 1
        
        # Start job if under limit
        await self._maybe_start_job(job_id)
        
        logger.info(f"Submitted job {job_id} for URL: {request.url}")
        return job_id
    
    async def get_job(self, job_id: str) -> Optional[ScrapeJob]:
        """Get job by ID."""
        return self.jobs.get(job_id)
    
    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a job."""
        job = self.jobs.get(job_id)
        if not job:
            return False
        
        # Cancel running task
        if job_id in self.running_jobs:
            task = self.running_jobs[job_id]
            if not task.done():
                task.cancel()
                
                # Wait for cancellation
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        # Update job status
        with self.lock:
            job.status = JobStatus.CANCELLED
            self.stats['cancelled_jobs'] += 1
        
        logger.info(f"Cancelled job {job_id}")
        return True
    
    async def list_jobs(self, status: Optional[JobStatus] = None, limit: int = 100) -> List[ScrapeJob]:
        """List jobs with optional status filter."""
        jobs = list(self.jobs.values())
        
        if status:
            jobs = [job for job in jobs if job.status == status]
        
        # Sort by creation time (newest first)
        jobs.sort(key=lambda x: x.created_at, reverse=True)
        
        return jobs[:limit]
    
    async def get_stats(self) -> Dict[str, any]:
        """Get job manager statistics."""
        with self.lock:
            running_count = len(self.running_jobs)
            pending_count = len([j for j in self.jobs.values() if j.status == JobStatus.PENDING])
            
            return {
                'total_jobs': self.stats['total_jobs'],
                'completed_jobs': self.stats['completed_jobs'],
                'failed_jobs': self.stats['failed_jobs'],
                'cancelled_jobs': self.stats['cancelled_jobs'],
                'running_jobs': running_count,
                'pending_jobs': pending_count,
                'max_concurrent_jobs': self.max_concurrent_jobs,
                'memory_usage': len(self.jobs)
            }
    
    async def _maybe_start_job(self, job_id: str):
        """Start a job if under concurrent limit."""
        if len(self.running_jobs) >= self.max_concurrent_jobs:
            return
        
        job = self.jobs.get(job_id)
        if not job or job.status != JobStatus.PENDING:
            return
        
        # Start the job
        task = asyncio.create_task(self._run_job(job_id))
        self.running_jobs[job_id] = task
        
        # Update job status
        with self.lock:
            job.status = JobStatus.RUNNING
            job.started_at = time.time()
            job.progress = 0.1
    
    async def _run_job(self, job_id: str):
        """Run a scraping job."""
        job = self.jobs[job_id]
        
        try:
            logger.info(f"Starting job {job_id}")
            
            # Update progress
            job.progress = 0.2
            
            # Perform scraping
            result = await self.scraping_service.scrape(job.request)
            
            # Update progress
            job.progress = 0.9
            
            # Create response
            response = ScrapeResponse(
                success=result.get('success', False),
                url=str(job.request.url),
                fields=result.get('fields', {}),
                metadata=result.get('metadata', {}),
                formatting_preserved=result.get('formatting_preserved'),
                confidence_scores=result.get('confidence_scores'),
                alternative_matches=result.get('alternative_matches'),
                validation=result.get('validation'),
                error=result.get('error'),
                warnings=result.get('warnings', [])
            )
            
            # Update job
            with self.lock:
                job.status = JobStatus.COMPLETED
                job.result = response
                job.completed_at = time.time()
                job.progress = 1.0
                self.stats['completed_jobs'] += 1
            
            logger.info(f"Completed job {job_id}")
            
        except asyncio.CancelledError:
            logger.info(f"Job {job_id} was cancelled")
            with self.lock:
                job.status = JobStatus.CANCELLED
                job.completed_at = time.time()
                self.stats['cancelled_jobs'] += 1
            raise
            
        except Exception as e:
            logger.error(f"Job {job_id} failed: {e}", exc_info=True)
            
            with self.lock:
                job.status = JobStatus.FAILED
                job.error_message = str(e)
                job.completed_at = time.time()
                job.progress = 1.0
                self.stats['failed_jobs'] += 1
            
        finally:
            # Remove from running jobs
            if job_id in self.running_jobs:
                del self.running_jobs[job_id]
            
            # Try to start next pending job
            await self._start_next_pending_job()
    
    async def _start_next_pending_job(self):
        """Start the next pending job if under limit."""
        if len(self.running_jobs) >= self.max_concurrent_jobs:
            return
        
        # Find next pending job
        pending_jobs = [
            (job_id, job) for job_id, job in self.jobs.items()
            if job.status == JobStatus.PENDING
        ]
        
        if not pending_jobs:
            return
        
        # Sort by creation time (oldest first)
        pending_jobs.sort(key=lambda x: x[1].created_at)
        
        # Start the oldest pending job
        job_id, job = pending_jobs[0]
        await self._maybe_start_job(job_id)
    
    async def _cleanup_loop(self):
        """Background task to clean up old jobs."""
        while self.is_running:
            try:
                await asyncio.sleep(300)  # Run every 5 minutes
                
                if not self.is_running:
                    break
                
                current_time = time.time()
                max_age = 24 * 60 * 60  # 24 hours
                
                # Find old completed/failed jobs to remove
                old_jobs = []
                for job_id, job in self.jobs.items():
                    if (job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED] and
                        job.completed_at and 
                        current_time - job.completed_at > max_age):
                        old_jobs.append(job_id)
                
                # Remove old jobs
                if old_jobs:
                    with self.lock:
                        for job_id in old_jobs:
                            del self.jobs[job_id]
                    
                    logger.info(f"Cleaned up {len(old_jobs)} old jobs")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}", exc_info=True)