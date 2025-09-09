# user model
# has username, email, salted password, id
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from .base import BaseModel


class User(BaseModel):
    __tablename__ = "user"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=True)
    email = Column(String, unique=True, nullable=True)

    # Relationships
    resumes = relationship("Resume", back_populates="user")
    scores = relationship("Score")
    cover_letters = relationship("CoverLetter", back_populates="user")
    applications = relationship("Application", back_populates="user")
