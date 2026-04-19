from fastapi import APIRouter, HTTPException

from app_settings_model import get_app_settings
from auth_utils import verify_password
from schemas import UpdateMaxJobsRequest
from user_model import User

router = APIRouter(prefix="/settings", tags=["Settings"])

# Adzuna allows up to 50 results per request for typical plans
MAX_JOBS_CAP = 50
MIN_JOBS = 1


async def _require_admin(email: str, password: str) -> User:
    user = await User.find_one(User.email == email)
    if not user or not verify_password(password, user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


@router.get("/max-recommend-jobs")
async def get_max_recommend_jobs():
    settings = await get_app_settings()
    return {"max_recommend_jobs": settings.max_recommend_jobs}


@router.put("/max-recommend-jobs")
async def update_max_recommend_jobs(body: UpdateMaxJobsRequest):
    await _require_admin(body.admin_email, body.admin_password)

    n = int(body.max_recommend_jobs)
    if n < MIN_JOBS or n > MAX_JOBS_CAP:
        raise HTTPException(
            status_code=400,
            detail=f"max_recommend_jobs must be between {MIN_JOBS} and {MAX_JOBS_CAP}",
        )

    settings = await get_app_settings()
    settings.max_recommend_jobs = n
    await settings.save()

    return {"max_recommend_jobs": settings.max_recommend_jobs}
