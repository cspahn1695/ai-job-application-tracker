# used ChatGPT to help write this code; added comments where appropriate.
import os
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional

from database import get_db
from models import Application
from schemas import ApplicationCreate, ApplicationResponse

from ai_matcher import extract_resume_text, extract_job_text, compute_match_score, analyze_skill_gap

router = APIRouter(prefix="/applications", tags=["Applications"])
from schemas import ApplicationCreate, ApplicationResponse, ApplicationStatus



UPLOAD_FOLDER = "uploads"

# create application 
@router.post("/", response_model=ApplicationResponse)
def create_application(app: ApplicationCreate, db: Session = Depends(get_db)):
    new_app = Application(
        company=app.company, # have user enter all data
        role=app.role,
        status=app.status,
        priority = app.priority,
        recruitmentinfo=app.recruitmentinfo,
        jobpostinglink=app.jobpostinglink
    )

    db.add(new_app) # add this application to database and commit database
    db.commit()
    db.refresh(new_app)

    return new_app

@router.post("/{app_id}/resume") # add a resume to a pre-existing job application
async def upload_resume(app_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):

    application = db.query(Application).filter(Application.id == app_id).first() # find the app with the right ID

    if not application: 
        raise HTTPException(status_code=404, detail="Application not found")
    
    os.makedirs(UPLOAD_FOLDER, exist_ok = True)

    file_path = f"{UPLOAD_FOLDER}/{app_id}_{file.filename}"

    with open(file_path, "wb") as buffer: #"wb" = write binary
        buffer.write(await file.read()) # take all contents from 'fle' and store them to the 'file_path' path

    application.resume_path = file_path # add resume to the correct application (file path)

    db.commit() # commit database holding resumes + other info

    return {"message": "Resume uploaded", "file_path": file_path}

# get all applications (optional status filter)
@router.get("/", response_model=List[ApplicationResponse])
def get_applications(
    status: Optional[List[ApplicationStatus]] = Query(None), 
    company: Optional[str] = Query(None),  # NEW FEATURE: company search
    db: Session = Depends(get_db)
):
    query = db.query(Application)# get all applications through a query (no ID specified)

    #filter by status
    if status: #statuses include applied, interview, offer, and rejected
        query = query.filter(Application.status.in_(status))
        
    # NEW FEATURE: case-insensitive search by company name
    if company:
        query = query.filter(Application.company.ilike(f"%{company}%"))

    return query.all()

# get single application 
@router.get("/{app_id}", response_model=ApplicationResponse) 
def get_application(app_id: int, db: Session = Depends(get_db)):
    application = db.query(Application).filter(Application.id == app_id).first() # find app corresponding to the entered ID in the database

    if not application: # if user enters invalid ID, throw 404 error
        raise HTTPException(status_code=404, detail="Application not found")

    return application

# update application 

@router.put("/{app_id}", response_model=ApplicationResponse) # update application corresponding to app_id
def update_application(app_id: int, updated_app: ApplicationCreate, db: Session = Depends(get_db)):
    application = db.query(Application).filter(Application.id == app_id).first()

    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    application.company = updated_app.company # update any of these parameters for the application
    application.role = updated_app.role
    application.status = updated_app.status
    application.priority = updated_app.priority
    application.recruitmentinfo = updated_app.recruitmentinfo
    application.jobpostinglink = updated_app.jobpostinglink

    db.commit()
    db.refresh(application)

    return application

# delete application 

@router.delete("/{app_id}")
def delete_application(app_id: int, db: Session = Depends(get_db)):
    application = db.query(Application).filter(Application.id == app_id).first()

    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    db.delete(application) # delete application corresponding to id app_id
    db.commit() # commit database to save changes

    return {"message": "Application deleted"}

    
# get match score (how well does a resume suit a job)
@router.get("/{app_id}/match")
def get_match_score(app_id: int, db: Session = Depends(get_db)):

    application = db.query(Application).filter(Application.id == app_id).first() # find the application corresponding to application_ID

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
        "match_score": score,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills
    }