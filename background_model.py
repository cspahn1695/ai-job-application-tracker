from beanie import Document
from typing import List
from pydantic import EmailStr

class Background(Document):
    email: EmailStr
    skills: List[str] = []
    education: List[str] = []
    experience: List[str] = []
    saved_jobs: List[str] = []

    class Settings:
        name = "backgrounds"