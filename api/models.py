"""
Pydantic models for API request and response schemas.
"""

from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field, HttpUrl, validator
from enum import Enum
import re


class CrawlerType(str, Enum):
    """Available crawler types."""
    AUTO = "auto"
    HTML = "html"
    JS = "js"
    PDF = "pdf"


class OutputFormat(str, Enum):
    """Available output formats."""
    JSON = "json"
    TEXT = "text"
    STRUCTURED = "structured"
    RAW = "raw"


class FormattingType(str, Enum):
    """Available formatting preservation types."""
    AUTO = "auto"
    UNICODE = "unicode"
    HTML = "html"
    LATEX = "latex"
    MARKDOWN = "markdown"


class FieldSpec(BaseModel):
    """Specification for a single field to extract."""
    pattern: str = Field(..., description="Regex pattern or built-in pattern name")
    multiple: bool = Field(False, description="Extract multiple matches")
    required: bool = Field(False, description="Field is required")
    max_matches: Optional[int] = Field(None, description="Maximum number of matches")
    preserve_formatting: bool = Field(True, description="Preserve special formatting")
    formatting_type: FormattingType = Field(FormattingType.AUTO, description="Type of formatting to preserve")
    transform: Optional[List[str]] = Field(None, description="Post-processing transformations")
    context_keywords: Optional[List[str]] = Field(None, description="Keywords for context validation")
    unique: bool = Field(True, description="Remove duplicates for multiple matches")
    include_alternatives: bool = Field(False, description="Include alternative matches")
    max_alternatives: int = Field(5, description="Maximum alternative matches")
    
    @validator('pattern')
    def validate_pattern(cls, v):
        """Validate regex pattern."""
        if not v or not v.strip():
            raise ValueError("Pattern cannot be empty")
        
        # Test if it's a valid regex (unless it's a built-in pattern name)
        if not v.isalpha():  # Built-in patterns are typically single words
            try:
                re.compile(v)
            except re.error as e:
                raise ValueError(f"Invalid regex pattern: {e}")
        
        return v


class ScrapeRequest(BaseModel):
    """Request model for scraping operations."""
    url: HttpUrl = Field(..., description="Target URL to scrape")
    fields: Dict[str, Union[str, FieldSpec]] = Field(..., description="Fields to extract")
    crawler_type: CrawlerType = Field(CrawlerType.AUTO, description="Type of crawler to use")
    output_format: OutputFormat = Field(OutputFormat.STRUCTURED, description="Output format")
    
    # Crawler options
    max_retries: int = Field(3, description="Maximum retry attempts", ge=0, le=10)
    delay: float = Field(1.0, description="Delay between requests in seconds", ge=0, le=10)
    timeout: int = Field(30, description="Request timeout in seconds", ge=5, le=120)
    
    # JavaScript crawler options
    headless: bool = Field(True, description="Run browser in headless mode")
    browser_type: str = Field("chromium", description="Browser type for JS crawler")
    wait_for_selector: Optional[str] = Field(None, description="CSS selector to wait for")
    wait_for_function: Optional[str] = Field(None, description="JavaScript function to wait for")
    additional_wait: float = Field(2.0, description="Additional wait time in seconds", ge=0, le=30)
    
    # PDF crawler options
    extract_images: bool = Field(True, description="Extract images from PDFs")
    extract_tables: bool = Field(True, description="Extract tables from PDFs")
    
    # Proxy options
    use_proxy: bool = Field(False, description="Use proxy rotation")
    proxy_sources: Optional[List[str]] = Field(None, description="Custom proxy sources")
    
    # Headers and anti-detection
    custom_headers: Optional[Dict[str, str]] = Field(None, description="Custom HTTP headers")
    randomize_headers: bool = Field(True, description="Randomize headers for anti-detection")
    
    # Schema validation
    schema_name: Optional[str] = Field(None, description="Schema name for validation")
    
    # AI enhancement
    use_ai_enhancement: bool = Field(False, description="Use AI for improved extraction")
    ai_prompt: Optional[str] = Field(None, description="Custom AI prompt for enhancement")
    
    @validator('fields')
    def validate_fields(cls, v):
        """Validate field specifications."""
        if not v:
            raise ValueError("At least one field must be specified")
        
        # Convert string patterns to FieldSpec objects
        validated_fields = {}
        for field_name, field_spec in v.items():
            if isinstance(field_spec, str):
                validated_fields[field_name] = FieldSpec(pattern=field_spec)
            else:
                validated_fields[field_name] = field_spec
        
        return validated_fields


class ExtractionResult(BaseModel):
    """Single field extraction result."""
    value: Any = Field(..., description="Extracted value")
    confidence: float = Field(..., description="Confidence score (0.0-1.0)")
    formatted_value: Optional[str] = Field(None, description="Value with preserved formatting")
    alternatives: List[Dict[str, Any]] = Field(default_factory=list, description="Alternative matches")


