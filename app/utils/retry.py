from __future__ import annotations

import random
import time
from collections.abc import Callable
from typing import TypeVar

from app.config import get_retry_policy
from app.utils.logging import get_logger


T = TypeVar("T")


def retry_on_exception(func: Callable[[], T], *, operation: str) -> T:
    policy = get_retry_policy()
    logger = get_logger("retry").bind(operation=operation)

    attempt = 0
    delay = policy.base_delay_seconds

    while True:
        attempt += 1
        try:
            return func()
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "operation_failed",
                attempt=attempt,
                max_attempts=policy.max_attempts,
                error=str(exc),
            )
            if attempt >= policy.max_attempts:
                logger.error("operation_exhausted", attempt=attempt)
                raise
            jitter = delay * policy.jitter_factor * random.random()
            sleep_seconds = min(delay + jitter, policy.max_delay_seconds)
            time.sleep(sleep_seconds)
            delay = min(delay * 2, policy.max_delay_seconds)
