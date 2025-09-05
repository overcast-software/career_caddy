import argparse
import sys
import os
import yaml
from lib.handlers.db_handler import DatabaseHandler
from lib.models.resume import Resume
from lib.models.job_post import JobPost
from lib.models.score import Score
from lib.scoring.job_scorer import JobScorer
from openai import OpenAI

def get_api_key():
    if 'OPENAI_API_KEY' in os.environ:
        return os.environ['OPENAI_API_KEY']
    else:
        print("API key is required. Set OPENAI_API_KEY environment variable.")
        sys.exit(1)

def parse_arguments():
    parser = argparse.ArgumentParser(description="CLI for scoring resumes against job postings.")
    parser.add_argument('resume_id', type=int, help='The ID of the resume to score.')
    parser.add_argument('job_id', type=int, help='The ID of the job to score against.')
    return parser.parse_args()

def main():
    args = parse_arguments()
    db_handler = DatabaseHandler()

    resume = db_handler.session.query(Resume).get(args.resume_id)
    job = db_handler.session.query(JobPost).get(args.job_id)

    if not resume:
        print(f"Resume with ID {args.resume_id} not found.")
        sys.exit(1)

    if not job:
        print(f"Job with ID {args.job_id} not found.")
        sys.exit(1)

    api_key = get_api_key()
    ai_client = OpenAI(api_key=api_key)
    scorer = JobScorer(ai_client)

    evaluation = scorer.score_job_match(job.description, resume.content)

    print(f"Job: {job.title}")
    print(f"Resume: {resume.file_path}")
    print(f"Evaluation: {evaluation}")

    # Save score to database
    score = Score(
        job_post_id=job.id,
        resume_id=resume.id,
        evaluation=evaluation.get('evaluation'),
        score=evaluation.get('score')
    )
    score.save()
    print("Score saved to database.")

if __name__ == "__main__":
    main()
