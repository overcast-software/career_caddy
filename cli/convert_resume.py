import argparse
import sys
from lib.handlers.db_handler import DatabaseHandler
from lib.models.resume import Resume
from lib.models.user import User

def parse_arguments():
    parser = argparse.ArgumentParser(description="CLI for converting resumes to database format.")
    parser.add_argument('resume_path', type=str, help='The path to the resume file.')
    parser.add_argument('--user-id', type=int, default=1, help='The user ID to associate with the resume.')
    return parser.parse_args()

def main():
    args = parse_arguments()
    db_handler = DatabaseHandler()

    # Check if user exists
    user = db_handler.session.query(User).get(args.user_id)
    if not user:
        print(f"User with ID {args.user_id} not found. Creating default user.")
        user = User(name="Default User", email="default@example.com")
        db_handler.session.add(user)
        db_handler.session.commit()

    try:
        resume = Resume.from_path_and_user_id(args.resume_path, args.user_id)
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
