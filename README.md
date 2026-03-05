# MatchPulse

An AI-powered job matching system that automatically scrapes, analyzes, and notifies you of relevant job opportunities from top tech companies.

## Overview

MatchPulse uses semantic matching and RAG (Retrieval-Augmented Generation) to analyze job postings against your resume, providing detailed insights on fit and areas for improvement. The system runs automated scans and sends notifications via Telegram for high-match positions.

## Features

- **Automated Job Scraping**: Monitors 7 major tech companies (NVIDIA, Google, Amazon, Microsoft, Salesforce, Oracle, Expedia)
- **Semantic Matching**: Uses sentence transformers and cosine similarity to calculate job-resume fit scores
- **RAG-based Analysis**: Retrieves relevant resume sections and generates detailed match explanations using Gemini LLM
- **Telegram Notifications**: Real-time alerts for high-match opportunities with customizable thresholds
- **Interactive Dashboard**: Streamlit-based UI for viewing job history, match scores, and AI-generated insights
- **Embedding Cache**: Optimized performance with cached embeddings for resume chunks and job descriptions

## Architecture

```
MatchPulse/
├── src/
│   ├── agents/
│   │   ├── fetcher_agent.py      # Web scraping with Playwright
│   │   ├── matcher_agent.py      # Semantic matching engine
│   │   ├── analyzer_agent.py     # RAG-based insights generation
│   │   └── notifier_agent.py     # Telegram notification service
│   ├── tools/
│   │   ├── scraper.py            # Job listing scraper
│   │   ├── details_scraper.py    # Job details extractor
│   │   ├── db.py                 # Database operations
│   │   └── utils.py              # Embedding utilities
│   ├── config/
│   │   └── config.yaml           # Company configurations
│   └── main.py                   # Pipeline orchestrator
├── dashboard/
│   ├── MatchPulse.py             # Main dashboard page
│   ├── pages/
│   │   ├── 1_Configuration.py    # Settings and manual scan
│   │   └── 2_Jobs.py             # Job history and analysis
│   └── utils/
│       └── db_helper.py          # Dashboard database helpers
├── data/
│   ├── resumes/                  # Resume PDFs
│   └── embeddings/               # Cached embeddings
├── match_pulse.db                # SQLite database
└── requirements.txt
```

## Prerequisites

- Python 3.9+
- Playwright browsers
- Gemini API key
- Telegram Bot token and Chat ID

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/MatchPulse.git
cd MatchPulse
```

2. Create and activate virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
playwright install chromium
```

4. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your credentials:
# - GEMINI_API_KEY
# - TELEGRAM_BOT_TOKEN
# - TELEGRAM_CHAT_ID
```

5. Place your resume in `data/resumes/` directory (PDF format)

## Usage

### Manual Scan

Run a one-time scan with custom parameters:

```bash
# Scan with default settings
python src/main.py

# Scan with custom threshold and limit
python src/main.py --threshold 0.75 --limit 20 --top-k 3

# Dry run (no notifications)
python src/main.py --dry-run
```

### Dashboard

Launch the interactive dashboard:

```bash
streamlit run dashboard/MatchPulse.py
```

Access at `http://localhost:8501`

### Scheduled Scans

For automated scanning every 2 hours during work hours (9 AM - 5 PM, Mon-Fri):

**Option 1: Cron (Linux/Mac)**

```bash
# Edit crontab
crontab -e

# Add entry (runs at 9 AM, 11 AM, 1 PM, 3 PM, 5 PM on weekdays)
0 9,11,13,15,17 * * 1-5 cd /path/to/MatchPulse && /path/to/.venv/bin/python src/main.py --threshold 0.72 --limit 40
```

**Option 2: Task Scheduler (Windows)**

Create a scheduled task via Task Scheduler GUI or PowerShell:
- Trigger: Daily at 9 AM, repeat every 2 hours for 8 hours
- Days: Monday through Friday
- Action: Run `python src/main.py --threshold 0.72 --limit 40`

**Option 3: Docker with Cron**

```bash
# Build image
docker build -t matchpulse .

# Run container with cron
docker run -d --name matchpulse \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/match_pulse.db:/app/match_pulse.db \
  --env-file .env \
  matchpulse
```

## Configuration

### Matching Parameters

- `threshold`: Minimum match score (0.0-1.0) for notifications. Default: 0.72
- `top-k`: Number of resume sections to retrieve for RAG analysis. Default: 3
- `limit`: Maximum jobs to process per scan. Default: 40

### Adding Companies

Edit `src/config/config.yaml` to add new companies:

```yaml
companies:
  - name: "newcompany"
    url: "https://careers.newcompany.com/jobs"
    selectors:
      job_card: ".job-listing"
      title: ".job-title"
      url: ".job-link"
```

Implement scraper logic in `src/tools/scraper.py` and `src/tools/details_scraper.py`.

## Database Schema

### push_history

| Column | Type | Description |
|--------|------|-------------|
| job_id | TEXT | Unique job identifier (company_id) |
| company | TEXT | Company name |
| title | TEXT | Job title |
| job_url | TEXT | Job posting URL |
| match_score | REAL | Semantic similarity score (0.0-1.0) |
| status | TEXT | fetched, matched, not_matched, pushed |
| explanation | TEXT | RAG-generated analysis |
| timestamp | TEXT | ISO 8601 timestamp |

### user_config

| Column | Type | Description |
|--------|------|-------------|
| key | TEXT | Configuration key |
| value | TEXT | Configuration value |

## Technology Stack

- **Web Scraping**: Playwright (stealth mode)
- **Embeddings**: sentence-transformers (all-MiniLM-L6-v2)
- **LLM**: Google Gemini (gemini-3-flash-preview)
- **Database**: SQLite
- **Dashboard**: Streamlit
- **Notifications**: Telegram Bot API
- **Orchestration**: CrewAI

## Troubleshooting

### Gemini API Rate Limits

Free tier: 5 requests/minute. Upgrade to paid plan or reduce `--limit` parameter.

### Playwright Browser Issues

```bash
playwright install --force chromium
```

### Database Locked

Ensure only one instance of the application is running.

### Missing Embeddings

Delete `data/embeddings/` and restart to regenerate.

## Development

### Running Tests

```bash
pytest tests/
```

### Code Structure

- **Agents**: Independent modules following single responsibility principle
- **Tools**: Reusable utilities for scraping, database, and embeddings
- **Pipeline**: Sequential execution: Fetch → Match → Analyze → Notify

## License

MIT License - see LICENSE file for details

## Contributing

Contributions are welcome. Please open an issue first to discuss proposed changes.

## Acknowledgments

- Sentence Transformers for semantic embeddings
- Google Gemini for LLM capabilities
- Playwright for reliable web scraping
- Streamlit for rapid dashboard development
