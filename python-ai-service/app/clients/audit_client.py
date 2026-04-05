from __future__ import annotations

import httpx


class AuditClient:
    def __init__(self, base_url: str, session: httpx.Client | None = None) -> None:
        self._base_url = base_url.rstrip("/")
        self._session = session or httpx.Client()

    def record_event(self, event_type: str, payload: dict) -> None:
        response = self._session.post(
            f"{self._base_url}/api/v1/audit/task-events",
            json={"event_type": event_type, "payload": payload},
            timeout=15,
        )
        response.raise_for_status()
