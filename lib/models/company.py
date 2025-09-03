from sqlalchemy import Column, Integer, String
from .base import BaseModel

class Company(BaseModel):
    __tablename__ = 'company'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    display_name = Column(String)
