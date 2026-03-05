"""NVIDIA careers scraper."""

import asyncio
import logging
import re
from typing import List, Dict, Optional
from playwright.async_api import Page
from .base import BaseScraper, safe_get_text

logger = logging.getLogger("MatchPulse")


class NvidiaScraper(BaseScraper):
    """Scraper for NVIDIA careers page (Greenhouse platform)."""
    
    def __init__(self):
        super().__init__("Nvidia")
    
    async def scrape_listings(self, page: Page, url: str) -> List[Dict]:
        """Scrape job listings from NVIDIA careers page."""
        jobs = []
        
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
            await page.wait_for_selector('div.title-1aNJK', timeout=10000)
            
            title_elements = await page.query_selector_all('div.title-1aNJK')
            logger.info(f"Found {len(title_elements)} NVIDIA jobs")
            
            for i, title_elem in enumerate(title_elements):
                try:
                    title_text = await safe_get_text(title_elem)
                    
                    # Find parent <a> tag
                    parent_link_href = await title_elem.evaluate('''
                        el => {
                            let current = el;
                            while (current && current.tagName !== 'A') {
                                current = current.parentElement;
                                if (!current) return null;
                            }
                            return current ? current.getAttribute('href') : null;
                        }
                    ''')
                    
                    job_url = None
                    if parent_link_href:
                        if parent_link_href.startswith('/careers/job/'):
                            job_url = f"https://jobs.nvidia.com{parent_link_href}"
                        elif parent_link_href.startswith('/'):
                            job_url = f"https://jobs.nvidia.com{parent_link_href}"
                        elif not parent_link_href.startswith('http'):
                            job_url = f"https://jobs.nvidia.com{parent_link_href}"
                        else:
                            job_url = parent_link_href
                    
                    job_id = str(i)
                    if job_url and '/job/' in job_url:
                        match = re.search(r'/job/(\d+)', job_url)
                        if match:
                            job_id = match.group(1)
                    
                    job = self.create_job_dict(
                        job_id=job_id,
                        job_url=job_url or f"https://jobs.nvidia.com/careers/job/{i}",
                        title=title_text,
                        description=f"{title_text} at NVIDIA"
                    )
                    
                    jobs.append(job)
                    
                    if i < len(title_elements) - 1:
                        await asyncio.sleep(0.5)
                        
                except Exception as e:
                    logger.warning(f"Error extracting NVIDIA job {i}: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Error scraping NVIDIA: {e}")
        
        return jobs
    
    async def scrape_details(self, page: Page, job_url: str) -> Optional[str]:
        """Scrape full job description from NVIDIA job detail page."""
        try:
            await page.goto(job_url, wait_until='networkidle', timeout=30000)
            await page.wait_for_selector('div#content', timeout=10000)
            
            desc_elem = await page.query_selector('div#content')
            description = await safe_get_text(desc_elem)
            
            return description if description else None
        
        except Exception as e:
            logger.error(f"Error scraping NVIDIA job details: {e}")
            return None
