from beanie import Document
from pydantic import EmailStr


class User(Document):
    """Auth identity; ``is_admin`` gates bootstrap/create-admin and settings updates."""
    email: EmailStr
    password: str  # hashed password!
    is_admin: bool = False

    class Settings:
        name = "users"