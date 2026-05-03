# used ChatGPT to help write this code; added comments where appropriate.
import os
import re
from enum import Enum

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

import logging

logging.basicConfig(filename = "app.log", level=logging.INFO)



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

    logging.info(f"Created application {new_app.id} for user {current_user.email}")
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
    logging.info(f"Resume uploaded for application {application.id}")
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

    logging.info(f"Getting applications for user {current_user.email} with filters: {query_filters}")

    return await Application.find(query_filters).to_list()

# second route to be used to test adzuna api. Test with city and title to see if it works.
@router.get("/search-jobs")
async def search_jobs_by_title_location(
    city: str = Query(..., min_length=1),
    title: str = Query(..., min_length=1),
):
    """Fetch jobs from Adzuna by location and title/keywords (no profile-based ranking)."""
    city = (city or "").strip()
    title = (title or "").strip()
    if not city or not title:
        raise HTTPException(
            status_code=400, detail="City and title (keywords) are required"
        )

    settings = await get_app_settings()
    limit = max(1, min(50, int(settings.max_recommend_jobs)))
    results_per_page = max(20, min(50, limit))

    jobs = fetch_jobs(
        city, keywords=title, results_per_page=results_per_page
    )
    logging.info(
        "Adzuna search by title/location: city=%r title=%r count=%s",
        city,
        title,
        len(jobs),
    )
    return jobs


class ProfileJobSearchMode(str, Enum):
    title_location = "title_location"
    profile = "profile"
    both = "both"


def _job_payload_entry(job_dict: dict, score: Optional[float]) -> dict:
    j = job_dict or {}
    return {
        "job": {
            "title": j.get("title"),
            "company": j.get("company"),
            "location": j.get("location") or j.get("search_city"),
            "description": j.get("description"),
            "url": j.get("url"),
        },
        "score": score,
    }


def _dedupe_jobs_by_url(jobs: List[dict]) -> List[dict]:
    seen = set()
    out: List[dict] = []
    for j in jobs:
        u = (j.get("url") or "").strip()
        key = u if u else f"{j.get('title')}|{j.get('company')}"
        if key in seen:
            continue
        seen.add(key)
        out.append(j)
    return out

# third route to be used to test adzuna api. Test with mode, city, email, and title to see if it works.
@router.get("/profile-job-search")
async def profile_job_search(
    mode: ProfileJobSearchMode,
    city: str = Query(..., min_length=1),
    email: Optional[str] = Query(None),
    title: Optional[str] = Query(None),
):
    """
    Profile page job search: (1) Adzuna by title + location only, (2) profile-ranked
    jobs for a city, or (3) merge title/keyword results with a broad search then rank
    by profile.
    """
    city = (city or "").strip()
    if not city:
        raise HTTPException(status_code=400, detail="Location (city) is required")

    settings = await get_app_settings()
    limit = max(1, min(50, int(settings.max_recommend_jobs)))
    rpp = max(20, min(50, limit))

    if mode == ProfileJobSearchMode.title_location:
        t = (title or "").strip()
        if not t:
            raise HTTPException(
                status_code=400,
                detail="Job title or keywords are required for this search mode.",
            )
        jobs = fetch_jobs(city, keywords=t, results_per_page=rpp)
        payload = [_job_payload_entry(j, None) for j in jobs[:limit]]
        logging.info(
            "profile_job_search title_location: city=%r title=%r n=%s",
            city,
            t,
            len(payload),
        )
        return payload

    if mode == ProfileJobSearchMode.profile:
        email_n = _norm_bg_email(email or "")
        if not email_n:
            raise HTTPException(
                status_code=400, detail="Email is required for profile-based search."
            )
        bg = await Background.find_one(Background.email == email_n)
        if not bg:
            raise HTTPException(status_code=404, detail="No background found")
        user_text = clean_text(
            " ".join(bg.skills + bg.education + bg.experience)
        )
        jobs = fetch_jobs(city, results_per_page=rpp)
        ranked = rank_jobs(user_text, jobs)
        payload = [
            _job_payload_entry(row["job"], float(row["score"]))
            for row in ranked[:limit]
        ]
        logging.info("profile_job_search profile: email=%r n=%s", email_n, len(payload))
        return payload

    if mode == ProfileJobSearchMode.both:
        email_n = _norm_bg_email(email or "")
        t = (title or "").strip()
        if not email_n:
            raise HTTPException(
                status_code=400,
                detail="Email is required when combining profile and title search.",
            )
        if not t:
            raise HTTPException(
                status_code=400,
                detail="Job title or keywords are required when combining search.",
            )
        bg = await Background.find_one(Background.email == email_n)
        if not bg:
            raise HTTPException(status_code=404, detail="No background found")
        user_text = clean_text(
            " ".join(bg.skills + bg.education + bg.experience)
        )
        jobs_keywords = fetch_jobs(city, keywords=t, results_per_page=rpp)
        jobs_broad = fetch_jobs(city, results_per_page=rpp)
        combined = _dedupe_jobs_by_url(jobs_keywords + jobs_broad)
        ranked = rank_jobs(user_text, combined)
        payload = [
            _job_payload_entry(row["job"], float(row["score"]))
            for row in ranked[:limit]
        ]
        logging.info("profile_job_search both: email=%r n=%s", email_n, len(payload))
        return payload

    raise HTTPException(status_code=400, detail="Invalid search mode")


# get single application
@router.get("/{app_id}")
async def get_application(app_id: str, current_user: User = Depends(_get_current_user)):
    app = await _get_owned_application(app_id, current_user)

    logging.info(f"Getting application {app_id} for user {current_user.email}")
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
    logging.info(f"Application updated: {app_id}")
    return app

# delete application 

@router.delete("/{app_id}")
async def delete_application(app_id: str, current_user: User = Depends(_get_current_user)):
    app = await _get_owned_application(app_id, current_user)
    await app.delete()
    logging.info(f"Application deleted: {app_id}")
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
    logging.info(f"Match score calculated for application {application.id}: {score}")
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

    logging.info(f"Match score calculated for application {application.id}: {score}")

    return {
        "match_score": score,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
    }

def _norm_bg_email(value: str) -> str:
    return (value or "").strip().lower()

# second route to be used to test adzuna api. Test with email and city to see if it works.
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
    logging.info(f"Recommended jobs for user {email}: {len(payload)}")
    return payload