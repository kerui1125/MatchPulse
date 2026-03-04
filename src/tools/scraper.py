import asyncio
import logging
from typing import List, Dict, Optional
from playwright.async_api import async_playwright
import playwright_stealth

# Handle both direct execution and module import
try:
    from .utils import get_company_links, setup_logging
except ImportError:
    from utils import get_company_links, setup_logging

logger = setup_logging()


async def fetch_jobs(company_links: Optional[Dict[str, str]] = None) -> List[Dict]:
    """
    Scrape jobs from company career pages.
    
    Args:
        company_links: Dict of {company_name: filtered_url}
                      If None, loads from config.yaml
    
    Returns:
        List of job dictionaries with fields:
        - company, job_id, job_url, title, location, 
          description, salary (optional), posted_date (optional)
    """
    if company_links is None:
        company_links = get_company_links()
    
    all_jobs = []
    
    async with async_playwright() as p:
        # Launch browser with stealth options
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
        
        # Enable stealth mode on the page
        try:
            # Use Stealth class from playwright_stealth
            from playwright_stealth.stealth import Stealth
            stealth_config = Stealth()
            await stealth_config.apply_stealth_async(page)
        except Exception as e:
            logger.warning(f"Could not apply stealth mode: {e}")
            # Continue without stealth
        
        for company, url in company_links.items():
            try:
                logger.info(f"Scraping {company}: {url}")
                
                if company == "google":
                    jobs = await scrape_google_jobs(page, url)
                elif company == "amazon":
                    jobs = await scrape_amazon_jobs(page, url)
                elif company == "microsoft":
                    jobs = await scrape_microsoft_jobs(page, url)
                elif company == "salesforce":
                    jobs = await scrape_salesforce_jobs(page, url)
                elif company == "nvidia":
                    jobs = await scrape_nvidia_jobs(page, url)
                elif company == "expedia":
                    jobs = await scrape_expedia_jobs(page, url)
                elif company == "oracle":
                    jobs = await scrape_oracle_jobs(page, url)
                else:
                    logger.warning(f"No scraper for company: {company}")
                    continue
                
                all_jobs.extend(jobs)
                logger.info(f"Found {len(jobs)} jobs from {company}")
                
                # Rate limiting between companies
                import random
                sleep_time = random.uniform(3, 6)
                await asyncio.sleep(sleep_time)
                
            except Exception as e:
                logger.error(f"Error scraping {company}: {e}")
                continue
        
        await browser.close()
    
    logger.info(f"Total jobs scraped: {len(all_jobs)}")
    return all_jobs





async def scrape_google_jobs(page, url: str) -> List[Dict]:
    """
    Scrape jobs from Google careers page.
    
    Strategy:
    1. Find job cards using h3.QJPWVe (title)
    2. Go up 3 levels to find link
    """
    jobs = []
    
    try:
        # Use domcontentloaded for faster loading
        await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        
        # Wait for job listings to load
        await page.wait_for_selector('h3.QJPWVe', timeout=10000)
        
        # Find all job titles
        titles = await page.query_selector_all('h3.QJPWVe')
        
        logger.info(f"Found {len(titles)} Google jobs")
        
        for i, title in enumerate(titles):
            try:
                # Get title text
                title_text = await title.inner_text()
                
                # Go up 3 levels to find the link
                level3 = await title.evaluate_handle('''
                    el => el.parentElement.parentElement.parentElement
                ''')
                
                # Find the link
                link_elem = await level3.query_selector('a.WpHeLc')
                job_url = None
                if link_elem:
                    href = await link_elem.get_attribute('href')
                    if href:
                        # Construct full URL
                        if href.startswith('jobs/'):
                            job_url = f"https://www.google.com/about/careers/applications/{href}"
                        elif href.startswith('/'):
                            job_url = f"https://www.google.com{href}"
                        else:
                            job_url = href
                
                # Generate job_id from URL
                job_id = f"google_{i}"
                if job_url and 'results/' in job_url:
                    # Extract job ID from URL like jobs/results/85809587231302342-...
                    import re
                    match = re.search(r'results/(\d+)', job_url)
                    if match:
                        job_id = f"google_{match.group(1)}"
                
                job = {
                    'company': 'google',
                    'job_id': job_id,
                    'job_url': job_url or f"https://www.google.com/about/careers/applications/jobs/{i}",
                    'title': title_text,
                    'description': f"{title_text} at Google",
                    'salary': None,
                    'posted_date': None
                }
                
                jobs.append(job)
                
                # Small delay between jobs
                if i < len(titles) - 1:
                    await asyncio.sleep(0.5)
                    
            except Exception as e:
                logger.warning(f"Error extracting Google job {i}: {e}")
                continue
        
    except Exception as e:
        logger.error(f"Error scraping Google: {e}")
    
    return jobs


