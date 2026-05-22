from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import StreamingResponse

from app.dependencies import build_collector_service


def create_app(*, collector_service=None) -> FastAPI:
    service = collector_service

    def get_service():
        nonlocal service
        if service is None:
            service = build_collector_service()
        return service

    app = FastAPI(title="monitor-service")

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.get("/api/v1/monitor/overview")
    def overview() -> dict:
        return get_service().get_overview()

    @app.get("/api/v1/monitor/alerts")
    def alerts() -> dict:
        return get_service().get_alerts()

    @app.get("/api/v1/monitor/stream")
    async def stream() -> StreamingResponse:
        return StreamingResponse(get_service().event_stream(), media_type="text/event-stream")

    return app


app = create_app()
