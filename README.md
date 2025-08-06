# 🚀 Advanced Web Scraping Framework

A comprehensive, production-ready web scraping framework with advanced field extraction, formatting preservation, proxy management, and AI enhancement capabilities.

## ✨ Features

### 🔍 **Multi-Format Content Extraction**
- **HTML Pages**: Static content with BeautifulSoup
- **JavaScript-Rendered Pages**: Dynamic content with Playwright
- **PDF Documents**: Text, tables, images, and metadata extraction
- **Auto-Detection**: Automatically chooses the best crawler for each URL

### 🎯 **Advanced Field Extraction**
- **Regex-Based Patterns**: 25+ built-in patterns for common data types
- **Custom Patterns**: Define your own extraction rules
- **Multiple Values**: Extract lists of matching items
- **Confidence Scoring**: Quality assessment for extracted data
- **Alternative Matches**: Backup options for uncertain extractions

### 🎨 **Formatting Preservation**
- **Subscripts/Superscripts**: Chemical formulas, math expressions
- **Special Characters**: Unicode symbols, Greek letters, math operators
- **Multiple Formats**: HTML, Unicode, LaTeX, Markdown output
- **Scientific Notation**: Proper handling of scientific data

### 🔄 **Smart Proxy Management**
- **Automatic Rotation**: Round-robin, random, or least-used strategies
- **Health Monitoring**: Continuous proxy validation and recovery
- **Headers Spoofing**: Realistic browser headers and user agents
- **Failure Handling**: Automatic proxy switching on errors

### 🤖 **AI Enhancement**
- **Content Validation**: AI-powered accuracy improvement
- **Natural Language Generation**: Convert data to readable sentences
- **Context Understanding**: Smarter field extraction with AI assistance
- **Multiple Models**: OpenAI GPT or local transformer models

### 🌐 **Production-Ready API**
- **RESTful Endpoints**: FastAPI-based with automatic documentation
- **Async Processing**: Background job queue for long-running tasks
- **Batch Operations**: Process multiple URLs efficiently
- **Rate Limiting**: Built-in protection and throttling
- **Schema Validation**: Pydantic models for data integrity

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd web_scraping

# Install dependencies
pip install -r requirements.txt

# Install browser for JavaScript rendering (optional)
playwright install chromium
```

### Basic Usage

#### 1. Start the API Server
```bash
python main.py --api
```

The API will be available at `http://localhost:8000` with interactive documentation at `/docs`.

#### 2. Simple URL Scraping
```bash
# Scrape with default fields
python main.py --url "https://example.com"

# Extract specific fields
python main.py --url "https://example.com" --fields "email,phone,chemical_formula"

# Use custom patterns
python main.py --url "https://example.com" --fields "price:\\$\\d+\\.\\d{2},date:date_iso"
```

#### 3. Batch Processing
```bash
# Create a file with URLs (one per line)
echo "https://example1.com" > urls.txt
echo "https://example2.com" >> urls.txt

# Process batch
python main.py --batch urls.txt --output results.json
```

## 📖 API Usage

### Basic Scraping Request

```python
import requests

response = requests.post("http://localhost:8000/api/v1/scrape", json={
    "url": "https://example.com/chemical-data",
    "fields": {
        "chemical_name": "chemical_formula",
        "concentration": "\\d+% w/v",
        "temperature": "\\d+°[CF]",
        "formula": {
            "pattern": "molecular_formula",
            "preserve_formatting": True,
            "formatting_type": "unicode"
        }
    },
    "output_format": "structured",
    "use_proxy": True,
    "randomize_headers": True
})

result = response.json()
print(result)
```

### Advanced Configuration

```python
{
    "url": "https://scientific-journal.com/article",
    "fields": {
        "title": "h1",
        "authors": {
            "pattern": "@[\\w\\s]+",
            "multiple": True,
            "unique": True
        },
        "doi": "doi",
        "chemical_formulas": {
            "pattern": "molecular_formula",
            "multiple": True,
            "preserve_formatting": True,
            "include_alternatives": True
        },
        "temperatures": {
            "pattern": "temperature",
            "multiple": True,
            "transform": ["normalize_whitespace", "extract:\\d+"]
        }
    },
    "crawler_type": "js",
    "headless": True,
    "wait_for_selector": ".article-content",
    "use_ai_enhancement": True,
    "schema_name": "scientific_publication"
}
```

## 🎯 Built-in Patterns

The framework includes 25+ pre-built extraction patterns:

