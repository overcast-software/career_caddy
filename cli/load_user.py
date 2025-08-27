#!/usr/bin/env python3

import argparse
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from lib.models.base import BaseModel
from lib.models.user import User

def parse_arguments():
    parser = argparse.ArgumentParser(description='Load a user into the database.')
    parser.add_argument('--name', help='Name of the user.')
    parser.add_argument('--email', help='Email of the user.')
    return parser.parse_args()

def prompt_for_missing_info(args):
    if not args.name:
        args.name = input("Enter the user's name: ")
    if not args.email:
        args.email = input("Enter the user's email: ")

def main():
    args = parse_arguments()
    prompt_for_missing_info(args)

    # Create a database engine and session
    engine = create_engine('sqlite:///job_data.db')  # Replace with your actual database URL
    Session = sessionmaker(bind=engine)
    session = Session()

    # Set the session for BaseModel
    BaseModel.set_session(session)

    # Find or create the user
    user, created = User.first_or_create(name=args.name, email=args.email)

    if created:
        print(f"User {user.name} with email {user.email} has been created successfully.")
    else:
        print(f"User {user.name} with email {user.email} already exists.")

if __name__ == '__main__':
    main()
