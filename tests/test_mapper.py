from __future__ import annotations

from pathlib import Path

from app.config import AppConfig
from app.services.mapper import map_metadata


def make_config(tmp_path: Path) -> AppConfig:
    return AppConfig(
        youtube_channel_id="test",
        web_sub_callback_base="https://example.com",
        web_sub_secret="secret",
        redis_url="redis://localhost:6379/0",
        work_dir=tmp_path,
        database_path=tmp_path / "test.db",
        enable_transcode=False,
        rutube_visibility="public",
        tags_from_yt=True,
        title_prefix="[YT] ",
        title_suffix="",
        max_title_len=20,
        max_desc_len=40,
        poll_interval_seconds=300,
        max_concurrency=1,
        log_level="INFO",
        application_version="test",
        cookies_path=tmp_path / "cookies.json",
    )


def test_map_metadata_normalizes(tmp_path: Path):
    cfg = make_config(tmp_path)
    desc_file = tmp_path / "video.description"
    desc_file.write_text("Line1\r\nLine2\u200b", encoding="utf-8")
    info_json = {
        "id": "video123",
        "title": "Video Title 🎉",
        "tags": ["Tag1", "Tag2", "Another Tag"],
    }

    mapped = map_metadata(info_json, desc_file, None, cfg)

    assert mapped.title == "[YT] Video Title"
    assert mapped.description == "Line1\nLine2"
    assert mapped.tags == ["Tag1", "Tag2", "Another Tag"]
    assert mapped.visibility == "public"
