import argparse
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from lib.models.base import BaseModel
from lib.models.user import User
from lib.models.resume import Resume
from lib.models.job_post import JobPost
from lib.models.score import Score

def parse_arguments():
    parser = argparse.ArgumentParser(description='Score a resume against a job.')
    parser.add_argument('--resume-id', type=int, required=True, help='ID of the resume to score.')
    parser.add_argument('--job-id', type=int, required=True, help='ID of the job to score against.')
    parser.add_argument('--score', type=int, required=True, help='Score (1-100).')
    parser.add_argument('--explanation', required=True, help='Explanation of the score.')
    return parser.parse_args()

def main():
    args = parse_arguments()

    # Create a database engine and session
    engine = create_engine('sqlite:///job_data.db')
    Session = sessionmaker(bind=engine)
    session = Session()

    # Set the session for BaseModel
    BaseModel.set_session(session)

    # Get the resume and job
    resume = Resume.get(args.resume_id)
    job = JobPost.get(args.job_id)

    if not resume:
        print(f"Resume with ID {args.resume_id} not found.")
        return

    if not job:
        print(f"Job with ID {args.job_id} not found.")
        return

    # Create a new score
    score = Score(
        score=args.score,
        explanation=args.explanation,
        resume_id=resume.id,
        job_id=job.id,
        user_id=getattr(resume, 'user_id', getattr(resume.user, 'id', None))
    )

    # Save the score to the database
    score.save()

    print(f"Score of {score.score} for resume {resume.id} against job {job.id} has been saved.")

if __name__ == '__main__':
    main()
