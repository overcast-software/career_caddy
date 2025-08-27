
import argparse
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from lib.models.base import BaseModel
from lib.models.user import User
from lib.models.resume import Resume

def parse_arguments():
    parser = argparse.ArgumentParser(description='Load a resume into the database.')
    parser.add_argument('--user-email', required=True, help='Email of the user to associate with the resume.')
    parser.add_argument('--resume-content', required=True, help='Content of the resume to load.')
    return parser.parse_args()

def main():
    args = parse_arguments()

    # Create a database engine and session
    engine = create_engine('sqlite:///job_data.db')  # Replace with your actual database URL
    Session = sessionmaker(bind=engine)
    session = Session()

    # Set the session for BaseModel
    BaseModel.set_session(session)

    # Find or create the user
    user, created = User.first_or_create(email=args.user_email, defaults={'name': 'Default Name'})

    # Create a new resume
    resume = Resume(content=args.resume_content, user=user)

    # Save the resume to the database
    resume.save()

    print(f"Resume for user {user.email} has been loaded successfully.")

if __name__ == '__main__':
    main()
