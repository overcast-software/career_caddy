import requests
import openai
from openai import OpenAI
from bs4 import BeautifulSoup
from lib.models import Scrape
import os
import sys
import json
from jinja2 import Environment, FileSystemLoader

class GenericParser:
    def __init__(self, client):
        self.client = client
        # Set up Jinja2 environment
        self.env = Environment(loader=FileSystemLoader('templates'))

    def extract_data_with_selectors(self, html_content, css_selectors_json):
        # Parse the HTML content
        soup = BeautifulSoup(html_content, 'html.parser')

        # Load the CSS selectors from JSON
        selectors = json.loads(css_selectors_json)

        # Extract data using the selectors
        title = soup.select_one(selectors.get('title')).get_text(strip=True) if selectors.get('title') and soup.select_one(selectors.get('title')) else None
        description = soup.select_one(selectors.get('description')).get_text(strip=True) if selectors.get('description') and soup.select_one(selectors.get('description')) else None
        company = soup.select_one(selectors.get('company')).get_text(strip=True) if selectors.get('company') and soup.select_one(selectors.get('company')) else None
        posted_date = soup.select_one(selectors.get('posted_date')).get_text(strip=True) if selectors.get('posted_date') and soup.select_one(selectors.get('posted_date')) else None

        return {
            "title": title,
            "description": description,
            "company": company,
            "posted_date": posted_date
        }

    def parse(self, scrape: Scrape):
        breakpoint()
        pass


    def analyze_html_with_chatgpt(self, html_content) -> str:
        # Load and render the template
        template = self.env.get_template('job_parser_prompt.j2')
        prompt = template.render(html_content=html_content)

        messages = [
            {"role": "system", "content": "You are a bot that evaluates html of job posts to extract relevant data as JSON"},
            {"role": "user", "content": prompt}
        ]

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                max_tokens=2000
            )
            return response.choices[0].message.content.strip()
        except openai.OpenAIError as e:
            print(f"Error analyzing with ChatGPT: {e}")
            sys.exit(1)
