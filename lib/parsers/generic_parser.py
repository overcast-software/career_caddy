import openai
from lib.models import Scrape, JobPost, Company
import sys
import json
from jinja2 import Environment, FileSystemLoader


class GenericParser:
    def __init__(self, client):
        self.client = client
        # Set up Jinja2 environment
        self.env = Environment(loader=FileSystemLoader("templates"))

    def parse(self, scrape: Scrape):
        job_description = self.analyze_html_with_ai(scrape)
        evaluation = json.loads(job_description)
        self.process_evaluation(scrape, evaluation)

    def process_evaluation(self, scrape, evaluation):
        """
        Push dom into chatgpt for evaluation
        """
        try:
            print("*" * 88)
            print("save off data")
            print("*" * 88)

            company, _ = Company.first_or_create(
                name=evaluation["company_name"],
                display_name=evaluation.get("company_display_name", None),
            )
            print(f"company id: {company.id}")
            job, _ = JobPost.first_or_create(
                title=evaluation["title"],
                company_id=company.id,
                defaults={"description": evaluation.get("description")},
            )
            print(f"job post id: {job.id}")
            scrape.job_id = job.id
            scrape.save()
        except Exception as e:
            print(e)
            breakpoint()

    def analyze_html_with_ai(self, scrape: Scrape) -> str:
        # Load and render the template
        template = self.env.get_template("job_parser_prompt.j2")
        prompt = template.render(html_content=scrape.html)

        messages = [
            {
                "role": "system",
                "content": "You are a bot that evaluates html of job posts to extract relevant data as JSON",
            },
            {"role": "user", "content": prompt},
        ]

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o", messages=messages, max_tokens=2000
            )
            return response.choices[0].message.content.strip()
        except openai.OpenAIError as e:
            print(f"Error analyzing with ChatGPT: {e}")
            sys.exit(1)
