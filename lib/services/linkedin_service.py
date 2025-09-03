# LinkedInService

import asyncio
from lib.parsers import LinkedInParser
from lib.scrapers import LinkedInScraper
from lib.models import Scrape


class LinkedInService:
    def __init__(self, url, browser, ai_client, credentials):
        """
        Keyword Arguments:
        url  -- Url for the linkedin job posting
        """
        self.url = url
        self.browser = browser
        self.ai_client = ai_client
        self.scraper = LinkedInScraper(browser, url, credentials)
        self.parser = LinkedInParser(ai_client)
        self.scrape = None
        self.external_scrape = None

    async def process(self) -> Scrape:
        # scrape and parse
        async for scrape in self.scraper.process():
            #first scrapes linkedin then the external link
            if "linkedin.com" in scrape.host:
                # create job post based on linkedin url
                self.scrape = scrape
                self.parser.parser(scrape)
            else:
                # an external destination when clicking "Apply"
                # electing not to do anything with it here
                # too many libraries needed to keep scraping
                self.external_scrape = scrape
