"""
Matcher Agent - Semantic matching between resume and job descriptions.

Part of the MatchPulse multi-agent pipeline:
  Fetcher → Matcher → Analyzer → Notifier

USAGE:
  For testing: python src/agents/matcher_agent.py
  For pipeline: python src/main.py
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from crewai import Agent, Task, LLM
from crewai.tools import BaseTool
from src.tools.utils import load_resume_embedding, generate_embeddings, compute_similarity, setup_logging, save_job_embedding, job_embedding_exists
from src.tools.db import get_jobs_by_status, update_job_match_score, update_job_status, get_jobs_by_threshold
import json
from typing import Type
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()
logger = setup_logging()

# Configure Gemini LLM (required by CrewAI Agent, even though we don't use it for matching)
llm = LLM(
    model="gemini/gemini-2.5-flash",
    api_key=os.getenv("GEMINI_API_KEY")
)
logger = setup_logging()


class MatchJobsInput(BaseModel):
    """Input schema for match_resume_and_jobs tool."""
    threshold: float = Field(default=0.7, description="Minimum match score (0-1) to consider a job matched")


class MatchResumeAndJobsTool(BaseTool):
    """
    Tool for matching jobs with resume using semantic similarity.
    
    This tool:
    1. Loads resume embedding from disk
    2. Gets jobs with status='fetched' from database
    3. Generates embeddings for each job description
    4. Computes cosine similarity between resume and job
    5. Updates match_score in database
    6. Filters jobs above threshold
    7. Updates status to 'matched' for high-match jobs
    """
    name: str = "match_resume_and_jobs"
    description: str = "Match fetched jobs with resume using semantic similarity. Returns high-match jobs."
    args_schema: Type[BaseModel] = MatchJobsInput
    
    def _run(self, threshold: float = 0.7) -> str:
        """Execute semantic matching."""
        logger.info(f"Matcher Agent: Starting (threshold={threshold})")
        
        # 1. Load resume embedding
        try:
            resume_embedding = load_resume_embedding()
            logger.info(f"✓ Loaded resume embedding (shape: {resume_embedding.shape})")
        except Exception as e:
            logger.error(f"✗ Failed to load resume embedding: {e}")
            return json.dumps({'status': 'error', 'message': 'Resume embedding not found'})
        
        # 2. Get jobs with status='fetched'
        jobs = get_jobs_by_status('fetched')
        logger.info(f"✓ Found {len(jobs)} jobs with status='fetched'")
        
        if not jobs:
            logger.info("⚠️  No jobs to match")
            return json.dumps({'status': 'success', 'total_jobs': 0, 'matched_jobs': 0, 'jobs': []})
        
        # 3. Compute similarity for each job
        logger.info("🔍 Computing similarities...")
        matched_count = 0
        
        for i, job in enumerate(jobs):
            try:
                # Skip if no description
                if not job.get('description'):
                    logger.warning(f"[{i+1}/{len(jobs)}] {job['job_id']}: No description, skipping")
                    continue
                
                # Generate job embedding (and save for Analyzer Agent)
                job_embedding = generate_embeddings([job['description']])[0]
                save_job_embedding(job['job_id'], job_embedding)
                logger.debug(f"✓ Saved job embedding: {job['job_id']}")
                
                # Compute similarity
                score = float(compute_similarity(resume_embedding, job_embedding))
                
                # Update database
                update_job_match_score(job['job_id'], score)
                
                # Log result
                match_status = "✓ MATCH" if score >= threshold else "○"
                logger.info(f"[{i+1}/{len(jobs)}] {match_status} {job['company']} - {job['title'][:40]}... (score: {score:.3f})")
                
                if score >= threshold:
                    matched_count += 1
                
            except Exception as e:
                logger.error(f"✗ Error processing {job['job_id']}: {e}")
                continue
        
        # 4. Get high-match jobs
        matched_jobs = get_jobs_by_threshold(threshold)
        logger.info(f"✓ Found {len(matched_jobs)} jobs above threshold {threshold}")
        
        # 5. Update status: 'matched' for high-match, 'not_matched' for low-match
        matched_job_ids = {job['job_id'] for job in matched_jobs}
        
        for job in jobs:
            if job['job_id'] in matched_job_ids:
                update_job_status(job['job_id'], 'matched')
            else:
                update_job_status(job['job_id'], 'not_matched')
        
        logger.info(f"✓ Updated {len(matched_jobs)} jobs to status='matched'")
        logger.info(f"✓ Updated {len(jobs) - len(matched_jobs)} jobs to status='not_matched'")
        
        # 6. Prepare summary
        summary = {
            'status': 'success',
            'total_jobs': len(jobs),
            'matched_jobs': len(matched_jobs),
            'threshold': threshold,
            'jobs': [
                {
                    'company': job['company'],
                    'job_id': job['job_id'],
                    'title': job['title'],
                    'job_url': job['job_url'],
                    'match_score': job['match_score']
                }
                for job in matched_jobs
            ]
        }
        
        logger.info(f"Matcher Agent: Completed. Matched {len(matched_jobs)}/{len(jobs)} jobs")
        return json.dumps(summary, indent=2)


# Tool instance
match_resume_and_jobs_tool = MatchResumeAndJobsTool()


# Matcher Agent (no LLM needed - pure math, but CrewAI requires it)
matcher_agent = Agent(
    role='Resume-Job Matcher',
    goal='Match jobs with resume using semantic similarity and filter high-quality matches',
    backstory="""Expert in semantic similarity and natural language processing.
    You analyze job descriptions and resumes to find the best matches using
    state-of-the-art embedding models and cosine similarity.""",
    tools=[match_resume_and_jobs_tool],
    llm=llm,
    verbose=True,
    allow_delegation=False
)


# Match Task
match_task = Task(
    description="""Match fetched jobs with resume using semantic similarity.
    
    Steps:
    1. Load resume embedding from disk
    2. Get jobs with status='fetched' from database
    3. Generate embeddings for each job description
    4. Compute cosine similarity scores
    5. Update match_score in database
    6. Filter jobs above threshold (default: 0.7)
    7. Update status: 'matched' for high-match jobs, 'not_matched' for low-match jobs
    8. Return list of matched jobs for Analyzer Agent
    
    Status flow:
    - fetched → matched (score >= threshold)
    - fetched → not_matched (score < threshold)
    - matched → pushed (after notification sent)
    - not_matched → stays as not_matched
    """,
    agent=matcher_agent,
    expected_output="""JSON object with:
    - status: success/error
    - total_jobs: number of jobs processed
    - matched_jobs: number of high-match jobs
    - threshold: similarity threshold used
    - jobs: array of matched job summaries with scores
    """
)


def test_matcher_agent(threshold: float = 0.7):
    """Test the matcher agent standalone."""
    print("\n" + "=" * 70)
    print("Testing Matcher Agent")
    print("=" * 70)
    print(f"Threshold: {threshold}")
    print("=" * 70 + "\n")
    
    # Call the tool directly
    result_json = match_resume_and_jobs_tool._run(threshold=threshold)
    result = json.loads(result_json)
    
    # Print summary
    print("\n" + "=" * 70)
    print("📊 Matcher Agent Results")
    print("=" * 70)
    print(f"Status: {result['status']}")
    print(f"Total jobs: {result['total_jobs']}")
    print(f"Matched jobs: {result['matched_jobs']}")
    print(f"Threshold: {result['threshold']}")
    print("=" * 70)
    
    if result.get('jobs'):
        print(f"\n📋 Matched jobs:\n")
        for i, job in enumerate(result['jobs'], 1):
            print(f"{i}. [{job['match_score']:.3f}] {job['company'].upper()}: {job['title']}")
            print(f"   URL: {job['job_url']}")
            print()
    else:
        print("\n⚠️  No jobs matched above threshold")
    
    print("=" * 70)
    
    return result


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Test Matcher Agent')
    parser.add_argument('--threshold', type=float, default=0.7, help='Match score threshold (0-1)')
    args = parser.parse_args()
    
    test_matcher_agent(threshold=args.threshold)
