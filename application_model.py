# application_model.py 

from beanie import Document
from typing import Optional
from pydantic import Field

class Application(Document):
    company: str
    role: str
    status: str
    priority: str
    recruitmentinfo: Optional[str] = None
    resume_path: Optional[str] = None
    jobpostinglink: Optional[str] = None

    class Settings:
        name = "applications"  # Mongo collection name