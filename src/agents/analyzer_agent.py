"""
Analyzer Agent - RAG-based personalized job insights generation.

Part of the MatchPulse multi-agent pipeline:
  Fetcher → Matcher → Analyzer → Notifier

Uses RAG (Retrieval-Augmented Generation) to reduce LLM hallucinations:
1. Chunk resume into sections
2. Retrieve most relevant sections for each job
3. Generate insights based ONLY on retrieved sections

USAGE:
  For testing: python src/agents/analyzer_agent.py
  For pipeline: python src/main.py
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from crewai import Agent, Task, LLM
from crewai.tools import BaseTool
from src.tools.utils import parse_resume, generate_embeddings, setup_logging, search_top_matches, save_resume_chunks, load_resume_chunks, resume_chunks_exist, load_job_embedding, job_embedding_exists, chunk_resume
from src.tools.db import get_jobs_by_status
import json
import numpy as np
from typing import Type, List, Tuple
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import sqlite3

load_dotenv()
logger = setup_logging()

# Configure Gemini LLM
llm = LLM(
    model="gemini/gemini-3-flash-preview",
    api_key=os.getenv("GEMINI_API_KEY")
)


class AnalyzeJobsInput(BaseModel):
    """Input schema for analyze_jobs tool."""
    top_k: int = Field(default=3, description="Number of resume chunks to retrieve per job")


class AnalyzeJobsTool(BaseTool):
    """
    Tool for generating personalized job insights using RAG.
    
    RAG Process:
    1. Chunk resume into sections (Education, Experience, Skills, etc.)
    2. Generate embeddings for each chunk
    3. For each matched job:
       - Generate job description embedding
       - Retrieve top-k most relevant resume chunks
       - Generate insights using ONLY retrieved chunks (reduces hallucination)
    4. Update explanation field in database
    """
    name: str = "analyze_jobs"
    description: str = "Generate personalized insights for matched jobs using RAG to reduce hallucinations."
    args_schema: Type[BaseModel] = AnalyzeJobsInput
    
    def _run(self, top_k: int = 3) -> str:
        """Execute RAG-based analysis."""
        logger.info(f"Analyzer Agent: Starting (RAG with top_k={top_k})")
        
        # 1. Get matched jobs
        matched_jobs = get_jobs_by_status('matched')
        logger.info(f"✓ Found {len(matched_jobs)} jobs with status='matched'")
        
        if not matched_jobs:
            logger.info("⚠️  No matched jobs to analyze")
            return json.dumps({'status': 'success', 'total_jobs': 0, 'analyzed_jobs': 0, 'jobs': []})
        
        # 2. Load or generate resume chunks
        try:
            if resume_chunks_exist():
                # Load cached chunks and embeddings
                resume_chunks, chunk_embeddings = load_resume_chunks()
                logger.info(f"✓ Loaded cached resume chunks ({len(resume_chunks)} chunks)")
            else:
                # Generate and cache for first time
                resume_text = parse_resume(file_path="data/resumes/Kerui Liu Resume - sde - FullStack.pdf")
                logger.info(f"✓ Loaded resume ({len(resume_text)} chars)")
                
                resume_chunks = chunk_resume(resume_text)
                logger.info(f"✓ Chunked resume into {len(resume_chunks)} sections")
                
                # Generate embeddings for all chunks
                chunk_embeddings = generate_embeddings(resume_chunks)
                logger.info(f"✓ Generated embeddings for resume chunks")
                
                # Save for future use
                save_resume_chunks(resume_chunks, chunk_embeddings)
                logger.info(f"✓ Cached resume chunks for future use")
            
        except Exception as e:
            logger.error(f"✗ Failed to process resume: {e}")
            return json.dumps({'status': 'error', 'message': 'Resume processing failed'})
        
        # 3. Generate insights for each job using RAG
        logger.info("🤖 Generating RAG-based insights...")
        analyzed_jobs = []
        
        for i, job in enumerate(matched_jobs):
            try:
                logger.info(f"[{i+1}/{len(matched_jobs)}] Analyzing: {job['company']} - {job['title'][:40]}...")
                
                # RAG: Retrieve relevant resume chunks
                relevant_chunks = self._retrieve_relevant_chunks(
                    job_id=job['job_id'],
                    job_description=job.get('description', ''),
                    resume_chunks=resume_chunks,
                    chunk_embeddings=chunk_embeddings,
                    top_k=top_k
                )
                
                logger.info(f"✓ Retrieved {len(relevant_chunks)} relevant resume sections")
                
                # Generate insights using ONLY retrieved chunks
                explanation = self._generate_insights_with_rag(
                    relevant_resume_chunks=relevant_chunks,
                    job_title=job['title'],
                    job_description=job.get('description', ''),
                    company=job['company'],
                    match_score=job.get('match_score', 0)
                )
                
                # Update database
                self._update_job_explanation(job['job_id'], explanation)
                
                analyzed_jobs.append({
                    'company': job['company'],
                    'job_id': job['job_id'],
                    'title': job['title'],
                    'match_score': job.get('match_score', 0),
                    'explanation': explanation
                })
                
                logger.info(f"✓ Generated RAG-based insights ({len(explanation)} chars)")
                
                # Rate limiting: Add delay between LLM calls to avoid hitting API limits
                # Even with upgraded plan, rapid consecutive calls can trigger rate limits
                if i < len(matched_jobs) - 1:  # Don't sleep after last job
                    import time
                    time.sleep(1.0)  # 1 second delay between jobs
                    logger.debug(f"⏱️  Rate limit delay (1.0s)")
                
            except Exception as e:
                logger.error(f"✗ Error analyzing {job['job_id']}: {e}")
                continue
        
        logger.info(f"Analyzer Agent: Completed. Analyzed {len(analyzed_jobs)}/{len(matched_jobs)} jobs")
        
        # 4. Prepare summary
        summary = {
            'status': 'success',
            'total_jobs': len(matched_jobs),
            'analyzed_jobs': len(analyzed_jobs),
            'jobs': analyzed_jobs
        }
        
        return json.dumps(summary, indent=2)
    
    
    def _retrieve_relevant_chunks(self, job_id: str, job_description: str, 
                                  resume_chunks: List[str], chunk_embeddings: np.ndarray, 
                                  top_k: int) -> List[str]:
        """
        Retrieve top-k most relevant resume chunks for a job.
        
        Uses cached job embedding if available (from Matcher Agent).
        """
        # Try to load cached job embedding first
        if job_embedding_exists(job_id):
            job_embedding = load_job_embedding(job_id)
            logger.debug(f"✓ Loaded cached job embedding for {job_id}")
        else:
            # Generate if not cached (shouldn't happen if Matcher ran first)
            job_embedding = generate_embeddings([job_description])[0]
            logger.warning(f"⚠️  Job embedding not cached for {job_id}, generated on-the-fly")
            logger.debug(f"Expected path: data/embeddings/job_embeddings/{job_id}.npy")
        
        # Use search_top_matches to find most similar chunks
        scores, indices = search_top_matches(
            query_embedding=job_embedding,
            corpus_embeddings=chunk_embeddings,
            k=min(top_k, len(resume_chunks))  # Don't exceed available chunks
        )
        
        # Get top-k chunks
        relevant_chunks = [resume_chunks[idx] for idx in indices]
        
        return relevant_chunks
    
    def _generate_insights_with_rag(self, relevant_resume_chunks: List[str], 
                                   job_title: str, job_description: str, 
                                   company: str, match_score: float) -> str:
        """
        Generate insights using RAG - ONLY based on retrieved resume chunks.
        
        This reduces hallucination by grounding LLM in actual resume content.
        """
        # Format retrieved chunks
        retrieved_context = "\n\n---\n\n".join([
            f"RESUME SECTION {i+1}:\n{chunk}" 
            for i, chunk in enumerate(relevant_resume_chunks)
        ])
        
        prompt = f"""You are an expert career advisor analyzing job-resume fit.

