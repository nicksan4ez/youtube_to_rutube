from __future__ import annotations

import time
from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from app.services.mapper import MappedMeta
from app.utils.logging import get_logger


logger = get_logger("uploader")

UPLOAD_URL = "https://studio.rutube.ru/video/upload"
TITLE_SELECTORS = [
    'textarea[name="title"]',
    'input[name="title"]',
    '[data-testid="title-input"] textarea',
    '[data-testid="title-input"] input',
    'textarea[placeholder*="Название"]',
]
DESCRIPTION_SELECTORS = [
    'textarea[name="description"]',
    '[data-testid="description-input"] textarea',
    'textarea[placeholder*="Описание"]',
]
TAGS_SELECTORS = [
    '[data-testid="tags-input"] input',
    'input[name="tags"]',
    'input[placeholder*="Теги"]',
]
VISIBILITY_LABELS = {
    "public": ["Открытый доступ", "Public", "Публичный доступ"],
    "unlisted": ["Доступ по ссылке", "Unlisted"],
    "private": ["Частный доступ", "Private"],
}
PREVIEW_SELECTORS = [
    'input[type="file"][data-testid="thumbnail-upload"]',
    'input[name="poster"]',
]


class UploadError(RuntimeError):
    pass


def _fill_first(page, selectors: list[str], value: str) -> None:
    for selector in selectors:
        locator = page.locator(selector)
        if locator.count():
            locator.first.fill(value)
            return
        try:
            locator.first.wait_for(timeout=2000)
            locator.first.fill(value)
            return
        except PlaywrightTimeoutError:
            continue
    raise UploadError(f"Unable to find selector from list {selectors}")


def _set_visibility(page, visibility: str) -> None:
    options = VISIBILITY_LABELS.get(visibility, [])
    for label in options:
        locator = page.locator(f"label:has-text('{label}')")
        if locator.count():
            locator.first.click()
            return
    # fallback to button text search
    for label in options:
        try:
            page.get_by_text(label, exact=False).click(timeout=3000)
            return
        except PlaywrightTimeoutError:
            continue
    raise UploadError(f"Unable to set visibility {visibility}")


def _wait_for_video_url(page, timeout_ms: int = 180_000) -> str:
    end_time = time.time() + timeout_ms / 1000
    checked_selector = 'a[href*="rutube.ru/video/"]'
    while time.time() < end_time:
        anchors = page.locator(checked_selector)
        if anchors.count():
            href = anchors.first.get_attribute("href")
            if href:
                return href
        try:
            anchors.first.wait_for(state="attached", timeout=5000)
        except PlaywrightTimeoutError:
            time.sleep(2)
    raise UploadError("Timed out waiting for RuTube URL after upload")


def upload_to_rutube(video_path: Path, meta: MappedMeta, cookies_path: Path) -> str:
    if not video_path.exists():
        raise FileNotFoundError(video_path)
    if not cookies_path.exists():
        raise FileNotFoundError(cookies_path)

    logger.info("uploader_start", video_path=str(video_path), visibility=meta.visibility)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(storage_state=str(cookies_path))
        page = context.new_page()
        page.set_default_timeout(60_000)

        page.goto(UPLOAD_URL, wait_until="domcontentloaded")
        page.wait_for_load_state("networkidle")
        logger.info("uploader_page_loaded")

        file_input = page.locator('input[type="file"]')
        file_input.set_input_files(str(video_path))
        logger.info("uploader_file_selected")

        _fill_first(page, TITLE_SELECTORS, meta.title)
        _fill_first(page, DESCRIPTION_SELECTORS, meta.description)

        if meta.tags:
            tags_value = ", ".join(meta.tags)
            try:
                _fill_first(page, TAGS_SELECTORS, tags_value)
            except UploadError:
                logger.warning("uploader_tags_not_found")

        try:
            _set_visibility(page, meta.visibility)
        except UploadError as exc:
            logger.warning("uploader_visibility_warning", error=str(exc))

        if meta.thumbnail_path and meta.thumbnail_path.exists():
            for selector in PREVIEW_SELECTORS:
                preview_input = page.locator(selector)
                if preview_input.count():
                    preview_input.set_input_files(str(meta.thumbnail_path))
                    logger.info("uploader_thumbnail_set")
                    break
            else:
                logger.info("uploader_thumbnail_ui_unavailable")
        else:
            logger.info("uploader_thumbnail_skipped")

        # wait for upload to process
        try:
            published_url = _wait_for_video_url(page)
        finally:
            context.close()
            browser.close()

    logger.info("uploader_complete", rutube_url=published_url)
    return published_url
