from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.config import AppConfig
from app.utils.logging import get_logger


logger = get_logger("mapper")

_CONTROL_CHARS = re.compile(r"[\u0000-\u001F\u007F]")
_INVISIBLE_CHARS = re.compile(
    "[\u200B\u200C\u200D\u200E\u200F\u202A-\u202E\u2060\uFE0F\uFEFF\U000E0000-\U000E0FFF]"
)


@dataclass(slots=True)
class MappedMeta:
    title: str
    description: str
    tags: list[str]
    visibility: str
    thumbnail_path: Path | None


def _sanitize_text(value: str) -> str:
    cleaned = _CONTROL_CHARS.sub("", value)
    cleaned = _INVISIBLE_CHARS.sub("", cleaned)
    cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")
    return cleaned.strip()


def _compose_title(original_title: str, cfg: AppConfig) -> str:
    composed = f"{cfg.title_prefix or ''}{original_title}{cfg.title_suffix or ''}"
    composed = composed.replace("\n", " ")
    composed = _sanitize_text(composed)
    if len(composed) > cfg.max_title_len:
        composed = composed[: cfg.max_title_len].rstrip()
    return composed


def _read_description(desc_path: Path | None) -> str:
    if not desc_path or not desc_path.exists():
        return ""
    text = desc_path.read_text(encoding="utf-8", errors="ignore")
    return _sanitize_text(text)


def _map_tags(info_json: dict[str, Any], cfg: AppConfig) -> list[str]:
    if not cfg.tags_from_yt:
        return []
    tags = info_json.get("tags") or []
    if not isinstance(tags, list):
        return []
    cleaned_tags = []
    for raw_tag in tags:
        if not isinstance(raw_tag, str):
            continue
        tag = _sanitize_text(raw_tag)
        if tag:
            cleaned_tags.append(tag[:100])
    return cleaned_tags[:30]


def map_metadata(
    info_json: dict[str, Any],
    desc_path: Path | None,
    thumb: Path | None,
    cfg: AppConfig,
) -> MappedMeta:
    original_title = info_json.get("title", "Untitled video")
    title = _compose_title(original_title, cfg)
    description = _read_description(desc_path)
    if cfg.max_desc_len and len(description) > cfg.max_desc_len:
        description = description[: cfg.max_desc_len].rstrip()

    tags = _map_tags(info_json, cfg)
    meta = MappedMeta(
        title=title,
        description=description,
        tags=tags,
        visibility=cfg.rutube_visibility,
        thumbnail_path=thumb if thumb and thumb.exists() else None,
    )
    logger.info(
        "metadata_mapped",
        title=meta.title,
        tags=len(meta.tags),
        thumbnail=meta.thumbnail_path.name if meta.thumbnail_path else None,
        visibility=meta.visibility,
    )
    return meta
