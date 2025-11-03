from __future__ import annotations

import time
from typing import Iterable

import feedparser

from app.config import get_settings
from app.db import repo
from app.db.base import session_scope
from app.services.orchestrator import enqueue_publish_job
from app.utils.logging import get_logger


logger = get_logger("rss")


def _extract_video_ids(entries: Iterable[feedparser.FeedParserDict]) -> list[str]:
    video_ids: list[str] = []
    for entry in entries:
        video_id = entry.get("yt_videoid") or entry.get("yt_video_id")
        if video_id:
            video_ids.append(str(video_id))
    return video_ids


def poll_once() -> list[str]:
    settings = get_settings()
    feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={settings.youtube_channel_id}"
    logger.info("rss_poll_start", feed_url=feed_url)
    parsed = feedparser.parse(feed_url)

    if parsed.bozo:
        logger.warning("rss_poll_error", error=str(parsed.bozo_exception))
        return []

    video_ids = _extract_video_ids(parsed.entries)
    logger.info("rss_entries", count=len(video_ids))

    enqueued: list[str] = []
    with session_scope() as session:
        for video_id in video_ids:
            if repo.is_published(session, video_id):
                continue
            enqueue_publish_job(video_id)
            enqueued.append(video_id)
    logger.info("rss_enqueued", count=len(enqueued), video_ids=enqueued)
    return enqueued


def poll_loop() -> None:
    settings = get_settings()
    interval = settings.poll_interval_seconds
    logger.info("rss_poll_loop_start", interval=interval)
    while True:
        try:
            poll_once()
        except Exception as exc:  # noqa: BLE001
            logger.error("rss_poll_failed", error=str(exc))
        time.sleep(interval)


def main() -> None:
    from app.utils.logging import configure_logging

    settings = get_settings()
    configure_logging(settings.log_level)
    poll_loop()


if __name__ == "__main__":
    main()
