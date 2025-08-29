from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from typing import Dict, Any, Optional
from .base import BaseModel

class Job(BaseModel):
    __tablename__ = 'job'
    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    description = Column(Text)
    title = Column(String)
    company_id = Column(Integer, ForeignKey('company.id'))
    posted_date = Column(DateTime, default=datetime.utcnow)
    company = relationship('Company')
    scores = relationship('Score', back_populates='job')

    @classmethod
    def from_json(cls, parsed_job: Dict[str, Any], company_id: int) -> Optional['Job']:
        """
        Create or retrieve a Job instance from a JSON-like dictionary and a company ID.

        :param parsed_job: A dictionary containing job details.
        :param company_id: The ID of the company associated with the job.
        :return: A Job instance or None if creation fails.
        """
        return cls.first_or_create(
            defaults={
                'description': parsed_job.get('description'),
                'posted_date': parsed_job.get('posted_date')
            },
            title=parsed_job.get('title'),
            company_id=company_id
        )
