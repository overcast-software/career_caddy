# JobHandler
# Instantiates the things necessary to extract job data
# instantiates chatgpt client
# It's kinda dumb
# it calls the methods from the extractor interface
# really it could be kicked off with a url
import requests
import json
import re
from datetime import datetime
from lib.scrapers.parser_creation import JobSiteParser
from lib.parsers.generic import JobParser
from lib.scoring.job_scorer import JobScorer
from lib.models.company import Company
from lib.models.job import Job
from lib.models.scrape import Scrape
from urllib.parse import urlparse
from openai import OpenAI

class JobHandler:
    def __init__(self, url, api_key):
        self.url = url
        self.api_key = api_key
        self.client = OpenAI(api_key=api_key)
        self._html_content = None
        self._job_description = None
        self._scrape = None
        self._job = None
        self._company = None
        self._selectors = None


    def process_url(self):
        #when starting from nothing we instantiate a scrape
        scrape, newly_created = Scrape.first_or_create(
            url = self.url,
            host = self.host
        )
        if newly_created: #new url
            self.html_content = self.fetch_webpage()
            scrape.html = self.html_content
            scrape.save() # grab a save to prevent refetching
            parsed_jobsite = self.parse_webpage()
            self.company = self.get_company(parsed_jobsite)
            self.job = self.get_job(parsed_jobsite, self.company)
            scrape.company = self.company
            scrape.job = self.job
            scrape.save()

        else:
            self.company = scrape.job.company
            self.job = scrape.job
            self.html_content = scrape.html
        self.scrape = scrape
        return scrape

    def get_job(self, parsed_website: dict, company: Company) -> Job:
        #company must be established first
        job, _ = Job.from_json(parsed_website, company.id)
        return job

    def get_company(self, parsed_jobsite):
        company_name = parsed_jobsite.get('company').lower()
        company, _ = Company.first_or_create(name=company_name)
        return company

    def save_job_description(self, job_description, company_id):
        self.db_handler.save_job_description(job_description, company_id)

    def parse_job_description(self, selectors, html):
        jp = JobParser(self.client)
        return jp.extract_data_with_selectors(selectors, html)

    def score_job_match(self, job_description, resume) -> dict:
        job_scorer = JobScorer(self.client)
        score_and_eval=job_scorer.score_job_match(job_description, resume)
        score_match = re.search(r'Score: (\d+)', score_and_eval)
        score_explination = re.search(r'Evaluation: (.+)', score_and_eval, re.DOTALL)
        return {
            "evaluation": score_explination,
            "score": score_match
        }
