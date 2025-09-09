from sqlalchemy import Column, Integer, Text, ForeignKey, String
from sqlalchemy.orm import relationship
from .base import BaseModel


class Resume(BaseModel):
    __tablename__ = "resume"
    id = Column(Integer, primary_key=True, autoincrement=True)
    content = Column(Text, nullable=False)
    user_id = Column(Integer, ForeignKey("user.id"))
    file_path = Column(String)
    # Relationships
    user = relationship("User", back_populates="resumes")
    scores = relationship("Score", back_populates="resume")
    cover_letters = relationship("CoverLetter", back_populates="resume")
    applications = relationship("Application", back_populates="resume")

    @classmethod
    def from_path_and_user_id(cls, path, user_id):
        with open(path) as file:
            body = file.read()
            resume, _ = cls.first_or_create(
                content=body, file_path=path, user_id=user_id
            )
        return resume
