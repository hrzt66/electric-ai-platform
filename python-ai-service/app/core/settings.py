from __future__ import annotations

"""Python AI 运行时配置入口，集中管理本机目录、微服务地址与资源释放策略。"""

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

DEFAULT_RUNTIME_ROOT = Path(r"G:\electric-ai-runtime")
DEFAULT_UNIPIC2_OFFLOAD_MODE = "model"


def _read_path_env(name: str, fallback: Path) -> Path:
    value = os.getenv(name)
    return Path(value) if value else fallback


def _read_bool_env(name: str, fallback: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return fallback
    return value.strip().lower() not in {"0", "false", "no", "off"}


def _read_choice_env(name: str, fallback: str, *, allowed: set[str]) -> str:
    value = os.getenv(name)
    if value is None:
        return fallback
    normalized = value.strip().lower()
    return normalized if normalized in allowed else fallback


@dataclass(slots=True)
class Settings:
    """运行时进程级配置对象，优先从环境变量读取。"""
    runtime_root: Path = DEFAULT_RUNTIME_ROOT
    task_service_base_url: str = "http://localhost:8083"
    asset_service_base_url: str = "http://localhost:8084"
    audit_service_base_url: str = "http://localhost:8085"
    model_service_base_url: str = "http://localhost:8082"
    redis_url: str = "redis://localhost:6379/0"
    unipic2_offload_mode: str = DEFAULT_UNIPIC2_OFFLOAD_MODE
    scoring_release_after_batch: bool = True

    @classmethod
    def from_env(cls) -> "Settings":
        # 保持所有入口共享同一套变量命名，便于本机、Docker 和测试环境之间切换。
        return cls(
            runtime_root=_read_path_env("ELECTRIC_AI_RUNTIME_ROOT", DEFAULT_RUNTIME_ROOT),
            task_service_base_url=os.getenv("TASK_SERVICE_BASE_URL", "http://localhost:8083"),
            asset_service_base_url=os.getenv("ASSET_SERVICE_BASE_URL", "http://localhost:8084"),
            audit_service_base_url=os.getenv("AUDIT_SERVICE_BASE_URL", "http://localhost:8085"),
            model_service_base_url=os.getenv("MODEL_SERVICE_BASE_URL", "http://localhost:8082"),
            redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            unipic2_offload_mode=_read_choice_env(
                "ELECTRIC_AI_UNIPIC2_OFFLOAD_MODE",
                DEFAULT_UNIPIC2_OFFLOAD_MODE,
                allowed={"model", "sequential", "none"},
            ),
            scoring_release_after_batch=_read_bool_env("ELECTRIC_AI_SCORING_RELEASE_AFTER_BATCH", True),
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
    """缓存 settings，避免一次任务内反复解析环境变量。"""
    return Settings.from_env()


# TODO: 后续可补充生产环境专用配置分层，例如对象存储、外部日志与远程模型仓库地址。
