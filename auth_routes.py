"""Authentication and admin onboarding.

Regular users register and receive JWTs from ``/login``. Admins are flagged with
``is_admin`` in MongoDB; the token embeds ``role`` for optional checks elsewhere.
Bootstrap creates the first admin using a server secret; further admins are
created only by an existing admin (see ``/create-admin``).
"""
import os
import re
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query

from user_model import User
from schemas import UserCreate, UserLogin, BootstrapAdminRequest, CreateAdminRequest, TokenResponse
from auth_utils import hash_password, verify_password # hash pws when registering
from jwt_handler import create_access_token # create an access token when logging in 
router = APIRouter(prefix="/auth", tags=["Auth"])
import logging


def _norm_email(value: str) -> str:
    return (value or "").strip().lower()


async def _find_user_by_email(value: str):
    """Resolve login/register lookups; falls back to case-insensitive regex for older rows."""
    e = _norm_email(value)
    if not e:
        return None
    user = await User.find_one(User.email == e)
    logging.info(f"Finding user by email {e}: {user}")
    if user:
        return user
    return await User.find_one(
        {"email": {"$regex": f"^{re.escape(value.strip())}$", "$options": "i"}}
    )


def _bootstrap_secret() -> str:
    return os.getenv("ADMIN_BOOTSTRAP_SECRET", "dev-bootstrap-change-me")


# ✅ Register (standard user only)
@router.post("/register")
async def register(user: UserCreate):
    email = _norm_email(str(user.email))
    existing = await _find_user_by_email(email)

    if existing:
        raise HTTPException(status_code=400, detail="User already exists")

    new_user = User(
        email=email,
        password=hash_password(user.password),
        is_admin=False,
    )

    await new_user.insert()
    
    logging.info(f"User {email} created: {new_user}")

    return {"message": "User created"}


# ✅ Login
@router.post("/login", response_model=TokenResponse)
async def login(user: UserLogin):
    email = _norm_email(str(user.email))
    db_user = await _find_user_by_email(email)
    if not db_user or not verify_password(user.password, db_user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    is_admin = getattr(db_user, "is_admin", False)
    token, expire = create_access_token(
        {"email": email, "role": "admin" if is_admin else "user"}
    )

    logging.info(f"User {email} logged in: {db_user}")

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=int((expire - datetime.now(timezone.utc)).total_seconds()),
        email=email,
        is_admin=bool(is_admin),
    )


@router.get("/me")
async def me(email: str = Query(..., description="Logged-in user email")):
    # Frontend passes email explicitly because this endpoint does not read the Bearer token.
    db_user = await _find_user_by_email(email)
    logging.info(f"Getting user {email}: {db_user}")
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    logging.info(f"User {email} found: {db_user}")
    return {
        "email": _norm_email(str(db_user.email)),
        "is_admin": bool(getattr(db_user, "is_admin", False)),
    }


@router.post("/bootstrap-admin")
async def bootstrap_admin(req: BootstrapAdminRequest):
    """
    Creates the first admin account when no admin exists.
    Requires ADMIN_BOOTSTRAP_SECRET env var (or default in dev).
    """
    logging.info(f"Bootstrapping admin {req.email} with secret {req.bootstrap_secret}")
    if req.bootstrap_secret != _bootstrap_secret():
        raise HTTPException(status_code=403, detail="Invalid bootstrap secret")

    existing_admin = await User.find_one(User.is_admin == True)
    if existing_admin:
        raise HTTPException(
            status_code=400,
            detail="An admin already exists. Use create-admin from an admin account.",
        )

    if await _find_user_by_email(str(req.email)):
        raise HTTPException(status_code=400, detail="User already exists")

    logging.info(f"Creating admin {req.email}")
    admin = User(
        email=_norm_email(str(req.email)),
        password=hash_password(req.password),
        is_admin=True,
    )
    await admin.insert()

    return {"message": "Admin account created", "email": admin.email, "is_admin": True}


@router.post("/create-admin")
async def create_admin(req: CreateAdminRequest):
    """An existing admin creates another admin user."""
    actor = await _find_user_by_email(str(req.admin_email))
    if not actor or not verify_password(req.admin_password, actor.password):
        raise HTTPException(status_code=401, detail="Invalid admin credentials")
    if not getattr(actor, "is_admin", False):
        raise HTTPException(status_code=403, detail="Admin access required")

    if await _find_user_by_email(str(req.new_email)):
        raise HTTPException(status_code=400, detail="User already exists")

    new_admin = User(
        email=_norm_email(str(req.new_email)),
        password=hash_password(req.new_password),
        is_admin=True,
    )
    await new_admin.insert()

    logging.info(f"Admin {req.new_email} created: {new_admin}")

    return {"message": "Admin account created", "email": new_admin.email}