#Scrape
#Scrape is different from a job description in that it defines the how
#a website data was obtained
#originaly thought to be define css selectors
#I think this relationship is inverted
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import BaseModel
from urllib.parse import urlparse

class Scrape(BaseModel):
    __tablename__ = 'scrape'
    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(String, nullable=False)
    company_id = Column(Integer, ForeignKey('company.id'))
    job_id = Column(Integer, ForeignKey('job.id'))
    css_selectors = Column(Text)
    job_content = Column(Text)
    external_link = Column(String)
    parse_method = Column(String, default='chatgpt')
    scraped_at = Column(DateTime, default=datetime.utcnow)
    state = Column(String)
    source_scrape_id = Column(Integer, ForeignKey('scrape.id'))
    html = Column(Text)
    job = relationship('Job')
    company = relationship('Company')

    @property
    def host(self):
        return urlparse(self.url).netloc
