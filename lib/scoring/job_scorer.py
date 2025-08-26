import openai

class JobScorer:
    def __init__(self, client):
        self.client = client

    def score_job_match(self, job_description, resume):
        prompt = f"""
        Given the following job description and resume, evaluate the match between the two and provide a match score between 0 and 100, where 100 indicates a perfect match.

        Job Description:
        {job_description}

        Resume:
        {resume}

        Please provide the match score and a brief explanation of the score in the following format:

        Score: {{score}}
        Explanation: {{explanation}}
        """

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
            breakpoint()
            return evaluation
        except openai.OpenAIError as e:
            print(f"Error scoring job match: {e}")
            return None
