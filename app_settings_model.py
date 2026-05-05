"""Singleton Mongo document for tunables shared by all users (e.g. job search limit)."""
from beanie import Document


class AppSettings(Document):
    """One row in ``app_settings``; ``get_app_settings`` inserts defaults if missing."""

    max_recommend_jobs: int = 10

    class Settings:
        name = "app_settings"


async def get_app_settings() -> AppSettings:
    doc = await AppSettings.find_one()
    if not doc:
        doc = AppSettings(max_recommend_jobs=10)
        await doc.insert()
    return doc
