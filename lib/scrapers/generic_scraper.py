from lib.models.scrape import Scrape
from markdownify import markdownify as md


class GenericScraper:
    def __init__(self, browser, url):
        self.url = url
        self.browser = browser

    async def process(self):
        scrape, is_new = Scrape.first_or_initialize(
            url=self.url,
        )

        if is_new or scrape.html is None:
            print("contents needs to be downloaded")
            html_content = await self.browser.get_page_content(self.url)
            scrape.html = html_content
        else:
            print("contents already downloaded")
            html_content = scrape.html
            await self.browser.page.goto(
                self.url,
                wait_until="domcontentloaded",
            )

        # convert that shit to markdown
        markdown_text = md(html_content)
        scrape.job_content = markdown_text
        scrape.save()
        yield scrape
