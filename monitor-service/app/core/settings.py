from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache


@dataclass(slots=True)
class Settings:
    monitor_stream_interval_seconds: float = 1.0


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
