from __future__ import annotations

import json
from pathlib import Path

try:
    from scripts.bootstrap import ensure_project_root_on_path
except ImportError:  # pragma: no cover - direct script execution path
    from bootstrap import ensure_project_root_on_path

ensure_project_root_on_path()

from app.core.settings import get_settings
from scripts.download_models import get_legacy_project_root
from training.generation.prepare_dataset import prepare_generation_dataset


def _existing(paths: list[Path]) -> list[Path]:
    return [path for path in paths if path.exists()]


def main() -> int:
    settings = get_settings()
    runtime_root = Path(settings.runtime_root)
    legacy_static = get_legacy_project_root() / "static"

    report = prepare_generation_dataset(
        settings=settings,
        public_roots=_existing([runtime_root / "datasets" / "external"]),
        local_roots=_existing([legacy_static]),
        external_roots=[],
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
