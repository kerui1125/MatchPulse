"""
Google careers scraper.

Usage:
    from src.scrapers.google import GoogleScraper
    scraper = GoogleScraper()
    jobs = await scraper.scrape_listings(page, url)
    description = await scraper.scrape_details(page, job_url)
"""

import asyncio
import logging
import re
from typing import List, Dict, Optional
from playwright.async_api import Page
from .base import BaseScraper, safe_get_text, safe_get_attribute

logger = logging.getLogger("MatchPulse")


class GoogleScraper(BaseScraper):
    """Scraper for Google careers page."""
    
    def __init__(self):
        super().__init__("Google")
    
    async def scrape_listings(self, page: Page, url: str) -> List[Dict]:
        """
        Scrape job listings from Google careers page.
        
        Strategy:
        1. Find job cards using h3.QJPWVe (title)
        2. Go up 3 levels to find link
        """
        jobs = []
        
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
            await page.wait_for_selector('h3.QJPWVe', timeout=10000)
            
            titles = await page.query_selector_all('h3.QJPWVe')
            logger.info(f"Found {len(titles)} Google jobs")
            
            for i, title in enumerate(titles):
                try:
                    title_text = await safe_get_text(title)
                    
                    # Go up 3 levels to find the link
                    level3 = await title.evaluate_handle('el => el.parentElement.parentElement.parentElement')
                    link_elem = await level3.query_selector('a.WpHeLc')
                    
                    job_url = None
                    if link_elem:
                        href = await safe_get_attribute(link_elem, 'href')
                        if href:
                            if href.startswith('jobs/'):
                                job_url = f"https://www.google.com/about/careers/applications/{href}"
                            elif href.startswith('/'):
                                job_url = f"https://www.google.com{href}"
                            else:
                                job_url = href
                    
                    # Extract job_id from URL
                    job_id = str(i)
                    if job_url and 'results/' in job_url:
                        match = re.search(r'results/(\d+)', job_url)
                        if match:
                            job_id = match.group(1)
                    
                    job = self.create_job_dict(
                        job_id=job_id,
                        job_url=job_url or f"https://www.google.com/about/careers/applications/jobs/{i}",
                        title=title_text,
                        description=f"{title_text} at Google"
                    )
                    
                    jobs.append(job)
                    
                    if i < len(titles) - 1:
                        await asyncio.sleep(0.5)
                        
                except Exception as e:
                    logger.warning(f"Error extracting Google job {i}: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Error scraping Google: {e}")
        
        return jobs
    
    async def scrape_details(self, page: Page, job_url: str) -> Optional[str]:
        """Scrape full job description from Google job detail page."""
        try:
            await page.goto(job_url, wait_until='networkidle', timeout=30000)
            await page.wait_for_selector('div.KwJkGe', timeout=10000)
            
            desc_elem = await page.query_selector('div.KwJkGe')
            description = await safe_get_text(desc_elem)
            
            return description if description else None
        
        except Exception as e:
            logger.error(f"Error scraping Google job details: {e}")
            return None


# For standalone testing
async def test():
    """Test Google scraper standalone."""
    from playwright.async_api import async_playwright
    
    url = "https://www.google.com/about/careers/applications/jobs/results/?q=Software+Engineer&location=Kirkland%2C+WA%2C+USA&hl=en"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        scraper = GoogleScraper()
        jobs = await scraper.scrape_listings(page, url)
        
        print(f"\nFound {len(jobs)} jobs:")
        for job in jobs[:5]:
            print(f"- {job['title']}")
            print(f"  URL: {job['job_url']}")
        
        await browser.close()


if __name__ == "__main__":
    asyncio.run(test())
