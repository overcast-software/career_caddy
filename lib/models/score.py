#score is a rich join between a job description and a resume
#in addition to foriegn keys it has a score (1-100) and an explination (text)
from sqlalchemy import Column, Integer, String, ForeignKey, Text
from sqlalchemy.orm import relationship
from .base import BaseModel

class Score(BaseModel):
    __tablename__ = 'score'
    id = Column(Integer, primary_key=True, autoincrement=True)
    score = Column(Integer, nullable=False)
    explanation = Column(Text, nullable=False)
    resume_id = Column(Integer, ForeignKey('resume.id'))
    job_id = Column(Integer, ForeignKey('job.id'))
    user_id = Column(Integer, ForeignKey('user.id'))

    # Relationships
    resume = relationship('Resume', back_populates='scores')
    job = relationship('Job', back_populates='scores')
