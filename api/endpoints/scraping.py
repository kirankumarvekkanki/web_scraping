"""
Main scraping endpoints.
"""

import asyncio
import logging
import time
from typing import List

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse

from ..models import *
from ..dependencies import get_scraping_service, get_job_manager, rate_limit_check
from ..scraping_service import ScrapingService
from ..job_manager import JobManager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/scrape", response_model=ScrapeResponse)
async def scrape_url(
    request: ScrapeRequest,
    scraping_service: ScrapingService = Depends(get_scraping_service),
    rate_limit_ok: bool = Depends(rate_limit_check)
):
    """
    Scrape a single URL with specified field extraction.
    
    This is a synchronous endpoint that returns results immediately.
    For long-running operations, use the /jobs endpoint.
    """
    try:
        logger.info(f"Scraping request for: {request.url}")
        
        # Perform scraping
        result = await scraping_service.scrape(request)
        
        # Convert to response model
        response = ScrapeResponse(
            success=result.get('success', False),
            url=str(request.url),
            fields=result.get('fields', {}),
            metadata=result.get('metadata', {}),
            formatting_preserved=result.get('formatting_preserved'),
            confidence_scores=result.get('confidence_scores'),
            alternative_matches=result.get('alternative_matches'),
            validation=result.get('validation'),
            error=result.get('error'),
            warnings=result.get('warnings', [])
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Scraping failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch", response_model=BatchScrapeResponse)
async def batch_scrape(
    request: BatchScrapeRequest,
    scraping_service: ScrapingService = Depends(get_scraping_service),
    rate_limit_ok: bool = Depends(rate_limit_check)
):
    """
    Perform batch scraping of multiple URLs.
    
    This endpoint processes multiple scraping requests either sequentially or in parallel.
    """
    if len(request.requests) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 requests allowed per batch")
    
    start_time = time.time()
    results = []
    successful_count = 0
    failed_count = 0
    
    try:
        if request.parallel:
            # Process requests in parallel with concurrency limit
            semaphore = asyncio.Semaphore(request.max_concurrent)
            
            async def process_request(scrape_request):
                async with semaphore:
                    try:
                        result = await scraping_service.scrape(scrape_request)
                        response = ScrapeResponse(
                            success=result.get('success', False),
                            url=str(scrape_request.url),
                            fields=result.get('fields', {}),
                            metadata=result.get('metadata', {}),
                            formatting_preserved=result.get('formatting_preserved'),
                            confidence_scores=result.get('confidence_scores'),
                            alternative_matches=result.get('alternative_matches'),
                            validation=result.get('validation'),
                            error=result.get('error'),
                            warnings=result.get('warnings', [])
                        )
                        return response
                    except Exception as e:
                        logger.error(f"Batch item failed for {scrape_request.url}: {e}")
                        return ScrapeResponse(
                            success=False,
                            url=str(scrape_request.url),
                            fields={},
                            metadata={},
                            error=str(e)
                        )
            
            # Execute all requests
            results = await asyncio.gather(
                *[process_request(req) for req in request.requests],
                return_exceptions=True
            )
            
            # Handle exceptions
            final_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    final_results.append(ScrapeResponse(
                        success=False,
                        url=str(request.requests[i].url),
                        fields={},
                        metadata={},
                        error=str(result)
                    ))
                    failed_count += 1
                else:
                    final_results.append(result)
                    if result.success:
                        successful_count += 1
                    else:
                        failed_count += 1
            
            results = final_results
            
        else:
            # Process requests sequentially
            for scrape_request in request.requests:
                try:
                    result = await scraping_service.scrape(scrape_request)
                    response = ScrapeResponse(
                        success=result.get('success', False),
                        url=str(scrape_request.url),
                        fields=result.get('fields', {}),
                        metadata=result.get('metadata', {}),
                        formatting_preserved=result.get('formatting_preserved'),
                        confidence_scores=result.get('confidence_scores'),
                        alternative_matches=result.get('alternative_matches'),
                        validation=result.get('validation'),
                        error=result.get('error'),
                        warnings=result.get('warnings', [])
                    )
                    
                    results.append(response)
                    
                    if response.success:
                        successful_count += 1
                    else:
                        failed_count += 1
                        
                except Exception as e:
                    logger.error(f"Batch item failed for {scrape_request.url}: {e}")
                    results.append(ScrapeResponse(
                        success=False,
                        url=str(scrape_request.url),
                        fields={},
                        metadata={},
                        error=str(e)
                    ))
                    failed_count += 1
        
        processing_time = time.time() - start_time
        
        return BatchScrapeResponse(
            total_requests=len(request.requests),
            successful_requests=successful_count,
            failed_requests=failed_count,
            results=results,
            processing_time=processing_time
        )
        
    except Exception as e:
        logger.error(f"Batch processing failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate-url")
async def validate_url(
    url: HttpUrl,
    scraping_service: ScrapingService = Depends(get_scraping_service)
):
    """Validate if a URL is accessible and determine its content type."""
    try:
        result = await scraping_service.validate_url(str(url))
        return result
    except Exception as e:
        logger.error(f"URL validation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/patterns", response_model=List[PatternInfo])
async def get_patterns(
    scraping_service: ScrapingService = Depends(get_scraping_service)
):
    """Get all available built-in extraction patterns."""
    try:
        patterns = await scraping_service.get_available_patterns()
        
        # Convert to PatternInfo objects with descriptions and examples
        pattern_info = []
        pattern_descriptions = {
            'email': 'Email addresses',
            'phone': 'Phone numbers (US format)',
            'url': 'HTTP/HTTPS URLs',
            'date_iso': 'ISO date format (YYYY-MM-DD)',
            'date_us': 'US date format (MM/DD/YYYY)',
            'time': 'Time format (HH:MM or HH:MM:SS with optional AM/PM)',
            'price': 'Prices with optional dollar sign and currency',
            'percentage': 'Percentage values',
            'temperature': 'Temperature values in Celsius or Fahrenheit',
            'chemical_formula': 'Chemical formulas',
            'molecular_formula': 'Molecular formulas with subscripts',
            'doi': 'Digital Object Identifier (DOI)',
            'isbn': 'ISBN numbers',
            'coordinate': 'GPS coordinates (lat, lon)',
            'ip_address': 'IPv4 addresses',
            'hashtag': 'Social media hashtags',
            'mention': 'Social media mentions (@username)',
            'hex_color': 'Hexadecimal color codes',
            'credit_card': 'Credit card numbers',
            'social_security': 'Social security numbers'
        }
        
        pattern_examples = {
            'email': ['user@example.com', 'test.email@domain.org'],
            'phone': ['(555) 123-4567', '555-123-4567', '+1-555-123-4567'],
            'url': ['https://example.com', 'http://website.org/path'],
            'date_iso': ['2024-01-15', '2023-12-31'],
            'date_us': ['01/15/2024', '12/31/2023'],
            'time': ['14:30', '2:30 PM', '14:30:45'],
            'price': ['$19.99', '1,500.00', '$1,234.56'],
            'percentage': ['50%', '99.9%', '0.5%'],
            'temperature': ['25°C', '-10°F', '98.6°F'],
            'chemical_formula': ['H2O', 'CO2', 'NaCl'],
            'molecular_formula': ['H₂SO₄', 'C₆H₁₂O₆'],
            'doi': ['10.1000/182', '10.1038/nature12373'],
            'isbn': ['978-0-123456-78-9', '0-123456-78-9'],
            'coordinate': ['40.7128,-74.0060', '51.5074,-0.1278'],
            'ip_address': ['192.168.1.1', '10.0.0.1'],
            'hashtag': ['#example', '#webScraping'],
            'mention': ['@username', '@john_doe'],
            'hex_color': ['#FF0000', '#00FF00'],
            'credit_card': ['4111-1111-1111-1111', '4111 1111 1111 1111'],
            'social_security': ['123-45-6789']
        }
        
        for name, pattern in patterns.items():
            pattern_info.append(PatternInfo(
                name=name,
                pattern=pattern,
                description=pattern_descriptions.get(name, 'Custom pattern'),
                examples=pattern_examples.get(name, [])
            ))
        
        return pattern_info
        
    except Exception as e:
        logger.error(f"Failed to get patterns: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test-pattern")
async def test_pattern(
    pattern: str,
    test_text: str,
    scraping_service: ScrapingService = Depends(get_scraping_service)
):
    """Test a regex pattern against sample text."""
    try:
        result = await scraping_service.test_pattern(pattern, test_text)
        return result
    except Exception as e:
        logger.error(f"Pattern testing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))