# used ChatGPT to help write this code; added comments where appropriate.
import os
import re
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from typing import List, Optional

from application_model import Application
from authenticate import authenticate
from jwt_handler import TokenData
from schemas import ApplicationCreate, ApplicationResponse, JobTextRequest

from ai_matcher import extract_resume_text, extract_job_text, compute_match_score, analyze_skill_gap

from jobs_api import fetch_jobs
from background_model import Background
from ai_matcher import rank_jobs, clean_text
from app_settings_model import get_app_settings

from bson import ObjectId

from user_model import User



router = APIRouter(prefix="/applications", tags=["Applications"])
from schemas import ApplicationCreate, ApplicationResponse, ApplicationStatus



UPLOAD_FOLDER = "uploads"

def _app_owner_filter(current_user: User) -> dict:
    normalized_email = (str(current_user.email) or "").strip().lower()
    return {
        "$or": [
            {"owner_email": normalized_email},   # current ownership key
            {"owner_id": current_user.id},       # legacy ownership key
            {"Owner.$id": current_user.id},      # Beanie Link storage shape
        ]
    }

async def _get_current_user(token_data: TokenData = Depends(authenticate)) -> User:
    current_user = await User.find_one(User.email == token_data.email)
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User no longer exists"
        )
    return current_user


async def _get_owned_application(app_id: str, current_user: User) -> Application:
    try:
        oid = ObjectId(app_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    app = await Application.find_one({"_id": oid, **_app_owner_filter(current_user)})
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    return app


# create application 
@router.post("/")
async def create_application(
    app: ApplicationCreate, current_user: User = Depends(_get_current_user)
):
    new_app = Application(
        Owner=current_user,
        owner_email=(str(current_user.email) or "").strip().lower(),
        **app.dict(),
    )  # bind application ownership to logged-in user
    await new_app.insert()
    return new_app

@router.post("/{app_id}/resume")
async def upload_resume(
    app_id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(_get_current_user),
):
    application = await _get_owned_application(app_id, current_user)
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    file_path = f"{UPLOAD_FOLDER}/{app_id}_{file.filename}"
    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())

    application.resume_path = file_path
    await application.save()
    return {"message": "Resume uploaded", "file_path": file_path}

# get all applications (optional status filter)
@router.get("/")
async def get_applications(
    status: Optional[List[str]] = Query(None),
    company: Optional[str] = Query(None),
    current_user: User = Depends(_get_current_user),
):
    query_filters = _app_owner_filter(current_user)

    if status:
        query_filters["status"] = {"$in": status}

    if company:
        query_filters["company"] = {"$regex": f".*{re.escape(company)}.*", "$options": "i"}

    return await Application.find(query_filters).to_list()

# get single application 
@router.get("/{app_id}")
async def get_application(app_id: str, current_user: User = Depends(_get_current_user)):
    app = await _get_owned_application(app_id, current_user)

    return app

# update application 

@router.put("/{app_id}")
async def update_application(
    app_id: str,
    updated_app: ApplicationCreate,
    current_user: User = Depends(_get_current_user),
):
    app = await _get_owned_application(app_id, current_user)
    await app.set(updated_app.dict())
    return app

# delete application 

@router.delete("/{app_id}")
async def delete_application(app_id: str, current_user: User = Depends(_get_current_user)):
    app = await _get_owned_application(app_id, current_user)
    await app.delete()
    return {"message": "deleted"}

    
# get match score (how well does a resume suit a job)
@router.get("/{app_id}/match")
async def get_match_score(app_id: str, current_user: User = Depends(_get_current_user)):
    application = await _get_owned_application(app_id, current_user)

    if not application.resume_path:
        raise HTTPException(status_code=400, detail="No resume uploaded")

    if not application.jobpostinglink:
        raise HTTPException(status_code=400, detail="No job posting link")

    resume_text = extract_resume_text(application.resume_path)
    job_text = extract_job_text(application.jobpostinglink)
    if len((job_text or "").strip()) < 80:
        raise HTTPException(
            status_code=400,
            detail="Could not extract enough text from that job link (extracted < 80 chars). The URL may block scrapers. Try a public posting URL or include the LinkedIn job URL that contains the numeric job ID.",
        )
    score = compute_match_score(resume_text, job_text)
    matched_skills, missing_skills = analyze_skill_gap(resume_text, job_text)

    return {
        "match_score": score,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
    }




@router.post("/{app_id}/match")
async def get_match_score_from_text(
    app_id: str,
    body: JobTextRequest,
    current_user: User = Depends(_get_current_user),
):
    application = await _get_owned_application(app_id, current_user)

    if not application.resume_path:
        raise HTTPException(status_code=400, detail="No resume uploaded")

    if len((body.job_text or "").strip()) < 80:
        raise HTTPException(
            status_code=400,
            detail="Pasted job description is too short. Please paste more of the posting text.",
        )

    resume_text = extract_resume_text(application.resume_path)
    score = compute_match_score(resume_text, body.job_text)
    matched_skills, missing_skills = analyze_skill_gap(resume_text, body.job_text)

    return {
        "match_score": score,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
    }

def _norm_bg_email(value: str) -> str:
    return (value or "").strip().lower()


@router.get("/recommend-jobs/{email}") # this actually gets jobs from adzuna API and ranks them based on the user's background info (skills, experience, education) using the rank_jobs function in ai_matcher.py
async def recommend_jobs(email: str, city: str):

    email = _norm_bg_email(email)
    bg = await Background.find_one(Background.email == email)

    if not bg:
        raise HTTPException(status_code=404, detail="No background found")

    # build user profile text
    user_text = clean_text(
        " ".join(bg.skills + bg.education + bg.experience)
    )

    settings = await get_app_settings()
    limit = max(1, min(50, int(settings.max_recommend_jobs)))

    jobs = fetch_jobs(city, results_per_page=max(20, min(50, limit)))

    ranked = rank_jobs(user_text, jobs)

    # Plain dicts so JSON always includes nested job fields (title, company, location, url)
    payload = []
    for row in ranked[:limit]:
        j = row["job"] or {}
        payload.append(
            {
                "job": {
                    "title": j.get("title"),
                    "company": j.get("company"),
                    "location": j.get("location") or j.get("search_city"),
                    "description": j.get("description"),
                    "url": j.get("url"),
                },
                "score": row["score"],
            }
        )
    return payload