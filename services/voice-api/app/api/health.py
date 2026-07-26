from fastapi import APIRouter

from app.config import get_settings

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    settings = get_settings()
    return {
        "status": "ok",
        "version": settings.app_version,
        "stt": "mock",
        "llm": "mock",
        "tts": "mock",
    }
