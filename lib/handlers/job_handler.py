#!/usr/bin/env python3
from datetime import datetime
from lib.scrapers.parser_creation import JobSiteParser
from lib.parsers.generic import JobParser
from lib.scoring.job_scorer import JobScorer
from lib.models.company import Company
from lib.models.job import Job
from lib.models.scrape import Scrape
from urllib.parse import urlparse
from openai import OpenAI
import json

class JobHandler:
    def __init__(self, api_key):
        self.api_key = api_key
        self.client = OpenAI(api_key=api_key)
        self._html_content = None
        self._job_description = None
        self._scrape = None
        self._job = None
        self._company = None
        self._selectors = None


    def parser_from_url(self, url):
        scrape = Scrape.find_by(url=url)
        return scrape

    def save_job_description(self, job_description, company_id):
        self.db_handler.save_job_description(job_description, company_id)

    def save_scraper_data(self, url, css_selectors_json, html):
        # Extract host from URL
        parsed_url = urlparse(url)
        host = parsed_url.netloc

        # Use first_or_create to find or create the scrape data
        scrape_data, created = ScrapeData.first_or_create(
            session=self.session,
            defaults={'css_selectors_json': css_selectors_json, 'html': html},
            host=host,
            url=url
        )

    def parse_job_description(self, selectors, html):
        jp = JobParser(self.client)
        return jp.extract_data_with_selectors(selectors, html)

    def score_job_match(self, job_description, resume):
        job_scorer = JobScorer(self.client)
        return job_scorer.score_job_match(job_description, resume)

    @property
    def url(self):
        return self._scrape.url

    @url.setter
    def url(self, url):
        self._scrape = Scrape.first_or_initialize(url=url)

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
    def company(self):
        return self._company

    @company.setter
    def company(self, company):
        formatted_company = company.strip()
        self._company, _ = Company.first_or_create(name = formatted_company)

    @property
    def job_description(self):
        return self._job_description

    @job_description.setter
    def job_description(self, job: Job) -> None:
        self._job_description = job

    def job_from_description(self, description: dict) -> Job:
        if self.company is None:
            raise ValueError("company not set.")

        job, _ = Job.first_or_create(
            defaults={'description': description.get('description'),
                      'posted_date': description.get('posted_date', datetime.now())},
            title=description.get('title'),
            company_id=self.company.id
        )
        self._job_description = job
    @property
    def selectors(self) -> dict:
        return self._selectors

    @selectors.setter
    def selectors(self, selectors: str):
        try:
            self._selectors = json.loads(selectors)
        except Exception as e:
            breakpoint()
            raise e

    def save(self):
        self.company.save()
        self.job_description.save()
