from __future__ import annotations

from redis import Redis
from rq import Connection, Worker

from app.config import get_settings
from app.services.orchestrator import FAILED_QUEUE_NAME, PUBLISH_QUEUE_NAME
from app.utils.logging import configure_logging, get_logger


def run() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    logger = get_logger("worker")
    redis_conn = Redis.from_url(settings.redis_url)

    with Connection(redis_conn):
        queues = [PUBLISH_QUEUE_NAME, FAILED_QUEUE_NAME]
        worker = Worker(queues, disable_default_exception_handler=False)
        logger.info("worker_start", queues=queues)
        worker.work(with_scheduler=True)


if __name__ == "__main__":
    run()
