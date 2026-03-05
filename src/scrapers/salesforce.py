"""Salesforce careers scraper."""

import asyncio
import logging
import re
from typing import List, Dict, Optional
from playwright.async_api import Page
from .base import BaseScraper, safe_get_text, safe_get_attribute

logger = logging.getLogger("MatchPulse")


class SalesforceScraper(BaseScraper):
    """Scraper for Salesforce careers page."""
    
    def __init__(self):
        super().__init__("Salesforce")
    
    async def scrape_listings(self, page: Page, url: str) -> List[Dict]:
        """Scrape job listings from Salesforce careers page."""
        jobs = []
        
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
            await page.wait_for_selector('a[href*="/en/jobs/jr"]', timeout=10000)
            
            job_links = await page.query_selector_all('a[href*="/en/jobs/jr"]')
            logger.info(f"Found {len(job_links)} Salesforce jobs")
            
            for i, link in enumerate(job_links):
                try:
                    title_text = await safe_get_text(link)
                    
                    # Skip if title is too short or looks like navigation
                    if len(title_text) < 5 or title_text.isdigit():
                        continue
                    
                    href = await safe_get_attribute(link, 'href')
                    job_url = None
                    if href:
                        if href.startswith('/en/jobs/'):
                            job_url = f"https://careers.salesforce.com{href}"
                        elif href.startswith('/'):
                            job_url = f"https://careers.salesforce.com{href}"
                        else:
                            job_url = href
                    
                    job_id = str(i)
                    if job_url and '/jobs/jr' in job_url:
                        match = re.search(r'/jobs/jr(\d+)', job_url)
                        if match:
                            job_id = match.group(1)
                    
                    job = self.create_job_dict(
                        job_id=job_id,
                        job_url=job_url or f"https://careers.salesforce.com/en/jobs/jr{i}",
                        title=title_text,
                        description=f"{title_text} at Salesforce"
                    )
                    
                    jobs.append(job)
                    
                    if i < len(job_links) - 1:
                        await asyncio.sleep(0.5)
                        
                except Exception as e:
                    logger.warning(f"Error extracting Salesforce job {i}: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Error scraping Salesforce: {e}")
        
        return jobs
    
    async def scrape_details(self, page: Page, job_url: str) -> Optional[str]:
        """Scrape full job description from Salesforce job detail page."""
        try:
            await page.goto(job_url, wait_until='networkidle', timeout=30000)
            await page.wait_for_selector('div.job-description', timeout=10000)
            
            desc_elem = await page.query_selector('div.job-description')
            description = await safe_get_text(desc_elem)
            
            return description if description else None
        
        except Exception as e:
            logger.error(f"Error scraping Salesforce job details: {e}")
            return None
