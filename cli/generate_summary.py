import argparse
import sys
import os
from lib.handlers.db_handler import DatabaseHandler
from lib.models.job_post import JobPost
from lib.models.resume import Resume
from lib.services.summary_service import SummaryService
from openai import OpenAI


def get_api_key(args):
    if args.api_key:
        return args.api_key
    elif "OPENAI_API_KEY" in os.environ:
        return os.environ["OPENAI_API_KEY"]
    else:
        print("API key is required. Exiting...")
        sys.exit(1)


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="CLI for generating resume summaries from job postings."
    )
    parser.add_argument(
        "--job-id",
        required=False,
        type=int,
        help="The ID of the job to generate a summary for.",
    )
    parser.add_argument(
        "--resume-id", type=int, help="Optional resume ID to use for context."
    )
    parser.add_argument("--api-key", type=str, help="OpenAI API key")
    return parser.parse_args()


def main():
    args = parse_arguments()
    api_key = get_api_key(args)
    client = OpenAI(api_key=api_key)
    db_handler = DatabaseHandler()

    if args.job_id:
        job = JobPost.get(args.job_id)
    elif JobPost.count() > 0:
        job = JobPost.last()
    else:
        print(f"Job with ID {args.job_id} not found.")
        sys.exit(1)

    resume = None
    if args.resume_id:
        resume = db_handler.session.query(Resume).get(args.resume_id)
        if not resume:
            print(f"Resume with ID {args.resume_id} not found.")
            sys.exit(1)

    summary_service = SummaryService(client, job.description, resume.content)
    summary = summary_service.generate_summary()

    print("=" * 60)
    print("RESUME SUMMARY")
    print("=" * 60)
    print(summary)
    print("=" * 60)


if __name__ == "__main__":
    main()
