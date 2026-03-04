import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.agents.fetcher_agent import fetcher_agent, fetch_task
from src.agents.matcher_agent import matcher_agent, match_task
from src.agents.analyzer_agent import analyzer_agent, analyze_task
from src.agents.notifier_agent import notifier_agent, notify_task
from src.tools.utils import setup_logging
import json

logger = setup_logging()


def run_pipeline(limit: int = None, dry_run: bool = False, threshold: float = 0.7, top_k: int = 3):
    """
    Run the MatchPulse pipeline.
    
    Args:
        limit: Limit number of jobs (for testing)
        dry_run: Skip Telegram notifications
        threshold: Match score threshold (0-1)
        top_k: Number of resume chunks to retrieve for RAG (default: 3)
    """
    logger.info("=" * 70)
    logger.info("Starting MatchPulse Pipeline")
    logger.info("=" * 70)
    
    if dry_run:
        logger.info("⚠️  DRY-RUN MODE: No Telegram notifications")
    else:
        logger.info("🔴 PRODUCTION MODE: Telegram notifications enabled")
    
    if limit:
        logger.info(f"⚠️  LIMIT MODE: Processing {limit} jobs")
    
    logger.info(f"📊 Match threshold: {threshold}")
    logger.info(f"🔍 RAG top-k chunks: {top_k}")
    logger.info("=" * 70)
    
    # Week 1: All 4 agents implemented
    logger.info("\n📋 Pipeline Status:")
    logger.info("  ✅ Fetcher Agent  - Implemented")
    logger.info("  ✅ Matcher Agent  - Implemented")
    logger.info("  ✅ Analyzer Agent - Implemented (RAG-based)")
    logger.info("  ✅ Notifier Agent - Implemented (Telegram)\n")
    
    # Step 1: Fetcher Agent
    logger.info("=" * 70)
    logger.info("Step 1: Running Fetcher Agent...")
    logger.info("=" * 70)
    
    from src.agents.fetcher_agent import fetch_and_enrich_jobs_tool
    fetcher_result_json = fetch_and_enrich_jobs_tool._run(limit=limit)
    fetcher_result = json.loads(fetcher_result_json)
    
    logger.info(f"✓ Fetcher completed: {fetcher_result['total_jobs']} jobs fetched")
    
    # Step 2: Matcher Agent
    logger.info("\n" + "=" * 70)
    logger.info("Step 2: Running Matcher Agent...")
    logger.info("=" * 70)
    
    from src.agents.matcher_agent import match_resume_and_jobs_tool
    matcher_result_json = match_resume_and_jobs_tool._run(threshold=threshold)
    matcher_result = json.loads(matcher_result_json)
    
    logger.info(f"✓ Matcher completed: {matcher_result['matched_jobs']}/{matcher_result['total_jobs']} jobs matched")
    
    # Step 3: Analyzer Agent (only if there are matched jobs)
    if matcher_result['matched_jobs'] > 0:
        logger.info("\n" + "=" * 70)
        logger.info("Step 3: Running Analyzer Agent...")
        logger.info("=" * 70)
        
        from src.agents.analyzer_agent import analyze_jobs_tool
        analyzer_result_json = analyze_jobs_tool._run(top_k=top_k)
        analyzer_result = json.loads(analyzer_result_json)
        
        logger.info(f"✓ Analyzer completed: {analyzer_result['analyzed_jobs']}/{analyzer_result['total_jobs']} jobs analyzed")
    else:
        logger.info("\n⚠️  Skipping Analyzer Agent (no matched jobs)")
        analyzer_result = {'status': 'skipped', 'total_jobs': 0, 'analyzed_jobs': 0}
    
    # Step 4: Notifier Agent (only if there are analyzed jobs and not dry-run)
    if analyzer_result['status'] != 'skipped' and analyzer_result['analyzed_jobs'] > 0:
        logger.info("\n" + "=" * 70)
        logger.info("Step 4: Running Notifier Agent...")
        logger.info("=" * 70)
        
        from src.agents.notifier_agent import notify_jobs_tool
        notifier_result_json = notify_jobs_tool._run(dry_run=dry_run)
        notifier_result = json.loads(notifier_result_json)
        
        if dry_run:
            logger.info(f"✓ Notifier completed (DRY-RUN): {notifier_result['notified_jobs']}/{notifier_result['total_jobs']} jobs formatted")
        else:
            logger.info(f"✓ Notifier completed: {notifier_result['notified_jobs']}/{notifier_result['total_jobs']} jobs sent to Telegram")
    else:
        logger.info("\n⚠️  Skipping Notifier Agent (no analyzed jobs)")
        notifier_result = {'status': 'skipped', 'total_jobs': 0, 'notified_jobs': 0}
    
    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("Pipeline Completed")
    logger.info("=" * 70)
    logger.info(f"Fetched: {fetcher_result['total_jobs']} jobs")
    logger.info(f"Matched: {matcher_result['matched_jobs']} jobs (threshold: {threshold})")
    if analyzer_result['status'] != 'skipped':
        logger.info(f"Analyzed: {analyzer_result['analyzed_jobs']} jobs (RAG with top-k={top_k})")
    if notifier_result['status'] != 'skipped':
        if dry_run:
            logger.info(f"Formatted: {notifier_result['notified_jobs']} messages (dry-run)")
        else:
            logger.info(f"Notified: {notifier_result['notified_jobs']} jobs sent to Telegram")
    logger.info("=" * 70)
    
    return {
        'fetcher': fetcher_result,
        'matcher': matcher_result,
        'analyzer': analyzer_result,
        'notifier': notifier_result
    }


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='MatchPulse - AI-Powered Job Matching System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python src/main.py                          # Full pipeline (with Telegram)
  python src/main.py --dry-run                # Test without sending to Telegram
  python src/main.py --limit 10               # Test with limit
  python src/main.py --threshold 0.72         # Adjust match threshold
  python src/main.py --top-k 5                # Use top-5 resume chunks for RAG
  python src/main.py --limit 20 --threshold 0.72 --dry-run
        """
    )
    
    parser.add_argument('--limit', type=int, help='Limit number of jobs')
    parser.add_argument('--dry-run', action='store_true', help='No Telegram notifications')
    parser.add_argument('--threshold', type=float, default=0.7, help='Match score threshold (0-1)')
    parser.add_argument('--top-k', type=int, default=3, help='Number of resume chunks for RAG (default: 3)')
    
    args = parser.parse_args()
    run_pipeline(limit=args.limit, dry_run=args.dry_run, threshold=args.threshold, top_k=args.top_k)


if __name__ == "__main__":
    main()
