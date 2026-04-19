# used ChatGPT to help write this code; added comments where appropriate.
from email.mime import application
from hashlib import new
import os
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional

from application_model import Application
from schemas import ApplicationCreate, ApplicationResponse

from ai_matcher import extract_resume_text, extract_job_text, compute_match_score, analyze_skill_gap

from jobs_api import fetch_jobs
from background_model import Background
from ai_matcher import rank_jobs, clean_text
from app_settings_model import get_app_settings

from bson import ObjectId



router = APIRouter(prefix="/applications", tags=["Applications"])
from schemas import ApplicationCreate, ApplicationResponse, ApplicationStatus



UPLOAD_FOLDER = "uploads"

# create application 
@router.post("/")
async def create_application(app: ApplicationCreate):
    new_app = Application(**app.dict()) # create a new application using the data entered by the user in the frontend

    await new_app.insert() # insert application into database

    return new_app

@router.post("/{app_id}/resume") # add a resume to a pre-existing job application
async def upload_resume(app_id: str, file: UploadFile = File(...)):

    application = await Application.get(app_id) # find the application corresponding to the entered ID in the database

    if not application: 
        raise HTTPException(status_code=404, detail="Application not found")
    
    os.makedirs(UPLOAD_FOLDER, exist_ok = True)

    file_path = f"{UPLOAD_FOLDER}/{app_id}_{file.filename}"

    with open(file_path, "wb") as buffer: #"wb" = write binary
        buffer.write(await file.read()) # take all contents from 'fle' and store them to the 'file_path' path

    application.resume_path = file_path # add resume to the correct application (file path)
    await application.save() # save the updated application to the database

    return {"message": "Resume uploaded", "file_path": file_path}

# get all applications (optional status filter)
@router.get("/")
async def get_applications(
    status: Optional[List[str]] = Query(None), 
    company: Optional[str] = Query(None),  # NEW FEATURE: company search
):
    query = Application.find() # get all applications through a query (no ID specified)

    #filter by status
    if status: #statuses include applied, interview, offer, and rejected
        query = query.find({"status": {"$in": status}})
        
    # NEW FEATURE: case-insensitive search by company name
    if company:
        query = query.find({"company": {"$regex": f".*{company}.*", "$options": "i"}})

    return await query.to_list()

# get single application 
@router.get("/{app_id}")
async def get_application(app_id: str):
    app = await Application.get(app_id) # find app corresponding to the entered ID in the database

    if not app: # if user enters invalid ID, throw 404 error
        raise HTTPException(status_code=404, detail="Not found")

    return app

# update application 

@router.put("/{app_id}") # update application corresponding to app_id
async def update_application(app_id: str, updated_app: ApplicationCreate):
    app = await Application.get(app_id)

    if not app:
        raise HTTPException(status_code=404, detail="Not found")

    await app.set(updated_app.dict()) # update application with the new data entered by the user
    return app

# delete application 

@router.delete("/{app_id}")
async def delete_application(app_id: str):

    try:
        app = await Application.get(ObjectId(app_id))
    except:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    if not app:
        raise HTTPException(status_code=404, detail="Not found")

    await app.delete()

    return {"message": "deleted"}

    
# get match score (how well does a resume suit a job)
@router.get("/{app_id}/match")
async def get_match_score(app_id: str):

    application = await Application.get(app_id) # find application corresponding to the entered ID in the database

    if not application: # raise an error if the application has no resume, no job posting link, or if the application doesn't exist
        raise HTTPException(status_code=404, detail="Application not found")

    if not application.resume_path:
        raise HTTPException(status_code=400, detail="No resume uploaded")

    if not application.jobpostinglink:
        raise HTTPException(status_code=400, detail="No job posting link")

    resume_text = extract_resume_text(application.resume_path) # extract resume and job texts, and compare them using the compute_match_score function in ai_matcher.py

    job_text = extract_job_text(application.jobpostinglink)

    #compute similarity score
    score = compute_match_score(resume_text, job_text)

   # NEW FEATURE: analyze skill gaps
    matched_skills, missing_skills = analyze_skill_gap(resume_text, job_text)

    return {
        "match_score": score, # return these to front end so they can be printed out
        "matched_skills": matched_skills,
        "missing_skills": missing_skills
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