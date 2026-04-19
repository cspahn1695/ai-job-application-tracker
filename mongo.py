import asyncio

from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from application_model import Application
from user_model import User
from background_model import Background

async def init_mongo():
    client = AsyncIOMotorClient("mongodb+srv://chriss:VRf4H6BafmZbe8C@cluster0.acnynb2.mongodb.net/?appName=Cluster0")
    db = client["job_app_db"]

    print("✅ Connecting to MongoDB...")

    await init_beanie(
        database=db,
        document_models=[User, Background, Application]
    )

    print("✅ MongoDB connected and Beanie initialized")

