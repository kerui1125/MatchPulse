"""Microsoft careers scraper."""

import asyncio
import logging
import re
from typing import List, Dict, Optional
from playwright.async_api import Page
from .base import BaseScraper, safe_get_text, safe_get_attribute

logger = logging.getLogger("MatchPulse")


class MicrosoftScraper(BaseScraper):
    """Scraper for Microsoft careers page."""
    
    def __init__(self):
        super().__init__("Microsoft")
    
    async def scrape_listings(self, page: Page, url: str) -> List[Dict]:
        """Scrape job listings from Microsoft careers page."""
        jobs = []
        
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
            await asyncio.sleep(2)
            
            # Try multiple selectors
            selectors_to_try = [
                'a.r-link.card-F1ebU',
                'a[href*="/careers/job/"]',
                'div[class*="job-card"]',
                'div[class*="job-item"]'
            ]
            
            job_cards = []
            for selector in selectors_to_try:
                cards = await page.query_selector_all(selector)
                if cards:
                    job_cards = cards
                    logger.info(f"Found {len(job_cards)} Microsoft jobs using selector: {selector}")
                    break
            
            if not job_cards:
                all_links = await page.query_selector_all('a')
                for link in all_links:
                    href = await safe_get_attribute(link, 'href')
                    if href and '/careers/job/' in href:
                        job_cards.append(link)
                logger.info(f"Found {len(job_cards)} Microsoft jobs via href search")
            
            for i, card in enumerate(job_cards):
                try:
                    title_text = "N/A"
                    title_elem = await card.query_selector('div.title-1aNJK')
                    if title_elem:
                        title_text = await safe_get_text(title_elem)
                    else:
                        card_text = await safe_get_text(card)
                        if card_text and len(card_text) > 10:
                            title_text = card_text.split('\n')[0]
                    
                    href = await safe_get_attribute(card, 'href')
                    job_url = None
                    if href:
                        if href.startswith('/careers/job/'):
                            job_url = f"https://apply.careers.microsoft.com{href}"
                        elif href.startswith('/'):
                            job_url = f"https://apply.careers.microsoft.com{href}"
                        else:
                            job_url = href
                    
                    if title_text == "N/A" or not job_url:
                        continue
                    
                    job_id = str(i)
                    if job_url and '/job/' in job_url:
                        match = re.search(r'/job/(\d+)', job_url)
                        if match:
                            job_id = match.group(1)
                    
                    job = self.create_job_dict(
                        job_id=job_id,
                        job_url=job_url,
                        title=title_text,
                        description=f"{title_text} at Microsoft"
                    )
                    
                    jobs.append(job)
                    
                    if i < len(job_cards) - 1:
                        await asyncio.sleep(0.5)
                        
                except Exception as e:
                    logger.warning(f"Error extracting Microsoft job {i}: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Error scraping Microsoft: {e}")
        
        return jobs
    
    async def scrape_details(self, page: Page, job_url: str) -> Optional[str]:
        """Scrape full job description from Microsoft job detail page."""
        try:
            await page.goto(job_url, wait_until='domcontentloaded', timeout=45000)
            await asyncio.sleep(3)
            
            # Try multiple selectors (fallback strategy from old working version)
            desc_selectors = [
                '#job-description-container',
                'div[data-automation-id*="description"]',
                'div#content'
            ]
            
            description = None
            for selector in desc_selectors:
                try:
                    elem = await page.query_selector(selector)
                    if elem:
                        text = await safe_get_text(elem)
                        if text and len(text.strip()) > 100:
                            description = text.strip()
                            logger.info(f"✓ Microsoft description found using {selector} ({len(description)} chars)")
                            break
                except Exception:
                    continue
            
            if not description:
                logger.warning(f"No description found for Microsoft job: {job_url}")
            
            return description
        
        except Exception as e:
            logger.error(f"Error scraping Microsoft job details: {e}")
            return None
