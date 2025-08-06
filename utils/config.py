"""
Configuration management utilities.
"""

import os
import json
import yaml
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass, asdict
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class CrawlerConfig:
    """Configuration for crawler behavior."""
    max_retries: int = 3
    delay: float = 1.0
    timeout: int = 30
    user_agent_rotation: bool = True
    respect_robots_txt: bool = True
    
    # JavaScript crawler settings
    headless: bool = True
    browser_type: str = "chromium"
    page_load_timeout: int = 30000
    navigation_timeout: int = 30000
    
    # PDF crawler settings
    extract_images: bool = True
    extract_tables: bool = True
    preserve_layout: bool = True


@dataclass
class ProxyConfig:
    """Configuration for proxy management."""
    enabled: bool = False
    proxy_sources: list = None
    max_failures: int = 3
    health_check_interval: int = 300
    rotation_strategy: str = "round_robin"
    proxy_timeout: int = 10
    
    def __post_init__(self):
        if self.proxy_sources is None:
            self.proxy_sources = []


@dataclass
class ExtractionConfig:
    """Configuration for field extraction."""
    preserve_formatting: bool = True
    default_formatting_type: str = "auto"
    include_confidence_scores: bool = True
    include_alternatives: bool = False
    max_alternatives: int = 5
    pattern_timeout: float = 5.0


@dataclass
class AIConfig:
    """Configuration for AI features."""
    enabled: bool = False
    openai_api_key: Optional[str] = None
    model: str = "gpt-3.5-turbo"
    max_tokens: int = 1000
    temperature: float = 0.7
    use_local_models: bool = False
    local_model_path: Optional[str] = None


@dataclass
class APIConfig:
    """Configuration for API server."""
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1
    max_concurrent_jobs: int = 10
    job_cleanup_interval: int = 3600
    enable_cors: bool = True
    cors_origins: list = None
    rate_limit_enabled: bool = False
    rate_limit_requests: int = 100
    rate_limit_window: int = 60
    
    def __post_init__(self):
        if self.cors_origins is None:
            self.cors_origins = ["*"]


@dataclass
class LoggingConfig:
    """Configuration for logging."""
    level: str = "INFO"
    format: str = "standard"
    console_output: bool = True
    file_output: bool = False
    log_file: Optional[str] = None
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    structured_logging: bool = False


