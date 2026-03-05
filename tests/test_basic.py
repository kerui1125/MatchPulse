"""
Basic unit tests for MatchPulse core functionality.

Run with: pytest tests/test_basic.py -v
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import numpy as np
from src.tools.utils import (
    generate_embeddings,
    compute_similarity,
    chunk_resume,
    format_telegram_message,
    validate_match_score,
    get_company_links
)


class TestEmbeddings:
    """Test embedding generation and similarity computation."""
    
    def test_generate_embeddings_single(self):
        """Test generating embedding for single text."""
        texts = ["This is a test sentence"]
        embeddings = generate_embeddings(texts)
        
        assert embeddings.shape == (1, 768), "Embedding shape should be (1, 768)"
        assert np.linalg.norm(embeddings[0]) > 0.99, "Embedding should be normalized"
    
    def test_generate_embeddings_batch(self):
        """Test generating embeddings for multiple texts."""
        texts = ["First sentence", "Second sentence", "Third sentence"]
        embeddings = generate_embeddings(texts)
        
        assert embeddings.shape == (3, 768), "Should generate 3 embeddings"
        assert all(np.linalg.norm(emb) > 0.99 for emb in embeddings), "All embeddings should be normalized"
    
    def test_compute_similarity_self(self):
        """Test that self-similarity is close to 1.0."""
        text = "Machine learning engineer with Python experience"
        embedding = generate_embeddings([text])[0]
        
        similarity = compute_similarity(embedding, embedding)
        assert 0.99 <= similarity <= 1.0, f"Self-similarity should be ~1.0, got {similarity}"
    
    def test_compute_similarity_different(self):
        """Test similarity between different texts."""
        text1 = "Python software engineer"
        text2 = "Java backend developer"
        
        emb1 = generate_embeddings([text1])[0]
        emb2 = generate_embeddings([text2])[0]
        
        similarity = compute_similarity(emb1, emb2)
        assert 0.0 <= similarity <= 1.0, "Similarity should be in [0, 1] range"
        assert similarity < 0.99, "Different texts should have similarity < 0.99"


class TestResumeChunking:
    """Test resume chunking functionality."""
    
    def test_chunk_resume_basic(self):
        """Test basic resume chunking."""
        resume_text = """
        Education
        University of Washington, Seattle
        Bachelor of Science in Computer Science
        
        Experience
        Software Engineer at Google
        Developed machine learning models for search ranking
        
        Skills
        Python, TensorFlow, PyTorch, Docker, Kubernetes
        """
        
        chunks = chunk_resume(resume_text)
        assert len(chunks) > 0, "Should generate at least one chunk"
        assert all(len(chunk) >= 100 for chunk in chunks), "All chunks should be >= 100 chars"
    
    def test_chunk_resume_empty(self):
        """Test chunking empty resume."""
        resume_text = ""
        chunks = chunk_resume(resume_text)
        assert len(chunks) == 0, "Empty resume should produce no chunks"


class TestTelegramFormatting:
    """Test Telegram message formatting."""
    
    def test_format_telegram_message_basic(self):
        """Test basic message formatting."""
        job = {
            'company': 'Google',
            'title': 'Software Engineer',
            'job_url': 'https://careers.google.com/jobs/123',
            'salary': '$150K - $200K',
            'posted_date': '2024-01-15'
        }
        match_score = 0.85
        explanation = "✨ Why this fits:\n- Python experience\n\n💡 Need improvement:\n- More ML experience"
        
        message = format_telegram_message(job, match_score, explanation)
        
        assert '85%' in message, "Should show match percentage"
        assert 'Google' in message, "Should include company name"
        assert 'Software Engineer' in message, "Should include job title"
        assert job['job_url'] in message, "Should include job URL"
        assert explanation in message, "Should include explanation"
    
    def test_format_telegram_message_no_optional_fields(self):
        """Test formatting without optional fields."""
        job = {
            'company': 'Amazon',
            'title': 'ML Engineer',
            'job_url': 'https://amazon.jobs/123'
        }
        match_score = 0.72
        explanation = "Test explanation"
        
        message = format_telegram_message(job, match_score, explanation)
        
        assert 'Amazon' in message, "Should include company"
        assert 'ML Engineer' in message, "Should include title"
        assert message.count('N/A') == 0, "Should not show N/A for missing optional fields"


class TestValidation:
    """Test validation functions."""
    
    def test_validate_match_score_valid(self):
        """Test validation of valid scores."""
        assert validate_match_score(0.5) == 0.5
        assert validate_match_score(0.0) == 0.0
        assert validate_match_score(1.0) == 1.0
    
    def test_validate_match_score_clipping(self):
        """Test that out-of-range scores are clipped."""
        assert validate_match_score(-0.1) == 0.0, "Negative scores should be clipped to 0"
        assert validate_match_score(1.5) == 1.0, "Scores > 1 should be clipped to 1"


class TestConfig:
    """Test configuration loading."""
    
    def test_get_company_links(self):
        """Test loading company links from config."""
        links = get_company_links()
        
        assert isinstance(links, dict), "Should return a dictionary"
        assert len(links) > 0, "Should have at least one company"
        
        # Check that all values are valid URLs
        for company, url in links.items():
            assert url.startswith('http'), f"{company} URL should start with http"


# Run tests with: pytest tests/test_basic.py -v
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
