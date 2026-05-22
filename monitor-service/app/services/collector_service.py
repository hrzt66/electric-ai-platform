from __future__ import annotations

import json
from typing import AsyncGenerator


class CollectorService:
    def get_overview(self) -> dict:
        return {
            "overall_health": "healthy",
            "host_snapshot": {"platform_family": "unknown", "cpu_usage_percent": 0.0},
            "accelerator_snapshot": {"accelerator_type": "unavailable", "available": False},
            "service_snapshots": [],
            "task_runtime_context": {"active_task_count": 0},
            "active_alerts": [],
            "recent_alerts": [],
        }

    def get_alerts(self) -> dict:
        return {"active_alerts": [], "recent_alerts": []}

    async def event_stream(self) -> AsyncGenerator[str, None]:
        payload = {"overall_health": self.get_overview()["overall_health"]}
        yield f"event: snapshot\ndata: {json.dumps(payload)}\n\n"
