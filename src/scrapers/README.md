# Company Scrapers

This directory contains standalone scraper test files for each company.

## Purpose

When a company's scraper fails (like Oracle), you can:
1. Run the standalone test file to debug
2. See the browser in action (headless=False)
3. Try different selectors
4. Take screenshots
5. Fix the scraper without affecting other companies

### Easy to Add New Companies
```python
# 1. Create new file: src/scrapers/meta.py
from .base import BaseScraper

class MetaScraper(BaseScraper):
    def __init__(self):
        super().__init__("Meta")
    
    async def scrape_listings(self, page, url):
        # Your scraping logic
        pass
    
    async def scrape_details(self, page, job_url):
        # Your details scraping logic
        pass

# 2. Register in src/scrapers/__init__.py
from .meta import MetaScraper

SCRAPERS = {
    # ... existing scrapers
    'meta': MetaScraper,
}

# 3. Add URL to src/config/config.yaml
links:
  meta: https://www.metacareers.com/jobs?q=software%20engineer
```

## How It Works

### Base Class (`base.py`)
```python
class BaseScraper(ABC):
    @abstractmethod
    async def scrape_listings(self, page, url):
        """Scrape job listings from search page"""
        pass
    
    @abstractmethod
    async def scrape_details(self, page, job_url):
        """Scrape full description from detail page"""
        pass
    
    def create_job_dict(self, job_id, job_url, title, ...):
        """Helper to create standardized job dict"""
        return {...}
```

### Company Scraper (e.g., `google.py`)
```python
class GoogleScraper(BaseScraper):
    def __init__(self):
        super().__init__("Google")
    
    async def scrape_listings(self, page, url):
        # Google-specific scraping logic
        jobs = []
        # ... scraping code ...
        return jobs
    
    async def scrape_details(self, page, job_url):
        # Google-specific details scraping
        description = ...
        return description
```

### Registry (`__init__.py`)
```python
SCRAPERS = {
    'google': GoogleScraper,
    'amazon': AmazonScraper,
    # ... all companies
}

def get_scraper(company):
    return SCRAPERS[company]()
```

### Main Scraper (`scraper.py`)
```python
from src.scrapers import get_scraper

async def fetch_jobs(company_links):
    for company, url in company_links.items():
        scraper = get_scraper(company)  # Get company-specific scraper
        jobs = await scraper.scrape_listings(page, url)
        all_jobs.extend(jobs)
    return all_jobs
```

## Testing

### Test All Companies
```bash
python src/main.py --limit 5 --dry-run
```

### Test Individual Company
```bash
# Edit src/config/config.yaml to only include one company
links:
  google: https://...

# Then run
python src/main.py --limit 5 --dry-run
```

### Test Scraper Module
```bash
python src/tools/scraper.py
```


## Usage

### Test a specific company

```bash
# Test Oracle scraper (currently failing)
python src/scrapers/test_oracle.py

# Test any other company (create similar files)
python src/scrapers/test_amazon.py
python src/scrapers/test_google.py
```

### Create a new company test file

Copy `test_oracle.py` and modify:
1. Change the URL
2. Update the selectors to try
3. Run and debug

### Fix the main scraper

Once you find the working selector in the test file:
1. Update `src/tools/scraper.py` with the new selector
2. Update `src/tools/details_scraper.py` if needed
3. Test the full pipeline: `python src/main.py --limit 5 --dry-run`

## Current Status

| Company    | Status | Test File | Notes |
|------------|--------|-----------|-------|
| Amazon     | ✅ Working | - | - |
| Google     | ✅ Working | - | - |
| Microsoft  | ✅ Working | - | - |
| Nvidia     | ✅ Working | - | - |
| Salesforce | ✅ Working | - | - |
| Expedia    | ✅ Working | - | - |
| Oracle     | ❌ Failing | test_oracle.py | Timeout on selector |

## Future: Full Modular Architecture

Eventually, we can refactor to a fully modular system:

```
src/scrapers/
├── base.py              # Base scraper class
├── __init__.py          # Registry
├── amazon.py            # Amazon scraper class
├── google.py            # Google scraper class
└── ...
```

Benefits:
- Each company is a separate file (100-200 lines)
- Easy to test: `python -m src.scrapers.amazon`
- Easy to add new companies
- Easy to maintain

For now, we use test files for debugging failed scrapers.
