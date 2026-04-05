from __future__ import annotations

import httpx


class AssetClient:
    def __init__(self, base_url: str, session: httpx.Client | None = None) -> None:
        self._base_url = base_url.rstrip("/")
        self._session = session or httpx.Client()

    def save_results(self, job_id: int, results: list[dict]) -> None:
        response = self._session.post(
            f"{self._base_url}/api/v1/assets/results",
            json={"job_id": job_id, "results": results},
            timeout=30,
        )
        response.raise_for_status()
