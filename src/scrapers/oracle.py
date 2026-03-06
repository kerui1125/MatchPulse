"""Oracle careers scraper."""

import asyncio
import logging
import re
from typing import List, Dict, Optional
from playwright.async_api import Page
from .base import BaseScraper, safe_get_text, safe_get_attribute

logger = logging.getLogger("MatchPulse")


class OracleScraper(BaseScraper):
    """Scraper for Oracle careers page."""
    
    def __init__(self):
        super().__init__("Oracle")
    
    async def scrape_listings(self, page: Page, url: str) -> List[Dict]:
        """Scrape job listings from Oracle careers page."""
        jobs = []
        
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_selector('a[href*="/en/sites/jobsearch/job/"]', timeout=20000)
            
            job_links = await page.query_selector_all('a[href*="/en/sites/jobsearch/job/"]')
            logger.info(f"Found {len(job_links)} Oracle jobs")
            
            for i, link in enumerate(job_links):
                try:
                    title_text = await safe_get_text(link)
                    
                    # If no text in link, try to find title in parent
                    if not title_text or len(title_text.strip()) < 5:
                        parent = await link.evaluate_handle('el => el.parentElement')
                        parent_text = await safe_get_text(parent)
                        if parent_text and len(parent_text) > 10:
                            title_text = parent_text.split('\n')[0]
                        else:
                            continue
                    
                    href = await safe_get_attribute(link, 'href')
                    job_url = None
                    if href:
                        if href.startswith('/en/sites/jobsearch/job/'):
                            job_url = f"https://careers.oracle.com{href}"
                        elif href.startswith('/'):
                            job_url = f"https://careers.oracle.com{href}"
                        else:
                            job_url = href
                    
                    job_id = str(i)
                    if job_url and '/job/' in job_url:
                        match = re.search(r'/job/(\d+)', job_url)
                        if match:
                            job_id = match.group(1)
                    
                    job = self.create_job_dict(
                        job_id=job_id,
                        job_url=job_url or f"https://careers.oracle.com/en/sites/jobsearch/job/{i}",
                        title=title_text.strip(),
                        description=f"{title_text.strip()} at Oracle"
                    )
                    
                    jobs.append(job)
                    
                    if i < len(job_links) - 1:
                        await asyncio.sleep(0.5)
                        
                except Exception as e:
                    logger.warning(f"Error extracting Oracle job {i}: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Error scraping Oracle: {e}")
        
        return jobs
    
    async def scrape_details(self, page: Page, job_url: str) -> Optional[str]:
        """Scrape full job description from Oracle job detail page."""
        try:
            await page.goto(job_url, wait_until='domcontentloaded', timeout=45000)
            await asyncio.sleep(3)
            
            # Try multiple selectors (fallback strategy from old working version)
            desc_selectors = [
                'article',
                'main article',
                'div[class*="job-detail"]',
                'div.job-description'
            ]
            
            description = None
            for selector in desc_selectors:
                try:
                    elem = await page.query_selector(selector)
                    if elem:
                        text = await safe_get_text(elem)
                        if text and len(text.strip()) > 100:
                            description = text.strip()
                            logger.info(f"✓ Oracle description found using {selector} ({len(description)} chars)")
                            break
                except Exception:
                    continue
            
            if not description:
                logger.warning(f"No description found for Oracle job: {job_url}")
            
            return description
        
        except Exception as e:
            logger.error(f"Error scraping Oracle job details: {e}")
            return None
