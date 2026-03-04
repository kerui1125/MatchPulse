import sqlite3
import json
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

DB_PATH = 'match_pulse.db'


@contextmanager
def get_db_connection():
    """Context manager for database connections to avoid leaks."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Return dict-like rows instead of tuples
    try:
        yield conn
    finally:
        conn.close()


def setup_database():
    """Initialize database schema with tables and indexes."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # 1. Create user_config table (single user for Week 1 MVP)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_links TEXT NOT NULL,
                resume_path TEXT,
                telegram_chat_id TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 2. Create push_history table (dual purpose: tracking + deduplication)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS push_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company TEXT NOT NULL,
                job_id TEXT NOT NULL UNIQUE,
                job_url TEXT NOT NULL,
                title TEXT NOT NULL,
                salary TEXT,
                posted_date TEXT,
                description TEXT,
                match_score REAL,
                pushed_at TEXT DEFAULT CURRENT_TIMESTAMP,
                explanation TEXT,
                status TEXT DEFAULT 'pushed'
            )
        ''')

        # 3. Create indexes for performance
        cursor.execute('''
            CREATE UNIQUE INDEX IF NOT EXISTS idx_job_id 
            ON push_history(job_id)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_pushed_at 
            ON push_history(pushed_at DESC)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_company 
            ON push_history(company)
        ''')

        conn.commit()
        print("Database and tables created successfully.")


# ==================== User Config CRUD ====================

def get_user_config() -> Optional[Dict[str, Any]]:
    """Get user configuration (single user for Week 1 MVP)."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM user_config LIMIT 1')
        row = cursor.fetchone()
        if row:
            return {
                'id': row['id'],
                'company_links': json.loads(row['company_links']),
                'resume_path': row['resume_path'],
                'telegram_chat_id': row['telegram_chat_id'],
                'created_at': row['created_at'],
                'updated_at': row['updated_at']
            }
        return None


def update_user_config(company_links: Dict[str, str], resume_path: Optional[str] = None, 
                       telegram_chat_id: Optional[str] = None) -> int:
    """
    Update or insert user configuration.
    
    Args:
        company_links: Dict of company names to pre-filtered URLs
        resume_path: Path to resume file
        telegram_chat_id: Telegram chat ID for notifications
    
    Returns:
        User config ID
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Check if config exists
        cursor.execute('SELECT id FROM user_config LIMIT 1')
        existing = cursor.fetchone()
        
        company_links_json = json.dumps(company_links)
        
        if existing:
            # Update existing config
            cursor.execute('''
                UPDATE user_config 
                SET company_links = ?, 
                    resume_path = COALESCE(?, resume_path),
                    telegram_chat_id = COALESCE(?, telegram_chat_id),
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (company_links_json, resume_path, telegram_chat_id, existing['id']))
            conn.commit()
            return existing['id']
        else:
            # Insert new config
            cursor.execute('''
                INSERT INTO user_config (company_links, resume_path, telegram_chat_id)
                VALUES (?, ?, ?)
            ''', (company_links_json, resume_path, telegram_chat_id))
            conn.commit()
            return cursor.lastrowid


# ==================== Push History CRUD ====================

def is_job_seen(job_id: str) -> bool:
    """
    Check if a job has been seen before (for deduplication).
    
    Args:
        job_id: Unique job identifier
    
    Returns:
        True if job exists in push_history, False otherwise
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT 1 FROM push_history WHERE job_id = ?', (job_id,))
        return cursor.fetchone() is not None


def insert_job(company: str, job_id: str, job_url: str, title: str, 
               salary: Optional[str] = None, posted_date: Optional[str] = None, 
               description: Optional[str] = None, match_score: Optional[float] = None, 
               explanation: Optional[str] = None, status: str = 'pushed') -> int:
    """
    Insert a new job into push_history.
    
    Args:
        company: Company name
        job_id: Unique job identifier (for deduplication)
        job_url: URL to job posting
        title: Job title
        salary: Salary information (optional)
        posted_date: When job was posted (optional)
        description: Job description text
        match_score: Similarity score (0-1)
        explanation: RAG-generated insights
        status: Job status (default: 'pushed')
    
    Returns:
        Inserted row ID
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO push_history 
            (company, job_id, job_url, title, salary, posted_date, 
             description, match_score, explanation, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (company, job_id, job_url, title, salary, posted_date,
              description, match_score, explanation, status))
        conn.commit()
        return cursor.lastrowid


def get_push_history(page: int = 1, per_page: int = 20, 
                     company: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get push history with pagination.
    
    Args:
        page: Page number (1-indexed)
        per_page: Number of results per page
        company: Filter by company name (optional)
    
    Returns:
        List of job records
    """
    offset = (page - 1) * per_page
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        if company:
            cursor.execute('''
                SELECT * FROM push_history 
                WHERE company = ?
                ORDER BY pushed_at DESC 
                LIMIT ? OFFSET ?
            ''', (company, per_page, offset))
        else:
            cursor.execute('''
                SELECT * FROM push_history 
                ORDER BY pushed_at DESC 
                LIMIT ? OFFSET ?
            ''', (per_page, offset))
        
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_job_count(company: Optional[str] = None) -> int:
    """
    Get total count of jobs in push_history.
    
    Args:
        company: Filter by company name (optional)
    
    Returns:
        Total job count
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        if company:
            cursor.execute('SELECT COUNT(*) as count FROM push_history WHERE company = ?', (company,))
        else:
            cursor.execute('SELECT COUNT(*) as count FROM push_history')
        
        return cursor.fetchone()['count']


def update_job_status(job_id: str, new_status: str) -> bool:
    """
    Update job status (e.g., 'pushed' -> 'archived').
    
    Args:
        job_id: Unique job identifier
        new_status: New status value
    
    Returns:
        True if updated, False if job not found
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE push_history 
            SET status = ? 
            WHERE job_id = ?
        ''', (new_status, job_id))
        conn.commit()
        return cursor.rowcount > 0


def get_job_by_id(job_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a specific job by job_id.
    
    Args:
        job_id: Unique job identifier
    
    Returns:
        Job record or None if not found
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM push_history WHERE job_id = ?', (job_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_jobs_by_status(status: str) -> List[Dict[str, Any]]:
    """
    Get all jobs with a specific status.
    
    Args:
        status: Job status (e.g., 'fetched', 'matched', 'pushed')
    
    Returns:
        List of job records
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM push_history WHERE status = ?', (status,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def update_job_match_score(job_id: str, match_score: float) -> bool:
    """
    Update match_score for a job.
    
    Args:
        job_id: Unique job identifier
        match_score: Similarity score (0-1)
    
    Returns:
        True if updated, False if job not found
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE push_history 
            SET match_score = ? 
            WHERE job_id = ?
        ''', (match_score, job_id))
        conn.commit()
        return cursor.rowcount > 0


def get_jobs_by_threshold(threshold: float) -> List[Dict[str, Any]]:
    """
    Get jobs with match_score above threshold.
    
    Args:
        threshold: Minimum match score (0-1)
    
    Returns:
        List of job records sorted by match_score descending
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM push_history 
            WHERE match_score >= ? 
            ORDER BY match_score DESC
        ''', (threshold,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


if __name__ == "__main__":
    setup_database()
