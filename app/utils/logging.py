from __future__ import annotations

import logging
import sys
from typing import Any

import structlog


def _shared_processors() -> list[structlog.typing.Processor]:
    return [
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]


def configure_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level.upper(), logging.INFO),
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.EventRenamer("message"),
            *_shared_processors(),
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper(), logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)


def log_exception(logger: structlog.stdlib.BoundLogger, exc: BaseException, **extra: Any) -> None:
    logger.error(
        "exception",
        exception_name=exc.__class__.__name__,
        exception_message=str(exc),
        **extra,
    )
