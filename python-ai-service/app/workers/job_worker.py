from __future__ import annotations

"""Redis Stream 消费器，负责 FIFO 拉取、抢回挂起消息并驱动任务流水线执行。"""

import json
import logging
import time
from typing import Any

from redis.exceptions import ConnectionError as RedisConnectionError, ResponseError

from app.core.runtime_logging import configure_runtime_logging
from app.schemas.jobs import GenerateJob

configure_runtime_logging()
logger = logging.getLogger("electric_ai.runtime.worker")


class JobWorker:
    def __init__(
        self,
        pipeline,
        *,
        stream_name: str = "stream:generate:jobs",
        group_name: str = "python-ai-runtime",
        block_ms: int = 5000,
        read_count: int = 1,
        pending_idle_ms: int = 60000,
        pending_claim_count: int = 10,
        sleep_fn=time.sleep,
    ) -> None:
        """初始化消费组参数、批量大小、挂起消息回收策略和睡眠函数。"""
        self._pipeline = pipeline
        self._stream_name = stream_name
        self._group_name = group_name
        self._block_ms = block_ms
        self._read_count = read_count
        self._pending_idle_ms = pending_idle_ms
        self._pending_claim_count = pending_claim_count
        self._pending_start_id = "0-0"
        self._sleep_fn = sleep_fn

    def ensure_consumer_group(self, redis_client) -> None:
        """首次启动时确保消费组存在；重复创建消费组会被安全忽略。"""
        try:
            redis_client.xgroup_create(
                name=self._stream_name,
                groupname=self._group_name,
                id="0",
                mkstream=True,
            )
        except ResponseError as exc:
            if "BUSYGROUP" not in str(exc):
                raise

    def process_payload(self, payload: str, *, job_id: int | None = None) -> list[dict]:
        # 这里统一把 Redis 里的原始 JSON 负载恢复成 Pydantic 任务对象。
        payload_dict = json.loads(payload)
        if job_id is not None and "job_id" not in payload_dict:
            payload_dict["job_id"] = job_id
        job = GenerateJob.model_validate(payload_dict)
        return self._pipeline.run(job)

    def process_stream_message(self, fields: dict[str, Any]) -> list[dict]:
        """把 Redis Stream 原始字段解析成 payload，再交给任务流水线执行。"""
        decoded = self._normalize_fields(fields)
        payload = decoded.get("payload")
        if payload is None:
            raise ValueError("stream payload is missing")

        raw_job_id = decoded.get("job_id")
        job_id = int(raw_job_id) if raw_job_id is not None else None
        return self.process_payload(str(payload), job_id=job_id)

    def consume_once(self, redis_client, *, consumer_name: str) -> int:
        # 先消费新消息；如果队列暂时为空，再尝试领回长时间未确认的挂起消息。
        messages = redis_client.xreadgroup(
            groupname=self._group_name,
            consumername=consumer_name,
            streams={self._stream_name: ">"},
            count=self._read_count,
            block=self._block_ms,
        )
        if messages:
            return self._process_stream_batches(redis_client, messages)

        reclaimed = self._reclaim_stale_messages(redis_client, consumer_name=consumer_name)
        if reclaimed:
            logger.info("reclaimed stale messages count=%s consumer=%s", len(reclaimed), consumer_name)
            return self._process_stream_batches(redis_client, [(self._stream_name, reclaimed)])

        return 0

    def _process_stream_batches(self, redis_client, messages) -> int:
        # 只有 pipeline 成功返回后才会 ACK，对失败任务保留重试空间。
        processed = 0
        for stream_name, stream_messages in messages:
            normalized_stream_name = self._decode_value(stream_name)
            for message_id, fields in stream_messages:
                logger.info("processing stream message id=%s stream=%s", message_id, normalized_stream_name)
                self.process_stream_message(fields)
                redis_client.xack(normalized_stream_name, self._group_name, self._decode_value(message_id))
                processed += 1
        return processed

    def _reclaim_stale_messages(self, redis_client, *, consumer_name: str):
        """领回长时间未 ACK 的挂起消息，避免任务卡死在旧消费者上。"""
        if not hasattr(redis_client, "xautoclaim"):
            return []

        result = redis_client.xautoclaim(
            self._stream_name,
            self._group_name,
            consumer_name,
            self._pending_idle_ms,
            self._pending_start_id,
            count=self._pending_claim_count,
        )
        next_start_id, messages, _ = result
        self._pending_start_id = str(next_start_id or "0-0")
        return messages or []

    def consume_forever(self, redis_client, *, consumer_name: str) -> None:
        """进入常驻消费循环，持续从 Redis Stream 拉取或回收任务。"""
        self.ensure_consumer_group(redis_client)
        logger.info(
            "worker started stream=%s group=%s consumer=%s pending_idle_ms=%s",
            self._stream_name,
            self._group_name,
            consumer_name,
            self._pending_idle_ms,
        )
        while True:
            try:
                self.consume_once(redis_client, consumer_name=consumer_name)
            except RedisConnectionError as exc:
                # Redis 临时断连时保持进程存活，等待下一轮自动重试。
                logger.warning("worker lost redis connection consumer=%s error=%s", consumer_name, exc)
                self._sleep_fn(1)

    def _normalize_fields(self, fields: dict[Any, Any]) -> dict[str, Any]:
        """把 Redis 返回的 bytes / mixed dict 统一标准化为字符串键值。"""
        return {str(self._decode_value(key)): self._decode_value(value) for key, value in fields.items()}

    @staticmethod
    def _decode_value(value: Any) -> Any:
        """把 Redis bytes 值解码成 UTF-8 字符串，其余类型保持原样。"""
        if isinstance(value, bytes):
            return value.decode("utf-8")
        return value
