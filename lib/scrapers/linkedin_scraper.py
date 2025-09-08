# LinkedInScraper
from bs4 import BeautifulSoup
from lib.models.scrape import Scrape


class LinkedInScraper:
    def __init__(
        self, browser, url: str, credentials: dict = {}, cookies_file="cookies.json"
    ):
        self.username = credentials.get("username")
        self.password = credentials.get("password")
        self.cookies_file = cookies_file
        self.url = url
        self.browser = browser
        self.page = browser.page

    async def process(self):
        # this process might have an external link
        # if it does mark the scrape and move to the next
        # In this process the external link requires clicking
        # the link
        linkedin_scrape, is_new = Scrape.first_or_initialize(
            url=self.url,
        )
        # TODO sometimes we don't need to log in
        await self.test_login()

        if is_new or linkedin_scrape.html is None:
            print("contents needs to be downloaded")
            html_content = await self.browser.get_page_content(self.url)
            linkedin_scrape.html = html_content
        else:
            print("contents already downloaded")
            html_content = linkedin_scrape.html
            await self.page.goto(
                self.url,
                wait_until="domcontentloaded",
            )

        # Parse the HTML content with BeautifulSoup
        soup = BeautifulSoup(html_content, "html.parser")

        # Extract the <main> tag content
        main_content = soup.find("main")

        if linkedin_scrape.job_content is None:
            linkedin_scrape.job_content = str(main_content)
        linkedin_scrape.save()
        yield linkedin_scrape

        # Get the external URL and HTML content
        external_url, external_html = await self.get_external_url(html_content)
        if external_url:
            external_scrape = Scrape(
                url=external_url,
                html=external_html,
                source_scrape_id=linkedin_scrape.id,
            )
            external_scrape.save()
            yield external_scrape

    async def get_external_url(self, html_content: str):
        # Log the HTML content for debugging
        print("HTML Content Length:", len(html_content))

        # Parse the HTML content with BeautifulSoup
        soup = BeautifulSoup(html_content, "html.parser")

        # Find all button elements with the specified selector
        button_selector = ".jobs-apply-button--top-card button:first-child"
        button_elements = soup.select(button_selector)

        if button_elements:
            button_text = button_elements[0].get_text(strip=True)

            # Check if the button text is "Apply" and not "easy apply"
            if button_text == "Apply":
                try:
                    # Ensure the page is fully loaded
                    # content = await self.page.content()
                    # Log the presence of the element
                    element = await self.page.query_selector(button_selector)

                    if element:
                        print(
                            'Element with ID "jobs-apply-button-id" exists on the page.'
                        )
                    else:
                        print(
                            'Element with ID "jobs-apply-button-id" does not exist on the page.'
                        )
                        return None, None

                    # Wait for the button to be visible and click it
                    # await self.page.wait_for_selector(button_selector, state="visible", timeout=30000)
                    await self.page.click(button_selector)

                    # Wait for the network to be idle after clicking
                    await self.page.wait_for_load_state("domcontentloaded")

                    # Get the new page content and URL
                    new_html_content = await self.page.content()
                    new_url = self.page.url

                    # Return the new URL and HTML content
                    return new_url, new_html_content
                except Exception as e:
                    breakpoint()
                    print("Error during button click:", e)
                    return None, None

        return None, None

    async def test_login(self):
        try:
            # TODO try this with the job url too
            await self.page.goto("https://www.linkedin.com/feed/")
            # this is when you have cookies but there is an extra step saying you'd like to use this session
            if "linkedin.com/uas/login" in self.page.url:
                print("select session for logged in user")
                # this is a intermediate login prompt click the name
                # div.member-profile-container div.member-profile-bock
                user_login_block_selector = (
                    "div.member-profile-container div.member-profile-block"
                )
                await self.page.click(user_login_block_selector)
            else:  # not logged in
                await self.login()
            await self.page.wait_for_selector(".global-nav__me-photo", timeout=5000)
            print("found logged in user image.  logged in.")
            return True
        except Exception as e:
            print("Error checking login status:", e)
            return False

    async def login(self):
        try:
            await self.page.goto("https://www.linkedin.com/login")
            await self.page.fill("input#username", self.username)
            await self.page.fill("input#password", self.password)
            await self.page.click('button[type="submit"]')
            await self.page.wait_for_load_state("networkidle")
        except Exception as e:
            print("Login error:", e)
