from typing import Annotated

from fastapi import APIRouter, FastAPI, HTTPException, Path, File, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from database import engine
from models import Base 
from routes import router
from fastapi.middleware.cors import CORSMiddleware



app = FastAPI(title="Todo Items App", version="1.0.0")

#CORS= cross origin resource sharing 
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# connect the backend to the frontend (specifically index.html)
@app.get("/")
async def home():
    return FileResponse("frontend/index.html")

# Create database tables automatically at startup.
Base.metadata.create_all(bind=engine)

app.include_router(router) # connect to router

# the router needs to be before the mount.
# otherwise, the routes cannot be found.
app.mount("/static", StaticFiles(directory="frontend"), name="static")  # static are details the user enters

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads") #uploads are the resume the user uploads

