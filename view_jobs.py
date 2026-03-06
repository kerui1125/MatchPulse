#!/usr/bin/env python3
"""
Quick script to view jobs in database with nice formatting.
"""
import sqlite3
import sys

def view_jobs(status=None, limit=None, simple=False):
    """View jobs from database with nice formatting."""
    conn = sqlite3.connect('match_pulse.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Build query
    if status:
        query = "SELECT * FROM push_history WHERE status = ? ORDER BY match_score DESC"
        cursor.execute(query, (status,))
    else:
        query = "SELECT * FROM push_history ORDER BY match_score DESC"
        if limit:
            query += f" LIMIT {limit}"
        cursor.execute(query)
    
    jobs = cursor.fetchall()
    conn.close()
    
    if not jobs:
        print("No jobs found.")
        return
    
    print("\n" + "=" * 100)
    print(f"Found {len(jobs)} jobs")
    print("=" * 100 + "\n")
    
    if simple:
        # Simple mode: just score, status, company, and title
        for i, job in enumerate(jobs, 1):
            status_emoji = {
                'pushed': '✅',
                'matched': '🎯',
                'fetched': '📥',
                'not_matched': '❌'
            }.get(job['status'], '❓')
            
            print(f"{i:2d}. [{job['match_score']:.3f}] {status_emoji} {job['company']:15s} | {job['title']}")
    else:
        # Detailed mode
        for i, job in enumerate(jobs, 1):
            print(f"{i}. [{job['match_score']:.3f}] {job['status'].upper()}")
            print(f"   Company: {job['company']}")
            print(f"   Title: {job['title']}")
            print(f"   URL: {job['job_url']}")
            
            if job['explanation']:
                print(f"\n   Explanation:")
                # Print explanation with indentation
                for line in job['explanation'].split('\n'):
                    if line.strip():
                        print(f"   {line}")
            
            print("\n" + "-" * 100 + "\n")


def view_summary():
    """View summary statistics."""
    conn = sqlite3.connect('match_pulse.db')
    cursor = conn.cursor()
    
    # Status counts
    cursor.execute("SELECT status, COUNT(*) as count FROM push_history GROUP BY status")
    status_counts = cursor.fetchall()
    
    # Score distribution
    cursor.execute("""
        SELECT 
            CASE 
                WHEN match_score >= 0.8 THEN '0.80+'
                WHEN match_score >= 0.75 THEN '0.75-0.79'
                WHEN match_score >= 0.70 THEN '0.70-0.74'
                WHEN match_score >= 0.65 THEN '0.65-0.69'
                WHEN match_score >= 0.60 THEN '0.60-0.64'
                ELSE '<0.60'
            END as score_range,
            COUNT(*) as count
        FROM push_history
        GROUP BY score_range
        ORDER BY score_range DESC
    """)
    score_dist = cursor.fetchall()
    
    # Top companies
    cursor.execute("""
        SELECT company, COUNT(*) as count, AVG(match_score) as avg_score
        FROM push_history
        GROUP BY company
        ORDER BY count DESC
    """)
    companies = cursor.fetchall()
    
    conn.close()
    
    print("\n" + "=" * 80)
    print("DATABASE SUMMARY")
    print("=" * 80)
    
    print("\n📊 Status Distribution:")
    for status, count in status_counts:
        print(f"   {status}: {count}")
    
    print("\n📈 Score Distribution:")
    for score_range, count in score_dist:
        print(f"   {score_range}: {count}")
    
    print("\n🏢 Companies:")
    for company, count, avg_score in companies:
        print(f"   {company}: {count} jobs (avg score: {avg_score:.3f})")
    
    print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='View jobs from database')
    parser.add_argument('--status', choices=['fetched', 'matched', 'pushed', 'not_matched'], 
                        help='Filter by status')
    parser.add_argument('--limit', type=int, help='Limit number of results')
    parser.add_argument('--summary', action='store_true', help='Show summary statistics')
    parser.add_argument('--simple', action='store_true', help='Simple mode: just score and title')
    
    args = parser.parse_args()
    
    if args.summary:
        view_summary()
    else:
        view_jobs(status=args.status, limit=args.limit, simple=args.simple)
