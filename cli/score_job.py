# Score a job based on job_id and resume_id
#
import argparse
import sys
import re
from lib.handlers.db_handler import DatabaseHandler
from lib.handlers.chatgpt_handler import ai_client
from lib.models.resume import Resume
from lib.models.job_post import JobPost
from lib.models.score import Score
from lib.scoring.job_scorer import JobScorer


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="CLI for scoring resumes against job postings."
    )
    parser.add_argument(
        "resume_id",
        type=int,
        nargs="?",
        default=1,
        help="The ID of the resume to score (default: 1).",
    )
    parser.add_argument("job_id", type=int, help="The ID of the job to score against.")
    return parser.parse_args()


def main():
    args = parse_arguments()
    DatabaseHandler()

    resume = Resume.get(args.resume_id)
    job = JobPost.get(args.job_id)

    if not resume:
        print(f"Resume with ID {args.resume_id} not found.")
        sys.exit(1)

    if not job:
        print(f"Job with ID {args.job_id} not found.")
        sys.exit(1)

    scorer = JobScorer(ai_client)

    evaluation = scorer.score_job_match(job.description, resume.content)

    # Normalize evaluation to score (int) and explanation (str)
    def _parse_eval(e):
        if isinstance(e, dict):
            s = e.get("score")
            expl = e.get("explanation") or e.get("evaluation")
            if isinstance(expl, dict):
                expl = expl.get("text") or str(expl)
            if s is not None and expl:
                return int(s), str(expl)
        text = str(e)
        m_score = re.search(r"(?i)\bscore\s*[:\-]\s*(\d{1,3})", text)
        m_expl = re.search(r"(?i)\bexplanation\s*[:\-]\s*(.+)", text, re.DOTALL)
        s_val = int(m_score.group(1)) if m_score else None
        expl = m_expl.group(1).strip() if m_expl else text
        return s_val, expl

    score_value, explanation = _parse_eval(evaluation)

    print(f"Job: {job.title}")
    print(f"Resume: {resume.file_path}")
    print(f"Evaluation: {evaluation}")
    if score_value is None:
        print(
            "Could not parse a numeric score from evaluation; not saving to database."
        )
        sys.exit(1)

    user_id = getattr(
        resume, "user_id", getattr(getattr(resume, "user", None), "id", None)
    )
    score = Score(
        job_post_id=job.id,
        resume_id=resume.id,
        score=score_value,
        explanation=explanation,
        **({"user_id": user_id} if user_id is not None else {}),
    )
    score.save()
    print("Score saved to database.")


if __name__ == "__main__":
    main()
