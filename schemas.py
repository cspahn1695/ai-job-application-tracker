# used ChatGPT to help write this code; added comments where appropriate.
from pydantic import BaseModel, EmailStr
from enum import Enum
from typing import Optional
from pydantic import BaseModel

class ApplicationStatus(str, Enum):
    applied = "applied" # all values for ApplicationStatus are applied, interview, rejected, and offer
    interview = "interview"
    rejected = "rejected"
    offer = "offer"

class ApplicationPriority(str, Enum): # all values for ApplicationPriority are high, medium, and low
    high = "high"
    medium = "medium"
    low = "low"

class ApplicationCreate(BaseModel): # to create a new application, enter company, role, status, and priority. The jobpostinglink and recruitment info are optional.
    company: str
    role: str
    status: ApplicationStatus
    priority: ApplicationPriority
    recruitmentinfo: Optional[str] = None   # ← ADD THIS
    jobpostinglink: str

class ApplicationResponse(BaseModel): # used so that resume and job posting can be compared for similar phrases/keywords
    id: str
    company: str
    role: str
    status: str
    priority: str
    recruitmentinfo: Optional[str]
    resume_path: Optional[str]
    jobpostinglink: Optional[str]

    @classmethod
    def from_mongo(cls, doc):
        return cls(
            id=str(doc.id),
            **doc.dict()
        )

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str