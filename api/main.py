from fastapi import FastAPI
from .routes import audio_routes

app = FastAPI(
    title="Audio Processing API",
    description="API for processing audio files and YouTube videos",
    version="1.0.0"
)

app.include_router(
    audio_routes.router,
    prefix="/audio",
    tags=["audio"]
)