| Pattern | Description | Example |
|---------|-------------|---------|
| `email` | Email addresses | `user@example.com` |
| `phone` | Phone numbers | `(555) 123-4567` |
| `url` | Web URLs | `https://example.com` |
| `chemical_formula` | Chemical formulas | `H2O`, `CO2` |
| `molecular_formula` | With subscripts | `H₂SO₄`, `C₆H₁₂O₆` |
| `temperature` | Temperature values | `25°C`, `98.6°F` |
| `price` | Currency amounts | `$19.99`, `€1,234.56` |
| `percentage` | Percentages | `75%`, `99.9%` |
| `date_iso` | ISO dates | `2024-01-15` |
| `date_us` | US dates | `01/15/2024` |
| `time` | Time values | `14:30`, `2:30 PM` |
| `doi` | Academic DOIs | `10.1000/182` |
| `isbn` | Book ISBNs | `978-0-123456-78-9` |
| `coordinate` | GPS coordinates | `40.7128,-74.0060` |
| `ip_address` | IP addresses | `192.168.1.1` |
| `hashtag` | Social hashtags | `#webScraping` |
| `mention` | Social mentions | `@username` |
| `hex_color` | Color codes | `#FF0000` |

## 🔧 Configuration

### YAML Configuration File

```yaml
# config.yaml
crawler:
  max_retries: 3
  delay: 1.0
  timeout: 30
  headless: true
  browser_type: "chromium"

proxy:
  enabled: true
  proxy_sources:
    - "http://proxy1.example.com:8080"
    - "http://proxy2.example.com:8080"
  rotation_strategy: "round_robin"
  max_failures: 3

extraction:
  preserve_formatting: true
  default_formatting_type: "unicode"
  include_confidence_scores: true
  include_alternatives: false

ai:
  enabled: false
  openai_api_key: "your-api-key"
  model: "gpt-3.5-turbo"
  max_tokens: 1000

api:
  host: "0.0.0.0"
  port: 8000
  max_concurrent_jobs: 10
  enable_cors: true

logging:
  level: "INFO"
  console_output: true
  file_output: true
  log_file: "scraper.log"
```

### Environment Variables

```bash
# Crawler settings
export SCRAPER_CRAWLER_MAX_RETRIES=5
export SCRAPER_CRAWLER_DELAY=2.0
export SCRAPER_CRAWLER_HEADLESS=true

# Proxy settings
export SCRAPER_PROXY_ENABLED=true
export SCRAPER_PROXY_ROTATION_STRATEGY=random

# AI settings
export SCRAPER_AI_ENABLED=true
export SCRAPER_OPENAI_API_KEY=your-api-key

# API settings
export SCRAPER_API_HOST=0.0.0.0
export SCRAPER_API_PORT=8080

# Logging
export SCRAPER_LOG_LEVEL=DEBUG
export SCRAPER_LOG_FILE=debug.log
```

## 🧪 Examples

### Scientific Data Extraction

```python
# Extract chemical compound data
fields = {
    "compound_name": "h2",
    "molecular_formula": {
        "pattern": "molecular_formula",
        "preserve_formatting": True,
        "formatting_type": "unicode"
    },
    "melting_point": "\\d+°C",
    "boiling_point": "\\d+°C",
    "cas_number": "\\d{2,7}-\\d{2}-\\d",
    "molecular_weight": "\\d+\\.\\d+ g/mol"
}

response = requests.post("http://localhost:8000/api/v1/scrape", json={
    "url": "https://chemical-database.com/compound/123",
    "fields": fields,
    "schema_name": "chemical_compound"
})
```

### E-commerce Product Data

```python
# Extract product information
fields = {
    "title": "h1",
    "price": {
        "pattern": "price",
        "transform": ["extract:\\d+\\.\\d{2}"]
    },
    "description": "meta[name='description']",
    "brand": "chemical_formula",  # If product contains chemicals
    "availability": "in stock|out of stock",
    "rating": "\\d\\.\\d/5|\\d/5"
}

response = requests.post("http://localhost:8000/api/v1/scrape", json={
    "url": "https://shop.example.com/product/123",
    "fields": fields,
    "schema_name": "product_listing"
})
```

### Academic Paper Extraction

```python
# Extract research paper data
fields = {
    "title": "h1",
    "authors": {
        "pattern": "Dr\\. [A-Z][a-z]+ [A-Z][a-z]+|[A-Z][a-z]+ [A-Z]\\. [A-Z][a-z]+",
        "multiple": True
    },
    "abstract": ".abstract",
    "keywords": {
        "pattern": "#\\w+",
        "multiple": True
    },
    "doi": "doi",
    "chemical_formulas": {
        "pattern": "molecular_formula",
        "multiple": True,
        "preserve_formatting": True
    },
    "temperatures": {
        "pattern": "temperature",
        "multiple": True
    }
}
```

### PDF Document Processing

```python
# Extract from PDF files
response = requests.post("http://localhost:8000/api/v1/scrape", json={
    "url": "https://example.com/research-paper.pdf",
    "fields": {
        "title": "^[A-Z][^\\n]+",
        "chemical_formulas": "molecular_formula",
        "temperature_values": "temperature",
        "concentrations": "\\d+(?:\\.\\d+)?\\s*%\\s*w/v"
    },
    "crawler_type": "pdf",
    "extract_tables": True,
    "extract_images": True
})
```