async def scrape_nvidia_jobs(page, url: str) -> List[Dict]:
    """
    Scrape jobs from NVIDIA careers page (Greenhouse platform).
    
    Strategy:
    1. Find job cards using div[class*="jobListSection"]
    2. Extract title from div.title-1aNJK
    3. Extract link from a tags
    """
    jobs = []
    
    try:
        # Use domcontentloaded for faster loading
        await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        
        # Wait for job listings to load
        await page.wait_for_selector('div.title-1aNJK', timeout=10000)
        
        # Find all job titles
        title_elements = await page.query_selector_all('div.title-1aNJK')
        
        logger.info(f"Found {len(title_elements)} NVIDIA jobs")
        
        for i, title_elem in enumerate(title_elements):
            try:
                # Get title text
                title_text = await title_elem.inner_text()
                
                # Find the parent <a> tag that contains the job link
                # The structure is: <a class="r-link card-F1ebU"> ... <div class="title-1aNJK">Title</div> ... </a>
                job_url = None
                
                # Method: Go up from title to find the parent <a> tag
                parent_link_href = await title_elem.evaluate('''
                    el => {
                        // Go up to find parent <a> tag
                        let current = el;
                        while (current && current.tagName !== 'A') {
                            current = current.parentElement;
                            if (!current) return null;
                        }
                        // Found <a> tag, return href
                        return current ? current.getAttribute('href') : null;
                    }
                ''')
                
                if parent_link_href:
                    # Construct full URL
                    if parent_link_href.startswith('/careers/job/'):
                        job_url = f"https://jobs.nvidia.com{parent_link_href}"
                    elif parent_link_href.startswith('/'):
                        job_url = f"https://jobs.nvidia.com{parent_link_href}"
                    elif not parent_link_href.startswith('http'):
                        job_url = f"https://jobs.nvidia.com{parent_link_href}"
                    else:
                        job_url = parent_link_href
                
                # Generate job_id from URL
                job_id = f"nvidia_{i}"
                if job_url and '/job/' in job_url:
                    # Extract job ID from URL like /careers/job/893393815235
                    import re
                    match = re.search(r'/job/(\d+)', job_url)
                    if match:
                        job_id = f"nvidia_{match.group(1)}"
                
                job = {
                    'company': 'nvidia',
                    'job_id': job_id,
                    'job_url': job_url or f"https://jobs.nvidia.com/careers/job/{i}",
                    'title': title_text,
                    'description': f"{title_text} at NVIDIA",
                    'salary': None,
                    'posted_date': None
                }
                
                jobs.append(job)
                
                # Small delay between jobs
                if i < len(title_elements) - 1:
                    await asyncio.sleep(0.5)
                    
            except Exception as e:
                logger.warning(f"Error extracting NVIDIA job {i}: {e}")
                continue
        
    except Exception as e:
        logger.error(f"Error scraping NVIDIA: {e}")
    
    return jobs


async def scrape_amazon_jobs(page, url: str) -> List[Dict]:
    """
    Scrape jobs from Amazon careers page.
    
    Strategy:
    1. Find job links using a[href*="/en/jobs/"]
    2. Extract title from link text
    """
    jobs = []
    
    try:
        # Use domcontentloaded instead of networkidle for faster loading
        # Increase timeout to 60 seconds
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        
        # Wait for job listings to load with longer timeout
        await page.wait_for_selector('a[href*="/en/jobs/"]', timeout=20000)
        
        # Find all job links
        job_links = await page.query_selector_all('a[href*="/en/jobs/"]')
        
        # Filter to only job posting links (not navigation links)
        filtered_links = []
        for link in job_links:
            href = await link.get_attribute('href')
            text = await link.inner_text()
            # Check if it looks like a job link (has job ID and reasonable text)
            if href and '/jobs/' in href and len(text) > 10 and '...' not in text:
                filtered_links.append(link)
        
        logger.info(f"Found {len(filtered_links)} Amazon jobs")
        
        for i, link in enumerate(filtered_links):
            try:
                # Get title text
                title_text = await link.inner_text()
                
                # Get URL
                href = await link.get_attribute('href')
                job_url = None
                if href:
                    # Construct full URL
                    if href.startswith('/en/jobs/'):
                        job_url = f"https://www.amazon.jobs{href}"
                    elif href.startswith('/'):
                        job_url = f"https://www.amazon.jobs{href}"
                    else:
                        job_url = href
                
                # Generate job_id from URL
                job_id = f"amazon_{i}"
                if job_url and '/jobs/' in job_url:
                    # Extract job ID from URL like /en/jobs/3146660/software-development-engineer
                    import re
                    match = re.search(r'/jobs/(\d+)', job_url)
                    if match:
                        job_id = f"amazon_{match.group(1)}"
                
                job = {
                    'company': 'amazon',
                    'job_id': job_id,
                    'job_url': job_url or f"https://www.amazon.jobs/en/jobs/{i}",
                    'title': title_text,
                    'description': f"{title_text} at Amazon",
                    'salary': None,
                    'posted_date': None
                }
                
                jobs.append(job)
                
                # Small delay between jobs
                if i < len(filtered_links) - 1:
                    await asyncio.sleep(0.5)
                    
            except Exception as e:
                logger.warning(f"Error extracting Amazon job {i}: {e}")
                continue
        
    except Exception as e:
        logger.error(f"Error scraping Amazon: {e}")
    
    return jobs





