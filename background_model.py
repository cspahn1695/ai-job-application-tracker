from beanie import Document
from typing import List, Optional, Union
from pydantic import BaseModel, Field
from pydantic import EmailStr


class SavedJob(BaseModel):
    title: str
    url: str
    company: Optional[str] = None
    location: Optional[str] = None


class Background(Document):
    email: EmailStr
    skills: List[str] = Field(default_factory=list)
    education: List[str] = Field(default_factory=list)
    experience: List[str] = Field(default_factory=list)
    saved_jobs: List[Union[SavedJob, str]] = Field(default_factory=list)

    class Settings:
        name = "backgrounds"