from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class RuntimeDirectoryState(BaseModel):
    path: str
    exists: bool


class RuntimeModelManifestEntry(BaseModel):
    name: str
    target: Literal["generation", "scoring"]
    source: Literal["huggingface", "local-copy"]
    repo_id: str | None = None
    local_source: str | None = None
    local_dir: str
    description: str = ""


class RuntimeProbeReport(BaseModel):
    runtime_root: str
    directories: dict[str, RuntimeDirectoryState]
    packages: dict[str, bool] = Field(default_factory=dict)
    python_version: str
    cuda_available: bool | None = None
