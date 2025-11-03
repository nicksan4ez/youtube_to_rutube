from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from app.utils.logging import get_logger


logger = get_logger("transcoder")


FFMPEG_COMMAND = [
    "ffmpeg",
    "-y",
    "-i",
    "{input}",
    "-c:v",
    "libx264",
    "-crf",
    "20",
    "-preset",
    "veryfast",
    "-pix_fmt",
    "yuv420p",
    "-c:a",
    "aac",
    "-b:a",
    "160k",
    "-movflags",
    "+faststart",
    "{output}",
]


def _ffmpeg_exists() -> bool:
    return shutil.which("ffmpeg") is not None


def maybe_transcode(path_in: Path, work_dir: Path, enabled: bool) -> Path:
    if not enabled:
        logger.info("transcode_skipped", reason="disabled")
        return path_in

    if not _ffmpeg_exists():
        logger.warning("transcode_skipped", reason="ffmpeg_missing")
        return path_in

    output_path = work_dir / f"{path_in.stem}_transcoded.mp4"
    cmd = [arg.format(input=str(path_in), output=str(output_path)) for arg in FFMPEG_COMMAND]
    logger.info("transcode_start", command=cmd)

    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as exc:
        logger.error(
            "transcode_failed",
            returncode=exc.returncode,
            stderr=exc.stderr.decode("utf-8", errors="ignore"),
        )
        raise

    logger.info("transcode_success", output=str(output_path))
    return output_path
