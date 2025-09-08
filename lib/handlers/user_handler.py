#!/usr/bin/env python3
import os
from lib.models.user import User


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
