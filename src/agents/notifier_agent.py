"""
Notifier Agent - Send Telegram notifications for matched jobs.

Part of the MatchPulse multi-agent pipeline:
  Fetcher → Matcher → Analyzer → Notifier

USAGE:
  For testing: python src/agents/notifier_agent.py
  For pipeline: python src/main.py
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from crewai import Agent, Task, LLM
from crewai.tools import BaseTool
from src.tools.utils import format_telegram_message, send_telegram_message, setup_logging
from src.tools.db import get_jobs_by_status, update_job_status
import json
import asyncio
from typing import Type, List
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()
logger = setup_logging()

# Configure Gemini LLM (required by CrewAI, though not used for notifications)
llm = LLM(
    model="gemini/gemini-3-flash-preview",
    api_key=os.getenv("GEMINI_API_KEY")
)


class NotifyJobsInput(BaseModel):
    """Input schema for notify_jobs tool."""
    dry_run: bool = Field(default=False, description="If True, skip actual Telegram sending (for testing)")


class NotifyJobsTool(BaseTool):
    """
    Tool for sending Telegram notifications for matched jobs.
    
    This tool:
    1. Gets jobs with status='matched' and explanation IS NOT NULL
    2. Formats each job into Telegram message
    3. Sends to Telegram with rate limiting (1.5 sec delay between messages)
    4. Updates status to 'pushed' after successful send
    5. Handles errors with logging
    """
    name: str = "notify_jobs"
    description: str = "Send Telegram notifications for matched jobs with personalized insights."
    args_schema: Type[BaseModel] = NotifyJobsInput
    
    def _run(self, dry_run: bool = False) -> str:
        """Execute Telegram notifications."""
        logger.info(f"Notifier Agent: Starting (dry_run={dry_run})")
        
        # Get Telegram credentials
        telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
        telegram_bot_token = os.getenv("TELEGRAM_TOKEN")  # Note: .env uses TELEGRAM_TOKEN
        
        if not dry_run and (not telegram_chat_id or not telegram_bot_token):
            logger.error("✗ Telegram credentials not found in .env")
            return json.dumps({'status': 'error', 'message': 'Missing Telegram credentials'})
        
        # 1. Get matched jobs with explanations
        matched_jobs = get_jobs_by_status('matched')
        logger.info(f"✓ Found {len(matched_jobs)} jobs with status='matched'")
        
        # Filter jobs that have explanations
        jobs_to_notify = [job for job in matched_jobs if job.get('explanation')]
        logger.info(f"✓ {len(jobs_to_notify)} jobs have explanations (ready to notify)")
        
        if not jobs_to_notify:
            logger.info("⚠️  No jobs to notify")
            return json.dumps({'status': 'success', 'total_jobs': 0, 'notified_jobs': 0, 'jobs': []})
        
        # 2. Send notifications
        if dry_run:
            logger.info("🔵 DRY-RUN MODE: Skipping actual Telegram sends")
            notified_jobs = self._dry_run_notify(jobs_to_notify)
        else:
            logger.info("📤 Sending Telegram notifications...")
            notified_jobs = self._send_notifications(jobs_to_notify, telegram_chat_id, telegram_bot_token)
        
        logger.info(f"Notifier Agent: Completed. Notified {len(notified_jobs)}/{len(jobs_to_notify)} jobs")
        
        # 3. Prepare summary
        summary = {
            'status': 'success',
            'total_jobs': len(jobs_to_notify),
            'notified_jobs': len(notified_jobs),
            'dry_run': dry_run,
            'jobs': notified_jobs
        }
        
        return json.dumps(summary, indent=2)
    
    def _dry_run_notify(self, jobs: List[dict]) -> List[dict]:
        """Dry-run mode: format messages but don't send."""
        notified = []
        
        for i, job in enumerate(jobs):
            try:
                # Format message
                message = format_telegram_message(
                    job=job,
                    match_score=job.get('match_score', 0),
                    explanation=job.get('explanation', '')
                )
                
                logger.info(f"[{i+1}/{len(jobs)}] 🔵 DRY-RUN: {job['company']} - {job['title'][:40]}...")
                logger.debug(f"Message preview:\n{message[:200]}...")
                
                notified.append({
                    'company': job['company'],
                    'job_id': job['job_id'],
                    'title': job['title'],
                    'match_score': job.get('match_score', 0),
                    'message_length': len(message)
                })
                
            except Exception as e:
                logger.error(f"✗ Error formatting message for {job['job_id']}: {e}")
                continue
        
        return notified
    
    def _send_notifications(self, jobs: List[dict], chat_id: str, bot_token: str) -> List[dict]:
        """Send actual Telegram notifications with rate limiting."""
        notified = []
        
        for i, job in enumerate(jobs):
            try:
                # Format message
                message = format_telegram_message(
                    job=job,
                    match_score=job.get('match_score', 0),
                    explanation=job.get('explanation', '')
                )
                
                logger.info(f"[{i+1}/{len(jobs)}] 📤 Sending: {job['company']} - {job['title'][:40]}...")
                
                # Send to Telegram (async)
                success = asyncio.run(send_telegram_message(chat_id, message, bot_token))
                
                if success:
                    # Update status to 'pushed'
                    update_job_status(job['job_id'], 'pushed')
                    logger.info(f"✓ Sent and updated status to 'pushed'")
                    
                    notified.append({
                        'company': job['company'],
                        'job_id': job['job_id'],
                        'title': job['title'],
                        'match_score': job.get('match_score', 0),
                        'status': 'sent'
                    })
                else:
                    logger.warning(f"⚠️  Failed to send notification for {job['job_id']}")
                
                # Rate limiting: 1.5 second delay between messages
                if i < len(jobs) - 1:  # Don't delay after last message
                    asyncio.run(asyncio.sleep(1.5))
                
            except Exception as e:
                logger.error(f"✗ Error notifying {job['job_id']}: {e}")
                continue
        
        return notified


