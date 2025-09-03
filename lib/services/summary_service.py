from lib.models.job import Job
from lib.models.resume import Resume

class SummaryService:
    def __init__(self, job: Job, resume: Resume):
        self.job = job
        self.resume = resume

    def generate_summary(self) -> str:
        # Example implementation: Combine job title and first 100 characters of resume
        job_title = self.job.title or "Job Title"
        resume_excerpt = self.resume.content[:100] + "..." if len(self.resume.content) > 100 else self.resume.content
        summary = f"Summary for {job_title}:\n{resume_excerpt}"
        return summary