class ScrapeResponse(BaseModel):
    """Response model for scraping operations."""
    success: bool = Field(..., description="Whether the operation was successful")
    url: str = Field(..., description="Scraped URL")
    fields: Dict[str, Any] = Field(..., description="Extracted field values")
    metadata: Dict[str, Any] = Field(..., description="Scraping metadata")
    
    # Optional detailed results
    formatting_preserved: Optional[Dict[str, str]] = Field(None, description="Fields with preserved formatting")
    confidence_scores: Optional[Dict[str, float]] = Field(None, description="Confidence scores for each field")
    alternative_matches: Optional[Dict[str, List[Dict[str, Any]]]] = Field(None, description="Alternative matches")
    validation: Optional[Dict[str, Any]] = Field(None, description="Schema validation results")
    
    # Error information
    error: Optional[str] = Field(None, description="Error message if operation failed")
    warnings: List[str] = Field(default_factory=list, description="Warning messages")


class BatchScrapeRequest(BaseModel):
    """Request model for batch scraping operations."""
    requests: List[ScrapeRequest] = Field(..., description="List of scrape requests", max_items=100)
    parallel: bool = Field(True, description="Process requests in parallel")
    max_concurrent: int = Field(5, description="Maximum concurrent requests", ge=1, le=20)


class BatchScrapeResponse(BaseModel):
    """Response model for batch scraping operations."""
    total_requests: int = Field(..., description="Total number of requests")
    successful_requests: int = Field(..., description="Number of successful requests")
    failed_requests: int = Field(..., description="Number of failed requests")
    results: List[ScrapeResponse] = Field(..., description="Individual scraping results")
    processing_time: float = Field(..., description="Total processing time in seconds")


class JobStatus(str, Enum):
    """Job status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ScrapeJob(BaseModel):
    """Asynchronous scraping job model."""
    job_id: str = Field(..., description="Unique job identifier")
    status: JobStatus = Field(..., description="Current job status")
    request: ScrapeRequest = Field(..., description="Original scrape request")
    result: Optional[ScrapeResponse] = Field(None, description="Job result (if completed)")
    created_at: float = Field(..., description="Job creation timestamp")
    started_at: Optional[float] = Field(None, description="Job start timestamp")
    completed_at: Optional[float] = Field(None, description="Job completion timestamp")
    progress: float = Field(0.0, description="Job progress (0.0-1.0)", ge=0.0, le=1.0)
    error_message: Optional[str] = Field(None, description="Error message if job failed")


class SystemStats(BaseModel):
    """System statistics model."""
    active_jobs: int = Field(..., description="Number of active jobs")
    completed_jobs: int = Field(..., description="Number of completed jobs")
    failed_jobs: int = Field(..., description="Number of failed jobs")
    proxy_stats: Optional[Dict[str, Any]] = Field(None, description="Proxy manager statistics")
    uptime: float = Field(..., description="System uptime in seconds")
    memory_usage: float = Field(..., description="Memory usage percentage")
    cpu_usage: float = Field(..., description="CPU usage percentage")


class HealthCheck(BaseModel):
    """Health check response model."""
    status: str = Field(..., description="Service status")
    timestamp: float = Field(..., description="Health check timestamp")
    version: str = Field(..., description="API version")
    dependencies: Dict[str, str] = Field(..., description="Dependency status")


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: float = Field(..., description="Error timestamp")


class PatternInfo(BaseModel):
    """Information about available patterns."""
    name: str = Field(..., description="Pattern name")
    pattern: str = Field(..., description="Regex pattern")
    description: str = Field(..., description="Pattern description")
    examples: List[str] = Field(..., description="Example matches")


class SchemaInfo(BaseModel):
    """Information about available schemas."""
    name: str = Field(..., description="Schema name")
    description: str = Field(..., description="Schema description")
    fields: Dict[str, Dict[str, Any]] = Field(..., description="Schema field definitions")


class ConfigUpdate(BaseModel):
    """Configuration update model."""
    proxy_sources: Optional[List[str]] = Field(None, description="Update proxy sources")
    max_retries: Optional[int] = Field(None, description="Update default max retries", ge=0, le=10)
    default_delay: Optional[float] = Field(None, description="Update default delay", ge=0, le=10)
    enable_ai: Optional[bool] = Field(None, description="Enable/disable AI features")
    log_level: Optional[str] = Field(None, description="Update log level")
    
    @validator('log_level')
    def validate_log_level(cls, v):
        """Validate log level."""
        if v and v.upper() not in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
            raise ValueError("Invalid log level")
        return v.upper() if v else v