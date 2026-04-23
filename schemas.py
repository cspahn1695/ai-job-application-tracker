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


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    email: EmailStr
    is_admin: bool


class BootstrapAdminRequest(BaseModel):
    """Create the first admin when no admin exists yet (requires server secret)."""
    email: EmailStr
    password: str
    bootstrap_secret: str


class CreateAdminRequest(BaseModel):
    """Existing admin creates another admin account."""
    new_email: EmailStr
    new_password: str
    admin_email: EmailStr
    admin_password: str


class UpdateMaxJobsRequest(BaseModel):
    admin_email: EmailStr
    admin_password: str
    max_recommend_jobs: int