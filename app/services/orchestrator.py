from __future__ import annotations

import random
from pathlib import Path
from typing import Any

from redis import Redis
from rq import Queue
from rq.job import Job
from rq.retry import Retry

from app.config import get_retry_policy, get_settings
from app.db import repo
from app.db.base import session_scope
from app.services.downloader import DownloadResult, download_youtube
from app.services.mapper import MappedMeta, map_metadata
from app.services.transcoder import maybe_transcode
from app.services.uploader import upload_to_rutube
from app.utils.logging import get_logger
from app.utils.paths import cleanup_dir, get_video_work_dir


logger = get_logger("orchestrator")

PUBLISH_QUEUE_NAME = "publish"
FAILED_QUEUE_NAME = "failed"


def _redis_connection() -> Redis:
    settings = get_settings()
    return Redis.from_url(settings.redis_url)


def _publish_queue() -> Queue:
    return Queue(PUBLISH_QUEUE_NAME, connection=_redis_connection())


def _retry_strategy() -> Retry:
    policy = get_retry_policy()
    intervals: list[int] = []
    delay = policy.base_delay_seconds
    for _ in range(policy.max_attempts):
        jitter = delay * policy.jitter_factor * random.random()
        intervals.append(int(delay + jitter))
        delay = min(delay * 2, policy.max_delay_seconds)
    return Retry(max=policy.max_attempts, interval=intervals)


def enqueue_publish_job(video_id: str) -> Job:
    queue = _publish_queue()
    job_id = f"publish:{video_id}"
    retry = _retry_strategy()
    job = queue.enqueue(
        publish_video,
        video_id,
        job_id=job_id,
        retry=retry,
        result_ttl=0,
        failure_ttl=7 * 24 * 3600,
        description=f"Publish video {video_id} to RuTube",
    )
    logger.info("job_enqueued", video_id=video_id, job_id=job.id)
    return job


def _should_skip(video_id: str) -> tuple[bool, str | None]:
    with session_scope() as session:
        record = repo.get_published(session, video_id)
        if record is None:
            return False, None
        return True, record.rutube_url


def publish_video(video_id: str) -> str:
    settings = get_settings()
    logger_local = logger.bind(video_id=video_id)

    skip, existing_url = _should_skip(video_id)
    if skip:
        logger_local.info("publish_skip_duplicate")
        if existing_url:
            return existing_url
        raise RuntimeError(f"Video {video_id} already published")

    youtube_url = f"https://www.youtube.com/watch?v={video_id}"
    work_dir = get_video_work_dir(settings.work_dir, video_id)
    logger_local.info("publish_start", youtube_url=youtube_url, work_dir=str(work_dir))

    redis_conn = _redis_connection()
    lock = redis_conn.lock(f"lock:publish:{video_id}", timeout=3600, blocking_timeout=5)
    if not lock.acquire(blocking=True):
        raise RuntimeError("Unable to acquire lock for video processing")

    try:
        try:
            download_result = download_youtube(youtube_url, work_dir)

            final_video_path = maybe_transcode(
                download_result.video_path, work_dir, settings.enable_transcode
            )
            mapped_meta = map_metadata(
                download_result.info_json,
                download_result.description_path,
                download_result.thumbnail_path,
                settings,
            )
            rutube_url = upload_to_rutube(final_video_path, mapped_meta, settings.cookies_path)

            with session_scope() as session:
                repo.mark_published(session, video_id, rutube_url)
            logger_local.info("publish_success", rutube_url=rutube_url)
            return rutube_url
        except Exception as exc:  # noqa: BLE001
            logger_local.error("publish_failed", error=str(exc))
            raise
        finally:
            preserve = {".info.json", ".json", ".log"}
            cleanup_dir(work_dir, preserve_suffixes=preserve)
    finally:
        if lock.locked():
            lock.release()
