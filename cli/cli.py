#!/usr/bin/env python3

import os
import argparse
import json
import re
from urllib.parse import urlparse
from datetime import datetime
from openai import OpenAI
from lib.scrappers.parser_creation import JobSiteParser, get_api_key
from lib.scrappers.generic import JobScrapper
from lib.handlers.db_handler import DatabaseHandler
from lib.handlers.job_handler import JobHandler
from lib.models.scrape import Scrape
from lib.models.job import Job
from lib.models.score import Score
from lib.models.user import User
from lib.models.resume import Resume
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
        # Retrieve user based on environment variable or database state
        user = None
        if os.getenv("USERNAME"):
            user = User.find_by(name=os.getenv("USERNAME"))
            if not user:
                raise ValueError(f"No user found with name {os.getenv('USERNAME')}")
        else:
            # Use the count method from BaseModel
            user_count = User.count()
            if user_count == 1:
                user = User.first()
            elif user_count == 0:
                raise ValueError("No users found in database. Please create a user first using load_user.py")
            else:
                raise ValueError("Multiple users found. Please set the USERNAME environment variable to specify which user to use.")
        args = parse_arguments()
        resume_path = args.resume or os.getenv('RESUME_PATH')
        if not resume_path:
            raise ValueError("A resume file path must be provided either as an argument or through the RESUME_PATH environment variable.")
        resume = Resume.find_by(file_path=resume_path)
        if not resume and os.path.exists(resume_path):
            resume = Resume.from_path_and_user_id(resume_path, user.id)

        # Read the resume content
        with open(resume_path) as file:
            resume_content = file.read()
        api_key = get_api_key(args)
        job = JobHandler(api_key)
        job.resume = resume_content


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
        match_score = js.score_job_match(job.job_description, resume_content)
        print("Match Score and Explanation:")
        print(match_score)

        # Extract match score into score table with regex
        score_match = re.search(r'Score: (\d+)', match_score)
        explanation_match = re.search(r'Explanation: (.+)', match_score, re.DOTALL)

        if score_match and explanation_match:
            score_value = int(score_match.group(1))
            explanation = explanation_match.group(1).strip()

            # Create and save the Score object
            score = Score(
                score=score_value,
                explanation=explanation,
                resume_id=resume.id,
                job_id=job.job_description.id,
                user_id=user.id
            )
            score.save()
            print(f"Score {score_value} saved to database")

    finally:
        db_handler.close()

if __name__ == "__main__":
    main()
