from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace

from app.services import rss


@contextmanager
def dummy_session_scope():
    yield object()


def test_poll_once_enqueues(monkeypatch):
    fake_feed = SimpleNamespace(
        entries=[
            {"yt_videoid": "new_video"},
            {"yt_videoid": "existing_video"},
        ],
        bozo=0,
    )

    calls: list[str] = []

    monkeypatch.setattr(rss, "session_scope", lambda: dummy_session_scope())
    monkeypatch.setattr(
        rss.repo,
        "is_published",
        lambda session, video_id: video_id == "existing_video",
    )
    monkeypatch.setattr(rss, "enqueue_publish_job", lambda video_id: calls.append(video_id))
    monkeypatch.setattr(rss.feedparser, "parse", lambda url: fake_feed)

    result = rss.poll_once()

    assert result == ["new_video"]
    assert calls == ["new_video"]
