"""
Company scrapers registry.

To add a new company:
1. Create a new file: src/scrapers/{company}.py
2. Implement a class that inherits from BaseScraper
3. Import and register it in SCRAPERS dict below
4. Add company URL to src/config/config.yaml
"""

from .base import BaseScraper

# Import all company scrapers
from .amazon import AmazonScraper
from .google import GoogleScraper
from .microsoft import MicrosoftScraper
from .nvidia import NvidiaScraper
from .salesforce import SalesforceScraper
from .expedia import ExpediaScraper
from .oracle import OracleScraper

# Registry of all available scrapers
# Key: company name (lowercase, matches config.yaml)
# Value: Scraper class
SCRAPERS = {
    'amazon': AmazonScraper,
    'google': GoogleScraper,
    'microsoft': MicrosoftScraper,
    'nvidia': NvidiaScraper,
    'salesforce': SalesforceScraper,
    'expedia': ExpediaScraper,
    'oracle': OracleScraper,
}


def get_scraper(company: str) -> BaseScraper:
    """
    Get scraper instance for a company.
    
    Args:
        company: Company name (lowercase, e.g., 'google', 'amazon')
    
    Returns:
        Scraper instance
    
    Raises:
        KeyError: If company scraper not found
    """
    company_lower = company.lower()
    
    if company_lower not in SCRAPERS:
        raise KeyError(f"No scraper found for company: {company}")
    
    scraper_class = SCRAPERS[company_lower]
    return scraper_class()


def list_available_scrapers() -> list:
    """Get list of all available company scrapers."""
    return list(SCRAPERS.keys())


__all__ = ['BaseScraper', 'get_scraper', 'list_available_scrapers', 'SCRAPERS']
