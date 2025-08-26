#!/usr/bin/env python3

import os
import argparse
import json
from urllib.parse import urlparse
from datetime import datetime
from openai import OpenAI
from lib.scrappers.parser_creation import JobSiteParser, get_api_key
from lib.scrappers.generic import JobScrapper
from lib.handlers.db_handler import DatabaseHandler
from lib.handlers.job_handler import JobHandler
from lib.models.scrape import Scrape
from lib.models.job import Job
from lib.parsers.generic import JobParser
from lib.scoring.job_scorer import JobScorer

def parse_arguments():
    parser = argparse.ArgumentParser(description="CLI for parsing job site URLs and extracting CSS selectors.")
    parser.add_argument('url', type=str, help='The URL of the job site to parse.')
    parser.add_argument('--api-key', type=str, help='OpenAI API key')
    parser.add_argument('--resume', type=str, help='Path to the resume file')
    return parser.parse_args()

def main():
    db_handler = DatabaseHandler()
    try:
        args = parse_arguments()
        resume_path = args.resume or os.getenv('RESUME_PATH')
        if not resume_path:
            raise ValueError("A resume file path must be provided either as an argument or through the RESUME_PATH environment variable.")

        # Read the resume
        with open(resume_path) as file:
            resume = file.read()
        api_key = get_api_key(args)
        job = JobHandler(api_key)
        job.resume = resume


        # Check if the parser data already exists

        scrape_record = Scrape.find_by(url=args.url)
        # look for job description

        if scrape_record:
            job.scrape = scrape_record
            job.job_description = scrape_record.job
        else:
            # Create an instance of JobSiteParser
            jsp = JobSiteParser(job.client)

            # Fetch the webpage content
            job.html_content = jsp.fetch_webpage(args.url)

            # Use ChatGPT to find CSS selectors as json string
            # css_selectors = jsp.find_css_selectors(job.html_content)
            # job.css_selectors = css_selectors

            parsed_url = urlparse(args.url)
            host = parsed_url.netloc
            new_scrape = Scrape(
                url = args.url,
                host = host,
                html = job.html_content,
                css_selectors_json = "{}",
                scraped_at = datetime.utcnow()
            )
            job.scrape = new_scrape
            scrape_record = job.scrape

            jp = JobParser(job.client)
            # jd1 = jp.extract_data_with_selectors(job.html_content, job.css_selectors)
            jd = jp.analyze_html_with_chatgpt(job.html_content)

            job_description_meta = None
            try:
                job_description_meta = json.loads(jd)
            except Exception as e:
                print("bad json")
                breakpoint()

            job.company = job_description_meta.get('company')
            job.job_from_description(job_description_meta)
            job.scrape.job_id = job.job_description.id
            job.scrape.save()

        # Score the job match
        js = JobScorer(job.client)
        match_score = js.score_job_match(job.job_description, resume)
        print("Match Score and Explanation:")
        print(match_score)

    finally:
        db_handler.close()

if __name__ == "__main__":
    main()
