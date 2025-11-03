from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from yt_dlp import YoutubeDL

from app.utils.logging import get_logger
from app.utils.retry import retry_on_exception


logger = get_logger("downloader")


@dataclass(slots=True)
class DownloadResult:
    video_path: Path
    info_json: dict[str, Any]
    description_path: Path | None
    thumbnail_path: Path | None
    subtitles_paths: list[Path]


def _build_yt_dlp(video_url: str, work_dir: Path) -> YoutubeDL:
    output_template = str(work_dir / "%(id)s.%(ext)s")
    ydl_opts = {
        "outtmpl": output_template,
        "writethumbnail": True,
        "writedescription": True,
        "writeinfojson": True,
        "writesubtitles": True,
        "subtitleslangs": ["all"],
        "quiet": True,
        "no_warnings": True,
        "format": "bestvideo+bestaudio/best",
    }
    logger.info("yt_dlp_configured", output_template=output_template)
    return YoutubeDL(ydl_opts)


def download_youtube(video_url: str, work_dir: Path) -> DownloadResult:
    work_dir.mkdir(parents=True, exist_ok=True)
    logger.info("yt_dlp_start", video_url=video_url, work_dir=str(work_dir))

    def _download() -> dict[str, Any]:
        with _build_yt_dlp(video_url, work_dir) as ydl:
            return ydl.extract_info(video_url, download=True)

    info = retry_on_exception(_download, operation="yt_dlp")

    video_path = Path(info.get("_filename") or "")
    if not video_path.exists():
        # fallback to manual compose if _filename absent
        video_ext = info.get("ext", "mp4")
        video_path = work_dir / f"{info['id']}.{video_ext}"

    info_json_path = work_dir / f"{info['id']}.info.json"
    description_path = work_dir / f"{info['id']}.description"

    thumbnail_path = None
    possible_thumbs = list(work_dir.glob(f"{info['id']}*.jpg")) + list(
        work_dir.glob(f"{info['id']}*.png")
    )
    if possible_thumbs:
        thumbnail_path = possible_thumbs[0]

    description_file = description_path if description_path.exists() else None
    subtitles = list(work_dir.glob(f"{info['id']}.*.vtt"))

    if info_json_path.exists():
        with info_json_path.open("r", encoding="utf-8") as fh:
            info_json = json.load(fh)
    else:
        info_json = info
        info_json_path.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")

    result = DownloadResult(
        video_path=video_path,
        info_json=info_json,
        description_path=description_file,
        thumbnail_path=thumbnail_path,
        subtitles_paths=subtitles,
    )
    logger.info(
        "yt_dlp_complete",
        video_path=str(result.video_path),
        info_json_path=str(info_json_path),
        description_path=str(description_file) if description_file else None,
        thumbnails=[thumb.name for thumb in possible_thumbs],
    )
    return result
