from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import PublishedVideo


def get_published(session: Session, video_id: str) -> PublishedVideo | None:
    return session.get(PublishedVideo, video_id)


def is_published(session: Session, video_id: str) -> bool:
    return get_published(session, video_id) is not None


def mark_published(session: Session, video_id: str, rutube_url: str) -> None:
    session.merge(
        PublishedVideo(
            video_id=video_id,
            rutube_url=rutube_url,
            created_at=datetime.now(timezone.utc),
        )
    )


def get_recent(session: Session, limit: int = 50) -> Sequence[PublishedVideo]:
    stmt = (
        select(PublishedVideo)
        .order_by(PublishedVideo.created_at.desc())
        .limit(limit)
    )
    return session.execute(stmt).scalars().all()
