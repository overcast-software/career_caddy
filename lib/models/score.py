# score is a rich join between a job description and a resume
# in addition to foriegn keys it has a score (1-100) and an explination (text)
from sqlalchemy import Column, Integer, ForeignKey, Text
from sqlalchemy.orm import relationship
from .base import BaseModel


class Score(BaseModel):
    __tablename__ = "score"
    id = Column(Integer, primary_key=True, autoincrement=True)
    score = Column(Integer, nullable=True)
    explanation = Column(Text, nullable=True)
    resume_id = Column(Integer, ForeignKey("resume.id"))
    job_post_id = Column(Integer, ForeignKey("job_post.id"))
    user_id = Column(Integer, ForeignKey("user.id"))

    # Relationships
    resume = relationship("Resume", back_populates="scores")
    job_post = relationship("JobPost", back_populates="scores")
    user = relationship("User", overlaps="scores")
