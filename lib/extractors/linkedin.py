import asyncio
import json
from playwright.async_api import async_playwright

class LinkedInActor:
    def __init__(self, email: str, password: str, cookies_file='cookies.json'):
        self.email = email
        self.password = password
        self.cookies_file = cookies_file
        self.playwright = None
        self.browser = None
        self.browser_context = None
        self.page = None

    async def start_browser(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=False)
        self.browser_context = await self.browser.new_context()
        self.page = await self.browser_context.new_page()
        await self.load_cookies()
        await self.page.goto('https://www.linkedin.com')
        if not await self.is_logged_in():
            await self.login()
            await self.save_cookies()

    async def is_logged_in(self):
        try:
            await self.page.goto('https://www.linkedin.com/feed/')
            await self.page.wait_for_selector('.global-nav__me-photo', timeout=5000)
            return True
        except:
            return False

    async def login(self):
        try:
            await self.page.goto('https://www.linkedin.com/login')
            await self.page.fill('input#username', self.email)
            await self.page.fill('input#password', self.password)
            await self.page.click('button[type="submit"]')
            await self.page.wait_for_load_state('networkidle')
        except Exception as e:
            print('Login error:', e)

    async def navigate_to_job(self, job_url: str):
        if not self.page:
            print('Browser not started!')
            return None

        try:
            print("*" * 88)
            print(f"goto: {job_url}")
            print("*" * 88)
            await self.page.goto(job_url)
            await self.page.wait_for_load_state('networkidle')  # Ensure the page is fully loaded

            # Extract job details
            job_title = await self.page.inner_text('h1')
            company_name = await self.page.inner_text('.topcard__org-name-link')
            job_location = await self.page.inner_text('.topcard__flavor--bullet')

            return {
                'Job Title': job_title,
                'Company': company_name,
                'Location': job_location,
            }
        except Exception as e:
            print('Navigation error:', e)
            return None

    async def save_cookies(self):
        cookies = await self.browser_context.cookies()
        with open(self.cookies_file, 'w') as f:
            json.dump(cookies, f)

    async def load_cookies(self):
        try:
            with open(self.cookies_file, 'r') as f:
                cookies = json.load(f)
                await self.browser_context.add_cookies(cookies)
        except FileNotFoundError:
            pass

    async def close_browser(self):
        if self.browser_context:
            await self.browser_context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def get_job_details(self, job_url: str):
        await self.start_browser()
        job_details = await self.navigate_to_job(job_url)
        await self.close_browser()
        return job_details