@dataclass
class Config:
    """Main configuration class."""
    crawler: CrawlerConfig
    proxy: ProxyConfig
    extraction: ExtractionConfig
    ai: AIConfig
    api: APIConfig
    logging: LoggingConfig
    
    # Global settings
    debug: bool = False
    data_dir: str = "./data"
    temp_dir: str = "./temp"
    cache_enabled: bool = True
    cache_ttl: int = 3600
    
    def __post_init__(self):
        # Ensure data directories exist
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.temp_dir, exist_ok=True)
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'Config':
        """Create Config from dictionary."""
        return cls(
            crawler=CrawlerConfig(**config_dict.get('crawler', {})),
            proxy=ProxyConfig(**config_dict.get('proxy', {})),
            extraction=ExtractionConfig(**config_dict.get('extraction', {})),
            ai=AIConfig(**config_dict.get('ai', {})),
            api=APIConfig(**config_dict.get('api', {})),
            logging=LoggingConfig(**config_dict.get('logging', {})),
            **{k: v for k, v in config_dict.items() if k not in [
                'crawler', 'proxy', 'extraction', 'ai', 'api', 'logging'
            ]}
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert Config to dictionary."""
        return {
            'crawler': asdict(self.crawler),
            'proxy': asdict(self.proxy),
            'extraction': asdict(self.extraction),
            'ai': asdict(self.ai),
            'api': asdict(self.api),
            'logging': asdict(self.logging),
            'debug': self.debug,
            'data_dir': self.data_dir,
            'temp_dir': self.temp_dir,
            'cache_enabled': self.cache_enabled,
            'cache_ttl': self.cache_ttl
        }
    
    def save(self, file_path: Union[str, Path], format: str = "auto"):
        """Save configuration to file."""
        file_path = Path(file_path)
        
        if format == "auto":
            format = file_path.suffix.lower()[1:]  # Remove the dot
        
        config_dict = self.to_dict()
        
        try:
            if format in ["yaml", "yml"]:
                with open(file_path, 'w') as f:
                    yaml.dump(config_dict, f, default_flow_style=False, indent=2)
            elif format == "json":
                with open(file_path, 'w') as f:
                    json.dump(config_dict, f, indent=2)
            else:
                raise ValueError(f"Unsupported format: {format}")
            
            logger.info(f"Configuration saved to {file_path}")
            
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            raise
    
    @classmethod
    def load(cls, file_path: Union[str, Path], format: str = "auto") -> 'Config':
        """Load configuration from file."""
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")
        
        if format == "auto":
            format = file_path.suffix.lower()[1:]
        
        try:
            if format in ["yaml", "yml"]:
                with open(file_path, 'r') as f:
                    config_dict = yaml.safe_load(f)
            elif format == "json":
                with open(file_path, 'r') as f:
                    config_dict = json.load(f)
            else:
                raise ValueError(f"Unsupported format: {format}")
            
            logger.info(f"Configuration loaded from {file_path}")
            return cls.from_dict(config_dict)
            
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise
    
    def update_from_env(self, prefix: str = "SCRAPER_"):
        """Update configuration from environment variables."""
        env_mappings = {
            f"{prefix}DEBUG": ("debug", bool),
            f"{prefix}DATA_DIR": ("data_dir", str),
            f"{prefix}TEMP_DIR": ("temp_dir", str),
            
            # Crawler settings
            f"{prefix}CRAWLER_MAX_RETRIES": ("crawler.max_retries", int),
            f"{prefix}CRAWLER_DELAY": ("crawler.delay", float),
            f"{prefix}CRAWLER_TIMEOUT": ("crawler.timeout", int),
            f"{prefix}CRAWLER_HEADLESS": ("crawler.headless", bool),
            f"{prefix}CRAWLER_BROWSER_TYPE": ("crawler.browser_type", str),
            
            # Proxy settings
            f"{prefix}PROXY_ENABLED": ("proxy.enabled", bool),
            f"{prefix}PROXY_MAX_FAILURES": ("proxy.max_failures", int),
            f"{prefix}PROXY_ROTATION_STRATEGY": ("proxy.rotation_strategy", str),
            
            # AI settings
            f"{prefix}AI_ENABLED": ("ai.enabled", bool),
            f"{prefix}OPENAI_API_KEY": ("ai.openai_api_key", str),
            f"{prefix}AI_MODEL": ("ai.model", str),
            
            # API settings
            f"{prefix}API_HOST": ("api.host", str),
            f"{prefix}API_PORT": ("api.port", int),
            f"{prefix}API_WORKERS": ("api.workers", int),
            f"{prefix}API_MAX_CONCURRENT_JOBS": ("api.max_concurrent_jobs", int),
            
            # Logging settings
            f"{prefix}LOG_LEVEL": ("logging.level", str),
            f"{prefix}LOG_FILE": ("logging.log_file", str),
        }
        
        for env_var, (config_path, value_type) in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                try:
                    # Convert value to appropriate type
                    if value_type == bool:
                        value = env_value.lower() in ('true', '1', 'yes', 'on')
                    elif value_type == int:
                        value = int(env_value)
                    elif value_type == float:
                        value = float(env_value)
                    else:
                        value = env_value
                    
                    # Set nested attribute
                    self._set_nested_attr(config_path, value)
                    logger.debug(f"Updated {config_path} from environment: {value}")
                    
                except (ValueError, TypeError) as e:
                    logger.warning(f"Failed to parse environment variable {env_var}: {e}")
    
    def _set_nested_attr(self, path: str, value: Any):
        """Set nested attribute using dot notation."""
        parts = path.split('.')
        obj = self
        
        for part in parts[:-1]:
            obj = getattr(obj, part)
        
        setattr(obj, parts[-1], value)
    
    def validate(self) -> List[str]:
        """Validate configuration and return list of warnings/errors."""
        warnings = []
        
        # Validate crawler settings
        if self.crawler.max_retries < 0:
            warnings.append("crawler.max_retries should be >= 0")
        
        if self.crawler.delay < 0:
            warnings.append("crawler.delay should be >= 0")
        
        if self.crawler.browser_type not in ["chromium", "firefox", "webkit"]:
            warnings.append("crawler.browser_type should be one of: chromium, firefox, webkit")
        
        # Validate proxy settings
        if self.proxy.enabled and not self.proxy.proxy_sources:
            warnings.append("proxy.enabled is True but no proxy_sources configured")
        
        if self.proxy.rotation_strategy not in ["round_robin", "random", "least_used"]:
            warnings.append("proxy.rotation_strategy should be one of: round_robin, random, least_used")
        
        # Validate AI settings
        if self.ai.enabled and not self.ai.openai_api_key and not self.ai.use_local_models:
            warnings.append("ai.enabled is True but no OpenAI API key or local models configured")
        
        # Validate API settings
        if self.api.port < 1 or self.api.port > 65535:
            warnings.append("api.port should be between 1 and 65535")
        
        if self.api.max_concurrent_jobs < 1:
            warnings.append("api.max_concurrent_jobs should be >= 1")
        
        # Validate logging settings
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.logging.level.upper() not in valid_levels:
            warnings.append(f"logging.level should be one of: {', '.join(valid_levels)}")
        
        return warnings


def load_config(
    config_file: Optional[Union[str, Path]] = None,
    env_prefix: str = "SCRAPER_",
    create_default: bool = True
) -> Config:
    """
    Load configuration from file and environment variables.
    
    Args:
        config_file: Path to configuration file
        env_prefix: Prefix for environment variables
        create_default: Whether to create default config if file not found
        
    Returns:
        Configuration object
    """
    
    # Try to load from file
    if config_file:
        config_path = Path(config_file)
        if config_path.exists():
            try:
                config = Config.load(config_path)
                logger.info(f"Loaded configuration from {config_path}")
            except Exception as e:
                logger.error(f"Failed to load config from {config_path}: {e}")
                if create_default:
                    logger.info("Using default configuration")
                    config = create_default_config()
                else:
                    raise
        else:
            if create_default:
                logger.info(f"Config file {config_path} not found, using defaults")
                config = create_default_config()
            else:
                raise FileNotFoundError(f"Configuration file not found: {config_path}")
    else:
        # Look for default config files
        default_paths = [
            "config.yaml",
            "config.yml", 
            "config.json",
            "scraper.yaml",
            "scraper.yml",
            "scraper.json"
        ]
        
        config = None
        for path in default_paths:
            if Path(path).exists():
                try:
                    config = Config.load(path)
                    logger.info(f"Loaded configuration from {path}")
                    break
                except Exception as e:
                    logger.warning(f"Failed to load config from {path}: {e}")
        
        if config is None:
            if create_default:
                logger.info("No configuration file found, using defaults")
                config = create_default_config()
            else:
                raise FileNotFoundError("No configuration file found")
    
    # Update from environment variables
    config.update_from_env(env_prefix)
    
    # Validate configuration
    warnings = config.validate()
    for warning in warnings:
        logger.warning(f"Configuration warning: {warning}")
    
    return config


def create_default_config() -> Config:
    """Create default configuration."""
    return Config(
        crawler=CrawlerConfig(),
        proxy=ProxyConfig(),
        extraction=ExtractionConfig(),
        ai=AIConfig(),
        api=APIConfig(),
        logging=LoggingConfig()
    )


def create_sample_config_file(file_path: Union[str, Path], format: str = "yaml"):
    """Create a sample configuration file with all options documented."""
    config = create_default_config()
    
    # Add comments/documentation
    config_dict = config.to_dict()
    
    # Add example proxy sources
    config_dict['proxy']['proxy_sources'] = [
        "http://proxy1.example.com:8080",
        "http://proxy2.example.com:8080"
    ]
    
    # Add example AI settings
    config_dict['ai']['openai_api_key'] = "your-openai-api-key-here"
    
    config.save(file_path, format)
    logger.info(f"Sample configuration created at {file_path}")


if __name__ == "__main__":
    # CLI for config management
    import argparse
    
    parser = argparse.ArgumentParser(description="Configuration management")
    parser.add_argument("--create-sample", help="Create sample config file")
    parser.add_argument("--format", choices=["yaml", "json"], default="yaml")
    parser.add_argument("--validate", help="Validate config file")
    
    args = parser.parse_args()
    
    if args.create_sample:
        create_sample_config_file(args.create_sample, args.format)
    
    if args.validate:
        try:
            config = Config.load(args.validate)
            warnings = config.validate()
            if warnings:
                print("Configuration warnings:")
                for warning in warnings:
                    print(f"  - {warning}")
            else:
                print("Configuration is valid!")
        except Exception as e:
            print(f"Configuration validation failed: {e}")