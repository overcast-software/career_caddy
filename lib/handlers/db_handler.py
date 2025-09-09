from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from lib.models.base import BaseModel as Base
# Ensure all models are imported so Base.metadata is aware of them
from lib.models import (
    User,
    Resume,
    Score,
    JobPost,
    Scrape,
    Company,
    CoverLetter,
    Application,
)


class DatabaseHandler:
    def __init__(self, db_path="sqlite:///job_data.db"):
        self.engine = create_engine(db_path)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()
        Base.set_session(self.Session())

    def close(self):
        """Close the database session."""
        self.session.close()
