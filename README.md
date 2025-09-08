# Job Site Parser CLI

A command-line suite for scraping job postings, parsing job data with AI, storing structured results, importing resumes, and scoring job-resume matches.

## Features

- **Automated CSS Selector Detection**: Uses OpenAI's API to intelligently identify CSS selectors for job content extraction
- **Database Storage**: Caches parsed data to avoid redundant API calls
- **Job Description Extraction**: Extracts structured job information from web pages
- **Resume Matching**: Scores job compatibility against your resume using AI analysis
- **CLI Interface**: Simple command-line interface for easy automation

## Requirements

- Python 3.6+
- OpenAI API key
- Resume file (path configurable via command-line argument or environment variable)

## Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Dependencies

- `requests` - HTTP library for web scraping
- `openai` - OpenAI API client
- `beautifulsoup4` - HTML parsing library

## CLI tools

### Primary flows
- Create/load a user
  - `python cli/load_user.py --name "Jane Doe" --email jane@example.com`
- Import resume(s)
  - Single file: `python cli/load_resume.py --resume /path/to/resume.docx [--user-email jane@example.com]`
  - Directory (recursive): `python cli/load_resume.py --dir /path/to/resumes [--user-email jane@example.com]`
- Extract and store a job from a URL (uses browser + OpenAI)
  - `OPENAI_API_KEY=... python cli/extract_job.py "https://www.example.com/jobs/1234"`
- End-to-end: extract + score against a specific resume file path
  - `OPENAI_API_KEY=... RESUME_PATH=/path/to/resume.org python cli/cli.py "https://www.example.com/jobs/1234"`
  - Or: `OPENAI_API_KEY=... python cli/cli.py "https://www.example.com/jobs/1234" --resume /path/to/resume.org`
- Score a specific resume against a stored job
  - `OPENAI_API_KEY=... python cli/score_job.py <resume_id> <job_id>`
- Score all resumes for a user against a stored job
  - `OPENAI_API_KEY=... python cli/score_job_for_user.py <job_id> [--user-email jane@example.com]`
- Generate a tailored resume summary for a job (optionally provide a resume)
  - `OPENAI_API_KEY=... python cli/generate_summary.py <job_id> [--resume-id <id>]`

### All CLI scripts
- **cli/load_user.py**
  - Create or find a user by name/email and store in the database.
  - Usage: `python cli/load_user.py --name "Jane Doe" --email jane@example.com`
- **cli/load_resume.py**
  - Import a single resume file or a whole directory (recursive). Converts .docx/.pdf/.md/.txt to .org for storage.
  - Usage:
    - File: `python cli/load_resume.py --resume /path/to/resume.docx [--user-email jane@example.com]`
    - Directory: `python cli/load_resume.py --dir /path/to/resumes [--user-email jane@example.com]`
- **cli/convert_resume.py**
  - Directly store a single file as a Resume for a user (no conversion helpers/UI).
  - Usage: `python cli/convert_resume.py /path/to/resume.org --user-id 1`
- **cli/extract_job.py**
  - Scrape and parse a job posting from a URL, using the appropriate service (e.g., LinkedIn). Stores results in DB.
  - Requires OPENAI_API_KEY and, for LinkedIn, credentials in secrets.yml.
  - Usage: `OPENAI_API_KEY=... python cli/extract_job.py "https://www.linkedin.com/jobs/view/..."`
- **cli/cli.py**
  - End-to-end: extracts job and scores it against a resume file (path via --resume or RESUME_PATH).
  - Usage: `OPENAI_API_KEY=... python cli/cli.py "<job_url>" [--resume /path/to/resume.org]`
- **cli/score_job.py**
  - Score a single resume against a single stored job. Saves score.
  - Usage: `OPENAI_API_KEY=... python cli/score_job.py <resume_id> <job_id>`
- **cli/score_job_for_user.py**
  - Score all resumes for a specific user (by --user-email or USERNAME env) against a stored job. Saves scores.
  - Usage: `OPENAI_API_KEY=... python cli/score_job_for_user.py <job_id> [--user-email jane@example.com]`
- **cli/score_resume.py**
  - Manually create a Score entry without using OpenAI (you provide score and explanation).
  - Usage: `python cli/score_resume.py --resume-id <id> --job-id <id> --score 75 --explanation "Good skills match"`
- **cli/generate_summary.py**
  - Generate a tailored resume summary for a given job (and optionally a specific resume).
  - Usage: `OPENAI_API_KEY=... python cli/generate_summary.py <job_id> [--resume-id <id>]`
- **cli/parse_job.py**
  - Experimental job parsing using stored selectors; may be outdated.
  - Usage: `python cli/parse_job.py "<job_url>" [--api-key ...]`
- **cli/test_linkedin.py**
  - Developer test script for LinkedIn processing; requires secrets.yml and OPENAI_API_KEY.
  - Usage: `OPENAI_API_KEY=... python cli/test_linkedin.py`

### Helper script
- **import_resumes.sh.example**
  - Example bash helper to bulk import resumes from paths or a directory. Copy to import_resumes.sh, edit PATHS, then:
  - Usage: `./import_resumes.sh [PATH ...] [--user-email jane@example.com]`

### Environment and configuration
- Required for OpenAI-powered commands: `OPENAI_API_KEY`
- Optional:
  - `RESUME_PATH`: default resume file path for cli/cli.py
  - `USERNAME`: used to resolve a user when not specifying --user-email
- **secrets.yml** (see secrets.yml.example)
  - Provide credentials for services like LinkedIn (username/password).

## How It Works

1. **URL Analysis**: The tool fetches the webpage content from the provided job URL
2. **CSS Selector Detection**: Uses OpenAI's API to analyze the HTML and identify relevant CSS selectors for job content
3. **Data Extraction**: Applies the detected selectors to extract structured job information
4. **Database Storage**: Saves the parsing results to avoid redundant processing
5. **Resume Matching**: Compares the job description against your resume and provides a compatibility score

## Database

The tool uses a local SQLite database (`job_data.db`) to store:
- Parsed CSS selectors for each domain
- Extracted job descriptions
- Processing metadata

## Configuration

- Set your resume file path via the `--resume` argument or `RESUME_PATH` environment variable
- Set your OpenAI API key via the `--api-key` argument or environment variable

## File Structure

```
├── cli/
│   ├── cli.py                   # Main end-to-end: extract + score against a resume
│   ├── extract_job.py           # Extract and store a job from a URL
│   ├── score_job.py             # Score one resume against one job (OpenAI)
│   ├── score_job_for_user.py    # Score all resumes for a user against one job (OpenAI)
│   ├── generate_summary.py      # Generate tailored resume summary (OpenAI)
│   ├── load_user.py             # Create/find a user
│   ├── load_resume.py           # Import a resume file or directory
│   ├── convert_resume.py        # Store a single resume file for a user
│   ├── score_resume.py          # Manually create a Score record
│   ├── parse_job.py             # Experimental parser using stored selectors
│   └── test_linkedin.py         # Developer test for LinkedIn flow
├── lib/
│   ├── scrapers/          # Web scraping modules
│   ├── database/           # Database handling
│   ├── parsers/            # Job data parsing
│   └── scoring/            # Resume matching logic
├── requirements.txt        # Python dependencies
└── .gitignore             # Git ignore rules
```
