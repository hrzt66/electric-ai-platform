from __future__ import annotations

import importlib.util
import json
import sys

try:
    from scripts.bootstrap import ensure_project_root_on_path
except ImportError:  # pragma: no cover - direct script execution path
    from bootstrap import ensure_project_root_on_path

ensure_project_root_on_path()

from app.core.runtime_paths import RuntimePaths
from app.core.settings import get_settings
from app.schemas.runtime import RuntimeProbeReport


def _package_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def _detect_cuda() -> bool | None:
    if not _package_available("torch"):
        return None

    import torch

    return bool(torch.cuda.is_available())


def build_runtime_probe() -> dict[str, object]:
    settings = get_settings()
    paths = RuntimePaths(settings.runtime_root)
    base_report = paths.build_probe_report()

    report = RuntimeProbeReport(
        runtime_root=base_report["runtime_root"],
        directories=base_report["directories"],
        packages={
            "torch": _package_available("torch"),
            "diffusers": _package_available("diffusers"),
            "transformers": _package_available("transformers"),
            "huggingface_hub": _package_available("huggingface_hub"),
        },
        python_version=sys.version.split()[0],
        cuda_available=_detect_cuda(),
    )
    return report.model_dump()


def main() -> int:
    print(json.dumps(build_runtime_probe(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
