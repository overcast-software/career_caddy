from lib.models import JobPost, Resume
from jinja2 import Environment, FileSystemLoader


class SummaryService:
    def __init__(self, ai_client, job: JobPost, resume: Resume):
        self.job = job
        self.resume = resume
        self.env = Environment(loader=FileSystemLoader('templates'))
        self.ai_client = ai_client

    def generate_summary(self) -> str:
        template = self.env.get_template('summary_service_prompt.j2')
        prompt = template.render(job_description=self.job, resume=self.resume)
        breakpoint()
        response = self.ai_client.chat.completions.create(
            model="gpt-5",
            messages=[
                {
                    "role": "system",
                    "content": "You are a career counselor",
                },
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            # max_tokens=150 not supported with gpt-5
        )
        return response.choices[0].message.content.strip()
