from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app import __version__
from app.config import AppConfig, get_settings
from app.db.base import get_session
from app.db import repo
from app.services.orchestrator import enqueue_publish_job
from app.utils.logging import get_logger


router = APIRouter()
logger = get_logger("admin")


@router.get("/version")
def version(settings: AppConfig = Depends(get_settings)) -> dict[str, str]:
    return {"version": settings.application_version or __version__}


@router.get("/trigger")
def trigger_video(
    video_id: str = Query(..., alias="videoId"),
    force: bool = Query(False),
    session=Depends(get_session),
) -> Response:
    if not video_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid videoId")

    if not force and repo.is_published(session, video_id):
        logger.info("trigger_duplicate", video_id=video_id)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already published")

    enqueue_publish_job(video_id)
    logger.info("trigger_enqueued", video_id=video_id)
    return Response(status_code=status.HTTP_202_ACCEPTED)


@router.get("/published")
def list_published(
    limit: int = Query(50, ge=1, le=200),
    session=Depends(get_session),
) -> list[dict[str, Any]]:
    videos = repo.get_recent(session, limit=limit)
    return [
        {
            "videoId": item.video_id,
            "rutubeUrl": item.rutube_url,
            "createdAt": item.created_at.isoformat(),
        }
        for item in videos
    ]
