"""
Modular job scraper using company-specific scraper classes.

This is the new modular architecture. Each company has its own scraper file in src/scrapers/.
"""

import asyncio
import logging
import random
from typing import List, Dict, Optional
from playwright.async_api import async_playwright

# Handle both direct execution and module import
try:
    from .utils import get_company_links, setup_logging
    from ..scrapers import get_scraper, list_available_scrapers
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
    from src.tools.utils import get_company_links, setup_logging
    from src.scrapers import get_scraper, list_available_scrapers

logger = setup_logging()


async def fetch_jobs(company_links: Optional[Dict[str, str]] = None) -> List[Dict]:
    """
    Scrape jobs from company career pages using modular scrapers.
    
    Args:
        company_links: Dict of {company_name: filtered_url}
                      If None, loads from config.yaml
    
    Returns:
        List of job dictionaries with fields:
        - company, job_id, job_url, title, location, 
          description, salary (optional), posted_date (optional)
    """
    if company_links is None:
        company_links = get_company_links()
    
    all_jobs = []
    available_scrapers = list_available_scrapers()
    
    logger.info(f"Available scrapers: {available_scrapers}")
    
    async with async_playwright() as p:
        # Launch browser with stealth options
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox'
            ]
        )
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        page = await context.new_page()
        
        # Enable stealth mode on the page
        try:
            from playwright_stealth.stealth import Stealth
            stealth_config = Stealth()
            await stealth_config.apply_stealth_async(page)
        except Exception as e:
            logger.warning(f"Could not apply stealth mode: {e}")
        
        for company, url in company_links.items():
            try:
                logger.info(f"Scraping {company}: {url}")
                
                # Get scraper for this company
                try:
                    scraper = get_scraper(company)
                except KeyError:
                    logger.warning(f"No scraper found for company: {company}")
                    continue
                
                # Use the scraper to get jobs
                jobs = await scraper.scrape_listings(page, url)
                
                all_jobs.extend(jobs)
                logger.info(f"Found {len(jobs)} jobs from {company}")
                
                # Rate limiting between companies
                sleep_time = random.uniform(3, 6)
                await asyncio.sleep(sleep_time)
                
            except Exception as e:
                logger.error(f"Error scraping {company}: {e}")
                continue
        
        await browser.close()
    
    logger.info(f"Total jobs scraped: {len(all_jobs)}")
    return all_jobs


async def test_scraper():
    """Test function to run scraper manually."""
    links = get_company_links()
    print(f"Testing modular scraper with {len(links)} companies")
    
    jobs = await fetch_jobs(links)
    
    print(f"\nScraped {len(jobs)} jobs:")
    for i, job in enumerate(jobs[:10]):  # Show first 10
        print(f"{i+1}. {job['company']}: {job['title']}")
        print(f"   URL: {job['job_url']}")
        print()


if __name__ == "__main__":
    asyncio.run(test_scraper())
