"""Expedia careers scraper."""

import asyncio
import logging
import re
from typing import List, Dict, Optional
from playwright.async_api import Page
from .base import BaseScraper, safe_get_text, safe_get_attribute

logger = logging.getLogger("MatchPulse")


class ExpediaScraper(BaseScraper):
    """Scraper for Expedia careers page (Workday platform)."""
    
    def __init__(self):
        super().__init__("Expedia")
    
    async def scrape_listings(self, page: Page, url: str) -> List[Dict]:
        """Scrape job listings from Expedia careers page."""
        jobs = []
        
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(3)
            
            # Try multiple selectors for job listings
            job_selectors = [
                'li[data-automation-id="jobPostingListItem"]',
                'div[data-automation-id="jobPostingCard"]',
                'a[href*="/job/"]',
                'div.job-card',
                'article[class*="job"]',
            ]
            
            job_elements = []
            for selector in job_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    if elements and len(elements) > 0:
                        job_elements = elements
                        logger.info(f"Found {len(job_elements)} Expedia jobs using selector: {selector}")
                        break
                except Exception:
                    continue
            
            if not job_elements:
                logger.warning("No job elements found on Expedia page")
                return jobs
            
            for i, element in enumerate(job_elements):
                try:
                    # Try to extract title
                    title_text = None
                    title_selectors = ['h3', 'h2', 'a[data-automation-id="jobTitle"]', 
                                     'div[data-automation-id="jobTitle"]', '[class*="title"]']
                    
                    for title_sel in title_selectors:
                        try:
                            title_elem = await element.query_selector(title_sel)
                            if title_elem:
                                title_text = await safe_get_text(title_elem)
                                if title_text and len(title_text.strip()) > 5:
                                    break
                        except Exception:
                            continue
                    
                    if not title_text:
                        title_text = await safe_get_text(element)
                        if title_text:
                            title_text = title_text.split('\n')[0]
                    
                    if not title_text or len(title_text.strip()) < 5:
                        continue
                    
                    # Skip navigation links
                    skip_keywords = ['view job', 'apply now', 'apply', 'learn more', 'read more', 'see details']
                    if any(keyword in title_text.lower() for keyword in skip_keywords):
                        continue
                    
                    # Try to extract job URL
                    job_url = None
                    try:
                        href = await safe_get_attribute(element, 'href')
                        if href:
                            job_url = href
                        else:
                            link_elem = await element.query_selector('a')
                            if link_elem:
                                href = await safe_get_attribute(link_elem, 'href')
                                if href:
                                    job_url = href
                    except Exception:
                        pass
                    
                    # Construct full URL
                    if job_url:
                        if not job_url.startswith('http'):
                            if job_url.startswith('/'):
                                job_url = f"https://careers.expediagroup.com{job_url}"
                            else:
                                job_url = f"https://careers.expediagroup.com/{job_url}"
                    else:
                        job_url = f"https://careers.expediagroup.com/jobs?id={i}"
                    
                    # Generate job_id
                    job_id = str(i)
                    if job_url and '/job/' in job_url:
                        match = re.search(r'/job/([^/\?]+)', job_url)
                        if match:
                            job_id = match.group(1)
                    
                    job = self.create_job_dict(
                        job_id=job_id,
                        job_url=job_url,
                        title=title_text.strip(),
                        description=f"{title_text.strip()} at Expedia"
                    )
                    
                    jobs.append(job)
                    
                    if i < len(job_elements) - 1:
                        await asyncio.sleep(0.3)
                        
                except Exception as e:
                    logger.warning(f"Error extracting Expedia job {i}: {e}")
                    continue
            
            logger.info(f"Found {len(jobs)} Expedia jobs")
            
        except Exception as e:
            logger.error(f"Error scraping Expedia: {e}")
        
        return jobs
    
    async def scrape_details(self, page: Page, job_url: str) -> Optional[str]:
        """Scrape full job description from Expedia job detail page."""
        try:
            await page.goto(job_url, wait_until='networkidle', timeout=30000)
            await page.wait_for_selector('div[data-automation-id="jobPostingDescription"]', timeout=10000)
            
            desc_elem = await page.query_selector('div[data-automation-id="jobPostingDescription"]')
            description = await safe_get_text(desc_elem)
            
            return description if description else None
        
        except Exception as e:
            logger.error(f"Error scraping Expedia job details: {e}")
            return None
