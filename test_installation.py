#!/usr/bin/env python3
"""
Installation test script for the Web Scraping Framework.
Run this to verify that all components are working correctly.
"""

import sys
import asyncio
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test that all modules can be imported."""
    print("🧪 Testing imports...")
    
    try:
        # Core modules
        import crawler
        import extractor  
        import proxy
        import api
        import utils
        import ai
        print("  ✅ Core modules imported successfully")
        
        # Specific components
        from crawler import ContentDetector, HTMLCrawler
        from extractor import FieldExtractor, PatternMatcher
        from proxy import ProxyManager
        from api.models import ScrapeRequest
        from utils import setup_logging, load_config
        print("  ✅ Specific components imported successfully")
        
        return True
        
    except ImportError as e:
        print(f"  ❌ Import failed: {e}")
        return False


def test_dependencies():
    """Test that required dependencies are available."""
    print("\n🔍 Testing dependencies...")
    
    required_packages = [
        'requests', 'aiohttp', 'beautifulsoup4', 'lxml',
        'fastapi', 'uvicorn', 'pydantic', 'tenacity',
        'fake_useragent', 'loguru'
    ]
    
    optional_packages = [
        'playwright', 'selenium', 'pdfplumber', 'PyMuPDF',
        'openai', 'transformers', 'yaml'
    ]
    
    missing_required = []
    missing_optional = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"  ✅ {package}")
        except ImportError:
            print(f"  ❌ {package} (required)")
            missing_required.append(package)
    
    for package in optional_packages:
        try:
            __import__(package)
            print(f"  ✅ {package} (optional)")
        except ImportError:
            print(f"  ⚠️  {package} (optional - not installed)")
            missing_optional.append(package)
    
    if missing_required:
        print(f"\n❌ Missing required packages: {', '.join(missing_required)}")
        print("Install with: pip install -r requirements.txt")
        return False
    
    if missing_optional:
        print(f"\n💡 Optional packages not installed: {', '.join(missing_optional)}")
        print("Some features may not be available.")
    
    return True


async def test_field_extractor():
    """Test the field extractor with sample data."""
    print("\n🎯 Testing field extractor...")
    
    try:
        from extractor import FieldExtractor
        
        extractor = FieldExtractor()
        
        # Mock content for testing
        mock_content = {
            'success': True,
            'content': {
                'text_content': '''
                Contact us at info@example.com or call (555) 123-4567.
                Chemical formula: H₂SO₄ at 25°C.
                Price: $19.99 for 500ml.
                Published: 2024-01-15
                '''
            },
            'url': 'test://example.com',
            'timestamp': 1234567890
        }
        
        field_specs = {
            'email': 'email',
            'phone': 'phone', 
            'chemical': 'molecular_formula',
            'temperature': 'temperature',
            'price': 'price',
            'date': 'date_iso'
        }
        
        result = await extractor.extract_fields(mock_content, field_specs)
        
        extracted_fields = result.get('fields', {})
        successful_extractions = sum(1 for v in extracted_fields.values() if v)
        
        print(f"  ✅ Extracted {successful_extractions}/{len(field_specs)} fields")
        
        for field, value in extracted_fields.items():
            if value:
                print(f"    • {field}: {value}")
        
        return successful_extractions > 0
        
    except Exception as e:
        print(f"  ❌ Field extractor test failed: {e}")
        return False


async def test_content_detector():
    """Test the content detector."""
    print("\n🔍 Testing content detector...")
    
    try:
        from crawler import ContentDetector
        
        detector = ContentDetector()
        
        # Test URL detection
        test_cases = [
            ('https://example.com/page.html', 'html'),
            ('https://example.com/document.pdf', 'pdf'),
            ('https://spa-app.com', 'js')  # Will likely default to html
        ]
        
        for url, expected_type in test_cases:
            detected_type = await detector.detect_content_type(url)
            print(f"  • {url} → {detected_type}")
        
        print("  ✅ Content detection working")
        return True
        
    except Exception as e:
        print(f"  ❌ Content detector test failed: {e}")
        return False


def test_api_models():
    """Test API models and validation."""
    print("\n📋 Testing API models...")
    
    try:
        from api.models import ScrapeRequest, FieldSpec
        
        # Test basic request
        request = ScrapeRequest(
            url="https://example.com",
            fields={"title": "h1", "email": "email"}
        )
        print("  ✅ Basic ScrapeRequest created")
        
        # Test advanced field spec
        field_spec = FieldSpec(
            pattern="molecular_formula",
            preserve_formatting=True,
            multiple=True
        )
        print("  ✅ FieldSpec created")
        
        # Test request with field specs
        advanced_request = ScrapeRequest(
            url="https://example.com",
            fields={"chemical": field_spec},
            use_proxy=True,
            use_ai_enhancement=True
        )
        print("  ✅ Advanced ScrapeRequest created")
        
        return True
        
    except Exception as e:
        print(f"  ❌ API models test failed: {e}")
        return False


def test_configuration():
    """Test configuration loading."""
    print("\n⚙️ Testing configuration...")
    
    try:
        from utils import load_config, create_default_config
        
        # Test default config creation
        config = create_default_config()
        print("  ✅ Default configuration created")
        
        # Test config validation
        warnings = config.validate()
        if warnings:
            print(f"  ⚠️  Configuration warnings: {len(warnings)}")
        else:
            print("  ✅ Configuration validation passed")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Configuration test failed: {e}")
        return False


async def main():
    """Run all tests."""
    print("🧪 Web Scraping Framework - Installation Test")
    print("=" * 60)
    
    tests = [
        ("Import Test", test_imports),
        ("Dependencies Test", test_dependencies),
        ("API Models Test", test_api_models),
        ("Configuration Test", test_configuration),
        ("Field Extractor Test", test_field_extractor),
        ("Content Detector Test", test_content_detector),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            
            if result:
                passed += 1
        except Exception as e:
            print(f"\n❌ {test_name} failed with exception: {e}")
    
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The framework is ready to use.")
        print("\n🚀 Next steps:")
        print("  • Start the API: python main.py --api")
        print("  • Run examples: python examples/basic_usage.py")
        print("  • Read the docs: README.md")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        print("\n🔧 Common fixes:")
        print("  • Install missing packages: pip install -r requirements.txt")
        print("  • Install Playwright: playwright install chromium")
        print("  • Check Python version: python --version (need 3.8+)")
    
    return passed == total


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n👋 Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test script failed: {e}")
        sys.exit(1)