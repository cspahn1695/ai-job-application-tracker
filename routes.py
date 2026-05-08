# some of this code was made with the help of ChatGPT
"""Job application CRUD, resume uploads, Adzuna search, and AI match scoring.

Most handlers require a valid JWT (see ``authenticate``). Queries restrict rows to
the current user via ``_app_owner_filter`` so one user cannot read another's apps.
"""
import os
import re
import hashlib
from enum import Enum
from urllib.parse import urlparse, unquote

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from fastapi.responses import RedirectResponse
from typing import List, Optional

from application_model import Application
from authenticate import authenticate
from jwt_handler import TokenData
from schemas import ApplicationCreate, ApplicationResponse, JobTextRequest

from ai_matcher import (
    extract_resume_text,
    extract_job_text,
    compute_match_score,
    analyze_skill_gap,
)

from jobs_api import fetch_jobs, _resolve_adzuna_redirect
from background_model import Background
from ai_matcher import rank_jobs, clean_text
from app_settings_model import get_app_settings

from bson import ObjectId

from user_model import User

import logging

# File logging is configured here because ``main`` imports this module early on startup.
logging.basicConfig(filename="app.log", level=logging.INFO)


router = APIRouter(prefix="/applications", tags=["Applications"])
from schemas import ApplicationCreate, ApplicationResponse, ApplicationStatus



UPLOAD_FOLDER = "uploads"


def _app_owner_filter(current_user: User) -> dict: # this function is used to filter the applications by the current user
    normalized_email = (str(current_user.email) or "").strip().lower()
    return {
        "$or": [
            {"owner_email": normalized_email}, # this is the email of the current user
            {"owner_id": current_user.id}, # this is the id of the current user
            # Beanie stores Link[User] as DBRef-style fields in raw MongoDB queries.
            {"Owner.$id": current_user.id}, # this is the id of the current user
        ]
    }


async def _get_current_user(token_data: TokenData = Depends(authenticate)) -> User:
    current_user = await User.find_one(User.email == token_data.email)
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User no longer exists"
        )
    return current_user


