from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

from app.config import AppConfig
from app.services import orchestrator
from app.services.downloader import DownloadResult
from app.services.mapper import MappedMeta


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
        title_prefix="",
        title_suffix="",
        max_title_len=100,
        max_desc_len=5000,
        poll_interval_seconds=300,
        max_concurrency=1,
        log_level="INFO",
        application_version="test",
        cookies_path=tmp_path / "cookies.json",
    )


class DummyLock:
    def __init__(self):
        self.acquired = False

    def acquire(self, blocking: bool) -> bool:
        self.acquired = True
        return True

    def locked(self) -> bool:
        return self.acquired

    def release(self) -> None:
        self.acquired = False


@contextmanager
def dummy_session_scope():
    yield SimpleNamespace()


def test_publish_video_pipeline(monkeypatch, tmp_path: Path):
    cfg = make_config(tmp_path)
    order: list[str] = []

    monkeypatch.setattr(orchestrator, "get_settings", lambda: cfg)
    monkeypatch.setattr(orchestrator, "session_scope", lambda: dummy_session_scope())

    monkeypatch.setattr(orchestrator.repo, "get_published", lambda session, video_id: None)
    monkeypatch.setattr(orchestrator.repo, "mark_published", lambda session, video_id, url: order.append("mark"))

    def fake_download(url: str, work_dir: Path) -> DownloadResult:
        order.append("download")
        video_path = work_dir / "video.mp4"
        video_path.parent.mkdir(parents=True, exist_ok=True)
        video_path.write_text("data")
        return DownloadResult(
            video_path=video_path,
            info_json={"id": "abc", "title": "Title"},
            description_path=None,
            thumbnail_path=None,
            subtitles_paths=[],
        )

    monkeypatch.setattr(orchestrator, "download_youtube", fake_download)

    def fake_transcode(path_in: Path, work_dir: Path, enabled: bool) -> Path:
        order.append("transcode")
        return path_in

    monkeypatch.setattr(orchestrator, "maybe_transcode", fake_transcode)

    def fake_map(info_json, desc_path, thumb_path, cfg_param):
        order.append("map")
        return MappedMeta(title="t", description="d", tags=[], visibility="public", thumbnail_path=None)

    monkeypatch.setattr(orchestrator, "map_metadata", fake_map)

    monkeypatch.setattr(orchestrator, "upload_to_rutube", lambda path, meta, cookies: order.append("upload") or "https://rutube.ru/video/abc")

    monkeypatch.setattr(orchestrator, "cleanup_dir", lambda path, preserve_suffixes: order.append("cleanup"))

    dummy_lock = DummyLock()
    monkeypatch.setattr(orchestrator, "_redis_connection", lambda: SimpleNamespace(lock=lambda name, timeout, blocking_timeout: dummy_lock))

    result = orchestrator.publish_video("video123")

    assert result == "https://rutube.ru/video/abc"
    assert order == ["download", "transcode", "map", "upload", "mark", "cleanup"]
    assert not dummy_lock.locked()
