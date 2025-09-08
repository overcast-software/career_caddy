# JobSiteParser
# use chatgpt to find css selectors for building extractors
# right now it informs the scrape record
import argparse
import requests
from openai import OpenAI
import os
import sys


class JobSiteParser:
    def __init__(self, client):
        self.parser = argparse.ArgumentParser(
            description="Parse job site URL and extract CSS selectors."
        )
        self.client = client

    def setup_arguments(self):
        self.parser.add_argument(
            "url", type=str, help="The URL of the job site to parse."
        )

    def parse(self):
        self.setup_arguments()
        return self.parser.parse_args()

    def fetch_webpage(self, url):
        response = requests.get(url)
        response.raise_for_status()  # Raise an error for bad responses
        return response.text

    def find_css_selectors(self, html_content) -> str:
        prompt = (
            f"Given the following HTML content, identify the CSS selectors for extracting the job title, \n"
            f"job description, posted date and company name.\n"
            f"Company name is the name of the company posting the job and no other information.\n"
            f"Job description is the long form description of the job and it's requirements\n"
            f"Job title is the role's title\n"
            f"posted date is the either an obvious date of posting or null\n"
            f"Responses must be JSON compliant with keys: title, description, company, and posted_date.\n"
            "It is mandatory that the response has no markdown\n"
            "and only contains a JSON compliant string.\n"
            "Review the output to make sure before sending.\n\n"
            f"html:\n {html_content}"
        )
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are a machine that can asses css selectors from html content.  You specialize in extracting job data from webpages. and you only reply in complain json format",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            max_tokens=150,
        )
        return response.choices[0].message.content.strip()


def get_api_key(args):
    if args.api_key:
        return args.api_key
    elif "OPENAI_API_KEY" in os.environ:
        return os.environ["OPENAI_API_KEY"]
    else:
        print("API key is required. Exiting...")
        sys.exit(1)


# Usage
def main():
    parser = argparse.ArgumentParser(
        description="Scrape job details and analyze using OpenAI"
    )
    parser.add_argument("url", type=str, help="URL of the job description")
    parser.add_argument("--api-key", type=str, help="OpenAI API key")
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