# Tool instance
notify_jobs_tool = NotifyJobsTool()


# Notifier Agent
notifier_agent = Agent(
    role='Telegram Notification Manager',
    goal='Send personalized job notifications to users via Telegram with rate limiting',
    backstory="""Expert in messaging systems and user engagement.
    You ensure timely, well-formatted notifications reach users without overwhelming them.
    You handle rate limits gracefully and track delivery status.""",
    tools=[notify_jobs_tool],
    llm=llm,
    verbose=True,
    allow_delegation=False
)


# Notify Task
notify_task = Task(
    description="""Send Telegram notifications for matched jobs with personalized insights.
    
    Steps:
    1. Get jobs with status='matched' and explanation IS NOT NULL
    2. Format each job into Telegram message with:
       - Company, title, location, salary (if available)
       - Match score
       - Personalized insights (Why this fits + Need improvement)
       - Apply link
    3. Send to Telegram with rate limiting (1.5 sec delay between messages)
    4. Update status to 'pushed' after successful send
    5. Handle errors and log results
    
    Status flow:
    - matched → pushed (after successful notification)
    - matched → stays matched (if notification fails)
    """,
    agent=notifier_agent,
    expected_output="""JSON object with:
    - status: success/error
    - total_jobs: number of jobs ready to notify
    - notified_jobs: number of jobs successfully notified
    - dry_run: whether this was a dry-run
    - jobs: array of notified job summaries
    """
)


def test_notifier_agent(dry_run: bool = True):
    """Test the notifier agent standalone."""
    print("\n" + "=" * 70)
    print("Testing Notifier Agent")
    print("=" * 70)
    print(f"Dry-run mode: {dry_run}")
    print("=" * 70 + "\n")
    
    # Call the tool directly
    result_json = notify_jobs_tool._run(dry_run=dry_run)
    result = json.loads(result_json)
    
    # Print summary
    print("\n" + "=" * 70)
    print("📊 Notifier Agent Results")
    print("=" * 70)
    print(f"Status: {result['status']}")
    
    if result['status'] == 'error':
        print(f"Error: {result.get('message', 'Unknown error')}")
    else:
        print(f"Total jobs: {result.get('total_jobs', 0)}")
        print(f"Notified jobs: {result.get('notified_jobs', 0)}")
        print(f"Dry-run: {result.get('dry_run', False)}")
    
    print("=" * 70)
    
    if result.get('jobs'):
        print(f"\n📋 Notified jobs:\n")
        for i, job in enumerate(result['jobs'], 1):
            print(f"{i}. [{job.get('match_score', 0):.3f}] {job['company'].upper()}: {job['title']}")
            if 'message_length' in job:
                print(f"   Message length: {job['message_length']} chars")
            print()
    else:
        print("\n⚠️  No jobs notified")
    
    print("=" * 70)
    
    return result


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Test Notifier Agent')
    parser.add_argument('--send', action='store_true', help='Actually send to Telegram (default: dry-run)')
    args = parser.parse_args()
    
    test_notifier_agent(dry_run=not args.send)

    