#!/usr/bin/env python3
"""
Advanced Web Scraping Framework - Main Entry Point

A production-ready, high-performance web scraping framework with:
- Multi-format content extraction (HTML, JS-rendered pages, PDFs)
- Advanced field extraction with 50+ built-in patterns
- Formatting preservation for scientific content
- AI-enhanced extraction and validation
- Smart proxy management with health monitoring
- Comprehensive API with async job processing
- Performance monitoring and caching
- Production-ready deployment features

This entry point provides both CLI and API server functionality with
comprehensive configuration management, logging, and error handling.

Features:
- Command-line interface for direct scraping
- API server with FastAPI and async workers
- Configuration management with YAML/JSON
- Structured logging with performance metrics
- Docker and Kubernetes deployment support
- Health checks and monitoring endpoints

Author: Web Scraping Framework Team
License: MIT
Version: 1.0.0
"""

import asyncio
import argparse
import sys
import uvicorn
import signal
import os
from pathlib import Path
from typing import Optional, Dict, Any
import logging

# Ensure project root is in Python path for imports
PROJECT_ROOT = Path(__file__).parent.absolute()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Import after path setup to avoid import errors
try:
    from utils import setup_logging, load_config
    from api.main import app
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("💡 Make sure you've installed dependencies: pip install -r requirements.txt")
    sys.exit(1)

# Configure module-level logging
logger = logging.getLogger(__name__)


