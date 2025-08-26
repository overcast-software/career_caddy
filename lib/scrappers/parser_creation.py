import argparse
import requests
from openai import OpenAI
import os
import sys

class JobSiteParser:
    def __init__(self, client):
        self.parser = argparse.ArgumentParser(description='Parse job site URL and extract CSS selectors.')
        self.client = client

    def setup_arguments(self):
        self.parser.add_argument('url', type=str, help='The URL of the job site to parse.')

    def parse(self):
        self.setup_arguments()
        return self.parser.parse_args()

    def fetch_webpage(self, url):
        response = requests.get(url)
        response.raise_for_status()  # Raise an error for bad responses
        return response.text

    def find_css_selectors(self, url, html_content):
        prompt = (
            f"Given the following HTML content, identify the CSS selectors for the job title, "
            f"job description, and company name. Responses must be JSON compliant with keys: title, "
            f"description, company, and url.  Remove any markdown from response and reply with only json\n\n"
            f"url: {url}\n"
            f"html: {html_content}"
        )
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            max_tokens=150
        )
        return response.choices[0].message.content.strip()

def get_api_key(args):
    if args.api_key:
        return args.api_key
    elif 'OPENAI_API_KEY' in os.environ:
        return os.environ['OPENAI_API_KEY']
    else:
        print("API key is required. Exiting...")
        sys.exit(1)
# Usage
def main():
    parser = argparse.ArgumentParser(description="Scrape job details and analyze using OpenAI")
    parser.add_argument('url', type=str, help='URL of the job description')
    parser.add_argument('--api-key', type=str, help='OpenAI API key')
    args = parser.parse_args()
    url = args.url

    api_key = get_api_key(args)
    client = OpenAI(api_key=api_key)
    # Fetch the webpage content
    jsp = JobSiteParser(client)
    html_content = jsp.fetch_webpage(url)

    # Use ChatGPT to find CSS selectors
    css_selectors = jsp.find_css_selectors(url, html_content)
    print(css_selectors)

if __name__ == "__main__":
    main()
