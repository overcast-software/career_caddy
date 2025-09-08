import argparse
import sys
import os
from lib.handlers.db_handler import DatabaseHandler
from lib.models.resume import Resume
from lib.models.user import User


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="CLI for converting resumes to database format."
    )
    parser.add_argument("resume_path", type=str, help="The path to the resume file.")
    parser.add_argument(
        "--user-id",
        type=int,
        default=1,
        help="The user ID to associate with the resume.",
    )
    return parser.parse_args()


def resolve_user(args):
    if args.user_email:
        user = User.find_by(email=args.user_email)
        if not user:
            raise ValueError(f"No user found with email {args.user_email}.")
        return user
    if os.getenv("USERNAME"):
        user = User.find_by(name=os.getenv("USERNAME"))
        if not user:
            raise ValueError(f"No user found with name {os.getenv('USERNAME')}")
        return user
    cnt = User.count()
    if cnt == 1:
        return User.first()
    if cnt == 0:
        raise ValueError(
            "No users found in database."
            "Please create a user first using cli/load_user.py"
        )
    raise ValueError(
        "Multiple users found."
        "Set USERNAME env var or use --user-email to select a user."
    )


def main():
    args = parse_arguments()
    DatabaseHandler()

    # Check if user exists
    user = resolve_user(args)
    try:
        resume = Resume.from_path_and_user_id(args.resume_path, user.id)
        print(f"Resume saved to database with ID: {resume.id}")
        print(f"File path: {resume.file_path}")
        print(f"Content length: {len(resume.content)} characters")
    except FileNotFoundError:
        print(f"Resume file not found: {args.resume_path}")
        sys.exit(1)
    except Exception as e:
        print(f"Error processing resume: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
