# MatchPulse: A job finder agent AI Agent Design Document

## 1. Overview
### 1.1 Project Summary
MatchPulse is a personalized AI-powered job alert system designed for tech job seekers in North America, with a focus on Seattle, WA, targeting roles such as Software Development Engineer (SDE), AI Engineer, and similar technical positions. The system periodically scans tech companies career pages of user-selected companies (e.g., Meta, Amazon, Google, Salesforce), extracts new job postings, performs semantic matching against the user's resume, and sends high-quality notifications via Telegram. It emphasizes privacy, efficiency, and modularity, avoiding automated applications to mitigate risks like platform bans.

This project evolves from a single-user MVP (Week 1-2) to a multi-user system (Week 3+), incorporating modern AI engineering practices. It serves dual purposes: as a practical tool for job hunting and a portfolio piece demonstrating production-grade AI agent development.

### 1.2 Key Features
- User-configurable inputs: Pre-filtered company career page URLs (user manually creates filtered URLs from company career pages with location/position filters already applied), resume upload, Telegram integration.
- Timed scanning: Weekdays, every 2 hours (e.g., 4x/day), fetching only new jobs from user-provided pre-filtered career URLs.
- AI Matching: Semantic similarity via vector embeddings (not keyword filtering) to find positions that truly match the user's resume. RAG-enhanced LLM for personalized explanations (reducing hallucinations via grounded retrieval).
- Notifications: Telegram pushes with job details, links, and concise personalized insights (e.g., "Why this fits: Matches your xx, xx, and xx experience; suggest emphasizing yy, yy, and yy skills").
- Dashboard: Streamlit-based UI for viewing push history, trends, and configurations.

### 1.3 Telegram Notification Format
Each matched job is sent as an individual message with the following format:

```
🎯 New Job Match (Match: 87%)

📍 Company: Meta
💼 Position: Senior AI Engineer
📌 Location: Seattle, WA
💰 Salary: $180k-$250k

✨ Why this fits:
- Matches your ML infrastructure and PyTorch experience
- Your RAG system work aligns with their AI platform needs

💡 Suggest emphasizing:
- Distributed training experience
- Production ML system scaling

🔗 Apply Now: https://careers.meta.com/jobs/...

---
Posted: 2 hours ago
```

**Notification Strategy:**
- **Week 1 MVP**: One message per job (with 1-2 second delay between messages to avoid Telegram rate limits)
- **Future optimization**: If >10 matches in one scan, send a summary message first, then individual messages
- **Field availability**: Salary and Posted Date are optional; only displayed if scraped successfully

## 2. Goals and Non-Goals
### 2.1 Goals
- Deliver high-precision job alerts (match accuracy >80% via semantic + RAG).
- Support 20-50 target companies per user with minimal maintenance (users provide pre-filtered URLs, no login required).
- Ensure privacy: Local-first processing, no data sharing.
- Demonstrate industry-level engineering: Multi-agent orchestration, CI/CD, containerization.

### 2.2 Non-Goals
- Automated job applications (to avoid legal/risk issues).
- Real-time scanning (timed batches suffice for MVP).
- Integration with external job boards (focus on company career pages).
- Advanced analytics (e.g., market trends; defer to future iterations).

## 3. Scope
- **In Scope (Week 1 MVP)**: Single-user setup, resume parsing/embedding, job fetching/parsing, matching/push logic, basic dashboard.
- **In Scope (Future Phases)**: Multi-user auth, cloud deployment, advanced features.
- **Out of Scope**: Mobile app, payment integration, enterprise-scale monitoring (e.g., Prometheus), international localization.

## 4. System Architecture
### 4.1 High-Level Diagram

- **Frontend**: Streamlit app for user input and dashboard (single-user for Week 1 MVP).
- **Backend**: FastAPI for REST endpoints (e.g., /scan, /history).
- **Configuration**: 
  - Week 1 MVP: Default pre-filtered URLs in config.yaml for single user
  - Week 3+: Users input their own pre-filtered company career URLs via Streamlit UI, stored in user_config.company_links
  - Users manually create filtered search URLs from company career pages (no login required) and paste them into the system
- **AI Pipeline**: CrewAI multi-agent framework:
  - **Fetcher Agent**: Scrapes career pages using Playwright based on user-provided pre-filtered URLs (from user_config.company_links or config.yaml fallback). Stealth mode, pagination handling. Extracts: job_id, job_url, title, company, location, description, salary (optional), posted_date (optional).
  - **Matcher Agent**: Semantic matching via vector embedding similarity (FAISS) between job descriptions and resume. No keyword filtering - AI identifies truly suitable positions based on semantic understanding. Computes match score (0-1 scale).
  - **Analyzer Agent**: RAG chain (LangChain) for hallucination-reduced explanations. Generates "Why this fits" and "Suggest emphasizing" insights based on resume + job description.
  - **Notifier Agent**: Handles Telegram pushes with rate limit management (1-2 second delay between messages) and feedback loops.
