"""
Fetcher Agent - CrewAI agent for fetching and enriching job postings.

Part of the MatchPulse multi-agent pipeline:
  Fetcher → Matcher → Analyzer → Notifier

USAGE:
  For testing: python src/tools/details_scraper.py
  For pipeline: python src/main.py
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from crewai import Agent, Task, LLM
from crewai.tools import BaseTool
from src.tools.details_scraper import fetch_and_enrich_jobs
from src.tools.utils import setup_logging
import asyncio
import json
from typing import Type
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()
logger = setup_logging()

# Configure Gemini LLM
llm = LLM(
    model="gemini/gemini-2.5-flash",
    api_key=os.getenv("GEMINI_API_KEY")
)


class FetchJobsInput(BaseModel):
    """Input schema for fetch_and_enrich_jobs tool."""
    limit: int = Field(default=None, description="If set, only process first N jobs")


class FetchAndEnrichJobsTool(BaseTool):
    """Tool for fetching and enriching job postings."""
    name: str = "fetch_and_enrich_jobs"
    description: str = "Fetch new jobs from company career pages, scrape details, save to database."
    args_schema: Type[BaseModel] = FetchJobsInput
    
    def _run(self, limit: int = None) -> str:
        """Execute the tool in PRODUCTION mode (saves to database)."""
        logger.info(f"Fetcher Agent: Starting (limit={limit})")
        
        jobs = asyncio.run(fetch_and_enrich_jobs(dry_run=False, limit=limit))
        
        summary = {
            'status': 'success',
            'total_jobs': len(jobs),
            'saved_to_db': True,
            'jobs': [
                {
                    'company': job['company'],
                    'job_id': job['job_id'],
                    'title': job['title'],
                    'job_url': job['job_url'],
                    'description_length': len(job.get('description', '')) if job.get('description') else 0,
                    'has_salary': job.get('salary') is not None,
                    'has_posted_date': job.get('posted_date') is not None
                }
                for job in jobs
            ]
        }
        
        logger.info(f"Fetcher Agent: Completed. Fetched {len(jobs)} jobs")
        return json.dumps(summary, indent=2)


# Tool instance
fetch_and_enrich_jobs_tool = FetchAndEnrichJobsTool()


# Fetcher Agent
fetcher_agent = Agent(
    role='Job Fetcher and Enricher',
    goal='Fetch new job postings, extract full details, and save to database',
    backstory="""Expert web scraper specialized in extracting job postings.
    Efficiently fetches listings, filters duplicates, extracts detailed information,
    and saves to database for the Matcher Agent.""",
    tools=[fetch_and_enrich_jobs_tool],
    llm=llm,
    verbose=True,
    allow_delegation=False
)


# Fetch Task
fetch_task = Task(
    description="""Fetch new job postings from all configured company career pages.
    
    Steps:
    1. Fetch job listings from company career pages
    2. Filter out duplicates (check database)
    3. Scrape full details (description, salary, posted_date)
    4. Save to database with status='fetched'
    5. Return summary for Matcher Agent
    """,
    agent=fetcher_agent,
    expected_output="""JSON object with:
    - status: success/error
    - total_jobs: number of new jobs saved
    - saved_to_db: true
    - jobs: array of job summaries
    """
)


if __name__ == "__main__":
    print("""
⚠️  This is a CrewAI agent interface, not meant to be run standalone.

For testing:  python src/tools/details_scraper.py
For pipeline: python src/main.py
""")
