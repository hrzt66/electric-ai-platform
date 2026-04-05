from __future__ import annotations

"""Redis Stream Worker 入口，持续消费任务服务投递的真实生成任务。"""

import os
import socket

import redis

from app.core.settings import Settings, get_settings
from app.dependencies import build_job_pipeline
from app.workers.job_worker import JobWorker


def build_worker(*, pipeline=None, settings: Settings | None = None) -> JobWorker:
    """保留独立构造函数，便于测试时替换 pipeline 或自定义设置。"""
    return JobWorker(pipeline=pipeline or build_job_pipeline(settings=settings))


def main() -> int:
    settings = get_settings()
    redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    worker = build_worker(settings=settings)
    # 默认把主机名和进程号拼成 consumer 名称，方便排查多实例消费日志。
    consumer_name = os.getenv("ELECTRIC_AI_WORKER_NAME", f"{socket.gethostname()}-{os.getpid()}")
    worker.consume_forever(redis_client, consumer_name=consumer_name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
