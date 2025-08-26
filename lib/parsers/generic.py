import requests
import openai
from openai import OpenAI
from bs4 import BeautifulSoup
import argparse
import os
import sys
import json

class JobParser:
    def __init__(self, client):
        self.client = client

    def extract_data_with_selectors(self, css_selectors_json, html_content):
        # Parse the HTML content
        soup = BeautifulSoup(html_content, 'html.parser')

        # Load the CSS selectors from JSON
        selectors = json.loads(css_selectors_json)

        # Extract data using the selectors
        title = soup.select_one(selectors.get('title')).get_text(strip=True) if selectors.get('title') and soup.select_one(selectors.get('title')) else None
        description = soup.select_one(selectors.get('description')).get_text(strip=True) if selectors.get('description') and soup.select_one(selectors.get('description')) else None
        company = soup.select_one(selectors.get('company')).get_text(strip=True) if selectors.get('company') and soup.select_one(selectors.get('company')) else None

        return {
            "title": title,
            "description": description,
            "company": company
        }

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

    def analyze_html_with_chatgpt(self, html_content, css_selectors_json):
        prompt = f"""
        Given the following webpage HTML content and CSS selectors JSON, extract the job title, company name, and the main job description:

        HTML: {html_content}
        CSS Selectors JSON: {css_selectors_json}

        Please provide the title, company, and the description of the job in the following json format:

        """ + """
        {
            "title": "{{title}}",
            "description": "{{description}}",
            "company": "{{company}}"
        }
        """

        try:
            response = self.client.completions.create(
                engine="text-davinci-002",
                prompt=prompt,
                max_tokens=300  # Adjust based on expected output
            )
            return response.choices[0].text.strip()
        except openai.OpenAIError as e:
            print(f"Error analyzing with ChatGPT: {e}")
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

    parser = JobParser(client)

    # Assuming you have a function to fetch data from the database
    from modules.database.db_handler import DatabaseHandler
    db_handler = DatabaseHandler()
    fetched_data = db_handler.fetch_parser_from_url(args.url)
    if fetched_data:
        css_selectors_json, url, html_content = fetched_data
        extracted_data = parser.extract_data_with_selectors(html_content, css_selectors_json)
        print("Extracted Data:")
        print(extracted_data)
    else:
        print("No CSS selectors found for the URL.")
    db_handler.close()

if __name__ == '__main__':
    main()
