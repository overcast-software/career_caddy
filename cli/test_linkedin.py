# test_linkedin
# first of many ways to process a job description
import asyncio
import sys
import yaml
import os
from urllib.parse import urlparse
from openai import OpenAI
from lib.services import LinkedInService
from lib.browser import BrowserManager
from lib.models import Scrape
from lib.handlers.db_handler import DatabaseHandler


def load_secrets(file_path='secrets.yml'):
    with open(file_path, 'r') as file:
        return yaml.safe_load(file)


def select_processor(host):
    exstractor = {
        'linkedin.com': LinkedInService,
        'www.linkedin.com': LinkedInService
    }

def get_api_key():
    if 'OPENAI_API_KEY' in os.environ:
        return os.environ['OPENAI_API_KEY']
    else:
        print("API key is required. Exiting...")
        sys.exit(1)


async def main():
    DatabaseHandler()
    # Load secrets
    secrets = load_secrets()

    linkedin = secrets.get('linkedin.com')
    email = linkedin.get('username', '')
    password = linkedin.get('password', '')

    api_key = get_api_key()
    client = OpenAI(api_key=api_key)
    # Ensure email and password are provided
    if not email or not password:
        print("Email or password not found in secrets.yml")
        return

    # Start LinkedIn actor
    url = "https://www.linkedin.com/jobs/view/4269598536"
    url = "https://www.linkedin.com/jobs/view/4291767968"
    credentials = {"username": email, "password": password}
    browser = BrowserManager()
    await browser.start_browser(False)
    parsed_url = urlparse(url)
    host = parsed_url.netloc
    linkedin_service_class = select_processor(host)
    # if Scrape.find_by(url=url) is not None:
    li_service = linkedin_service(url, browser, client, credentials)
    # the process runs down url if it needs to
    await li_service.process()
    if li_servie.external_scrape:
       #do something with external link

if __name__ == "__main__":
    asyncio.run(main())
