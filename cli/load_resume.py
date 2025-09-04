
import argparse
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from lib.models.base import BaseModel
from lib.models.user import User
from lib.models.resume import Resume
from lib.handlers.db_handler import DatabaseHandler

def parse_arguments():
    parser = argparse.ArgumentParser(description='Load a resume into the database.')
    parser.add_argument('--user-email', required=False, help='Email of the user to associate with the resume.')
    parser.add_argument('--resume', type=str, help='Path to the resume file')
    return parser.parse_args()

def main():

    db_handler = DatabaseHandler()
    args = parse_arguments()

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
    resume_path = args.resume or os.getenv('RESUME_PATH')
    if not resume_path:
        raise ValueError("A resume file path must be provided either as an argument or through the RESUME_PATH environment variable.")
    resume = Resume.find_by(file_path=resume_path)
    if not resume and os.path.exists(resume_path):
        resume = Resume.from_path_and_user_id(resume_path, user.id)
    resume.save()

    print(f"Resume for user {user.email} has been loaded successfully.")

if __name__ == '__main__':
    main()