- **Storage**: SQLite for user preferences (user_config including company_links) and push history (deduplication via job_id).
- **Scheduling**: local: Docker scheduled run or APScheduler. cloud: cloud cron (e.g., AWS EventBridge) for timed runs.
- **Models**: Together AI Meta Llama models for LLM/RAG: meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8;  sentence-transformers/all-mpnet-base-v2 for embeddings (download from Hugging Face).

### 4.2 Data Flow (Week 1 MVP - Single User)
1. User configures inputs via Streamlit:
   - Pre-filtered company career URLs (user manually creates filtered URLs from company career pages, e.g., Meta careers filtered by "Seattle" + "Software Engineer")
   - Resume upload, Telegram chat_id
   - All saved to user_config table (Week 1: can use config.yaml as default)
2. Resume uploaded → Parsed/extracted → Embedded → Stored in FAISS index.
3. Manual scan triggered → Fetcher reads URLs from user_config.company_links (or config.yaml fallback) → Scrapes jobs → Extracts job_id, URL, title, company, location, description, salary (optional), posted_date (optional).
4. Matcher checks push_history DB (via job_id) → Skips duplicates → Computes semantic embedding similarity between job description and resume (match_score 0-1). No keyword filtering - AI finds truly suitable positions.
5. High matches (e.g., similarity > 0.7) → Analyzer generates RAG-based explanation ("Why this fits" + "Suggest emphasizing").
6. Notifier formats message → Pushes to Telegram (one message per job, 1-2 sec delay) → Logs to push_history DB.
7. User views history in dashboard.

Note: Week 1 includes full RAG pipeline for testing embedding quality. Automated scheduling added in Week 2.

### 4.3 Key Technologies
- **Language**: Python 3.12+.
- **Frameworks**: CrewAI (multi-agent), LangChain (RAG), FastAPI (API), Streamlit (UI), Playwright (scraping).
- **DB**: SQLite, FAISS (local MVP), Postgres/Supabase (cloud).
- **Deployment**: Docker Compose (local), GitHub Actions CI/CD to Render/AWS ECS Fargate.

## 5. Data Models
### 5.1 Database Schema (SQLite for Week 1 MVP)
- **user_config**: id (PK), company_links (TEXT, JSON object with company names as keys and pre-filtered URLs as values, e.g., {"meta": "https://...", "google": "https://..."}), resume_path (TEXT), telegram_chat_id (TEXT).
- **push_history**: id (PK), company (TEXT), job_id (TEXT, unique per company), job_url (TEXT), title (TEXT), location (TEXT), salary (TEXT, nullable), posted_date (DATETIME, nullable), match_score (FLOAT, 0-1), pushed_at (DATETIME), explanation (TEXT, RAG-generated insights), status (TEXT, default 'pushed').

### 5.2 Configuration File (config.yaml)
- **links**: Default pre-filtered company career page URLs for Week 1 MVP (single-user). Format: `company_name: filtered_url`
  - Example: `meta: https://www.metacareers.com/jobsearch?q=software%20engineer&offices[0]=Seattle%2C%20WA`
  - URLs already include filters for location, job type, etc.
  - Week 1: System reads from config.yaml as default/fallback
  - Week 3+ (multi-user): Each user provides their own pre-filtered URLs via Streamlit UI, stored in user_config.company_links

Constraints: UNIQUE (job_id) for deduplication. The push_history table serves dual purpose: tracking pushed jobs and deduplicating seen jobs. 

Note: Pre-filtered URLs are user-provided (no login to company websites required). Users manually create filtered search URLs from company career pages (e.g., filter by location, job type) and paste them into the system. AI performs semantic matching against resume to find truly suitable positions, not simple keyword filtering.

## 6. APIs
### 6.1 FastAPI Endpoints (Week 1 MVP)
- **POST /upload-resume**: Upload and process resume file (returns resume_path).
- **POST /configure**: Update user configs (company_links, telegram_chat_id). company_links is a JSON object with company names and their pre-filtered URLs.
- **POST /scan**: Manual/trigger scan (async). Reads company URLs from user_config.company_links (or config.yaml fallback).
- **GET /history**: Fetch push history (paginated).
- **GET /health**: System status.