def extract_job_id(job_url: str, company: str) -> str:
    """
    Extract unique job_id from URL.
    
    Args:
        job_url: Job posting URL
        company: Company name
    
    Returns:
        Unique job identifier
    """
    if not job_url:
        return f"{company}_unknown"
    
    # Try to extract ID from URL
    if '/jobs/' in job_url:
        parts = job_url.split('/')
        for i, part in enumerate(parts):
            if part == 'jobs' and i + 1 < len(parts):
                job_num = parts[i + 1]
                if job_num.isdigit() or len(job_num) > 5:
                    return f"{company}_{job_num}"
    
    # Fallback: hash the URL
    import hashlib
    url_hash = hashlib.md5(job_url.encode()).hexdigest()[:8]
    return f"{company}_{url_hash}"


async def test_scraper():
    """Test function to run scraper manually."""
    from utils import get_company_links
    
    links = get_company_links()
    print(f"Testing scraper with {len(links)} companies")
    
    # Test all companies
    test_links = links
    
    if not test_links:
        print("No testable companies found in config.yaml")
        return
    
    jobs = await fetch_jobs(test_links)
    
    print(f"\nScraped {len(jobs)} jobs:")
    print(jobs)
    for i, job in enumerate(jobs):  # Show all
        print(f"{i+1}. {job['company']}: {job['title']}")
        print(f"   URL: {job['job_url']}")
        print()

async def scrape_microsoft_jobs(page, url: str) -> List[Dict]:
    """
    Scrape jobs from Microsoft careers page.
    
    Strategy:
    1. Try multiple selectors for job cards
    2. Extract title from div.title-1aNJK
    3. Extract link from href attribute
    """
    jobs = []
    
    try:
        # Use domcontentloaded for faster loading
        await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        
        # Wait a bit longer for Microsoft page to load
        await asyncio.sleep(2)
        
        # Try multiple selectors for job cards
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
            # Fallback: look for any links with job IDs
            all_links = await page.query_selector_all('a')
            for link in all_links:
                href = await link.get_attribute('href')
                if href and '/careers/job/' in href:
                    job_cards.append(link)
            logger.info(f"Found {len(job_cards)} Microsoft jobs via href search")
        
        for i, card in enumerate(job_cards):
            try:
                # Extract title
                title_text = "N/A"
                title_elem = await card.query_selector('div.title-1aNJK')
                if title_elem:
                    title_text = await title_elem.inner_text()
                else:
                    # Try to get text from the card itself
                    card_text = await card.inner_text()
                    if card_text and len(card_text) > 10:
                        title_text = card_text.split('\n')[0]  # First line
                
                # Get URL
                href = await card.get_attribute('href')
                job_url = None
                if href:
                    # Construct full URL
                    if href.startswith('/careers/job/'):
                        job_url = f"https://apply.careers.microsoft.com{href}"
                    elif href.startswith('/'):
                        job_url = f"https://apply.careers.microsoft.com{href}"
                    else:
                        job_url = href
                
                # Skip if no title or URL
                if title_text == "N/A" or not job_url:
                    continue
                
                # Generate job_id from URL
                job_id = f"microsoft_{i}"
                if job_url and '/job/' in job_url:
                    # Extract job ID from URL like /careers/job/1970393556640555
                    import re
                    match = re.search(r'/job/(\d+)', job_url)
                    if match:
                        job_id = f"microsoft_{match.group(1)}"
                
                job = {
                    'company': 'microsoft',
                    'job_id': job_id,
                    'job_url': job_url,
                    'title': title_text,
                    'description': f"{title_text} at Microsoft",
                    'salary': None,
                    'posted_date': None
                }
                
                jobs.append(job)
                
                # Small delay between jobs
                if i < len(job_cards) - 1:
                    await asyncio.sleep(0.5)
                    
            except Exception as e:
                logger.warning(f"Error extracting Microsoft job {i}: {e}")
                continue
        
    except Exception as e:
        logger.error(f"Error scraping Microsoft: {e}")
    
    return jobs


