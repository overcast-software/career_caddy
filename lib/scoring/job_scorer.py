import openai
from jinja2 import Environment, FileSystemLoader

class JobScorer:
    def __init__(self, client):
        self.client = client
    def score_job_match(self, job_description, resume):
        template = self.env.get_template('job_scorer_prompt.j2')
        prompt = template.render(
            job_description=job_description,
            resume=resume
        )
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                max_tokens=500
            )
            evaluation = response.choices[0].message.content.strip()
            print(evaluation)
            return evaluation
        except openai.OpenAIError as e:
            print(f"Error scoring job match: {e}")
            return None
