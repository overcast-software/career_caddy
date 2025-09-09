from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from typing import Dict, Any, Optional
from .base import BaseModel


class JobPost(BaseModel):
    __tablename__ = "job_post"
    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    description = Column(Text)
    title = Column(String)
    company_id = Column(Integer, ForeignKey("company.id"))
    posted_date = Column(DateTime, default=datetime.utcnow)
    extraction_date = Column(DateTime)

    # Relationships
    company = relationship("Company", back_populates="job_posts")
    scores = relationship("Score", back_populates="job_post")
    scrapes = relationship("Scrape", back_populates="job_post")
    cover_letters = relationship("CoverLetter", back_populates="job_post")
    applications = relationship("Application", back_populates="job_post")

    @classmethod
    def from_json(
        cls, parsed_job: Dict[str, Any], company_id: int
    ) -> Optional["JobPost"]:
        """
        Create or retrieve a JobPost instance from a JSON-like dictionary and a company ID.

        :param parsed_job: A dictionary containing job details.
        :param company_id: The ID of the company associated with the job.
        :return: A JobPost instance or None if creation fails.
        """
        return cls.first_or_create(
            defaults={
                "description": parsed_job.get("description"),
                "posted_date": parsed_job.get("posted_date"),
                "extraction_date": parsed_job.get("extraction_date"),
            },
            title=parsed_job.get("title"),
            company_id=company_id,
        )
