from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

DEFAULT_RUNTIME_ROOT = Path(r"G:\electric-ai-runtime")


def _read_path_env(name: str, fallback: Path) -> Path:
    value = os.getenv(name)
    return Path(value) if value else fallback


@dataclass(slots=True)
class Settings:
    runtime_root: Path = DEFAULT_RUNTIME_ROOT
    task_service_base_url: str = "http://localhost:8083"
    asset_service_base_url: str = "http://localhost:8084"
    audit_service_base_url: str = "http://localhost:8085"
    model_service_base_url: str = "http://localhost:8082"
    redis_url: str = "redis://localhost:6379/0"

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            runtime_root=_read_path_env("ELECTRIC_AI_RUNTIME_ROOT", DEFAULT_RUNTIME_ROOT),
            task_service_base_url=os.getenv("TASK_SERVICE_BASE_URL", "http://localhost:8083"),
            asset_service_base_url=os.getenv("ASSET_SERVICE_BASE_URL", "http://localhost:8084"),
            audit_service_base_url=os.getenv("AUDIT_SERVICE_BASE_URL", "http://localhost:8085"),
            model_service_base_url=os.getenv("MODEL_SERVICE_BASE_URL", "http://localhost:8082"),
            redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        )

    @property
    def hf_home(self) -> Path:
        return self.runtime_root / "hf-home"

    @property
    def generation_model_dir(self) -> Path:
        return self.runtime_root / "models" / "generation"

    @property
    def scoring_model_dir(self) -> Path:
        return self.runtime_root / "models" / "scoring"

    @property
    def output_image_dir(self) -> Path:
        return self.runtime_root / "outputs" / "images"

    @property
    def logs_dir(self) -> Path:
        return self.runtime_root / "logs"

    @property
    def tmp_dir(self) -> Path:
        return self.runtime_root / "tmp"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings.from_env()
