from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import BaseModel


class Application(BaseModel):
    __tablename__ = "application"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    job_post_id = Column(Integer, ForeignKey("job_post.id"), nullable=False)
    resume_id = Column(Integer, ForeignKey("resume.id"))
    cover_letter_id = Column(Integer, ForeignKey("cover_letter.id"))
    applied_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String)         # e.g., submitted, interview, rejected, offer
    tracking_url = Column(String)   # link to ATS or application portal
    notes = Column(Text)

    # Relationships
    user = relationship("User", back_populates="applications")
    job_post = relationship("JobPost", back_populates="applications")
    resume = relationship("Resume", back_populates="applications")
    cover_letter = relationship("CoverLetter", back_populates="application")
