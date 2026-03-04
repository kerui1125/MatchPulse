"""
Job Details Scraper - Fetches complete job information from detail pages.

USAGE:
  python src/tools/details_scraper.py  # Test mode (dry_run=True)
  
In code:
  jobs = await fetch_and_enrich_jobs(dry_run=True, limit=3)
"""

import asyncio
import random
from typing import Dict, List, Optional
from playwright.async_api import async_playwright
from playwright_stealth.stealth import Stealth

try:
    from .scraper import fetch_jobs
    from .utils import get_company_links, setup_logging
    from .db import is_job_seen, insert_job
except ImportError:
    from scraper import fetch_jobs
    from utils import get_company_links, setup_logging
    from db import is_job_seen, insert_job

logger = setup_logging()


async def scrape_nvidia_job_details(page, job_url: str) -> Dict[str, Optional[str]]:
    """Scrape NVIDIA job details."""
    try:
        logger.info(f"Scraping NVIDIA details: {job_url}")
        await page.goto(job_url, wait_until="domcontentloaded", timeout=45000)
        await asyncio.sleep(3)
        
        description = None
        desc_selectors = ['div.container-3Gm1a', 'div[class*="container"]', '#main-content div[class*="description"]']
        
        for selector in desc_selectors:
            try:
                elem = await page.query_selector(selector)
                if elem:
                    text = await elem.inner_text()
                    if text and len(text.strip()) > 100:
                        description = text.strip()
                        logger.info(f"✓ NVIDIA description found ({len(description)} chars)")
                        break
            except Exception:
                continue
        
        if not description:
            logger.warning(f"No description found for NVIDIA job: {job_url}")
        
        return {'description': description, 'salary': None, 'posted_date': None}
        
    except Exception as e:
        logger.error(f"Error scraping NVIDIA details {job_url}: {e}")
        return {'description': None, 'salary': None, 'posted_date': None}


async def scrape_google_job_details(page, job_url: str) -> Dict[str, Optional[str]]:
    """Scrape Google job details."""
    try:
        logger.info(f"Scraping Google details: {job_url}")
        await page.goto(job_url, wait_until="domcontentloaded", timeout=45000)
        await asyncio.sleep(3)
        
        description = None
        desc_selectors = ['div.KwJkGe', 'div[class*="KwJkGe"]', 'div[itemprop="description"]']
        
        for selector in desc_selectors:
            try:
                elem = await page.query_selector(selector)
                if elem:
                    text = await elem.inner_text()
                    if text and len(text.strip()) > 100:
                        description = text.strip()
                        logger.info(f"✓ Google description found ({len(description)} chars)")
                        break
            except Exception:
                continue
        
        if not description:
            logger.warning(f"No description found for Google job: {job_url}")
        
        return {'description': description, 'salary': None, 'posted_date': None}
        
    except Exception as e:
        logger.error(f"Error scraping Google details {job_url}: {e}")
        return {'description': None, 'salary': None, 'posted_date': None}


async def scrape_amazon_job_details(page, job_url: str) -> Dict[str, Optional[str]]:
    """Scrape Amazon job details."""
    try:
        logger.info(f"Scraping Amazon details: {job_url}")
        await page.goto(job_url, wait_until="domcontentloaded", timeout=45000)
        await asyncio.sleep(3)
        
        description = None
        desc_selectors = ['#job-detail-body', '#job-detail', 'div[data-test="job-description"]']
        
        for selector in desc_selectors:
            try:
                elem = await page.query_selector(selector)
                if elem:
                    text = await elem.inner_text()
                    if text and len(text.strip()) > 100:
                        description = text.strip()
                        logger.info(f"✓ Amazon description found ({len(description)} chars)")
                        break
            except Exception:
                continue
        
        if not description:
            logger.warning(f"No description found for Amazon job: {job_url}")
        
        return {'description': description, 'salary': None, 'posted_date': None}
        
    except Exception as e:
        logger.error(f"Error scraping Amazon details {job_url}: {e}")
        return {'description': None, 'salary': None, 'posted_date': None}


async def scrape_microsoft_job_details(page, job_url: str) -> Dict[str, Optional[str]]:
    """Scrape Microsoft job details."""
    try:
        logger.info(f"Scraping Microsoft details: {job_url}")
        await page.goto(job_url, wait_until="domcontentloaded", timeout=45000)
        await asyncio.sleep(3)
        
        description = None
        desc_selectors = ['#job-description-container', 'div[data-automation-id*="description"]']
        
        for selector in desc_selectors:
            try:
                elem = await page.query_selector(selector)
                if elem:
                    text = await elem.inner_text()
                    if text and len(text.strip()) > 100:
                        description = text.strip()
                        logger.info(f"✓ Microsoft description found ({len(description)} chars)")
                        break
            except Exception:
                continue
        
        if not description:
            logger.warning(f"No description found for Microsoft job: {job_url}")
        
        return {'description': description, 'salary': None, 'posted_date': None}
        
    except Exception as e:
        logger.error(f"Error scraping Microsoft details {job_url}: {e}")
        return {'description': None, 'salary': None, 'posted_date': None}


