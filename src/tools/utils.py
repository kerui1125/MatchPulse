import os
import yaml
import logging
import time
import random
import asyncio
import numpy as np
import json
from typing import List, Dict, Optional, Tuple
from pathlib import Path

# Lazy imports for heavy dependencies
_model = None
_faiss = None


def get_embedding_model():
    """Lazy load sentence transformer model to avoid loading on import."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer('all-mpnet-base-v2')
    return _model


def get_faiss():
    """Lazy load faiss to avoid loading on import."""
    global _faiss
    if _faiss is None:
        import faiss
        _faiss = faiss
    return _faiss


# ==================== Resume Processing ====================

def extract_text_from_pdf(file_path: str) -> str:
    """
    Extract text content from PDF file.
    
    Args:
        file_path: Path to PDF file
    
    Returns:
        Extracted text content
    """
    try:
        from pypdf import PdfReader
        
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        
        return text.strip()
    except Exception as e:
        logging.error(f"Error extracting text from PDF {file_path}: {e}")
        raise


def parse_resume(file_path: str) -> str:
    """
    Parse resume file and extract text content.
    Currently supports PDF format.
    
    Args:
        file_path: Path to resume file
    
    Returns:
        Extracted resume text
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Resume file not found: {file_path}")
    
    file_ext = Path(file_path).suffix.lower()
    
    if file_ext == '.pdf':
        return extract_text_from_pdf(file_path)
    else:
        raise ValueError(f"Unsupported file format: {file_ext}. Only PDF is supported.")


# ==================== Embedding & FAISS ====================

def generate_embeddings(texts: List[str]) -> np.ndarray:
    """
    Convert texts to vector embeddings using sentence-transformers.
    
    Args:
        texts: List of text strings to embed
    
    Returns:
        Numpy array of embeddings (normalized)
    """
    model = get_embedding_model()
    embeddings = model.encode(texts, normalize_embeddings=True)
    return embeddings


def compute_similarity(embedding1: np.ndarray, embedding2: np.ndarray) -> float:
    """
    Compute cosine similarity between two embeddings.
    Assumes embeddings are already normalized.
    
    Use this for simple 1-on-1 comparisons (e.g., testing, validation).
    For batch matching (1-to-many), use search_top_matches() instead.
    
    Args:
        embedding1: First embedding vector
        embedding2: Second embedding vector
    
    Returns:
        Similarity score between 0 and 1
    """
    # For normalized vectors, cosine similarity = dot product
    similarity = np.dot(embedding1, embedding2)
    # Ensure score is in [0, 1] range
    # Cosine similarity is in [-1, 1], normalize to [0, 1]
    normalized_score = (similarity + 1) / 2
    return float(np.clip(normalized_score, 0, 1))


def search_top_matches(query_embedding: np.ndarray, corpus_embeddings: np.ndarray, 
                       k: int = 5) -> Tuple[np.ndarray, np.ndarray]:
    """
    Find top-k most similar job embeddings to resume embedding.
    
    This function is used during each scan to match NEW jobs (after deduplication)
    against the user's resume. It does NOT search the entire push_history database.
    
    Implementation note:
    - Creates a temporary FAISS index for each scan (not persisted to disk)
    - This is efficient because we only match against NEW jobs (typically 10-50 per scan)
    - Resume embedding is loaded from disk (saved once, reused many times)
    - Job embeddings are NOT saved (they're only used once for matching)
    
    Typical usage:
        1. Fetcher scrapes new jobs from company URLs
        2. Filter out already-seen jobs (check push_history via job_id)
        3. Generate embeddings for NEW unseen jobs → corpus_embeddings
        4. Load resume embedding → query_embedding
        5. Call this function to find which new jobs match the resume
        6. Filter by threshold (e.g., score > 0.7) and push to Telegram
    
    Args:
        query_embedding: Single embedding vector representing user's resume
        corpus_embeddings: Matrix of embeddings for NEW unseen job descriptions
                          (NOT the entire push_history, only current scan's new jobs)
        k: Number of top matches to return (default: 5)
    
    Returns:
        Tuple of (scores, indices):
            - scores: Normalized similarity scores in [0, 1] range
            - indices: Indices of top-k matches in corpus_embeddings
    """
    faiss = get_faiss()
    dimension = corpus_embeddings.shape[1]
    
    # Create temporary index (not saved to disk)
    index = faiss.IndexFlatIP(dimension)
    index.add(corpus_embeddings.astype('float32'))
    
    # Search for top-k matches using FAISS official API
    # index.search returns (distances, indices) for top-k results
    scores, indices = index.search(
        np.array([query_embedding]).astype('float32'), 
        min(k, len(corpus_embeddings))
    )
    
    # Normalize scores to [0, 1] range
    # IndexFlatIP returns inner product scores (for normalized vectors, this is cosine similarity in [-1, 1])
    normalized_scores = (scores[0] + 1) / 2
    normalized_scores = np.clip(normalized_scores, 0, 1)
    
    return normalized_scores, indices[0]