RETRIEVED RESUME SECTIONS (most relevant):
{retrieved_context}

JOB DETAILS:
Company: {company}
Title: {job_title}
Match Score: {match_score:.1%}
Description: {job_description[:1500]}

INSTRUCTIONS:
Analyze the job requirements and find specific matches in the resume sections.
Generate your analysis in this EXACT format (no extra headers or explanations):

✨ Why this fits:
- [Job requirement] → [Specific resume evidence with details]
- [Job requirement] → [Specific resume evidence with details]
- [Job requirement] → [Specific resume evidence with details]

💡 Need improvement:
- [Missing skill/experience from job requirements]
- [Another gap between job needs and resume]
- [Third area lacking in resume]

RULES:
1. Use ONLY information from the retrieved resume sections (no hallucination)
2. Each "Why this fits" line MUST follow format: [Requirement] → [Evidence]
3. Be specific: mention actual technologies, projects, companies, or metrics
4. Each line max 100 characters
5. Exactly 3 points per section
6. NO extra headers like "### 3 KEY REQUIREMENTS" or "### ANALYSIS"
7. NO generic phrases like "strong background" or "good fit"
8. Start directly with "✨ Why this fits:" (no preamble)

GOOD EXAMPLES:
✨ Why this fits:
- Requires Python/ML → Built recommendation engine using Python/TensorFlow at Google
- Needs AWS experience → Deployed microservices on AWS handling 1M+ daily requests
- Wants full-stack → Developed React+Node.js app serving 50K users