async def scrape_salesforce_jobs(page, url: str) -> List[Dict]:
    """
    Scrape jobs from Salesforce careers page.
    
    Strategy:
    1. Find job links using a[href*="/en/jobs/jr"]
    2. Extract title from link text
    """
    jobs = []
    
    try:
        # Use domcontentloaded for faster loading
        await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        
        # Wait for job listings to load
        await page.wait_for_selector('a[href*="/en/jobs/jr"]', timeout=10000)
        
        # Find all job links
        job_links = await page.query_selector_all('a[href*="/en/jobs/jr"]')
        
        logger.info(f"Found {len(job_links)} Salesforce jobs")
        
        for i, link in enumerate(job_links):
            try:
                # Get title text
                title_text = await link.inner_text()
                
                # Skip if title is too short or looks like navigation
                if len(title_text) < 5 or title_text.isdigit():
                    continue
                
                # Get URL
                href = await link.get_attribute('href')
                job_url = None
                if href:
                    # Construct full URL
                    if href.startswith('/en/jobs/'):
                        job_url = f"https://careers.salesforce.com{href}"
                    elif href.startswith('/'):
                        job_url = f"https://careers.salesforce.com{href}"
                    else:
                        job_url = href
                
                # Generate job_id from URL
                job_id = f"salesforce_{i}"
                if job_url and '/jobs/jr' in job_url:
                    # Extract job ID from URL like /en/jobs/jr326284/agentforce-technical-manager/
                    import re
                    match = re.search(r'/jobs/jr(\d+)', job_url)
                    if match:
                        job_id = f"salesforce_{match.group(1)}"
                
                job = {
                    'company': 'salesforce',
                    'job_id': job_id,
                    'job_url': job_url or f"https://careers.salesforce.com/en/jobs/jr{i}",
                    'title': title_text,
                    'description': f"{title_text} at Salesforce",
                    'salary': None,
                    'posted_date': None
                }
                
                jobs.append(job)
                
                # Small delay between jobs
                if i < len(job_links) - 1:
                    await asyncio.sleep(0.5)
                    
            except Exception as e:
                logger.warning(f"Error extracting Salesforce job {i}: {e}")
                continue
        
    except Exception as e:
        logger.error(f"Error scraping Salesforce: {e}")
    
    return jobs


async def scrape_oracle_jobs(page, url: str) -> List[Dict]:
    """
    Scrape jobs from Oracle careers page.
    
    Strategy:
    1. Find job links using a[href*="/en/sites/jobsearch/job/"]
    2. Extract title from link text or nearby elements
    """
    jobs = []
    
    try:
        # Use domcontentloaded instead of networkidle for faster loading
        # Increase timeout to 60 seconds
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        
        # Wait for job listings to load with longer timeout
        await page.wait_for_selector('a[href*="/en/sites/jobsearch/job/"]', timeout=20000)
        
        # Find all job links
        job_links = await page.query_selector_all('a[href*="/en/sites/jobsearch/job/"]')
        
        logger.info(f"Found {len(job_links)} Oracle jobs")
        
        for i, link in enumerate(job_links):
            try:
                # Get title text - Oracle links might not have visible text
                title_text = await link.inner_text()
                
                # If no text in link, try to find title in parent or sibling
                if not title_text or len(title_text.strip()) < 5:
                    # Look for title in parent element
                    parent = await link.evaluate_handle('el => el.parentElement')
                    parent_text = await parent.inner_text()
                    if parent_text and len(parent_text) > 10:
                        title_text = parent_text.split('\n')[0]
                    else:
                        # Skip if no title found
                        continue
                
                # Get URL
                href = await link.get_attribute('href')
                job_url = None
                if href:
                    # Construct full URL
                    if href.startswith('/en/sites/jobsearch/job/'):
                        job_url = f"https://careers.oracle.com{href}"
                    elif href.startswith('/'):
                        job_url = f"https://careers.oracle.com{href}"
                    else:
                        job_url = href
                
                # Generate job_id from URL
                job_id = f"oracle_{i}"
                if job_url and '/job/' in job_url:
                    # Extract job ID from URL like /en/sites/jobsearch/job/323413/
                    import re
                    match = re.search(r'/job/(\d+)', job_url)
                    if match:
                        job_id = f"oracle_{match.group(1)}"
                
                job = {
                    'company': 'oracle',
                    'job_id': job_id,
                    'job_url': job_url or f"https://careers.oracle.com/en/sites/jobsearch/job/{i}",
                    'title': title_text.strip(),
                    'description': f"{title_text.strip()} at Oracle",
                    'salary': None,
                    'posted_date': None
                }
                
                jobs.append(job)
                
                # Small delay between jobs
                if i < len(job_links) - 1:
                    await asyncio.sleep(0.5)
                    
            except Exception as e:
                logger.warning(f"Error extracting Oracle job {i}: {e}")
                continue
        
    except Exception as e:
        logger.error(f"Error scraping Oracle: {e}")
    
    return jobs


