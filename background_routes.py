"""Profile document per email: skills, education, experience, and bookmarked jobs.

Routes accept ``email`` in the path (the frontend uses the logged-in user's email).
GET lazily creates an empty Background row if none exists yet.
"""
from fastapi import APIRouter, HTTPException
from background_model import Background
from schemas import SavedJobCreate

import logging

router = APIRouter(prefix="/background", tags=["Background"])
TEXT_SECTIONS = {"skills", "education", "experience"}


def _norm_email(value: str) -> str:
    return (value or "").strip().lower()


# GET background
@router.get("/{email}")
async def get_background(email: str):
    email = _norm_email(email)
    bg = await Background.find_one(Background.email == email)

    if not bg:
        bg = Background(email=email)
        await bg.insert()

    logging.info(f"Getting background for {email}: {bg}")
    return bg


# ADD item
@router.post("/{email}/{section}")
async def add_item(email: str, section: str, item: str):
    if section not in TEXT_SECTIONS:
        raise HTTPException(status_code=400, detail="Invalid section")

    item = (item or "").strip()
    if not item:
        raise HTTPException(status_code=400, detail="Item cannot be empty")

    email = _norm_email(email)
    bg = await Background.find_one(Background.email == email)

    if not bg:
        bg = Background(email=email)
        await bg.insert()

    logging.info(f"Adding item {item} to section {section} for {email}: {bg}")

    section_items = getattr(bg, section)
    if item not in section_items:
        section_items.append(item)
    await bg.save()

    return bg


# DELETE item
@router.delete("/{email}/{section}")
async def delete_item(email: str, section: str, item: str):
    if section not in TEXT_SECTIONS:
        raise HTTPException(status_code=400, detail="Invalid section")

    email = _norm_email(email)
    bg = await Background.find_one(Background.email == email)

    if not bg:
        raise HTTPException(status_code=404, detail="Not found")

    section_items = getattr(bg, section)
    if item in section_items:
        section_items.remove(item)
    await bg.save()
    logging.info(f"Deleted item {item} from section {section} for {email}: {bg}")

    return bg


# Two paths support clients that append /item or post to the collection URL directly.
@router.post("/{email}/saved-jobs/item")
@router.post("/{email}/saved-jobs")
async def add_saved_job(email: str, saved_job: SavedJobCreate):
    email = _norm_email(email)
    bg = await Background.find_one(Background.email == email)

    if not bg:
        bg = Background(email=email)
        await bg.insert()

    normalized_url = (saved_job.url or "").strip()
    if not normalized_url:
        raise HTTPException(status_code=400, detail="Job URL is required")

    # Idempotent save: same URL does not create duplicate bookmarks.
    for job in bg.saved_jobs:
        existing_url = (getattr(job, "url", "") or "").strip()
        if existing_url == normalized_url:
            return bg

    bg.saved_jobs.append(saved_job)
    logging.info(f"Added saved job {saved_job} to {email}: {bg}")

    await bg.save()

    return bg



@router.delete("/{email}/saved-jobs/item")
@router.delete("/{email}/saved-jobs")
async def delete_saved_job(email: str, url: str):
    email = _norm_email(email)
    bg = await Background.find_one(Background.email == email)

    if not bg:
        raise HTTPException(status_code=404, detail="Not found")

    normalized_url = (url or "").strip()
    bg.saved_jobs = [
        j
        for j in bg.saved_jobs
        if ((getattr(j, "url", "") or "").strip() != normalized_url)
    ]
    await bg.save()
    logging.info(f"Deleted saved job {normalized_url} from {email}: {bg}")
    return bg