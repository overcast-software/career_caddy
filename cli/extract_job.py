import asyncio
import yaml
import argparse
from urllib.parse import urlparse
import os
import sys
from openai import OpenAI
from lib.browser import BrowserManager
from lib.handlers.db_handler import DatabaseHandler
from lib.select_service import SelectService

def load_secrets(file_path='secrets.yml'):
    with open(file_path, 'r') as file:
        return yaml.safe_load(file)

def parse_arguments():
    parser = argparse.ArgumentParser(description="CLI for parsing job site URLs and extracting CSS selectors.")
    parser.add_argument('url', type=str, help='The URL of the job site to parse.')
    parser.add_argument('--api-key', type=str, help='OpenAI API key')
    return parser.parse_args()

def get_api_key():
    if 'OPENAI_API_KEY' in os.environ:
        return os.environ['OPENAI_API_KEY']
    else:
        print("API key is required. Exiting...")
        sys.exit(1)

async def main():
    DatabaseHandler()

    secrets = load_secrets()
    args = parse_arguments()

    api_key = get_api_key()
    ai_client = OpenAI(api_key=api_key)
    parsed_url = urlparse(args.url)
    host = parsed_url.netloc

    browser_manager = BrowserManager()
    service_selector = SelectService(host)
    creds = service_selector.get_creds(secrets)
    my_service = service_selector.service(args.url, browser_manager, ai_client, creds)
    # Initialize BrowserManager
    try:
        await browser_manager.start_browser(headless=False)

        await my_service.process()

    finally:
        await browser_manager.close_browser()

if __name__ == "__main__":
    asyncio.run(main())
