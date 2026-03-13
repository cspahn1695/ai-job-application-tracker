from pydantic import BaseModel
from enum import Enum
from typing import Optional

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

class ApplicationResponse(ApplicationCreate): # used so that resume and job posting can be compared for similar phrases/keywords
    id: int
    resume_path: Optional[str] = None

    class Config:
        from_attributes = True  # ← FIX for Pydantic V2