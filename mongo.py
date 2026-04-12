import asyncio

from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie

from user_model import User

async def init_mongo():
    client = AsyncIOMotorClient("mongodb://localhost:27017/")
    db = client["job_app_db"]

    print("✅ Connecting to MongoDB...")

    await init_beanie(
        database=db,
        document_models=[User]
    )

    print("✅ MongoDB connected and Beanie initialized")

