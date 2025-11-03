from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright

from app.config import get_settings
from app.utils.logging import configure_logging, get_logger


def main() -> int:
    settings = get_settings()
    configure_logging(settings.log_level)
    logger = get_logger("auth_playwright")

    target_path = settings.cookies_path
    target_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info("auth_start", target=str(target_path))
    print("A Chromium window will open. Log in to RuTube, then return to this terminal.")
    print("After completing login and ensuring Studio access, press Enter here.")

    with sync_playwright() as sp:
        browser = sp.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto("https://rutube.ru/", wait_until="domcontentloaded")
        input("Press Enter after completing authentication: ")

        context.storage_state(path=str(target_path))
        logger.info("auth_storage_saved", path=str(target_path))
        print(f"OK: storage state saved to {target_path}")

        context.close()
        browser.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
