from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

from app.api import health, websocket
from app.config import get_settings
from app.core.logging import setup_logging

STATIC_DIR = Path(__file__).parent / "static"


def create_app() -> FastAPI:
    settings = get_settings()
    setup_logging(settings.log_level)
    app = FastAPI(title="voice-api", version=settings.app_version)
    app.include_router(health.router)
    app.include_router(websocket.router)

    if settings.app_env == "development":
        # 개발 전용 브라우저 테스트 콘솔. 운영 빌드에는 노출하지 않는다.
        @app.get("/test", include_in_schema=False)
        async def test_console() -> FileResponse:
            return FileResponse(STATIC_DIR / "test.html")

    return app


app = create_app()
