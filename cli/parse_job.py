#!/usr/bin/env python3

import argparse
import os
import sys
from openai import OpenAI
from lib.parsers.generic import JobParser

def get_api_key(args):
    if args.api_key:
        return args.api_key
    elif 'OPENAI_API_KEY' in os.environ:
        return os.environ['OPENAI_API_KEY']
    else:
        print("API key is required. Exiting...")
        sys.exit(1)

def parse_arguments():
    parser = argparse.ArgumentParser(description="Scrape job details and analyze using OpenAI")
    parser.add_argument('url', type=str, help='URL of the job description')
    parser.add_argument('--api-key', type=str, help='OpenAI API key')
    return parser.parse_args()

def main():
    args = parse_arguments()

    api_key = get_api_key(args)
    client = OpenAI(api_key=api_key)

    parser = JobParser(client)

    # Assuming you have a function to fetch data from the database
    from modules.database.db_handler import DatabaseHandler
    db_handler = DatabaseHandler()
    fetched_data = db_handler.fetch_parser_from_url(args.url)
    if fetched_data:
        css_selectors_json, url, html_content = fetched_data
        extracted_data = parser.extract_data_with_selectors(html_content, css_selectors_json)

        # Breakpoint or further processing
        print("Extracted Data:")
        print(extracted_data)
    else:
        print("No CSS selectors found for the URL.")
    db_handler.close()

if __name__ == '__main__':
    main()
