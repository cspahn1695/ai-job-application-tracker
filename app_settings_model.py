from beanie import Document


class AppSettings(Document):
    """Singleton-style global config (one document). First access creates defaults."""

    max_recommend_jobs: int = 10

    class Settings:
        name = "app_settings"


async def get_app_settings() -> AppSettings:
    doc = await AppSettings.find_one()
    if not doc:
        doc = AppSettings(max_recommend_jobs=10)
        await doc.insert()
    return doc
