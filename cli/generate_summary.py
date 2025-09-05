import argparse
import sys
from lib.handlers.db_handler import DatabaseHandler
from lib.models.job_post import JobPost
from lib.models.resume import Resume
from lib.services.summary_service import SummaryService

def parse_arguments():
    parser = argparse.ArgumentParser(description="CLI for generating resume summaries from job postings.")
    parser.add_argument('job_id', type=int, help='The ID of the job to generate a summary for.')
    parser.add_argument('--resume-id', type=int, help='Optional resume ID to use for context.')
    return parser.parse_args()

def main():
    args = parse_arguments()
    db_handler = DatabaseHandler()

    job = db_handler.session.query(JobPost).get(args.job_id)
    if not job:
        print(f"Job with ID {args.job_id} not found.")
        sys.exit(1)

    resume = None
    if args.resume_id:
        resume = db_handler.session.query(Resume).get(args.resume_id)
        if not resume:
            print(f"Resume with ID {args.resume_id} not found.")
            sys.exit(1)

    summary_service = SummaryService(job, resume)
    summary = summary_service.generate_summary()

    print("="*60)
    print("RESUME SUMMARY")
    print("="*60)
    print(summary)
    print("="*60)

if __name__ == "__main__":
    main()
