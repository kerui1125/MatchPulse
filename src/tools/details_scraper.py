"""
Modular job details scraper using company-specific scraper classes.

This enriches job listings with full descriptions by visiting each job's detail page.
"""

import asyncio
import logging
import random
from typing import List, Dict, Optional
from playwright.async_api import async_playwright

# Handle both direct execution and module import
try:
    from .db import insert_job as save_job, is_job_seen as job_exists
    from .utils import setup_logging
    from ..scrapers import get_scraper
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
    from src.tools.db import insert_job as save_job, is_job_seen as job_exists
    from src.tools.utils import setup_logging
    from src.scrapers import get_scraper

logger = setup_logging()


async def enrich_job_descriptions(jobs: List[Dict]) -> List[Dict]:
    """
    Enrich job listings with full descriptions from detail pages.
    
    Args:
        jobs: List of job dictionaries from scraper
    
    Returns:
        List of enriched job dictionaries with full descriptions
    """
    if not jobs:
        logger.info("No jobs to enrich")
        return []
    
    logger.info(f"🌐 Starting detail scraping for {len(jobs)} jobs...")
    
    enriched_jobs = []
    
    async with async_playwright() as p:
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
        
        # Enable stealth mode
        try:
            from playwright_stealth.stealth import Stealth
            stealth_config = Stealth()
            await stealth_config.apply_stealth_async(page)
            logger.info("✓ Stealth mode applied")
        except Exception as e:
            logger.warning(f"Could not apply stealth mode: {e}")
        
        for i, job in enumerate(jobs):
            try:
                company = job['company'].lower()
                job_url = job['job_url']
                
                logger.info(f"[{i+1}/{len(jobs)}] {job['company']} - {job['title'][:50]}...")
                
                # Get scraper for this company
                try:
                    scraper = get_scraper(company)
                except KeyError:
                    logger.warning(f"No scraper found for company: {company}")
                    enriched_jobs.append(job)
                    continue
                
                # Use the scraper to get job details
                description = await scraper.scrape_details(page, job_url)
                
                if description:
                    job['description'] = description
                    logger.info(f"✓ {job['company']} description found ({len(description)} chars)")
                else:
                    logger.warning(f"✗ {job['company']} description not found")
                
                # Save to database
                save_job(job)
                logger.info(f"✓ Saved to database: {job['job_id']}")
                
                enriched_jobs.append(job)
                
                # Rate limiting between jobs
                if i < len(jobs) - 1:
                    sleep_time = random.uniform(3, 5)
                    logger.info(f"⏳ Waiting {sleep_time:.1f}s...")
                    await asyncio.sleep(sleep_time)
                
            except Exception as e:
                logger.error(f"✗ Error enriching job {job.get('job_id', 'unknown')}: {e}")
                enriched_jobs.append(job)
                continue
        
        await browser.close()
    
    logger.info(f"\n{'='*60}")
    logger.info(f"📊 Summary")
    logger.info(f"{'='*60}")
    logger.info(f"✓ Enriched: {len(enriched_jobs)} jobs")
    logger.info(f"✗ Failed: {len(jobs) - len(enriched_jobs)} jobs")
    
    # Show sample
    logger.info(f"\n✓ Sample:")
    for job in enriched_jobs[:3]:
        desc_len = len(job.get('description', ''))
        logger.info(f"   - {job['company']}: {job['title'][:50]}... ({desc_len} chars)")
    
    logger.info(f"{'='*60}")
    
    return enriched_jobs


async def test_details_scraper():
    """Test details scraper with a few sample jobs."""
    # Sample jobs for testing
    test_jobs = [
        {
            'company': 'Google',
            'job_id': 'google_test_1',
            'job_url': 'https://www.google.com/about/careers/applications/jobs/results/130864805362705094-software-engineer-aiml',
            'title': 'Software Engineer, AI/ML',
            'description': None
        }
    ]
    
    enriched = await enrich_job_descriptions(test_jobs)
    
    print(f"\nEnriched {len(enriched)} jobs:")
    for job in enriched:
        print(f"\n{job['company']}: {job['title']}")
        print(f"Description length: {len(job.get('description', ''))} chars")
        if job.get('description'):
            print(f"Preview: {job['description'][:200]}...")


if __name__ == "__main__":
    asyncio.run(test_details_scraper())



async def fetch_and_enrich_jobs(dry_run: bool = True, limit: Optional[int] = None) -> List[Dict]:
    """
    Main function: Fetch jobs, filter new ones, scrape details, save to DB.
    
    This is the entry point used by fetcher_agent.
    
    Args:
        dry_run: If True, don't save to database (default: True)
        limit: If set, only process first N jobs
    
    Returns:
        List of enriched job dictionaries
    """
    from .scraper import fetch_jobs
    from .utils import get_company_links
    
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
    new_jobs = [job for job in jobs if not job_exists(job['job_id'])]
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
    
    # Enrich with details (this will also save to DB)
    enriched_jobs = await enrich_job_descriptions(new_jobs)
    
    return enriched_jobs
