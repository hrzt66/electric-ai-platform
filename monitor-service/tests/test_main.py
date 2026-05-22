from pathlib import Path
import sys

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class FakeCollectorService:
    def get_overview(self) -> dict:
        return {
            "overall_health": "healthy",
            "host_snapshot": {"platform_family": "macos", "cpu_usage_percent": 22.5},
            "accelerator_snapshot": {"accelerator_type": "apple-mps", "available": True},
            "service_snapshots": [],
            "task_runtime_context": {"active_task_count": 0},
            "active_alerts": [],
            "recent_alerts": [],
        }

    def get_alerts(self) -> dict:
        return {"active_alerts": [], "recent_alerts": []}

    async def event_stream(self):
        yield "event: snapshot\ndata: {\"overall_health\":\"healthy\"}\n\n"


def test_monitor_endpoints_return_expected_payloads():
    from app.main import create_app

    client = TestClient(create_app(collector_service=FakeCollectorService()))

    health_response = client.get("/health")
    overview_response = client.get("/api/v1/monitor/overview")
    alerts_response = client.get("/api/v1/monitor/alerts")

    assert health_response.status_code == 200
    assert health_response.json() == {"status": "ok"}
    assert overview_response.status_code == 200
    assert overview_response.json()["overall_health"] == "healthy"
    assert alerts_response.status_code == 200
    assert alerts_response.json()["active_alerts"] == []
    assert alerts_response.json()["recent_alerts"] == []


def test_monitor_stream_exposes_text_event_stream():
    from app.main import create_app

    client = TestClient(create_app(collector_service=FakeCollectorService()))

    with client.stream("GET", "/api/v1/monitor/stream") as response:
        body = b"".join(response.iter_bytes())

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert b"event: snapshot" in body
