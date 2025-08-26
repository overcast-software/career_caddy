import requests
import openai
from openai import OpenAI
import argparse
import os
import sys

class JobScrapper:
    def __init__(self, client):
        self.client = client

    def get_raw_html(self, url):
        try:
            # Prevent automatic redirects
            response = requests.get(url, allow_redirects=False)
            if response.status_code in (301, 302):
                print("Redirect detected, exiting process.")
                sys.exit(1)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            print(f"Error fetching page: {e}")
            sys.exit(1)

def get_api_key(args):
    if args.api_key:
        return args.api_key
    elif 'OPENAI_API_KEY' in os.environ:
        return os.environ['OPENAI_API_KEY']
    else:
        print("API key is required. Exiting...")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Scrape job details and analyze using OpenAI")
    parser.add_argument('url', type=str, help='URL of the job description')
    parser.add_argument('--api-key', type=str, help='OpenAI API key')

    args = parser.parse_args()

    api_key = get_api_key(args)
    client = OpenAI(api_key=api_key)

    scraper = JobScrapper(client)
    raw_html = scraper.get_raw_html(args.url)

    if raw_html:
        print("HTML Content Retrieved")
        # Assuming you have a function to fetch data from the database
        from modules.database.db_handler import DatabaseHandler
        db_handler = DatabaseHandler()
        fetched_data = db_handler.fetch_parser_from_url(args.url)
        if fetched_data:
            css_selectors_json = fetched_data[0]
            analysis = scraper.analyze_html_with_chatgpt(raw_html, css_selectors_json)
            print("Analysis Result:")
            print(analysis)
        else:
            print("No CSS selectors found for the URL.")
        db_handler.close()
    else:
        print("Failed to retrieve HTML content.")
        sys.exit(1)

if __name__ == '__main__':
    main()
