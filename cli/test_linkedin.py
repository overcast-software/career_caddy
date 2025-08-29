import asyncio
import yaml
from lib.extractors.linkedin import LinkedInActor

def load_secrets(file_path='secrets.yml'):
    with open(file_path, 'r') as file:
        return yaml.safe_load(file)

async def main():
    # Load secrets
    secrets = load_secrets()

    linkedin = secrets.get('linkedin')
    email = linkedin.get('username', '')
    password = linkedin.get('password', '')

    # Ensure email and password are provided
    if not email or not password:
        print("Email or password not found in secrets.yml")
        return

    # Start LinkedIn actor
    url = "https://www.linkedin.com/jobs/view/4269598536"
    actor = LinkedInActor(email, password)
    job_details = await actor.get_job_details(url)
    if job_details:
        print(job_details)

if __name__ == "__main__":
    asyncio.run(main())
