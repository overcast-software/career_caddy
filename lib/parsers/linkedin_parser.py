# LinkedInParser
# finds details of job and descriptoin
# from linkedin website
import requests
import openai
from openai import OpenAI
from bs4 import BeautifulSoup
from lib.models import Company, Job
import os
import sys
import json
from jinja2 import Environment, FileSystemLoader
from datetime import datetime

class LinkedInParser:
    def __init__(self, client):
        self.client = client
        # Set up Jinja2 environment
        self.env = Environment(loader=FileSystemLoader('templates'))

    def parse(self, scrape):
        if scrape.job_id:
            print("*"*88)
            print("scrape completed: NOOP")
            print("*"*88)
            return
        #job content is necessary since the html is too big
        if scrape.job_content is None:
            print("*"*88)
            print('job_content is none: evaluating.')
            print("*"*88)
            raise ValueError("job_content cannot be None")
        evaluation = self.analyze_with_ai(scrape.html, scrape.url)
        if type(evaluation) is str:
            print("*"*88)
            print("convert to json")
            print("*"*88)

            evaluation = json.loads(evaluation)

        print("*"*88)
        print(evaluation)
        print("*"*88)
        self.process_evaluation(scrape, evaluation)
        return scrape

    def process_evaluation(self, scrape, evaluation):
        """
        Push dom into chatgpt for evaluation
        """
        try:
            print("*"*88)
            print("save off data")
            print("*"*88)

            company, _ = Company.first_or_create(
                name=evaluation['company']
            )
            job, _ = Job.first_or_create(
                title=evaluation["title"],
                company_id=company.id,
                defaults={"description": evaluation.get("description")}
            )
            scrape.job_id = job.id
            scrape.save()
        except Exception as e:
            print(e)
            breakpoint()

    def analyze_with_ai(self, html_content, url) -> str:
        template = self.env.get_template('job_parser_prompt.j2')
        # Get today's date
        today_date = datetime.now().strftime('%Y-%m-%d')
        # Render the template with html_content and today's date
        prompt = template.render(html_content=html_content, today_date=today_date)
        messages = [
            {"role": "system", "content": "You are a bot that evaluates html of job posts to extract relevant data as JSON"},
            {"role": "user", "content": prompt}
        ]
        print("*"*88)
        print("call chatgpt")
        print("*"*88)
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                max_tokens=2000
            )
            response = response.choices[0].message.content.strip()
            return json.loads(response)
        except openai.OpenAIError as e:
            print(f"Error analyzing with ChatGPT: {e}")
            sys.exit(1)
        except Exception as e:
            # Might want to strip some markdown here
            print(f"Error: {e}")
