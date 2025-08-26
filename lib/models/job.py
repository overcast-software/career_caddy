from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
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
