# used ChatGPT to help write this code; added comments where appropriate.
"""FastAPI entrypoint: wires routers, static frontend, and uploaded files.

API routes must be registered before mounting ``/static`` and ``/uploads`` so
path-specific handlers win over the catch-all static mounts.
"""
from typing import Annotated

from fastapi import APIRouter, FastAPI, HTTPException, Path, File, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from routes import router
from fastapi.middleware.cors import CORSMiddleware

from mongo import init_mongo
from auth_routes import router as auth_router
from background_routes import router as background_router
from settings_routes import router as settings_router



app = FastAPI(title="Todo Items App", version="1.0.0")

# CORS lets the browser call this API from file:// or another origin during dev.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def on_startup():
    await init_mongo()

# connect the backend to the frontend (specifically index.html)
@app.get("/")
async def home():
    return FileResponse("frontend/login.html")


app.include_router(router) # connect to router
app.include_router(auth_router) # connect to auth router
app.include_router(background_router) # connect to background router
app.include_router(settings_router)

# Register routers before mounts so /applications/* etc. are not swallowed by StaticFiles.
app.mount("/static", StaticFiles(directory="frontend"), name="static")

# Resumes are saved under ./uploads by routes.py; this exposes them at /uploads/<filename>.
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

