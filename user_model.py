from beanie import Document
from pydantic import EmailStr

class User(Document):
    email: EmailStr
    password: str  # hashed password!

    class Settings:
        name = "users"