💡 Need improvement:
- Requires Kubernetes but resume lacks container orchestration experience
- Needs 5+ years but resume shows 3 years in this domain
- Wants team leadership but resume doesn't highlight management experience

BAD EXAMPLES (DO NOT DO THIS):
### 3 KEY REQUIREMENTS:
1. Python experience
2. AWS knowledge
...

✨ **Why this fits:**
- Strong technical background
- Good fit for the role
...

YOUR OUTPUT (start here, no extra text):"""
        
        try:
            # Use LLM to generate insights
            response = llm.call([{"role": "user", "content": prompt}])
            
            # Extract text from response
            if hasattr(response, 'content'):
                explanation = response.content
            elif isinstance(response, dict) and 'content' in response:
                explanation = response['content']
            else:
                explanation = str(response)
            
            return explanation.strip()
            
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            # Fallback: still show requirement → evidence format
            return f"""✨ Why this fits:
- High semantic match ({match_score:.1%}) → Resume aligns with job requirements
- Relevant experience found → Skills match {company}'s tech stack
- Background fits role → Experience level appropriate for position

💡 Need improvement:
- Review full job description → Identify any missing specific skills
- Compare requirements carefully → Note any experience gaps
- Consider certifications → Strengthen credentials if needed"""
    
    def _update_job_explanation(self, job_id: str, explanation: str):
        """Update explanation field in database."""
        conn = sqlite3.connect('match_pulse.db')
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE push_history 
            SET explanation = ? 
            WHERE job_id = ?
        ''', (explanation, job_id))
        conn.commit()
        conn.close()


# Tool instance
analyze_jobs_tool = AnalyzeJobsTool()


# Analyzer Agent
analyzer_agent = Agent(
    role='RAG-based Career Insights Analyst',
    goal='Generate personalized, grounded insights using RAG to avoid hallucinations',
    backstory="""Expert career advisor specializing in tech industry job matching.
    You use Retrieval-Augmented Generation (RAG) to ensure all insights are grounded
    in actual resume content. You never make up information - everything is based on
    retrieved resume sections that are most relevant to each job.""",
    tools=[analyze_jobs_tool],
    llm=llm,
    verbose=True,
    allow_delegation=False
)


# Analyze Task
analyze_task = Task(
    description="""Generate personalized insights for matched jobs using RAG.
    
    RAG Process:
    1. Chunk resume into sections (Education, Experience, Skills, etc.)
    2. Generate embeddings for each chunk
    3. For each matched job:
       - Retrieve top-3 most relevant resume chunks
       - Generate insights based ONLY on retrieved chunks
       - This reduces hallucination by grounding in actual resume content
    4. Update explanation field in database
    
    Requirements:
    - All insights must be grounded in retrieved resume sections
    - Be specific: mention actual technologies/projects from resume
    - Keep insights concise (3 points each)
    - Use professional, big tech industry language
    - NO generic statements or made-up information
    """,
    agent=analyzer_agent,
    expected_output="""JSON object with:
    - status: success/error
    - total_jobs: number of matched jobs
    - analyzed_jobs: number of jobs analyzed
    - jobs: array of job summaries with RAG-based explanations
    """
)


def test_analyzer_agent(top_k: int = 3):
    """Test the analyzer agent standalone."""
    print("\n" + "=" * 70)
    print("Testing Analyzer Agent (RAG-based)")
    print("=" * 70)
    print(f"Top-k resume chunks: {top_k}")
    print("=" * 70 + "\n")
    
    # Call the tool directly
    result_json = analyze_jobs_tool._run(top_k=top_k)
    result = json.loads(result_json)
    
    # Print summary
    print("\n" + "=" * 70)
    print("📊 Analyzer Agent Results")
    print("=" * 70)
    print(f"Status: {result['status']}")
    print(f"Total jobs: {result['total_jobs']}")
    print(f"Analyzed jobs: {result['analyzed_jobs']}")
    print("=" * 70)
    
    if result.get('jobs'):
        print(f"\n📋 RAG-based insights:\n")
        for i, job in enumerate(result['jobs'], 1):
            print(f"{i}. [{job['match_score']:.3f}] {job['company'].upper()}: {job['title']}")
            print(f"\n{job['explanation']}\n")
            print("-" * 70)
    else:
        print("\n⚠️  No jobs analyzed")
    
    print("=" * 70)
    
    return result


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Test Analyzer Agent with RAG')
    parser.add_argument('--top-k', type=int, default=4, help='Number of resume chunks to retrieve')
    args = parser.parse_args()
    
    test_analyzer_agent(top_k=args.top_k)
