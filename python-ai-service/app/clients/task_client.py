from __future__ import annotations

from typing import Any

import httpx


class TaskClient:
    def __init__(self, base_url: str, session: httpx.Client | None = None) -> None:
        self._base_url = base_url.rstrip("/")
        self._session = session or httpx.Client()

    def update_status(self, job_id: int, status: str, stage: str, error_message: str | None = None) -> None:
        payload: dict[str, Any] = {
            "status": status,
            "stage": stage,
            "error_message": error_message,
        }
        response = self._session.post(
            f"{self._base_url}/internal/tasks/{job_id}/status",
            json=payload,
            timeout=15,
        )
        response.raise_for_status()
