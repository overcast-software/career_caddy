#!/usr/bin/env python3

import os
import argparse
import json
import re
from urllib.parse import urlparse
from datetime import datetime
from openai import OpenAI
from lib.scrapers.parser_creation import JobSiteParser, get_api_key
from lib.scrapers.generic import JobScraper
from lib.handlers.db_handler import DatabaseHandler
from lib.handlers.job_handler import JobHandler
from lib.models.scrape import Scrape
from lib.models.job import Job
from lib.models.score import Score
from lib.models.user import User
from lib.models.resume import Resume
from lib.parsers.generic import JobParser
from lib.scoring.job_scorer import JobScorer
from lib.extractors.linkedin import LinkedInActor

def parse_arguments():
    parser = argparse.ArgumentParser(description="CLI for parsing job site URLs and extracting CSS selectors.")
    parser.add_argument('url', type=str, help='The URL of the job site to parse.')
    parser.add_argument('--api-key', type=str, help='OpenAI API key')
    parser.add_argument('--resume', type=str, help='Path to the resume file')
    return parser.parse_args()

def main():
    #instantiates the db - currently sqlite
    db_handler = DatabaseHandler()
    try:
        # Retrieve user based on environment variable or database state
        user = None
        if os.getenv("USERNAME"):
            user = User.find_by(name=os.getenv("USERNAME"))
            if not user:
                raise ValueError(f"No user found with name {os.getenv('USERNAME')}")
        else:
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
        job_handler = JobHandler(args.url, api_key)
        job_handler.process_url()

        job_handler.resume = resume_content

        score = Score.find_by(job_id=job_handler.scrape.job_id)
        if score:
            print('*'*88)
            print('job scored already')
            print('*'*88)
            return

        # Score the job match
        scorer = JobScorer(job_handler.client)
        match_score = scorer.score_job_match(job_handler.job.description, resume_content)
        print("Match Score and Explanation:\n")
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
                job_id=job_handler.job.id,
                user_id=user.id
            )
            score.save()
            print(f"Score {score_value} saved to database")

    finally:
        db_handler.close()

if __name__ == "__main__":
    main()
