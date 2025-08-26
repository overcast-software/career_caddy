# Job Site Parser CLI

A command-line tool for parsing job site URLs, extracting job descriptions using AI-powered CSS selector detection, and scoring job matches against your resume.

## Features

- **Automated CSS Selector Detection**: Uses OpenAI's API to intelligently identify CSS selectors for job content extraction
- **Database Storage**: Caches parsed data to avoid redundant API calls
- **Job Description Extraction**: Extracts structured job information from web pages
- **Resume Matching**: Scores job compatibility against your resume using AI analysis
- **CLI Interface**: Simple command-line interface for easy automation

## Requirements

- Python 3.6+
- OpenAI API key
- Resume file (currently expects `/Users/oldbones/Network/syncthing/org/roam/job_hunt/resume.org`)

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

## Usage

```bash
python cli/cli.py <job_url> [--api-key <your_openai_api_key>]
```

### Arguments

- `url` (required): The URL of the job posting to analyze
- `--api-key` (optional): Your OpenAI API key (can also be set via environment variable)

### Example

```bash
python cli/cli.py https://example.com/job-posting --api-key sk-your-api-key-here
```

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

- Update the resume file path in `cli/cli.py` to point to your resume location
- Set your OpenAI API key via the `--api-key` argument or environment variable

## File Structure

```
├── cli/
│   └── cli.py              # Main CLI script
├── lib/
│   ├── scrappers/          # Web scraping modules
│   ├── database/           # Database handling
│   ├── parsers/            # Job data parsing
│   └── scoring/            # Resume matching logic
├── requirements.txt        # Python dependencies
└── .gitignore             # Git ignore rules
```
