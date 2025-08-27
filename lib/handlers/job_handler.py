# JobHandler
# Instantiates the things necessary to extract job data
# instantiates chatgpt client
# It's kinda dumb
# it calls the methods from the extractor interface
# really it could be kicked off with a url
from datetime import datetime
from lib.scrapers.parser_creation import JobSiteParser
from lib.parsers.generic import JobParser
from lib.scoring.job_scorer import JobScorer
from lib.models.company import Company
from lib.models.job import Job
from lib.models.scrape import Scrape
from urllib.parse import urlparse
from openai import OpenAI
import requests
import json

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

    def parse_webpage(self) -> dict:
        #this is where extractors would come in
        #accuracy will matter
        job_parser = JobParser(self.client)
        job_json_string = job_parser.analyze_html_with_chatgpt(self.html_content)
        parsed_job = json.loads(job_json_string)
        return parsed_job

    def get_job(self, parsed_website: dict, company: Company) -> Job:
        #company must be established first
        job, _ = Job.from_json(parsed_website, company.id)
        return job

    def get_company(self, parsed_jobsite):
        company_name = parsed_jobsite.get('company').lower()
        company, _ = Company.first_or_create(name=company_name)
        return company

    def select_extractor(self):
        {
           "greenhouse.io": {}
        }

    def fetch_webpage(self):
        response = requests.get(self.url)
        response.raise_for_status()  # Raise an error for bad responses
        return response.text

    def parser_from_url(self, url):
        scrape = Scrape.find_by(url=url)
        return scrape

    def save_job_description(self, job_description, company_id):
        self.db_handler.save_job_description(job_description, company_id)

    def parse_job_description(self, selectors, html):
        jp = JobParser(self.client)
        return jp.extract_data_with_selectors(selectors, html)

    def score_job_match(self, job_description, resume):
        job_scorer = JobScorer(self.client)
        return job_scorer.score_job_match(job_description, resume)

    @property
    def scrape(self):
        return self._scrape

    @scrape.setter
    def scrape(self, scrape):
        self._scrape = scrape

    @property
    def html_content(self):
        return self._html_content

    @html_content.setter
    def html_content(self, content):
        self._html_content = content

    @property
    def host(self):
        parsed_url = urlparse(self.url)
        host = parsed_url.netloc
        return host
