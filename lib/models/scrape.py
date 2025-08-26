from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import BaseModel

class Scrape(BaseModel):
    __tablename__ = 'scrape'
    id = Column(Integer, primary_key=True, autoincrement=True)
    host = Column(String, nullable=False)
    url = Column(String, nullable=False)
    job_id = Column(Integer, ForeignKey('job.id'))
    css_selectors_json = Column(Text, nullable=False)
    scraped_at = Column(DateTime, default=datetime.utcnow)
    html = Column(Text)
    job = relationship('Job')
