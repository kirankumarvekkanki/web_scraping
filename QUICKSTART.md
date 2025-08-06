# 🚀 Quick Start Guide

Get up and running with the Web Scraping Framework in minutes!

## 📋 Prerequisites

- Python 3.8 or higher
- Git (for cloning the repository)

## ⚡ 5-Minute Setup

### 1. Clone and Install

```bash
# Clone the repository
git clone <repository-url>
cd web_scraping

# Install dependencies
pip install -r requirements.txt

# Optional: Install browser for JavaScript pages
playwright install chromium
```

### 2. Test the Installation

```bash
# Test with a simple scrape
python main.py --url "https://httpbin.org/html" --fields "title"
```

Expected output:
```
✓ Success - 1 fields extracted
title: Herman Melville - Moby-Dick
```

### 3. Start the API Server

```bash
python main.py --api
```

Visit `http://localhost:8000/docs` to see the interactive API documentation.

## 🎯 Common Use Cases

### Extract Contact Information

```bash
python main.py --url "https://example.com/contact" --fields "email,phone"
```

### Extract Chemical Data

```bash
python main.py --url "https://chemical-site.com" --fields "chemical_formula,temperature,concentration"
```

### Extract Product Information

```bash
python main.py --url "https://shop.com/product/123" --fields "price,title,description"
```

### Batch Processing

```bash
# Create a file with URLs
echo "https://site1.com" > urls.txt
echo "https://site2.com" >> urls.txt

# Process all URLs
python main.py --batch urls.txt --output results.json
```

## 🔧 API Usage

### Simple Request

```python
import requests

response = requests.post("http://localhost:8000/api/v1/scrape", json={
    "url": "https://example.com",
    "fields": {
        "title": "h1",
        "emails": "email",
        "prices": "price"
    }
})

print(response.json())
```

### Advanced Request with Chemical Data

```python
response = requests.post("http://localhost:8000/api/v1/scrape", json={
    "url": "https://chemical-database.com/compound/123",
    "fields": {
        "chemical_name": "h2",
        "molecular_formula": {
            "pattern": "molecular_formula",
            "preserve_formatting": True,
            "formatting_type": "unicode"
        },
        "melting_point": "\\d+°C",
        "molecular_weight": "\\d+\\.\\d+ g/mol"
    },
    "use_proxy": False,
    "output_format": "structured"
})

result = response.json()
print(f"Chemical: {result['fields']['chemical_name']}")
print(f"Formula: {result['fields']['molecular_formula']}")
```

## 📝 Built-in Patterns

Use these pattern names in your field specifications:

| Pattern | Matches | Example |
|---------|---------|---------|
| `email` | Email addresses | `user@example.com` |
| `phone` | Phone numbers | `(555) 123-4567` |
| `url` | Web URLs | `https://example.com` |
| `chemical_formula` | Chemical formulas | `H2O`, `CO2` |
| `molecular_formula` | Formulas with subscripts | `H₂SO₄` |
| `temperature` | Temperature values | `25°C`, `98.6°F` |
| `price` | Prices | `$19.99`, `€1,234.56` |
| `percentage` | Percentages | `75%`, `99.9%` |
| `date_iso` | ISO dates | `2024-01-15` |
| `time` | Time values | `14:30`, `2:30 PM` |

## 🔄 Configuration

### Environment Variables

```bash
# Basic settings
export SCRAPER_LOG_LEVEL=DEBUG
export SCRAPER_API_PORT=8080

# Enable AI features
export SCRAPER_AI_ENABLED=true
export SCRAPER_OPENAI_API_KEY=your-api-key

# Enable proxy rotation
export SCRAPER_PROXY_ENABLED=true
```

### Configuration File

Create `config.yaml`:

```yaml
api:
  port: 8080
  host: "0.0.0.0"

logging:
  level: "DEBUG"
  file_output: true
  log_file: "scraper.log"

ai:
  enabled: true
  openai_api_key: "your-api-key"

proxy:
  enabled: false
```

Run with config:
```bash
python main.py --config config.yaml --api
```

## 🛠️ Troubleshooting

### Common Issues

#### "playwright not found"
```bash
pip install playwright
playwright install chromium
```

#### "Permission denied" on port 8000
```bash
python main.py --api --port 8080
```

#### "No matches found"
- Check if the pattern is correct
- Try a simpler pattern first
- Use the pattern tester: `http://localhost:8000/docs` → `/test-pattern`

### Getting Help

1. **API Documentation**: Visit `/docs` when server is running
2. **Examples**: Check the `examples/` directory
3. **Logs**: Enable debug logging to see what's happening
4. **Test Patterns**: Use the API's `/test-pattern` endpoint

## 🎉 Next Steps

1. **Explore the API**: Visit `http://localhost:8000/docs`
2. **Try Examples**: Run `python examples/basic_usage.py`
3. **Custom Patterns**: Create your own regex patterns
4. **Production Setup**: Configure logging and monitoring
5. **AI Features**: Set up OpenAI integration for enhanced extraction

## 📚 Learn More

- **Full Documentation**: See `README.md`
- **API Reference**: `/docs` endpoint
- **Configuration Guide**: `config.yaml` example
- **Examples**: `examples/` directory

Happy scraping! 🕷️✨