def validate_match_score(score: float) -> float:
    """
    Ensure match score is in valid [0, 1] range.
    
    Args:
        score: Raw similarity score
    
    Returns:
        Validated score in [0, 1] range
    """
    return float(np.clip(score, 0, 1))


def save_resume_embedding(embedding: np.ndarray, path: str = "data/embeddings/resume_embedding.npy"):
    """
    Save resume embedding to disk for reuse across scans.
    
    Args:
        embedding: Resume embedding vector
        path: File path to save embedding (default: data/embeddings/resume_embedding.npy)
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    np.save(path, embedding)
    logging.info(f"Resume embedding saved to {path}")


def load_resume_embedding(path: str = "data/embeddings/resume_embedding.npy") -> np.ndarray:
    """
    Load resume embedding from disk.
    
    This is used during each scan to compare against new job embeddings.
    The resume embedding is generated once when user uploads resume,
    then reused for all subsequent scans.
    
    Args:
        path: File path to load embedding from (default: data/embeddings/resume_embedding.npy)
    
    Returns:
        Resume embedding vector
    
    Raises:
        FileNotFoundError: If resume embedding file doesn't exist
    """
    # Try new path first, fallback to old path for backward compatibility
    if not os.path.exists(path):
        old_path = "data/faiss_indices/resume_embedding.npy"
        if os.path.exists(old_path):
            logging.warning(f"Using old path: {old_path}. Consider moving to {path}")
            path = old_path
        else:
            raise FileNotFoundError(
                f"Resume embedding not found at {path}. "
                "Please upload and process resume first."
            )
    
    embedding = np.load(path)
    logging.info(f"Resume embedding loaded from {path}")
    return embedding


def chunk_resume(resume_text: str) -> List[str]:
    """
    Chunk resume into meaningful sections.
    
    Strategy:
    - Split by double newlines (paragraphs)
    - Each paragraph is a chunk
    - This is flexible and works with any resume format
    
    Args:
        resume_text: Full resume text
    
    Returns:
        List of resume text chunks
    """
    # Split by double newlines (paragraphs)
    paragraphs = resume_text.split('\n\n')
    
    # Clean and filter chunks
    chunks = []
    for para in paragraphs:
        para = para.strip()
        # Keep chunks with substantial content (at least 100 chars)
        if len(para) >= 100:
            chunks.append(para)
    
    # If no good chunks found, split by single newlines and group
    if len(chunks) < 3:
        lines = resume_text.split('\n')
        current_chunk = []
        
        for line in lines:
            current_chunk.append(line)
            # Create chunk every 8 lines
            if len(current_chunk) >= 8:
                chunk_text = '\n'.join(current_chunk).strip()
                if len(chunk_text) >= 100:
                    chunks.append(chunk_text)
                current_chunk = []
        
        # Add remaining lines
        if current_chunk:
            chunk_text = '\n'.join(current_chunk).strip()
            if len(chunk_text) >= 100:
                chunks.append(chunk_text)
    
    logging.info(f"Resume chunking: {len(chunks)} chunks created")
    for i, chunk in enumerate(chunks):
        logging.debug(f"Chunk {i+1}: {len(chunk)} chars, starts with: {chunk[:50]}...")
    
    return chunks


def save_resume_chunks(chunks: List[str], embeddings: np.ndarray):
    """
    Save resume chunks and their embeddings.
    
    Args:
        chunks: List of resume text chunks
        embeddings: 2D numpy array of chunk embeddings (shape: [n_chunks, embedding_dim])
    """
    os.makedirs("data/embeddings", exist_ok=True)
    
    # Save chunks text
    with open('data/embeddings/resume_chunks.json', 'w', encoding='utf-8') as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)
    
    # Save embeddings
    np.save('data/embeddings/resume_chunks_embeddings.npy', embeddings)
    
    logging.info(f"Saved {len(chunks)} resume chunks and embeddings")


def load_resume_chunks() -> Tuple[List[str], np.ndarray]:
    """
    Load resume chunks and their embeddings.
    
    Returns:
        Tuple of (chunks, embeddings)
        - chunks: List of resume text chunks
        - embeddings: 2D numpy array of chunk embeddings
    """
    chunks_file = 'data/embeddings/resume_chunks.json'
    embeddings_file = 'data/embeddings/resume_chunks_embeddings.npy'
    
    if not os.path.exists(chunks_file) or not os.path.exists(embeddings_file):
        raise FileNotFoundError("Resume chunks not found. Run preprocessing first.")
    
    # Load chunks text
    with open(chunks_file, 'r', encoding='utf-8') as f:
        chunks = json.load(f)
    
    # Load embeddings
    embeddings = np.load(embeddings_file)
    
    logging.info(f"Loaded {len(chunks)} resume chunks and embeddings")
    return chunks, embeddings


def resume_chunks_exist() -> bool:
    """Check if resume chunks and embeddings exist."""
    return (os.path.exists('data/embeddings/resume_chunks.json') and 
            os.path.exists('data/embeddings/resume_chunks_embeddings.npy'))


def save_job_embedding(job_id: str, embedding: np.ndarray):
    """
    Save job embedding to disk.
    
    Args:
        job_id: Unique job identifier
        embedding: 1D numpy array of job embedding
    """
    os.makedirs('data/embeddings/job_embeddings', exist_ok=True)
    file_path = f'data/embeddings/job_embeddings/{job_id}.npy'
    np.save(file_path, embedding)
    logging.debug(f"Job embedding saved: {job_id}")


def load_job_embedding(job_id: str) -> np.ndarray:
    """
    Load job embedding from disk.
    
    Args:
        job_id: Unique job identifier
    
    Returns:
        1D numpy array of job embedding
    """
    file_path = f'data/embeddings/job_embeddings/{job_id}.npy'
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Job embedding not found: {job_id}")
    
    return np.load(file_path)


def job_embedding_exists(job_id: str) -> bool:
    """Check if job embedding exists."""
    return os.path.exists(f'data/embeddings/job_embeddings/{job_id}.npy')


# ==================== Config Management ====================

def load_config(config_path: str = "src/config/config.yaml") -> Dict:
    """
    Load configuration from YAML file.
    
    Args:
        config_path: Path to config.yaml file
    
    Returns:
        Configuration dictionary
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    return config


