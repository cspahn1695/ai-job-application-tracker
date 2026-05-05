"""MongoDB connection and Beanie ODM registration.

Beanie maps each Document subclass to one collection; every model listed here
must be registered before any route uses it (called from FastAPI startup).
"""

from pymongo import AsyncMongoClient
from beanie import init_beanie

from application_model import Application
from user_model import User
from background_model import Background
from app_settings_model import AppSettings


async def init_mongo():
    # Async driver keeps the same API shape as the rest of the async FastAPI stack.
    client = AsyncMongoClient(
        "mongodb+srv://chriss:VRf4H6BafmZbe8C@cluster0.acnynb2.mongodb.net/?appName=Cluster0"
    )
    db = client["job_app_db"]

    print("✅ Connecting to MongoDB...")

    # Registers schemas ↔ collections (users, backgrounds, applications, app_settings).
    await init_beanie(
        database=db, document_models=[User, Background, Application, AppSettings]
    )

    print("✅ MongoDB connected and Beanie initialized")