async def scrape_salesforce_job_details(page, job_url: str) -> Dict[str, Optional[str]]:
    """Scrape Salesforce job details."""
    try:
        logger.info(f"Scraping Salesforce details: {job_url}")
        await page.goto(job_url, wait_until="domcontentloaded", timeout=45000)
        await asyncio.sleep(3)
        
        description = None
        desc_selectors = ['article', 'main article', '#js-job-detail article']
        
        for selector in desc_selectors:
            try:
                elem = await page.query_selector(selector)
                if elem:
                    text = await elem.inner_text()
                    if text and len(text.strip()) > 100:
                        description = text.strip()
                        logger.info(f"✓ Salesforce description found ({len(description)} chars)")
                        break
            except Exception:
                continue
        
        if not description:
            logger.warning(f"No description found for Salesforce job: {job_url}")
        
        return {'description': description, 'salary': None, 'posted_date': None}
        
    except Exception as e:
        logger.error(f"Error scraping Salesforce details {job_url}: {e}")
        return {'description': None, 'salary': None, 'posted_date': None}


async def scrape_expedia_job_details(page, job_url: str) -> Dict[str, Optional[str]]:
    """Scrape Expedia job details."""
    try:
        logger.info(f"Scraping Expedia details: {job_url}")
        await page.goto(job_url, wait_until="domcontentloaded", timeout=45000)
        await asyncio.sleep(3)
        
        description = None
        desc_selectors = ['div.Desc__copy', 'section.Desc', 'div[data-ui="job-description"]']
        
        for selector in desc_selectors:
            try:
                elem = await page.query_selector(selector)
                if elem:
                    text = await elem.inner_text()
                    if text and len(text.strip()) > 100:
                        description = text.strip()
                        logger.info(f"✓ Expedia description found ({len(description)} chars)")
                        break
            except Exception:
                continue
        
        if not description:
            logger.warning(f"No description found for Expedia job: {job_url}")
        
        return {'description': description, 'salary': None, 'posted_date': None}
        
    except Exception as e:
        logger.error(f"Error scraping Expedia details {job_url}: {e}")
        return {'description': None, 'salary': None, 'posted_date': None}


async def scrape_oracle_job_details(page, job_url: str) -> Dict[str, Optional[str]]:
    """Scrape Oracle job details."""
    try:
        logger.info(f"Scraping Oracle details: {job_url}")
        await page.goto(job_url, wait_until="domcontentloaded", timeout=45000)
        await asyncio.sleep(3)
        
        description = None
        desc_selectors = ['article', 'main article', 'div[class*="job-detail"]']
        
        for selector in desc_selectors:
            try:
                elem = await page.query_selector(selector)
                if elem:
                    text = await elem.inner_text()
                    if text and len(text.strip()) > 100:
                        description = text.strip()
                        logger.info(f"✓ Oracle description found ({len(description)} chars)")
                        break
            except Exception:
                continue
        
        if not description:
            logger.warning(f"No description found for Oracle job: {job_url}")
        
        return {'description': description, 'salary': None, 'posted_date': None}
        
    except Exception as e:
        logger.error(f"Error scraping Oracle details {job_url}: {e}")
        return {'description': None, 'salary': None, 'posted_date': None}


async def fetch_job_details(page, job_url: str, company: str) -> Dict[str, Optional[str]]:
    """Route to appropriate company-specific detail scraper."""
    scrapers = {
        'nvidia': scrape_nvidia_job_details,
        'google': scrape_google_job_details,
        'amazon': scrape_amazon_job_details,
        'microsoft': scrape_microsoft_job_details,
        'salesforce': scrape_salesforce_job_details,
        'expedia': scrape_expedia_job_details,
        'oracle': scrape_oracle_job_details,
    }
    
    scraper = scrapers.get(company)
    if scraper:
        return await scraper(page, job_url)
    else:
        logger.info(f"No detail scraper implemented for company: {company}")
        return {'description': None, 'salary': None, 'posted_date': None}


