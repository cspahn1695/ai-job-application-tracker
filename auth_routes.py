from fastapi import APIRouter, HTTPException
from user_model import User
from schemas import UserCreate, UserLogin
from auth_utils import hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["Auth"])


# ✅ Register
@router.post("/register")
async def register(user: UserCreate):
    existing = await User.find_one(User.email == user.email)

    if existing:
        raise HTTPException(status_code=400, detail="User already exists")

    new_user = User(
        email=user.email,
        password=hash_password(user.password)
    )

    await new_user.insert()

    return {"message": "User created"}


# ✅ Login
@router.post("/login")
async def login(user: UserLogin):
    db_user = await User.find_one(User.email == user.email)

    if not db_user:
        raise HTTPException(status_code=400, detail="Invalid credentials")

    if not verify_password(user.password, db_user.password):
        raise HTTPException(status_code=400, detail="Invalid credentials")

    return {"message": "Login successful"}