async def scrape_expedia_jobs(page, url: str) -> List[Dict]:
    """
    Scrape jobs from Expedia careers page (Workday platform).
    
    Strategy:
    1. Wait for page to load completely
    2. Look for job cards or listings
    3. Extract job information from visible elements
    """
    jobs = []
    
    try:
        # Use domcontentloaded for faster loading, with longer timeout for Workday
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        
        # Wait a bit for dynamic content to load
        await asyncio.sleep(3)
        
        # Try multiple selectors for job listings
        job_selectors = [
            'li[data-automation-id="jobPostingListItem"]',  # Workday job items
            'div[data-automation-id="jobPostingCard"]',      # Workday job cards
            'a[href*="/job/"]',                              # Generic job links
            'div.job-card',                                  # Generic job cards
            'article[class*="job"]',                         # Article-based job listings
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
                title_selectors = [
                    'h3',
                    'h2',
                    'a[data-automation-id="jobTitle"]',
                    'div[data-automation-id="jobTitle"]',
                    '[class*="title"]',
                ]
                
                for title_sel in title_selectors:
                    try:
                        title_elem = await element.query_selector(title_sel)
                        if title_elem:
                            title_text = await title_elem.inner_text()
                            if title_text and len(title_text.strip()) > 5:
                                break
                    except Exception:
                        continue
                
                if not title_text:
                    # Fallback: get text from element itself
                    title_text = await element.inner_text()
                    if title_text:
                        # Take first line as title
                        title_text = title_text.split('\n')[0]
                
                if not title_text or len(title_text.strip()) < 5:
                    continue
                
                # Skip navigation links like "View Job", "Apply Now", etc.
                skip_keywords = ['view job', 'apply now', 'apply', 'learn more', 'read more', 'see details']
                if any(keyword in title_text.lower() for keyword in skip_keywords):
                    continue
                
                # Try to extract job URL
                job_url = None
                try:
                    # Check if element itself is a link
                    href = await element.get_attribute('href')
                    if href:
                        job_url = href
                    else:
                        # Look for link inside element
                        link_elem = await element.query_selector('a')
                        if link_elem:
                            href = await link_elem.get_attribute('href')
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
                    # No URL found, create placeholder
                    job_url = f"https://careers.expediagroup.com/jobs?id={i}"
                
                # Generate job_id
                job_id = f"expedia_{i}"
                if job_url and '/job/' in job_url:
                    import re
                    match = re.search(r'/job/([^/\?]+)', job_url)
                    if match:
                        job_id = f"expedia_{match.group(1)}"
                
                job = {
                    'company': 'expedia',
                    'job_id': job_id,
                    'job_url': job_url,
                    'title': title_text.strip(),
                    'description': f"{title_text.strip()} at Expedia",
                    'salary': None,
                    'posted_date': None
                }
                
                jobs.append(job)
                
                # Small delay between jobs
                if i < len(job_elements) - 1:
                    await asyncio.sleep(0.3)
                    
            except Exception as e:
                logger.warning(f"Error extracting Expedia job {i}: {e}")
                continue
        
        logger.info(f"Found {len(jobs)} Expedia jobs")
        
    except Exception as e:
        logger.error(f"Error scraping Expedia: {e}")
    
    return jobs


if __name__ == "__main__":
    # Run test
    asyncio.run(test_scraper())
