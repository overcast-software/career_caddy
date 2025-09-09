#!/usr/bin/env python3
import argparse
import os
import sys
from jinja2 import Environment, FileSystemLoader
from openai import OpenAI
from lib.handlers.db_handler import DatabaseHandler
from lib.models.job_post import JobPost
from lib.models.resume import Resume


def parse_arguments():
    p = argparse.ArgumentParser(
        description="Generate a tailored cover letter from a resume and job post."
    )
    p.add_argument("--job-id", type=int, required=True, help="JobPost ID.")
    p.add_argument("--resume-id", type=int, required=True, help="Resume ID.")
    p.add_argument("--api-key", type=str, help="OpenAI API key (optional).")
    p.add_argument(
        "--output",
        type=str,
        help="Optional path to write the generated cover letter. Prints to stdout if omitted.",
    )
    return p.parse_args()


def get_api_key(args):
    if args.api_key:
        return args.api_key
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        print("API key is required. Provide --api-key or set OPENAI_API_KEY.")
        sys.exit(1)
    return key


def main():
    args = parse_arguments()
    DatabaseHandler()  # initializes DB and BaseModel session

    job = JobPost.get(args.job_id)
    if not job:
        print(f"Job with ID {args.job_id} not found.")
        sys.exit(1)

    resume = Resume.get(args.resume_id)
    if not resume:
        print(f"Resume with ID {args.resume_id} not found.")
        sys.exit(1)

    api_key = get_api_key(args)
    client = OpenAI(api_key=api_key)

    env = Environment(loader=FileSystemLoader("templates"))
    tmpl = env.get_template("cover_letter_prompt.j2")
    prompt = tmpl.render(
        job_title=getattr(job, "title", None),
        company_name=getattr(job, "company_name", None)
        or getattr(job, "company_display_name", None),
        job_description=job.description,
        resume=resume.content,
    )

    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "You are a professional cover letter writer. Output only the letter text.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
    )
    cover_letter = completion.choices[0].message.content.strip()

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(cover_letter)
        print(f"Wrote cover letter to {args.output}")
    else:
        print("=" * 60)
        print("COVER LETTER")
        print("=" * 60)
        print(cover_letter)
        print("=" * 60)


if __name__ == "__main__":
    main()
