#!/usr/bin/env python3
import argparse
import os
import re
import sys
from openai import OpenAI
from lib.handlers.db_handler import DatabaseHandler
from lib.models.user import User
from lib.models.resume import Resume
from lib.models.job_post import JobPost
from lib.models.score import Score


def get_api_key():
    key = os.getenv('OPENAI_API_KEY')
    if not key:
        print('API key is required. Set OPENAI_API_KEY environment variable.')
        sys.exit(1)
    return key


def parse_arguments():
    p = argparse.ArgumentParser(description='Score a job against all resumes for a user.')
    p.add_argument('job_id', type=int, help='The ID of the job to score against.')
    p.add_argument('--user-email', help='Email of the user whose resumes to score.')
    return p.parse_args()


def resolve_user(args):
    if args.user_email:
        user = User.find_by(email=args.user_email)
        if not user:
            raise ValueError(f'No user found with email {args.user_email}.')
        return user
    if os.getenv('USERNAME'):
        user = User.find_by(name=os.getenv('USERNAME'))
        if not user:
            raise ValueError(f"No user found with name {os.getenv('USERNAME')}")
        return user
    cnt = User.count()
    if cnt == 1:
        return User.first()
    if cnt == 0:
        raise ValueError('No users found in database. Please create a user first using cli/load_user.py')
    raise ValueError('Multiple users found. Set USERNAME env var or use --user-email to select a user.')


def parse_eval(e):
    if isinstance(e, dict):
        s = e.get('score')
        expl = e.get('explanation') or e.get('evaluation')
        if isinstance(expl, dict):
            expl = expl.get('text') or str(expl)
        if s is not None and expl:
            return int(s), str(expl)
    text = str(e)
    m_score = re.search(r'(?i)\bscore\s*[:\-]\s*(\d{1,3})', text)
    m_expl = re.search(r'(?i)\bexplanation\s*[:\-]\s*(.+)', text, re.DOTALL)
    s_val = int(m_score.group(1)) if m_score else None
    expl = m_expl.group(1).strip() if m_expl else text
    return s_val, expl


def main():
    args = parse_arguments()
    db = DatabaseHandler()

    job = db.session.query(JobPost).get(args.job_id)
    if not job:
        print(f'Job with ID {args.job_id} not found.')
        sys.exit(1)

    try:
        user = resolve_user(args)
    except ValueError as e:
        print(str(e))
        sys.exit(1)

    resumes = db.session.query(Resume).filter(Resume.user_id == user.id).all()
    if not resumes:
        print(f'No resumes found for user {user.email or user.name}.')
        sys.exit(1)

    client = OpenAI(api_key=get_api_key())
    from lib.scoring.job_scorer import JobScorer
    scorer = JobScorer(client)

    for resume in resumes:
        evaluation = scorer.score_job_match(job.description, resume.content)
        score_value, explanation = parse_eval(evaluation)

        if score_value is None:
            print(f'- Skipping {resume.file_path}: could not parse score from evaluation.')
            continue

        # Optional: skip if already scored
        existing = Score.find_by(job_post_id=job.id, resume_id=resume.id)
        if existing:
            print(f'- Skipping {resume.file_path}: score already exists.')
            continue

        score = Score(
            job_post_id=job.id,
            resume_id=resume.id,
            user_id=user.id,
            score=score_value,
            explanation=explanation
        )
        score.save()
        print(f'- Saved score {score_value} for {resume.file_path}')

    print('Done.')

if __name__ == '__main__':
    main()
