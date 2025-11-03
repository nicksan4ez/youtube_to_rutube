from __future__ import annotations

import hashlib
import hmac
import xml.etree.ElementTree as ET
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.config import AppConfig, get_settings
from app.db.base import get_session
from app.db import repo
from app.services.orchestrator import enqueue_publish_job
from app.utils.logging import get_logger


router = APIRouter()
logger = get_logger("webhook")


def _verify_signature(config: AppConfig, signature_headers: dict[str, str], body: bytes) -> bool:
    if not config.web_sub_secret:
        return True

    expected = hmac.new(config.web_sub_secret.encode("utf-8"), body, hashlib.sha1).hexdigest()
    header_value = signature_headers.get("x-hub-signature", "")
    if header_value.startswith("sha1="):
        header_value = header_value[5:]
    if hmac.compare_digest(expected, header_value):
        return True

    header_sha256 = signature_headers.get("x-hub-signature-256", "")
    if header_sha256.startswith("sha256="):
        digest = hashlib.sha256
        expected256 = hmac.new(config.web_sub_secret.encode("utf-8"), body, digest).hexdigest()
        return hmac.compare_digest(expected256, header_sha256[7:])
    return False


def _extract_video_ids(xml_body: bytes) -> list[str]:
    try:
        root = ET.fromstring(xml_body)
    except ET.ParseError as exc:  # noqa: BLE001
        logger.warning("websub_invalid_xml", error=str(exc))
        return []

    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "yt": "http://www.youtube.com/xml/schemas/2015",
    }
    video_ids: list[str] = []
    for entry in root.findall("atom:entry", ns):
        video_id_elem = entry.find("yt:videoId", ns)
        if video_id_elem is not None and video_id_elem.text:
            video_ids.append(video_id_elem.text.strip())
    return video_ids


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/webhook/youtube")
async def youtube_challenge(request: Request, settings: AppConfig = Depends(get_settings)) -> Response:
    challenge = request.query_params.get("hub.challenge")
    if not challenge:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing challenge")
    logger.info(
        "websub_challenge",
        mode=request.query_params.get("hub.mode"),
        topic=request.query_params.get("hub.topic"),
    )
    return Response(content=challenge, media_type="text/plain")


@router.post("/webhook/youtube")
async def youtube_notification(
    request: Request,
    settings: AppConfig = Depends(get_settings),
    db_session=Depends(get_session),
) -> Response:
    body = await request.body()
    headers = {k.lower(): v for k, v in request.headers.items()}

    if not _verify_signature(settings, headers, body):
        logger.warning("websub_signature_invalid")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid signature")

    video_ids = _extract_video_ids(body)
    logger.info("websub_notification", video_ids=video_ids)
    accepted = []
    for video_id in video_ids:
        if repo.is_published(db_session, video_id):
            logger.info("websub_duplicate", video_id=video_id)
            continue
        enqueue_publish_job(video_id)
        accepted.append(video_id)

    if not accepted:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    return Response(status_code=status.HTTP_202_ACCEPTED)
