from __future__ import annotations

import sys
from urllib.parse import urljoin

import httpx

from app.config import get_settings
from app.utils.logging import configure_logging, get_logger


HUB_URL = "https://pubsubhubbub.appspot.com/subscribe"


def build_payload(callback_url: str, topic_url: str, secret: str) -> dict[str, str]:
    payload = {
        "hub.callback": callback_url,
        "hub.mode": "subscribe",
        "hub.topic": topic_url,
        "hub.verify": "async",
        "hub.verify_token": secret,
    }
    if secret:
        payload["hub.secret"] = secret
    return payload


def main() -> int:
    settings = get_settings()
    configure_logging(settings.log_level)
    logger = get_logger("websub_init")

    callback_url = urljoin(
        settings.web_sub_callback_base.rstrip("/") + "/",
        "webhook/youtube",
    )
    topic_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={settings.youtube_channel_id}"
    payload = build_payload(callback_url, topic_url, settings.web_sub_secret)

    logger.info("websub_subscribe_start", callback_url=callback_url, topic_url=topic_url)
    with httpx.Client(timeout=30) as client:
        response = client.post(HUB_URL, data=payload, follow_redirects=True)
    if response.status_code not in (202, 204, 200):
        logger.error(
            "websub_subscribe_failed",
            status_code=response.status_code,
            body=response.text[:500],
        )
        return 1
    logger.info("websub_subscribe_ok", hub_response=response.status_code)
    return 0


if __name__ == "__main__":
    sys.exit(main())
