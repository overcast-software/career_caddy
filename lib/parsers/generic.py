import requests
import openai
from openai import OpenAI
from bs4 import BeautifulSoup
import os
import sys
import json

class JobParser:
    def __init__(self, client):
        self.client = client

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

    def analyze_html_with_chatgpt(self, html_content) -> str:
        messages = [
            {"role": "system", "content": "You are a bot that evaluates html of job posts to extract relevant data as JSON"},
            {"role": "user", "content": f"""
        Given the following webpage HTML content, extract the job title, company name, posted date and the job description fromt the html:

        HTML: {html_content}

        Please provide the title, company, posted_date and the description of the job in the following json format:\n
        """+"""\n
        {
            "title": "{{title}}",
            "description": "{{description}}",
            "company": "{{company}}",
            "posted_date": "{{posted_date}}"
        }\n
        posted date is null if not explicit.\n
        It is mandatory that you remove any markdown from the response and only respond JSON complain string.\n
        Be certain to evaluate the accuracy of the format of your answer before responding.
        Make sure no markdown such as '```json' exist in the response.
        """}
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
