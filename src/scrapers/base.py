"""
Base scraper class and common utilities for all company scrapers.
"""

import logging
from typing import List, Dict, Optional
from abc import ABC, abstractmethod
from playwright.async_api import Page

logger = logging.getLogger("MatchPulse")


class BaseScraper(ABC):
    """
    Abstract base class for company job scrapers.
    
    Each company scraper should inherit from this class and implement:
    - scrape_listings(): Scrape job listings from search page
    - scrape_details(): Scrape full job description from detail page
    """
    
    def __init__(self, company_name: str):
        """
        Initialize scraper.
        
        Args:
            company_name: Display name of the company (e.g., "Google", "Amazon")
        """
        self.company_name = company_name
        self.company_id = company_name.lower()
    
    @abstractmethod
    async def scrape_listings(self, page: Page, url: str) -> List[Dict]:
        """
        Scrape job listings from company career page.
        
        Args:
            page: Playwright page object
            url: Pre-filtered career page URL
        
        Returns:
            List of job dictionaries with fields:
            - company: str
            - job_id: str (format: "{company}_{id}")
            - job_url: str
            - title: str
            - location: Optional[str]
            - description: Optional[str] (if available on listing page)
            - salary: Optional[str]
            - posted_date: Optional[str]
        """
        pass
    
    @abstractmethod
    async def scrape_details(self, page: Page, job_url: str) -> Optional[str]:
        """
        Scrape full job description from job detail page.
        
        Args:
            page: Playwright page object
            job_url: URL of job detail page
        
        Returns:
            Full job description text, or None if failed
        """
        pass
    
    def create_job_dict(self, job_id: str, job_url: str, title: str,
                       location: Optional[str] = None,
                       description: Optional[str] = None,
                       salary: Optional[str] = None,
                       posted_date: Optional[str] = None) -> Dict:
        """
        Create standardized job dictionary.
        
        Args:
            job_id: Unique job identifier (without company prefix)
            job_url: Full URL to job posting
            title: Job title
            location: Job location (optional)
            description: Job description (optional)
            salary: Salary range (optional)
            posted_date: Posted date (optional)
        
        Returns:
            Standardized job dictionary
        """
        return {
            'company': self.company_name,
            'job_id': f"{self.company_id}_{job_id}",
            'job_url': job_url,
            'title': title.strip() if title else None,
            'location': location.strip() if location else None,
            'description': description.strip() if description else None,
            'salary': salary.strip() if salary else None,
            'posted_date': posted_date.strip() if posted_date else None
        }


async def safe_get_text(element, default: str = "") -> str:
    """
    Safely extract text from Playwright element.
    
    Args:
        element: Playwright element locator
        default: Default value if extraction fails
    
    Returns:
        Extracted text or default value
    """
    try:
        if element:
            text = await element.inner_text()
            return text.strip() if text else default
        return default
    except Exception:
        return default


async def safe_get_attribute(element, attribute: str, default: str = "") -> str:
    """
    Safely extract attribute from Playwright element.
    
    Args:
        element: Playwright element locator
        attribute: Attribute name (e.g., 'href', 'data-id')
        default: Default value if extraction fails
    
    Returns:
        Attribute value or default value
    """
    try:
        if element:
            value = await element.get_attribute(attribute)
            return value.strip() if value else default
        return default
    except Exception:
        return default
