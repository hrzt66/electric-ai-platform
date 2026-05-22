from __future__ import annotations

from app.services.collector_service import CollectorService


def build_collector_service() -> CollectorService:
    return CollectorService()