async def fetch_and_enrich_jobs(dry_run: bool = True, limit: Optional[int] = None) -> List[Dict]:
    """
    Main function: Fetch jobs, filter new ones, scrape details, save to DB.
    
    Args:
        dry_run: If True, don't save to database (default: True)
        limit: If set, only process first N jobs
    
    Returns:
        List of enriched job dictionaries
    """
    logger.info("=" * 60)
    logger.info("Starting job fetch and enrichment process")
    logger.info("=" * 60)
    
    if dry_run:
        logger.warning("⚠️  DRY-RUN MODE: Jobs will NOT be saved to database")
    else:
        logger.warning("🔴 PRODUCTION MODE: Jobs WILL be saved to database")
    
    if limit:
        logger.warning(f"⚠️  LIMIT MODE: Only processing first {limit} jobs")
    
    logger.info("=" * 60)
    
    # Get company links
    company_links = get_company_links()
    logger.info(f"📋 Configured companies: {list(company_links.keys())}")
    
    # Fetch basic job info
    logger.info("🔍 Fetching job listings...")
    jobs = await fetch_jobs(company_links)
    logger.info(f"✓ Found {len(jobs)} total jobs")
    
    # Filter duplicates
    logger.info("🔎 Checking for duplicates...")
    new_jobs = [job for job in jobs if not is_job_seen(job['job_id'])]
    logger.info(f"✓ Found {len(new_jobs)} NEW jobs (filtered {len(jobs) - len(new_jobs)} duplicates)")
    
    # Apply limit
    if limit and len(new_jobs) > limit:
        logger.warning(f"⚠️  Limiting to first {limit} jobs")
        new_jobs = new_jobs[:limit]
    
    if not new_jobs:
        logger.info("✓ No new jobs to process")
        return []
    
    # Group by company
    jobs_by_company = {}
    for job in new_jobs:
        company = job['company']
        jobs_by_company[company] = jobs_by_company.get(company, 0) + 1
    
    logger.info("📊 New jobs by company:")
    for company, count in jobs_by_company.items():
        logger.info(f"   - {company}: {count} jobs")
    
    # Scrape details
    logger.info(f"🌐 Starting detail scraping for {len(new_jobs)} jobs...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled', '--disable-dev-shm-usage', '--no-sandbox']
        )
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        )
        
        page = await context.new_page()
        
        try:
            stealth_config = Stealth()
            await stealth_config.apply_stealth_async(page)
            logger.info("✓ Stealth mode applied")
        except Exception as e:
            logger.warning(f"Could not apply stealth mode: {e}")
        
        enriched_jobs = []
        failed_jobs = []
        
        for i, job in enumerate(new_jobs):
            try:
                logger.info(f"[{i+1}/{len(new_jobs)}] {job['company']} - {job['title'][:50]}...")
                
                details = await fetch_job_details(page, job['job_url'], job['company'])
                job.update(details)
                
                if not dry_run:
                    try:
                        insert_job(
                            company=job['company'],
                            job_id=job['job_id'],
                            job_url=job['job_url'],
                            title=job['title'],
                            description=job.get('description'),
                            salary=job.get('salary'),
                            posted_date=job.get('posted_date'),
                            status='fetched'
                        )
                        logger.info(f"✓ Saved to database: {job['job_id']}")
                        enriched_jobs.append(job)
                    except Exception as db_error:
                        logger.error(f"✗ Database error: {db_error}")
                        failed_jobs.append(job)
                else:
                    logger.info(f"🔍 DRY-RUN: Would save {job['job_id']}")
                    enriched_jobs.append(job)
                
                # Rate limiting
                if i < len(new_jobs) - 1:
                    delay = random.uniform(3, 5)
                    logger.info(f"⏳ Waiting {delay:.1f}s...")
                    await asyncio.sleep(delay)
                
            except Exception as e:
                logger.error(f"✗ Error processing {job['job_id']}: {e}")
                failed_jobs.append(job)
                if i < len(new_jobs) - 1:
                    await asyncio.sleep(random.uniform(3, 5))
        
        await browser.close()
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("📊 Summary")
    logger.info("=" * 60)
    logger.info(f"✓ Enriched: {len(enriched_jobs)} jobs")
    logger.info(f"✗ Failed: {len(failed_jobs)} jobs")
    
    if enriched_jobs:
        logger.info("\n✓ Sample:")
        for job in enriched_jobs[:3]:
            desc_len = len(job.get('description', '')) if job.get('description') else 0
            logger.info(f"   - {job['company']}: {job['title'][:40]}... ({desc_len} chars)")
    
    logger.info("=" * 60)
    
    return enriched_jobs


async def test_details_scraper():
    """Test function with logging to file."""
    import logging
    from datetime import datetime
    
    test_log_file = 'details_scraper_test.log'
    test_logger = logging.getLogger('details_scraper_test')
    test_logger.setLevel(logging.INFO)
    
    file_handler = logging.FileHandler(test_log_file, mode='w', encoding='utf-8')
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
    test_logger.addHandler(file_handler)
    
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter('%(message)s'))
    test_logger.addHandler(console_handler)
    
    test_logger.info("=" * 60)
    test_logger.info("Testing Job Details Scraper")
    test_logger.info(f"Results saved to: {test_log_file}")
    test_logger.info("=" * 60)
    
    start_time = datetime.now()
    jobs = await fetch_and_enrich_jobs(dry_run=True, limit=None)
    duration = (datetime.now() - start_time).total_seconds()
    
    test_logger.info(f"\nTest completed: {len(jobs)} jobs enriched in {duration:.1f}s")
    
    if jobs:
        test_logger.info(f"\n📋 All {len(jobs)} enriched jobs:\n")
        for i, job in enumerate(jobs, 1):
            test_logger.info(f"{i}. {job['company'].upper()}: {job['title']}")
            test_logger.info(f"   URL: {job['job_url']}")
            desc = job.get('description', '')
            if desc:
                test_logger.info(f"   Description: {len(desc)} chars")
                test_logger.info(f"   Preview: {desc[:200]}...")
            else:
                test_logger.info(f"   Description: ❌ Not found")
            test_logger.info("")
    
    file_handler.close()
    console_handler.close()


if __name__ == "__main__":
    asyncio.run(test_details_scraper())