Note: Resume upload is handled via FastAPI endpoint, while configuration and dashboard viewing use Streamlit UI. Users provide their own pre-filtered company career URLs (manually created from company career pages with location/position filters already applied, no login required).

## 7. Security and Privacy
- **Data Storage**: Resume embeddings stored locally; single-user setup for Week 1 MVP.
- **Scraping Risks**: Residential proxies, rate limiting, stealth to avoid bans.
- **Compliance**: GDPR-like privacy (no data resale); user consent for Telegram.
- **Vulnerabilities**: Input sanitization (e.g., SQL injection), HTTPS for APIs.

## 8. Testing Plan
### 8.1 Week 1 MVP Testing
- **Unit Tests**: Pytest for agents (e.g., mock scraping, embedding accuracy).
- **Integration Tests**: End-to-end flow (scan → match → push).
- **E2E Tests**: Selenium for Streamlit UI.
- **Metrics**: Match accuracy (manual review), latency (<5 min/scan), error rate (<1%).

### 8.2 Future Phases Testing
- **Load Tests**: Locust for 50 concurrent users (Week 3, multi-user support).

## 9. Deployment and Operations
### 9.1 Local MVP (Week 1)
- Docker Compose: Services for FastAPI, Streamlit (SQLite embedded, no separate DB service needed)
- Run: `docker-compose up`.

### 9.2 Cloud MVP (AWS/Render)
- CI/CD: GitHub Actions → Build Docker → Push to ECR → Deploy to ECS Fargate.
- Scaling: Auto-scale based on CPU; use Lambda for scheduler.
- Monitoring: CloudWatch logs; basic alerts for failures.
- Cost: Free tier for low usage (~$10-20/month for prod-like).

## 10. Risks and Dependencies
### 10.1 Risks
- Career page changes: Mitigate with user-editable URLs in config.yaml; fallback to search tools.
- LLM Hallucinations: RAG grounding + prompt engineering; test with real resume/job pairs.
- Rate Limits/Bans: 
  - Scraping: Stealth mode + proxies; monitor error logs. Pre-filtered URLs reduce scraping complexity.
  - Telegram: Rate limit (1 msg/sec per chat); mitigate with 1-2 sec delays between messages.
- API Costs: Together AI API usage; monitor and set rate limits.
- Salary/Date Scraping: Many companies don't display salary; handle missing fields gracefully.

### 10.2 Dependencies
- External: Telegram Bot API, Together AI API (for LLM), Hugging Face (for embedding models).
- Internal: None (self-contained).
- Tools: Playwright (browser automation), FAISS (vector search).

## 11. Timeline (Estimated for Solo Developer)
- **Week 1: MVP Core (Single-User Scanning + Matching + RAG)**
  - Setup: Project structure, Docker Compose, SQLite database
  - Core Pipeline: 
    - Fetcher Agent (Playwright scraping)
    - Matcher Agent (embedding + FAISS for semantic similarity)
    - Analyzer Agent (RAG chain with LangChain for personalized explanations)
  - Resume upload and parsing: Extract text, generate embeddings
  - Notifications: Telegram integration with job details and "Why this fits" insights
  - Basic Dashboard: Streamlit UI for configuration and viewing push history
  - Single-user configuration (no auth required)
  - Testing: Validate embedding similarity and RAG explanation quality

- **Week 2: Scheduling + Refinement**
  - Scheduler integration (APScheduler for timed scans: weekdays, every 2 hours)
  - Resume parsing improvements and embedding refinements
  - Enhanced filtering logic (location, position keywords)
  - Testing and refinement of matching accuracy
  - Error handling and retry logic for scraping failures

- **Week 3: Multi-User Support**
  - Auth: streamlit-authenticator or OAuth for multi-user login
  - Database migration: Add users table, user_configs with user_id FK
  - UI Enhancement: Allow users to input/manage their own pre-filtered company URLs via Streamlit
  - Data Isolation: Per-user DB partitioning and FAISS indexes
  - API Security: JWT auth for FastAPI endpoints
  - Updated dashboard for multi-user scenarios

- **Week 4: Cloud Deployment + Polish**
  - CI/CD: GitHub Actions pipeline
  - Cloud deployment: AWS ECS Fargate or Render
  - Monitoring: CloudWatch logs and basic alerts
  - Final testing, documentation, and polish

## 12. Appendices
- **References**: Inspired by tools like JobCopilot, Wobo AI; follows Google Design Doc template.
- **Open Questions**: Handling ATS-specific parsers? Mobile notifications beyond Telegram?

This design aligns with North American tech industry standards (e.g., modular, scalable, secure), drawing from practices at companies like Amazon and Google. Feedback welcome for iterations!