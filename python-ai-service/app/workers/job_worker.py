from __future__ import annotations

import json

from app.schemas.jobs import GenerateJob


class JobWorker:
    def __init__(self, pipeline) -> None:
        self._pipeline = pipeline

    def process_payload(self, payload: str) -> list[dict]:
        job = GenerateJob.model_validate(json.loads(payload))
        return self._pipeline.run(job)
