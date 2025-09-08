#!/usr/bin/env python3
import os
import sys
from openai import OpenAI


def get_api_key():
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        print("API key is required. Set OPENAI_API_KEY environment variable.")
        sys.exit(1)
    return key


ai_client = OpenAI(api_key=get_api_key())
