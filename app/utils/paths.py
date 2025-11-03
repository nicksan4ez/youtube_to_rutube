from __future__ import annotations

import re
from pathlib import Path


_SAFE_CHARS_PATTERN = re.compile(r"[^A-Za-z0-9_.-]+")


def safe_name(value: str) -> str:
    cleaned = _SAFE_CHARS_PATTERN.sub("_", value)
    return cleaned.strip("_") or "video"


def get_video_work_dir(base_dir: Path, video_id: str) -> Path:
    path = base_dir / safe_name(video_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def cleanup_dir(path: Path, preserve_suffixes: set[str] | None = None) -> None:
    if not path.exists() or not path.is_dir():
        return
    for item in path.iterdir():
        if item.is_dir():
            cleanup_dir(item, preserve_suffixes)
            try:
                item.rmdir()
            except OSError:
                continue
        else:
            if preserve_suffixes and any(item.name.endswith(suffix) for suffix in preserve_suffixes):
                continue
            item.unlink(missing_ok=True)
