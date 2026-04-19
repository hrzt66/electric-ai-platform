from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class RuntimePaths:
    runtime_root: Path

    def __post_init__(self) -> None:
        self.runtime_root = Path(self.runtime_root)

    @property
    def hf_home(self) -> Path:
        return self.runtime_root / "hf-home"

    @property
    def models_generation(self) -> Path:
        return self.runtime_root / "generation"

    @property
    def models_scoring(self) -> Path:
        return self.runtime_root / "scoring"

    @property
    def outputs_images(self) -> Path:
        return self.runtime_root / "image"

    @property
    def outputs_image_checks(self) -> Path:
        return self.runtime_root / "image_check"

    @property
    def logs(self) -> Path:
        return self.runtime_root / "logs"

    @property
    def tmp(self) -> Path:
        return self.runtime_root / "tmp"

    def directory_map(self) -> dict[str, Path]:
        return {
            "hf_home": self.hf_home,
            "models_generation": self.models_generation,
            "models_scoring": self.models_scoring,
            "outputs_images": self.outputs_images,
            "outputs_image_checks": self.outputs_image_checks,
            "logs": self.logs,
            "tmp": self.tmp,
        }

    def ensure_directories(self) -> None:
        for directory in self.directory_map().values():
            directory.mkdir(parents=True, exist_ok=True)

    def build_probe_report(self) -> dict[str, object]:
        directories = {
            name: {
                "path": str(path),
                "exists": path.exists(),
            }
            for name, path in self.directory_map().items()
        }
        return {
            "runtime_root": str(self.runtime_root),
            "directories": directories,
        }
