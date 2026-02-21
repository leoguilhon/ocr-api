from datetime import datetime, timezone

from fastapi import APIRouter, Request

from app.core.config import get_settings

router = APIRouter(tags=["health"])
settings = get_settings()


@router.get("/health")
def health(request: Request) -> dict:
    started_at: datetime = request.app.state.started_at
    uptime = (datetime.now(timezone.utc) - started_at).total_seconds()
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
        "uptime_seconds": round(uptime, 2),
    }
