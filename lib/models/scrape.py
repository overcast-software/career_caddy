#Scrape
#Scrape is different from a job description in that it defines the how
#a website data was obtained
#originaly thought to be define css selectors
#I think this relationship is inverted
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import BaseModel

class Scrape(BaseModel):
    __tablename__ = 'scrape'
    id = Column(Integer, primary_key=True, autoincrement=True)
    host = Column(String, nullable=False)
    url = Column(String, nullable=False)
    company_id = Column(Integer, ForeignKey('company.id'))
    job_id = Column(Integer, ForeignKey('job.id'))
    css_selectors = Column(Text)
    parse_method = Column(String, default='chatgpt')
    scraped_at = Column(DateTime, default=datetime.utcnow)
    html = Column(Text)
    job = relationship('Job')
    company = relationship('Company')
