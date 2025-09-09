from sqlalchemy import Column, Integer, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import BaseModel


class CoverLetter(BaseModel):
    __tablename__ = "cover_letter"
    id = Column(Integer, primary_key=True, autoincrement=True)
    content = Column(Text, nullable=False)
    user_id = Column(Integer, ForeignKey("user.id"))
    resume_id = Column(Integer, ForeignKey("resume.id"))
    job_post_id = Column(Integer, ForeignKey("job_post.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="cover_letters")
    resume = relationship("Resume", back_populates="cover_letters")
    job_post = relationship("JobPost", back_populates="cover_letters")
    application = relationship("Application", back_populates="cover_letter", uselist=False)
