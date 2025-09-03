import asyncio
from lib.parsers import GenericParser
from lib.scrapers import GenericScraper
from lib.models import Scrape

class GenericService:
    def __init__(self, url, browser, ai_client):
        self.url = url
        self.browser = browser
        self.scraper = GenericScraper(browser, url)
        self.parser = GenericParser(ai_client)
        self.scrape = None

    async def process(self) -> Scrape:
        async for scrape in self.scraper.process():
            self.scrape = scrape