## 🔄 Advanced Features

### Asynchronous Job Processing

```python
# Submit long-running job
job_response = requests.post("http://localhost:8000/api/v1/jobs", json={
    "url": "https://large-dataset.com",
    "fields": {"data": "complex_pattern"},
    "use_ai_enhancement": True
})

job_id = job_response.json()["job_id"]

# Check job status
status = requests.get(f"http://localhost:8000/api/v1/jobs/{job_id}")
print(status.json())
```

### Batch Processing

```python
# Process multiple URLs
batch_request = {
    "requests": [
        {
            "url": "https://site1.com",
            "fields": {"email": "email", "phone": "phone"}
        },
        {
            "url": "https://site2.com", 
            "fields": {"chemical": "molecular_formula"}
        }
    ],
    "parallel": True,
    "max_concurrent": 5
}

response = requests.post("http://localhost:8000/api/v1/batch", json=batch_request)
```

### Custom Schema Validation

```python
# Define custom validation schema
schema_request = {
    "fields": {
        "temperature": {
            "pattern": "temperature",
            "required": True,
            "transform": ["extract:\\d+"]
        },
        "pressure": {
            "pattern": "\\d+\\s*bar",
            "required": False
        }
    },
    "schema": {
        "temperature": {"type": "int", "min": -273, "max": 5000},
        "pressure": {"type": "int", "min": 0, "max": 10000}
    }
}
```

## 🛠️ Development

### Project Structure

```
web_scraping/
├── api/                    # FastAPI application
│   ├── endpoints/         # API route handlers
│   ├── models.py          # Pydantic models
│   ├── main.py           # FastAPI app
│   └── ...
├── crawler/               # Web crawling modules
│   ├── html_crawler.py   # Static HTML crawler
│   ├── js_crawler.py     # JavaScript crawler
│   ├── pdf_crawler.py    # PDF processor
│   └── ...
├── extractor/             # Field extraction
│   ├── field_extractor.py
│   ├── pattern_matcher.py
│   ├── formatter.py
│   └── ...
├── proxy/                 # Proxy management
│   ├── proxy_manager.py
│   ├── proxy_validator.py
│   └── ...
├── utils/                 # Utilities
│   ├── logging_config.py
│   ├── retry_utils.py
│   ├── config.py
│   └── ...
├── main.py               # Entry point
├── requirements.txt      # Dependencies
└── README.md            # Documentation
```

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run tests
pytest tests/

# Run with coverage
pytest --cov=. tests/
```

### API Documentation

Once the server is running, visit:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI JSON**: `http://localhost:8000/openapi.json`

## 🚀 Deployment

### Docker

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

# Install Playwright browsers
RUN playwright install chromium

COPY . .

EXPOSE 8000
CMD ["python", "main.py", "--api", "--host", "0.0.0.0"]
```

### Production Configuration

```yaml
# production.yaml
api:
  host: "0.0.0.0"
  port: 8000
  workers: 4

logging:
  level: "WARNING"
  file_output: true
  log_file: "/var/log/scraper.log"

proxy:
  enabled: true
  proxy_sources:
    - "http://premium-proxy-service.com/api/proxies"
```

## 🔒 Security Considerations

- **Rate Limiting**: Implement proper rate limiting for production
- **Input Validation**: All inputs are validated with Pydantic
- **Proxy Security**: Use trusted proxy services
- **API Keys**: Store OpenAI keys securely
- **CORS**: Configure CORS appropriately for your domain

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

- **Documentation**: Check `/docs` endpoint when API is running
- **Issues**: Report bugs via GitHub issues
- **Examples**: See the `examples/` directory for more use cases

## 🎯 Use Cases

This framework is perfect for:

- **Scientific Data Extraction**: Research papers, chemical databases
- **E-commerce Monitoring**: Product prices, availability, reviews
- **Financial Data**: Stock prices, company information
- **Academic Research**: Citation extraction, author networks
- **Content Aggregation**: News articles, blog posts
- **Lead Generation**: Contact information, company data
- **SEO Analysis**: Meta tags, content structure
- **Competitive Intelligence**: Feature comparison, pricing

## 🔮 Roadmap

- [ ] **Enhanced AI Models**: GPT-4, Claude integration
- [ ] **Real-time Monitoring**: Webhook notifications for changes
- [ ] **Database Integration**: Direct storage to SQL/NoSQL databases
- [ ] **Caching Layer**: Redis/Memcached for performance
- [ ] **Monitoring Dashboard**: Real-time scraping statistics
- [ ] **Plugin System**: Custom extractors and processors
- [ ] **OCR Integration**: Image text extraction
- [ ] **Data Pipeline**: Integration with Apache Airflow

---

**Happy Scraping! 🕷️✨**