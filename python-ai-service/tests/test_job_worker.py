import json

from redis.exceptions import ConnectionError as RedisConnectionError


class FakePipeline:
    def __init__(self) -> None:
        self.jobs = []

    def run(self, job):
        self.jobs.append(job)
        return [{"file_path": "G:/electric-ai-runtime/outputs/images/7_0_11.png"}]


class FakeRedis:
    def __init__(self, messages, reclaimed=None):
        self.messages = messages
        self.reclaimed = reclaimed or ["0-0", [], []]
        self.acked = []
        self.autoclaim_calls = []

    def xreadgroup(self, **kwargs):
        return self.messages

    def xautoclaim(self, *args, **kwargs):
        self.autoclaim_calls.append((args, kwargs))
        return self.reclaimed

    def xack(self, stream_name, group_name, message_id):
        self.acked.append((stream_name, group_name, message_id))
        return 1


def test_job_worker_merges_stream_job_id_into_payload():
    from app.workers.job_worker import JobWorker

    pipeline = FakePipeline()
    worker = JobWorker(pipeline=pipeline)

    result = worker.process_stream_message(
        {
            "job_id": "7",
            "payload": json.dumps(
                {
                    "prompt": "substation",
                    "negative_prompt": "blurry",
                    "model_name": "sd15-electric",
                    "seed": 11,
                    "steps": 20,
                    "guidance_scale": 7.5,
                    "width": 512,
                    "height": 512,
                    "num_images": 1,
                }
            ),
        }
    )

    assert result[0]["file_path"].endswith("7_0_11.png")
    assert pipeline.jobs[0].job_id == 7


def test_job_worker_consume_once_acks_processed_messages():
    from app.workers.job_worker import JobWorker

    pipeline = FakePipeline()
    worker = JobWorker(pipeline=pipeline, stream_name="stream:generate:jobs", group_name="python-ai-runtime")
    redis_client = FakeRedis(
        [
            (
                "stream:generate:jobs",
                [
                    (
                        "1743840000000-0",
                        {
                            "job_id": "9",
                            "payload": json.dumps(
                                {
                                    "prompt": "inspection robot",
                                    "negative_prompt": "artifact",
                                    "model_name": "sd15-electric",
                                    "seed": 22,
                                    "steps": 30,
                                    "guidance_scale": 7.5,
                                    "width": 512,
                                    "height": 512,
                                    "num_images": 1,
                                }
                            ),
                        },
                    )
                ],
            )
        ]
    )

    processed = worker.consume_once(redis_client, consumer_name="worker-1")

    assert processed == 1
    assert pipeline.jobs[0].job_id == 9
    assert redis_client.acked == [("stream:generate:jobs", "python-ai-runtime", "1743840000000-0")]


def test_job_worker_consume_once_reclaims_stale_pending_messages_when_no_new_messages():
    from app.workers.job_worker import JobWorker

    pipeline = FakePipeline()
    worker = JobWorker(
        pipeline=pipeline,
        stream_name="stream:generate:jobs",
        group_name="python-ai-runtime",
        pending_idle_ms=60000,
    )
    redis_client = FakeRedis(
        [],
        reclaimed=[
            "0-0",
            [
                (
                    "1743840000001-0",
                    {
                        "job_id": "10",
                        "payload": json.dumps(
                            {
                                "prompt": "inspection robot",
                                "negative_prompt": "artifact",
                                "model_name": "sd15-electric",
                                "seed": 23,
                                "steps": 30,
                                "guidance_scale": 7.5,
                                "width": 512,
                                "height": 512,
                                "num_images": 1,
                            }
                        ),
                    },
                )
            ],
            [],
        ],
    )

    processed = worker.consume_once(redis_client, consumer_name="worker-1")

    assert processed == 1
    assert pipeline.jobs[0].job_id == 10
    assert redis_client.acked == [("stream:generate:jobs", "python-ai-runtime", "1743840000001-0")]
    assert redis_client.autoclaim_calls


def test_job_worker_prioritizes_new_messages_before_reclaiming_pending():
    from app.workers.job_worker import JobWorker

    pipeline = FakePipeline()
    worker = JobWorker(
        pipeline=pipeline,
        stream_name="stream:generate:jobs",
        group_name="python-ai-runtime",
        pending_idle_ms=60000,
    )
    redis_client = FakeRedis(
        [
            (
                "stream:generate:jobs",
                [
                    (
                        "1743840000002-0",
                        {
                            "job_id": "11",
                            "payload": json.dumps(
                                {
                                    "prompt": "new task",
                                    "negative_prompt": "artifact",
                                    "model_name": "sd15-electric",
                                    "seed": 24,
                                    "steps": 30,
                                    "guidance_scale": 7.5,
                                    "width": 512,
                                    "height": 512,
                                    "num_images": 1,
                                }
                            ),
                        },
                    )
                ],
            )
        ],
        reclaimed=[
            "0-0",
            [
                (
                    "1743840000003-0",
                    {
                        "job_id": "12",
                        "payload": json.dumps(
                            {
                                "prompt": "stale task",
                                "negative_prompt": "artifact",
                                "model_name": "sd15-electric",
                                "seed": 25,
                                "steps": 30,
                                "guidance_scale": 7.5,
                                "width": 512,
                                "height": 512,
                                "num_images": 1,
                            }
                        ),
                    },
                )
            ],
            [],
        ],
    )

    processed = worker.consume_once(redis_client, consumer_name="worker-1")

    assert processed == 1
    assert pipeline.jobs[0].job_id == 11
    assert redis_client.acked == [("stream:generate:jobs", "python-ai-runtime", "1743840000002-0")]
    assert redis_client.autoclaim_calls == []


def test_job_worker_retries_after_redis_connection_drop():
    from app.workers.job_worker import JobWorker

    pipeline = FakePipeline()
    sleep_calls = []
    worker = JobWorker(
        pipeline=pipeline,
        sleep_fn=lambda seconds: sleep_calls.append(seconds),
    )
    worker.ensure_consumer_group = lambda redis_client: None

    attempts = {"count": 0}

    def fake_consume_once(redis_client, *, consumer_name):
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise RedisConnectionError("Connection closed by server.")
        raise StopIteration("stop loop for test")

    worker.consume_once = fake_consume_once

    try:
        worker.consume_forever(object(), consumer_name="worker-1")
    except StopIteration:
        pass

    assert attempts["count"] == 2
    assert sleep_calls == [1]
