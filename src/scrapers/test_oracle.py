"""
Standalone Oracle scraper for testing and debugging.

Usage:
    python src/scrapers/test_oracle.py

This allows you to quickly test and fix Oracle scraper without affecting other companies.
"""

import asyncio
import logging
from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_oracle_scraper():
    """Test Oracle scraper with detailed logging."""
    
    url = "https://careers.oracle.com/en/sites/jobsearch/jobs?keyword=Software+Developer&location=Seattle%2C+WA%2C+United+States&locationId=100000000731910&locationLevel=city&mode=location&radius=25&radiusUnit=KM"
    
    logger.info(f"Testing Oracle scraper...")
    logger.info(f"URL: {url}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,  # Show browser for debugging
            slow_mo=1000     # Slow down by 1 second per action
        )
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        )
        
        page = await context.new_page()
        
        try:
            logger.info("Navigating to Oracle careers page...")
            await page.goto(url, wait_until='networkidle', timeout=30000)
            
            logger.info("Waiting for page to load...")
            await asyncio.sleep(3)
            
            # Try different selectors
            selectors_to_try = [
                'a[href*="/en/sites/jobsearch/job/"]',
                'a[href*="/job/"]',
                '.job-card',
                '[data-job-id]',
                'div.job-listing',
                'article',
                'li.job-item'
            ]
            
            logger.info("Trying different selectors...")
            for selector in selectors_to_try:
                try:
                    elements = await page.query_selector_all(selector)
                    if elements:
                        logger.info(f"✓ Found {len(elements)} elements with selector: {selector}")
                    else:
                        logger.info(f"✗ No elements found with selector: {selector}")
                except Exception as e:
                    logger.error(f"✗ Error with selector {selector}: {e}")
            
            # Take screenshot for debugging
            await page.screenshot(path='oracle_debug.png')
            logger.info("Screenshot saved to oracle_debug.png")
            
            # Print page HTML (first 2000 chars)
            html = await page.content()
            logger.info(f"\nPage HTML (first 2000 chars):\n{html[:2000]}")
            
        except Exception as e:
            logger.error(f"Error: {e}")
        
        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(test_oracle_scraper())
