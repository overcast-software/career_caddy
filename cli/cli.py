#!/usr/bin/env python3

import os
import argparse
from openai import OpenAI
from lib.scrappers.parser_creation import JobSiteParser, get_api_key
from lib.scrappers.generic import JobScrapper
from lib.database.db_handler import DatabaseHandler
from lib.parsers.generic import JobParser
from lib.scoring.job_scorer import JobScorer

def parse_arguments():
    parser = argparse.ArgumentParser(description="CLI for parsing job site URLs and extracting CSS selectors.")
    parser.add_argument('url', type=str, help='The URL of the job site to parse.')
    parser.add_argument('--api-key', type=str, help='OpenAI API key')
    parser.add_argument('--resume', type=str, help='Path to the resume file')
    return parser.parse_args()

def main():
    args = parse_arguments()
    url = args.url

    # Get the API key
    api_key = get_api_key(args)

    # Initialize the database handler
    db_handler = DatabaseHandler()

    # Check if the parser data already exists
    existing_css_selectors = db_handler.fetch_parser_from_url(url)
    if existing_css_selectors:
        print("CSS Selectors (from database):", existing_css_selectors[0])
    else:
        # Instantiate the OpenAI client
        client = OpenAI(api_key=api_key)

        # Create an instance of JobSiteParser
        jsp = JobSiteParser(client)

        # Fetch the webpage content
        html_content = jsp.fetch_webpage(url)

        # Use ChatGPT to find CSS selectors
        css_selectors = jsp.find_css_selectors(url, html_content)
        print("CSS Selectors (from scraping):", css_selectors)

        # Save the data to the database
        db_handler.save_data(url, css_selectors, html_content)
    # Fetch the job description using the existing CSS selectors
    client = OpenAI(api_key=api_key)
    jp = JobParser(client)
    job_data_id = existing_css_selectors[0]
    selectors = existing_css_selectors[1]
    url_id = existing_css_selectors[2]
    html = existing_css_selectors[4]
    job_description = jp.extract_data_with_selectors(selectors, html)
    db_handler.save_job_description(job_description, job_data_id, url_id)

    # Determine the resume path
    resume_path = args.resume or os.getenv('RESUME_PATH')
    if not resume_path:
        raise ValueError("A resume file path must be provided either as an argument or through the RESUME_PATH environment variable.")

    # Read the resume
    with open(resume_path) as file:
        resume = file.read()

    # Score the job match
    job_scorer = JobScorer(client)
    match_score = job_scorer.score_job_match(job_description, resume)
    print("Match Score and Explanation:")
    print(match_score)

    db_handler.close()

if __name__ == "__main__":
    main()
