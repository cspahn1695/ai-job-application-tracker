from beanie import Document
from pydantic import EmailStr


class User(Document):
    email: EmailStr
    password: str  # hashed password!
    is_admin: bool = False

    class Settings:
        name = "users"