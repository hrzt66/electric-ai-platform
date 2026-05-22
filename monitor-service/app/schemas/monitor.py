from __future__ import annotations

from pydantic import BaseModel


class AlertsResponse(BaseModel):
    active_alerts: list[dict] = []
    recent_alerts: list[dict] = []