def get_company_links(config_path: str = "src/config/config.yaml") -> Dict[str, str]:
    """
    Get company career page links from config.
    
    Args:
        config_path: Path to config.yaml file
    
    Returns:
        Dictionary of company names to URLs
    """
    config = load_config(config_path)
    return config.get('links', {})


# ==================== Telegram Notifications ====================

def format_telegram_message(job: Dict, match_score: float, explanation: str) -> str:
    """
    Format job data into Telegram message according to design doc format.
    
    Args:
        job: Job data dictionary with keys: company, title, location, salary, 
             posted_date, job_url
        match_score: Match score (0-1)
        explanation: RAG-generated explanation text
    
    Returns:
        Formatted message string
    """
    # Convert match score to percentage
    match_percentage = int(match_score * 100)
    
    message = f"🎯 New Job Match (Match: {match_percentage}%)\n\n"
    message += f"📍 Company: {job.get('company', 'N/A')}\n"
    message += f"💼 Position: {job.get('title', 'N/A')}\n"
    
    # Optional fields
    if job.get('salary'):
        message += f"💰 Salary: {job['salary']}\n"
    
    message += f"\n{explanation}\n"
    message += f"\n🔗 Apply Now: {job.get('job_url', 'N/A')}\n"
    
    # Optional posted date
    if job.get('posted_date'):
        message += f"\n---\nPosted: {job['posted_date']}"
    
    return message


async def send_telegram_message(chat_id: str, message: str, bot_token: str) -> bool:
    """
    Send a message via Telegram Bot API (async).
    Uses python-telegram-bot library (same as tested in main.py).
    
    Args:
        chat_id: Telegram chat ID
        message: Message text to send
        bot_token: Telegram bot token
    
    Returns:
        True if successful, False otherwise
    """
    try:
        from telegram import Bot
        
        bot = Bot(token=bot_token)
        await bot.send_message(chat_id=chat_id, text=message)
        
        logging.info(f"Telegram message sent successfully to chat {chat_id}")
        return True
        
    except Exception as e:
        logging.error(f"Error sending Telegram message: {e}")
        return False


async def send_with_rate_limit(messages: List[str], chat_id: str, bot_token: str, 
                                delay: float = 1.5) -> int:
    """
    Send multiple Telegram messages with rate limiting (async).
    
    Args:
        messages: List of message strings to send
        chat_id: Telegram chat ID
        bot_token: Telegram bot token
        delay: Delay in seconds between messages (default: 1.5s)
    
    Returns:
        Number of successfully sent messages
    """
    success_count = 0
    
    for i, message in enumerate(messages):
        if await send_telegram_message(chat_id, message, bot_token):
            success_count += 1
        
        # Add delay between messages (except after last message)
        if i < len(messages) - 1:
            await asyncio.sleep(delay)
    
    logging.info(f"Sent {success_count}/{len(messages)} Telegram messages")
    return success_count


# ==================== Logging ====================

def setup_logging(log_file: str = "app.log", level: int = logging.INFO) -> logging.Logger:
    """
    Setup logging configuration.
    
    Args:
        log_file: Path to log file
        level: Logging level (default: INFO)
    
    Returns:
        Logger instance
    """
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger("MatchPulse")


# ==================== Utilities ====================

def random_sleep(min_sec: float = 1, max_sec: float = 3):
    """
    Sleep for a random duration to avoid rate limiting.
    
    Args:
        min_sec: Minimum sleep duration in seconds
        max_sec: Maximum sleep duration in seconds
    """
    sleep_time = random.uniform(min_sec, max_sec)
    time.sleep(sleep_time)


def ensure_directory(path: str):
    """
    Ensure directory exists, create if it doesn't.
    
    Args:
        path: Directory path
    """
    os.makedirs(path, exist_ok=True)