async def _get_owned_application(app_id: str, current_user: User) -> Application: # only returns one application
    try:
        oid = ObjectId(app_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    # Combine ObjectId match with ownership so IDs alone are not enough to read others' data.
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

    # Filename prefixed with app_id avoids collisions; path is also stored on the Application doc.
    file_path = f"{UPLOAD_FOLDER}/{app_id}_{file.filename}"
    with open(file_path, "wb") as buffer:
        buffer.write(await file.read()) # write the file to the buffer

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
    title: Optional[str] = Query(None),
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


def _dedupe_jobs_by_url(jobs: List[dict]) -> List[dict]: # this function is used to deduplicate the jobs by the url
    seen = set() # this is a set of the urls of the jobs
    out: List[dict] = [] # this is a list of the jobs
    for j in jobs:
        u = (j.get("url") or "").strip() # this is the url of the job
        key = u if u else f"{j.get('title')}|{j.get('company')}" # this is the key of the job
        if key in seen:
            continue # if the key is already in the set, skip the job
        seen.add(key)
        out.append(j) # add the job to the list
    return out

# third route to be used to test adzuna api. Test with mode, city, email, and title to see if it works.
@router.get("/profile-job-search")
async def profile_job_search(
    mode: ProfileJobSearchMode,
    city: Optional[str] = Query(None),
    email: Optional[str] = Query(None),
    title: Optional[str] = Query(None),
):
    """
    Profile page job search: (1) Adzuna by title + optional location, (2) profile-ranked
    jobs with optional location filtering, or (3) merge title/keyword results with a
    broad search then rank by profile.
    """
    city = (city or "").strip()

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

   
def _is_adzuna_listing_url(url: str) -> bool: 
    """Only allow resolving Adzuna tracking links (avoid open-redirect / SSRF abuse)."""
    try:
        p = urlparse((url or "").strip())
        if p.scheme not in ("http", "https"): # must be one of these
            return False
        host = (p.netloc or "").lower().split(":")[0]
        return ( 
            host == "adzuna.com" # must be one of these formats
            or host.endswith(".adzuna.com")
            or host == "adzuna.co.uk"
            or host.endswith(".adzuna.co.uk")
        )
    except Exception:
        return False


_INTERVIEW_NOISE_PATTERNS = [
    "suspicious behaviour",
    "unusual behaviour",
    "vpn",
    "company internet gateway",
    "contact us if you believe this is an error",
    "do not discriminate on the basis of",
    "equal opportunity employer",
    "more information about",
    "can be found at www",
    "privacy policy",
    "terms of use",
]


def _is_noise_line(text: str) -> bool:
    t = (text or "").strip().lower()
    if not t:
        return True
    if len(t) < 30:
        return True
    if any(p in t for p in _INTERVIEW_NOISE_PATTERNS):
        return True
    return False


def _posting_snippets(job_text: str, max_snippets: int = 6) -> List[str]:
    """
    Pull distinct, content-rich lines/sentences from a posting so generated
    questions differ per role instead of reusing a static skill list.
    """
    raw = (job_text or "").replace("\r", "\n")
    lines = [ln.strip(" -•\t") for ln in raw.split("\n") if ln.strip()]
    sentence_lines: List[str] = []
    for ln in lines:
        if _is_noise_line(ln):
            continue
        if len(ln) < 25:
            continue
        parts = re.split(r"(?<=[.!?])\s+", ln)
        for p in parts:
            p = p.strip()
            if len(p) >= 35 and not _is_noise_line(p):
                sentence_lines.append(p)

    # Prefer requirement/responsibility style lines first.
    priority_terms = [
        "responsib",
        "require",
        "qualif",
        "experience",
        "must",
        "preferred",
        "ability",
        "knowledge",
        "design",
        "develop",
        "analyze",
        "support",
        "manage",
    ]
    ranked = sorted(
        sentence_lines,
        key=lambda s: sum(1 for t in priority_terms if t in s.lower()),
        reverse=True,
    )

    out: List[str] = []
    seen = set()
    for s in ranked:
        normalized = clean_text(s)[:160]
        if not normalized or normalized in seen:
            continue
        if len(set(normalized.split())) < 6:
            continue
        seen.add(normalized)
        out.append(s)
        if len(out) >= max_snippets:
            break
    return out


def _url_focus_terms(link: str, max_terms: int = 5) -> List[str]:
    """Extract useful topic words from job URL slug/path for link-specific fallback."""
    try:
        p = urlparse(link or "")
        raw = unquote((p.path or "") + " " + (p.query or ""))
    except Exception:
        raw = link or ""
    raw = raw.replace("-", " ").replace("_", " ").replace("/", " ")
    tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9+#]{2,}", raw.lower())
    stop = {
        "jobs", "job", "view", "posting", "apply", "application", "company",
        "www", "http", "https", "com", "org", "net", "html", "php", "ref",
        "utm", "source", "linkedin", "indeed", "workday", "greenhouse",
        "position", "role", "career", "careers", "search", "result", "results",
    }
    out: List[str] = []
    seen = set()
    for t in tokens:
        if t in stop or t.isdigit():
            continue
        if t in seen:
            continue
        seen.add(t)
        out.append(t)
        if len(out) >= max_terms:
            break
    return out


def _fallback_role_questions(
    role: str, company: str, seed: str, link: str, max_questions: int = 6
) -> List[str]:
    """Deterministic, role-aware fallback when scraping returns poor text."""
    role_text = (role or "this role").strip()
    company_text = (company or "this company").strip()
    role_templates = [
        f"For this {role_text} role at {company_text}, which day-one responsibility would you prioritize first, and why?",
        f"What project best demonstrates your fit for this {role_text} position, and what measurable outcome did you achieve?",
        f"Which tools or methods would you use in your first 30 days to succeed in this {role_text} role?",
        f"Describe a past challenge most similar to what this {role_text} role likely involves, and how you solved it.",
        f"What trade-offs would you expect to make in this {role_text} role, and how would you justify your decisions?",
        f"How would you collaborate with teammates and stakeholders to deliver results in this {role_text} position?",
    ]
    link_terms = _url_focus_terms(link, max_terms=3)
    term_templates: List[str] = []
    for term in link_terms:
        term_label = term.replace("+", " ").strip()
        term_templates.append(
            f"This posting appears to emphasize '{term_label}'. What direct experience do you have applying it in a real scenario?"
        )
        term_templates.append(
            f"How would you demonstrate competency in '{term_label}' during your first month in this {role_text} role?"
        )

    templates = term_templates + role_templates
    start = int(hashlib.sha256(seed.encode("utf-8")).hexdigest()[:8], 16) % len(templates)
    ordered = templates[start:] + templates[:start]

    out: List[str] = []
    seen = set()
    for q in ordered:
        key = clean_text(q)
        if key in seen:
            continue
        seen.add(key)
        out.append(q)
        if len(out) >= max_questions:
            break
    return out


def _interview_questions_for_job(
    role: str, company: str, link: str, job_text: str, seed: str, max_questions: int = 6
) -> List[str]:
    """Generate 1..6 posting-specific interview questions (no resume input)."""
    role_text = (role or "this role").strip()
    snippets = _posting_snippets(job_text, max_snippets=max_questions)

    questions: List[str] = []
    prompt_styles = [
        'The posting highlights: "{snippet}". How have you handled this in a real project?',
        'This role expects: "{snippet}". Can you give a concrete example where you delivered this outcome?',
        'Based on "{snippet}", what specific experience proves you can do this well?',
        'The description includes "{snippet}". Walk me through a time you solved a similar challenge.',
    ]
    style_seed = int(hashlib.sha256(seed.encode("utf-8")).hexdigest()[:8], 16)
    for snip in snippets:
        short = re.sub(r"\s+", " ", snip).strip()
        short = short[:170].rstrip(" ,;:")
        style = prompt_styles[style_seed % len(prompt_styles)]
        style_seed += 1
        questions.append(style.format(snippet=short))
        if len(questions) >= max_questions:
            break

    # Ensure at least one question is returned even if extraction is sparse.
    if not questions:
        questions = _fallback_role_questions(
            role_text, company, seed, link, max_questions=max_questions
        )
    return questions[:max_questions]


@router.get("/interview-prep")
async def interview_prep(current_user: User = Depends(_get_current_user)):
    """
    Return interview questions for each owned application that has a job posting link.
    Questions are generated from posting text only (no resume usage).
    """
    apps = await Application.find(_app_owner_filter(current_user)).to_list()
    payload = []
    for app in apps:
        link = (app.jobpostinglink or "").strip()
        if not link:
            continue
        try:
            job_text = extract_job_text(link)
        except Exception:
            job_text = ""
        seed = f"{str(app.id)}|{link}"
        questions = _interview_questions_for_job(
            app.role or "", app.company or "", link, job_text, seed, max_questions=6
        )
        payload.append(
            {
                "app_id": str(app.id),
                "company": app.company,
                "role": app.role,
                "jobpostinglink": link,
                "questions": questions[:6],
            }
        )
    return payload


@router.get("/resolve-listing-url")
async def resolve_listing_url(
    url: str = Query(..., min_length=12, max_length=4000, description="Adzuna redirect_url"),
):
    """
    Follow a single Adzuna listing URL and redirect the browser to the final site.
    Used by 'View job' so job search stays fast (no bulk resolve during search).
    """
    listing = url.strip()
    if not _is_adzuna_listing_url(listing):
        raise HTTPException(
            status_code=400,
            detail="Only Adzuna listing URLs can be resolved through this endpoint.",
        )
    final = _resolve_adzuna_redirect(listing, timeout=5.0)
    return RedirectResponse(url=final, status_code=302)


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
    # Partial field update so resume_path / Owner / owner_email are not wiped by Beanie.set().
    for key, value in updated_app.dict().items():
        setattr(app, key, value)
    await app.save()
    logging.info(f"Application updated: {app_id}")
    return app

    # @router.put("/{app_id}/resume")
# async def update_resume(
#     app_id: str,
#     file: UploadFile = File(...),
#     current_user: User = Depends(_get_current_user),
# ):
#     application = await _get_owned_application(app_id, current_user)
#     os.makedirs(UPLOAD_FOLDER, exist_ok=True)

#     # Overwrites ``resume_path``; previous file may remain on disk until cleaned up manually.
#     file_path = f"{UPLOAD_FOLDER}/{app_id}_{file.filename}"
#     with open(file_path, "wb") as buffer:
#         buffer.write(await file.read()) # write the file to the buffer

#     application.resume_path = file_path
#     await application.save()
#     logging.info(f"Resume updated for application {application.id}")
#     return {"message": "Resume updated", "file_path": file_path}

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