def create_arg_parser() -> argparse.ArgumentParser:
    """
    Create comprehensive command line argument parser with all options.
    
    Provides arguments for:
    - API server configuration
    - CLI scraping operations
    - Configuration management
    - Logging and debugging
    - Performance tuning
    
    Returns:
        Configured ArgumentParser instance
    """
    parser = argparse.ArgumentParser(
        description="🚀 Advanced Web Scraping Framework v1.0.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
🎯 Examples:

  API Server:
    %(prog)s --api                                      # Start API server
    %(prog)s --api --host 0.0.0.0 --port 8080         # Custom host/port
    %(prog)s --api --workers 4 --reload                # Development mode
    %(prog)s --config production.yaml --api            # Production config

  CLI Scraping:
    %(prog)s --url https://example.com --fields email,phone
    %(prog)s --url https://chemical-site.com --fields "formula:molecular_formula,temp:temperature"
    %(prog)s --batch urls.txt --output results.json --format structured
    %(prog)s --url https://example.com --proxy --ai --fields chemical_formula

  Configuration:
    %(prog)s --create-config config.yaml               # Create sample config
    %(prog)s --validate-config config.yaml             # Validate configuration

  Advanced Features:
    %(prog)s --url https://spa-app.com --crawler js --wait-for ".content"
    %(prog)s --url https://example.com --schema scientific_paper
    %(prog)s --test-installation                        # Verify setup

🔗 Documentation: http://localhost:8000/docs (when API is running)
🐛 Issues: https://github.com/your-org/web-scraping-framework/issues
        """
    )
    
    # Configuration Management
    config_group = parser.add_argument_group('Configuration Management')
    config_group.add_argument(
        "--config", 
        type=str, 
        metavar="FILE",
        help="Path to configuration file (YAML or JSON)"
    )
    config_group.add_argument(
        "--create-config", 
        type=str,
        metavar="FILE",
        help="Create a sample configuration file with all options"
    )
    config_group.add_argument(
        "--validate-config",
        type=str,
        metavar="FILE", 
        help="Validate configuration file and show warnings"
    )
    config_group.add_argument(
        "--show-config",
        action="store_true",
        help="Display current configuration and exit"
    )
    
    # API Server Configuration
    api_group = parser.add_argument_group('API Server Options')
    api_group.add_argument(
        "--api", 
        action="store_true",
        help="🌐 Start the FastAPI server"
    )
    api_group.add_argument(
        "--host", 
        type=str, 
        default="127.0.0.1",
        metavar="HOST",
        help="Host to bind the API server (default: 127.0.0.1, use 0.0.0.0 for external access)"
    )
    api_group.add_argument(
        "--port", 
        type=int, 
        default=8000,
        metavar="PORT",
        help="Port to bind the API server (default: 8000)"
    )
    api_group.add_argument(
        "--workers", 
        type=int, 
        default=1,
        metavar="N",
        help="Number of worker processes for production (default: 1, recommend CPU count)"
    )
    api_group.add_argument(
        "--reload", 
        action="store_true",
        help="🔄 Enable auto-reload for development (disables workers)"
    )
    api_group.add_argument(
        "--ssl-keyfile",
        type=str,
        metavar="FILE",
        help="SSL key file for HTTPS"
    )
    api_group.add_argument(
        "--ssl-certfile", 
        type=str,
        metavar="FILE",
        help="SSL certificate file for HTTPS"
    )
    
    # CLI scraping options
    parser.add_argument(
        "--url", 
        type=str,
        help="URL to scrape"
    )
    parser.add_argument(
        "--batch", 
        type=str,
        help="File containing URLs to scrape (one per line)"
    )
    parser.add_argument(
        "--fields", 
        type=str,
        help="Comma-separated list of fields to extract (or field:pattern pairs)"
    )
    parser.add_argument(
        "--output", 
        type=str,
        help="Output file for results (JSON format)"
    )
    parser.add_argument(
        "--format", 
        choices=["json", "text", "structured"],
        default="structured",
        help="Output format (default: structured)"
    )
    parser.add_argument(
        "--crawler", 
        choices=["auto", "html", "js", "pdf"],
        default="auto",
        help="Crawler type to use (default: auto)"
    )
    
    # Proxy options
    parser.add_argument(
        "--proxy", 
        action="store_true",
        help="Enable proxy rotation"
    )
    parser.add_argument(
        "--proxy-sources", 
        type=str, 
        nargs="+",
        help="Proxy URLs or source files"
    )
    
    # AI options
    parser.add_argument(
        "--ai", 
        action="store_true",
        help="Enable AI-enhanced extraction"
    )
    
    # Logging options
    parser.add_argument(
        "--log-level", 
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level (default: INFO)"
    )
    parser.add_argument(
        "--log-file", 
        type=str,
        help="Log file path"
    )
    parser.add_argument(
        "--quiet", 
        action="store_true",
        help="Suppress console output"
    )
    
    # System and Development Options
    system_group = parser.add_argument_group('System Options')
    system_group.add_argument(
        "--test-installation",
        action="store_true",
        help="🧪 Run installation tests and verify setup"
    )
    system_group.add_argument(
        "--benchmark",
        action="store_true", 
        help="📊 Run performance benchmarks"
    )
    system_group.add_argument(
        "--health-check",
        action="store_true",
        help="💊 Run health check and show system status"
    )
    system_group.add_argument(
        "--version", 
        action="version", 
        version="🚀 Advanced Web Scraping Framework v1.0.0"
    )
    
    return parser


async def cli_scrape(args, config):
    """Perform CLI-based scraping."""
    from api.scraping_service import ScrapingService
    from api.models import ScrapeRequest, FieldSpec
    import json
    
    # Initialize scraping service
    service = ScrapingService()
    await service.initialize()
    
    try:
        # Parse fields
        fields = {}
        if args.fields:
            for field_spec in args.fields.split(','):
                if ':' in field_spec:
                    field_name, pattern = field_spec.split(':', 1)
                    fields[field_name.strip()] = FieldSpec(pattern=pattern.strip())
                else:
                    fields[field_spec.strip()] = FieldSpec(pattern=field_spec.strip())
        else:
            # Default fields for general scraping
            fields = {
                "title": "title",
                "links": "url",
                "emails": "email",
                "phones": "phone"
            }
        
        urls = []
        
        # Collect URLs
        if args.url:
            urls.append(args.url)
        
        if args.batch:
            try:
                with open(args.batch, 'r') as f:
                    batch_urls = [line.strip() for line in f if line.strip()]
                    urls.extend(batch_urls)
            except FileNotFoundError:
                print(f"Error: Batch file not found: {args.batch}")
                return
        
        if not urls:
            print("Error: No URLs provided. Use --url or --batch")
            return
        
        results = []
        
        print(f"Scraping {len(urls)} URL(s)...")
        
        for i, url in enumerate(urls, 1):
            print(f"[{i}/{len(urls)}] Processing: {url}")
            
            # Create request
            request = ScrapeRequest(
                url=url,
                fields=fields,
                crawler_type=args.crawler,
                output_format=args.format,
                use_proxy=args.proxy,
                proxy_sources=args.proxy_sources or [],
                use_ai_enhancement=args.ai
            )
            
            # Perform scraping
            result = await service.scrape(request)
            results.append(result)
            
            if result.get('success'):
                print(f"  ✓ Success - {len(result.get('fields', {}))} fields extracted")
            else:
                print(f"  ✗ Failed - {result.get('error', 'Unknown error')}")
        
        # Output results
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            print(f"\nResults saved to: {args.output}")
        else:
            # Print to console
            if args.format == "json":
                print(json.dumps(results, indent=2, default=str))
            elif args.format == "text":
                for i, result in enumerate(results):
                    print(f"\n--- Result {i+1} ---")
                    if result.get('success'):
                        for field, value in result.get('fields', {}).items():
                            print(f"{field}: {value}")
                    else:
                        print(f"Error: {result.get('error')}")
            else:  # structured
                for i, result in enumerate(results):
                    print(f"\n=== URL {i+1}: {result.get('metadata', {}).get('source_url', 'Unknown')} ===")
                    if result.get('success'):
                        fields = result.get('fields', {})
                        confidence = result.get('confidence_scores', {})
                        
                        for field, value in fields.items():
                            conf_score = confidence.get(field, 1.0)
                            print(f"{field:20}: {value} (confidence: {conf_score:.2f})")
                    else:
                        print(f"ERROR: {result.get('error')}")
        
        print(f"\nCompleted! Processed {len(urls)} URLs")
        
    finally:
        await service.cleanup()


def setup_signal_handlers() -> None:
    """
    Setup graceful shutdown signal handlers.
    
    Handles SIGINT (Ctrl+C) and SIGTERM for clean shutdown.
    """
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        sys.exit(0)
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    if hasattr(signal, 'SIGTERM'):
        signal.signal(signal.SIGTERM, signal_handler)


def validate_api_config(args) -> bool:
    """
    Validate API server configuration.
    
    Args:
        args: Parsed command line arguments
        
    Returns:
        True if configuration is valid, False otherwise
    """
    # Port validation
    if not (1 <= args.port <= 65535):
        print(f"❌ Invalid port {args.port}. Must be between 1 and 65535.")
        return False
    
    # SSL validation
    if (args.ssl_keyfile or args.ssl_certfile):
        if not (args.ssl_keyfile and args.ssl_certfile):
            print("❌ Both --ssl-keyfile and --ssl-certfile must be provided for HTTPS.")
            return False
        
        if not Path(args.ssl_keyfile).exists():
            print(f"❌ SSL key file not found: {args.ssl_keyfile}")
            return False
            
        if not Path(args.ssl_certfile).exists():
            print(f"❌ SSL certificate file not found: {args.ssl_certfile}")
            return False
    
    # Workers validation
    if args.workers < 1:
        print(f"❌ Invalid worker count {args.workers}. Must be at least 1.")
        return False
    
    if args.workers > 1 and args.reload:
        print("⚠️  Auto-reload is enabled, forcing workers=1")
        args.workers = 1
    
    return True


def start_api_server(args, config) -> None:
    """
    Start the FastAPI server with comprehensive configuration.
    
    Args:
        args: Parsed command line arguments
        config: Loaded configuration object
    """
    # Validate configuration
    if not validate_api_config(args):
        sys.exit(1)
    
    # Setup signal handlers for graceful shutdown
    setup_signal_handlers()
    
    # Determine protocol
    protocol = "https" if (args.ssl_keyfile and args.ssl_certfile) else "http"
    
    # Print startup information
    print("🚀 Starting Advanced Web Scraping Framework API Server...")
    print(f"📍 Server URL: {protocol}://{args.host}:{args.port}")
    print(f"📚 API Documentation: {protocol}://{args.host}:{args.port}/docs")
    print(f"📖 ReDoc Documentation: {protocol}://{args.host}:{args.port}/redoc")
    print(f"🔧 Workers: {args.workers}")
    print(f"📊 Log Level: {args.log_level}")
    
    if args.reload:
        print("🔄 Development mode: Auto-reload enabled")
    
    if args.ssl_keyfile:
        print("🔒 HTTPS enabled")
    
    print("\n" + "="*60)
    print("🎯 Quick API Usage Examples:")
    print(f"  curl -X POST {protocol}://{args.host}:{args.port}/api/v1/scrape \\")
    print("    -H 'Content-Type: application/json' \\")
    print("    -d '{\"url\": \"https://example.com\", \"fields\": {\"title\": \"h1\"}}'")
    print("="*60)
    print("\n👋 Press Ctrl+C to stop the server\n")
    
    # Prepare uvicorn configuration
    uvicorn_config = {
        "app": "api.main:app",
        "host": args.host,
        "port": args.port,
        "log_level": args.log_level.lower(),
        "access_log": not args.quiet,
        "reload": args.reload,
        "workers": args.workers if not args.reload else 1,
    }
    
    # Add SSL configuration if provided
    if args.ssl_keyfile and args.ssl_certfile:
        uvicorn_config.update({
            "ssl_keyfile": args.ssl_keyfile,
            "ssl_certfile": args.ssl_certfile
        })
    
    try:
        # Start server
        uvicorn.run(**uvicorn_config)
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        logger.error(f"❌ Failed to start server: {e}")
        sys.exit(1)


async def run_installation_test() -> bool:
    """
    Run comprehensive installation test.
    
    Returns:
        True if all tests pass, False otherwise
    """
    try:
        # Import and run the test module
        import test_installation
        success = await test_installation.main()
        return success
    except Exception as e:
        print(f"❌ Installation test failed: {e}")
        return False


def run_health_check() -> None:
    """Run system health check and display status."""
    print("💊 Running System Health Check...")
    print("=" * 50)
    
    # Check Python version
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    print(f"🐍 Python Version: {python_version}")
    
    if sys.version_info < (3, 8):
        print("⚠️  Warning: Python 3.8+ recommended")
    else:
        print("✅ Python version OK")
    
    # Check dependencies
    print("\n📦 Checking Dependencies...")
    required_modules = [
        'requests', 'aiohttp', 'beautifulsoup4', 'fastapi', 
        'uvicorn', 'pydantic', 'tenacity'
    ]
    
    missing_modules = []
    for module in required_modules:
        try:
            __import__(module)
            print(f"✅ {module}")
        except ImportError:
            print(f"❌ {module} (missing)")
            missing_modules.append(module)
    
    # Check optional dependencies
    print("\n🔧 Optional Dependencies...")
    optional_modules = ['playwright', 'openai', 'transformers', 'pdfplumber']
    
    for module in optional_modules:
        try:
            __import__(module)
            print(f"✅ {module}")
        except ImportError:
            print(f"⚠️  {module} (optional)")
    
    # System resources
    print(f"\n💻 System Info...")
    try:
        import psutil
        cpu_count = psutil.cpu_count()
        memory_gb = psutil.virtual_memory().total / (1024**3)
        print(f"✅ CPU Cores: {cpu_count}")
        print(f"✅ RAM: {memory_gb:.1f} GB")
    except ImportError:
        print("⚠️  psutil not available for system monitoring")
    
    # Configuration
    print(f"\n⚙️  Configuration...")
    try:
        from utils import load_config
        config = load_config()
        print("✅ Configuration system working")
    except Exception as e:
        print(f"❌ Configuration error: {e}")
    
    # Summary
    print("\n" + "=" * 50)
    if missing_modules:
        print(f"❌ Health Check: {len(missing_modules)} missing dependencies")
        print(f"💡 Install with: pip install {' '.join(missing_modules)}")
    else:
        print("✅ Health Check: All systems operational")


def main() -> None:
    """
    Main entry point with comprehensive command handling.
    
    Provides:
    - Command line argument parsing
    - Configuration management
    - API server startup
    - CLI scraping operations
    - System testing and health checks
    """
    # Parse command line arguments
    parser = create_arg_parser()
    args = parser.parse_args()
    
    # Handle special commands first
    if args.test_installation:
        print("🧪 Running installation tests...")
        try:
            success = asyncio.run(run_installation_test())
            sys.exit(0 if success else 1)
        except Exception as e:
            print(f"❌ Test execution failed: {e}")
            sys.exit(1)
    
    if args.health_check:
        run_health_check()
        return
    
    if args.benchmark:
        print("📊 Benchmark feature not yet implemented")
        return
    
    # Handle configuration operations
    if args.create_config:
        from utils.config import create_sample_config_file
        try:
            create_sample_config_file(args.create_config)
            print(f"✅ Sample configuration created: {args.create_config}")
            print("💡 Edit the file to customize settings, then run with --config")
            print(f"🚀 Start API: python {sys.argv[0]} --config {args.create_config} --api")
            return
        except Exception as e:
            print(f"❌ Failed to create config file: {e}")
            sys.exit(1)
    
    if args.validate_config:
        try:
            from utils.config import load_config
            config = load_config(args.validate_config)
            warnings = config.validate() if hasattr(config, 'validate') else []
            if warnings:
                print(f"⚠️  Configuration warnings:")
                for warning in warnings:
                    print(f"  - {warning}")
            else:
                print("✅ Configuration is valid")
            return
        except Exception as e:
            print(f"❌ Configuration validation failed: {e}")
            sys.exit(1)
    
    if args.show_config:
        try:
            from utils.config import load_config
            config = load_config(args.config)
            print("📄 Current Configuration:")
            print(config)  # This will use the config's __str__ method
            return
        except Exception as e:
            print(f"❌ Failed to load configuration: {e}")
            sys.exit(1)
    
    # Load configuration
    try:
        config = load_config(args.config)
    except Exception as e:
        print(f"✗ Failed to load configuration: {e}")
        sys.exit(1)
    
    # Override config with command line arguments
    if args.host:
        config.api.host = args.host
    if args.port:
        config.api.port = args.port
    if args.workers:
        config.api.workers = args.workers
    if args.log_level:
        config.logging.level = args.log_level
    if args.log_file:
        config.logging.log_file = args.log_file
        config.logging.file_output = True
    if args.quiet:
        config.logging.console_output = False
    
    # Setup logging
    setup_logging(
        level=config.logging.level,
        log_file=config.logging.log_file if config.logging.file_output else None,
        console_output=config.logging.console_output,
        structured=config.logging.structured_logging
    )
    
    # Determine mode of operation
    if args.api:
        # Start API server
        start_api_server(args, config)
        
    elif args.url or args.batch:
        # CLI scraping mode
        asyncio.run(cli_scrape(args, config))
        
    else:
        # Show help if no action specified
        parser.print_help()
        print("\n💡 Quick start:")
        print("  python main.py --api                          # Start API server")
        print("  python main.py --url https://example.com      # Scrape a URL")
        print("  python main.py --create-config config.yaml    # Create sample config")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        sys.exit(1)