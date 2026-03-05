"""Amazon careers scraper."""

import asyncio
import logging
import re
from typing import List, Dict, Optional
from playwright.async_api import Page
from .base import BaseScraper, safe_get_text, safe_get_attribute

logger = logging.getLogger("MatchPulse")


class AmazonScraper(BaseScraper):
    """Scraper for Amazon careers page."""
    
    def __init__(self):
        super().__init__("Amazon")
    
    async def scrape_listings(self, page: Page, url: str) -> List[Dict]:
        """Scrape job listings from Amazon careers page."""
        jobs = []
        
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_selector('a[href*="/en/jobs/"]', timeout=20000)
            
            job_links = await page.query_selector_all('a[href*="/en/jobs/"]')
            
            # Filter to only job posting links
            filtered_links = []
            for link in job_links:
                href = await safe_get_attribute(link, 'href')
                text = await safe_get_text(link)
                if href and '/jobs/' in href and len(text) > 10 and '...' not in text:
                    filtered_links.append(link)
            
            logger.info(f"Found {len(filtered_links)} Amazon jobs")
            
            for i, link in enumerate(filtered_links):
                try:
                    title_text = await safe_get_text(link)
                    href = await safe_get_attribute(link, 'href')
                    
                    job_url = None
                    if href:
                        if href.startswith('/en/jobs/'):
                            job_url = f"https://www.amazon.jobs{href}"
                        elif href.startswith('/'):
                            job_url = f"https://www.amazon.jobs{href}"
                        else:
                            job_url = href
                    
                    job_id = str(i)
                    if job_url and '/jobs/' in job_url:
                        match = re.search(r'/jobs/(\d+)', job_url)
                        if match:
                            job_id = match.group(1)
                    
                    job = self.create_job_dict(
                        job_id=job_id,
                        job_url=job_url or f"https://www.amazon.jobs/en/jobs/{i}",
                        title=title_text,
                        description=f"{title_text} at Amazon"
                    )
                    
                    jobs.append(job)
                    
                    if i < len(filtered_links) - 1:
                        await asyncio.sleep(0.5)
                        
                except Exception as e:
                    logger.warning(f"Error extracting Amazon job {i}: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Error scraping Amazon: {e}")
        
        return jobs
    
    async def scrape_details(self, page: Page, job_url: str) -> Optional[str]:
        """Scrape full job description from Amazon job detail page."""
        try:
            await page.goto(job_url, wait_until='networkidle', timeout=30000)
            await page.wait_for_selector('div.job-description', timeout=10000)
            
            desc_elem = await page.query_selector('div.job-description')
            description = await safe_get_text(desc_elem)
            
            return description if description else None
        
        except Exception as e:
            logger.error(f"Error scraping Amazon job details: {e}")
            return None
