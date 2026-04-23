import os
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from jose import JWTError, jwt
from pydantic import BaseModel

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
ALGORITHM = "HS256"


class TokenData(BaseModel):
    email: str
    role: str
    exp_datetime: datetime


def create_access_token(data: dict, expires_delta: timedelta = timedelta(minutes=20)):
    payload = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    payload.update({"exp": int(expire.timestamp())})
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token, expire


def verify_access_token(token: str) -> TokenData:
    try:
        data = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        exp = data.get("exp")
        email = data.get("email")
        role = data.get("role")

        if exp is None or email is None or role is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload"
            )

        exp_datetime = datetime.fromtimestamp(exp, tz=timezone.utc)
        return TokenData(email=email, role=role, exp_datetime=exp_datetime)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )
