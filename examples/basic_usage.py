#!/usr/bin/env python3
"""
Basic usage examples for the Web Scraping Framework.
"""

import asyncio
import json
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.scraping_service import ScrapingService
from api.models import ScrapeRequest, FieldSpec


async def example_1_basic_html_scraping():
    """Example 1: Basic HTML scraping with built-in patterns."""
    print("🔍 Example 1: Basic HTML Scraping")
    print("=" * 50)
    
    service = ScrapingService()
    await service.initialize()
    
    try:
        request = ScrapeRequest(
            url="https://httpbin.org/html",
            fields={
                "title": "h1",
                "paragraphs": "p",
                "links": "url"
            },
            output_format="structured"
        )
        
        result = await service.scrape(request)
        
        print(f"Success: {result.get('success')}")
        print(f"Fields extracted: {list(result.get('fields', {}).keys())}")
        print(f"Title: {result.get('fields', {}).get('title')}")
        
    finally:
        await service.cleanup()


async def example_2_chemical_formula_extraction():
    """Example 2: Chemical formula extraction with formatting preservation."""
    print("\n🧪 Example 2: Chemical Formula Extraction")
    print("=" * 50)
    
    service = ScrapingService()
    await service.initialize()
    
    try:
        # Sample HTML with chemical formulas
        html_content = """
        <html>
        <body>
        <h1>Chemical Compounds</h1>
        <p>Water (H₂O) is essential for life.</p>
        <p>Sulfuric acid (H₂SO₄) is a strong acid.</p>
        <p>Glucose (C₆H₁₂O₆) is a simple sugar.</p>
        <p>Temperature: 25°C, Pressure: 1 atm</p>
        </body>
        </html>
        """
        
        # For demo purposes, we'll create a mock crawler result
        # In real usage, this would come from actual web crawling
        mock_result = {
            'success': True,
            'content': {'raw_html': html_content, 'text_content': html_content},
            'crawler_type': 'HTMLCrawler',
            'url': 'http://example.com',
            'timestamp': 1234567890
        }
        
        field_specs = {
            "chemical_formulas": {
                "pattern": "molecular_formula",
                "multiple": True,
                "preserve_formatting": True,
                "formatting_type": "unicode"
            },
            "temperature": {
                "pattern": "temperature",
                "preserve_formatting": True
            }
        }
        
        # Extract fields using the field extractor
        extraction_result = await service.field_extractor.extract_fields(
            mock_result, field_specs
        )
        
        print(f"Success: {extraction_result.get('metadata', {}).get('success', True)}")
        print(f"Chemical formulas found: {extraction_result.get('fields', {}).get('chemical_formulas')}")
        print(f"Temperature: {extraction_result.get('fields', {}).get('temperature')}")
        print(f"Formatted versions: {extraction_result.get('formatting_preserved', {})}")
        
    finally:
        await service.cleanup()


async def example_3_pattern_testing():
    """Example 3: Testing custom patterns."""
    print("\n🎯 Example 3: Pattern Testing")
    print("=" * 50)
    
    service = ScrapingService()
    await service.initialize()
    
    try:
        test_text = """
        Contact us at: info@example.com or support@company.org
        Phone: (555) 123-4567 or 555-987-6543
        Chemical: H₂SO₄ at 98% concentration
        Price: $19.99 or €15.50
        Date: 2024-01-15
        """
        
        patterns_to_test = {
            "email": "email",
            "phone": "phone",
            "chemical": "molecular_formula",
            "price": "price",
            "date": "date_iso"
        }
        
        for pattern_name, pattern in patterns_to_test.items():
            result = await service.test_pattern(pattern, test_text)
            print(f"{pattern_name:10}: {result['matches_found']} matches")
            if result['matches']:
                for match in result['matches'][:2]:  # Show first 2 matches
                    print(f"           -> {match['value']} (confidence: {match['confidence']:.2f})")
        
    finally:
        await service.cleanup()


async def example_4_advanced_extraction():
    """Example 4: Advanced extraction with transformations."""
    print("\n⚡ Example 4: Advanced Extraction")
    print("=" * 50)
    
    service = ScrapingService()
    await service.initialize()
    
    try:
        # Create a request with advanced field specifications
        request = ScrapeRequest(
            url="https://httpbin.org/json",
            fields={
                "prices": FieldSpec(
                    pattern="price",
                    multiple=True,
                    transform=["extract:\\d+\\.\\d{2}", "normalize_whitespace"],
                    include_alternatives=True
                ),
                "emails": FieldSpec(
                    pattern="email",
                    multiple=True,
                    unique=True,
                    max_matches=5
                ),
                "temperatures": FieldSpec(
                    pattern="temperature",
                    multiple=True,
                    preserve_formatting=True,
                    context_keywords=["measured", "recorded", "observed"]
                )
            },
            crawler_type="html",
            output_format="structured"
        )
        
        result = await service.scrape(request)
        
        print(f"Success: {result.get('success')}")
        print(f"Available data: {list(result.get('fields', {}).keys())}")
        
        # Show confidence scores if available
        confidence_scores = result.get('confidence_scores', {})
        for field, score in confidence_scores.items():
            print(f"Confidence for {field}: {score:.2f}")
        
    finally:
        await service.cleanup()


def example_5_api_client():
    """Example 5: Using the API client."""
    print("\n🌐 Example 5: API Client Usage")
    print("=" * 50)
    
    import requests
    
    # Note: This assumes the API server is running on localhost:8000
    base_url = "http://localhost:8000/api/v1"
    
    try:
        # Test if API is available
        health_response = requests.get(f"{base_url}/health", timeout=5)
        print(f"API Health: {health_response.json()['status']}")
        
        # Get available patterns
        patterns_response = requests.get(f"{base_url}/patterns", timeout=10)
        patterns = patterns_response.json()
        print(f"Available patterns: {len(patterns)}")
        
        # Example scraping request
        scrape_request = {
            "url": "https://httpbin.org/html",
            "fields": {
                "title": "h1",
                "links": "url"
            },
            "output_format": "structured"
        }
        
        scrape_response = requests.post(
            f"{base_url}/scrape", 
            json=scrape_request,
            timeout=30
        )
        
        if scrape_response.status_code == 200:
            result = scrape_response.json()
            print(f"Scraping success: {result.get('success')}")
            print(f"Fields: {list(result.get('fields', {}).keys())}")
        else:
            print(f"API request failed: {scrape_response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("❌ API server not running. Start it with: python main.py --api")
    except requests.exceptions.Timeout:
        print("⏱️ API request timed out")
    except Exception as e:
        print(f"❌ API request failed: {e}")


async def main():
    """Run all examples."""
    print("🚀 Web Scraping Framework - Examples")
    print("=" * 60)
    
    # Run async examples
    await example_1_basic_html_scraping()
    await example_2_chemical_formula_extraction()
    await example_3_pattern_testing()
    await example_4_advanced_extraction()
    
    # Run API example (sync)
    example_5_api_client()
    
    print("\n✅ All examples completed!")
    print("\n💡 Next steps:")
    print("  1. Start the API server: python main.py --api")
    print("  2. Visit http://localhost:8000/docs for interactive API docs")
    print("  3. Try scraping your own URLs with custom patterns")


if __name__ == "__main__":
    asyncio.run(main())