from fastapi import APIRouter, HTTPException
from background_model import Background

router = APIRouter(prefix="/background", tags=["Background"])


def _norm_email(value: str) -> str:
    return (value or "").strip().lower()


# GET background
@router.get("/{email}")
async def get_background(email: str):
    email = _norm_email(email)
    bg = await Background.find_one(Background.email == email)

    if not bg:
        bg = Background(email=email)
        await bg.insert()

    return bg


# ADD item
@router.post("/{email}/{section}")
async def add_item(email: str, section: str, item: str):
    email = _norm_email(email)
    bg = await Background.find_one(Background.email == email)

    if not bg:
        bg = Background(email=email)
        await bg.insert()

    getattr(bg, section).append(item)
    await bg.save()

    return bg


# DELETE item
@router.delete("/{email}/{section}")
async def delete_item(email: str, section: str, item: str):
    email = _norm_email(email)
    bg = await Background.find_one(Background.email == email)

    if not bg:
        raise HTTPException(status_code=404, detail="Not found")

    getattr(bg, section).remove(item)
    await bg.save()

    return bg