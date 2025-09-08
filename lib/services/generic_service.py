from lib.parsers import GenericParser
from lib.scrapers import GenericScraper
from lib.models import Scrape


class GenericService:
    def __init__(self, url, browser, ai_client, creds={}):
        self.url = url
        self.browser = browser
        self.creds = creds  # Not referenced
        self.scraper = GenericScraper(browser, url)
        self.parser = GenericParser(ai_client)
        self.scrape = None

    async def process(self) -> Scrape:
        async for scrape in self.scraper.process():
            self.scrape = scrape
            # Process the scrape with the parser
            parsed_scrape = self.parser.parse(scrape)
            return parsed_scrape
        return self.scrape
