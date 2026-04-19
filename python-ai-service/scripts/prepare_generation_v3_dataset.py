from __future__ import annotations

import argparse
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
    parser = argparse.ArgumentParser(description="Prepare the generation-v3 dataset, optionally downloading public electric images.")
    parser.add_argument("--skip-public-downloads", action="store_true", help="Skip downloading public images from official providers.")
    parser.add_argument("--openverse-limit", type=int, default=None, help="Override the default Openverse download limit.")
    parser.add_argument("--wikimedia-limit", type=int, default=None, help="Override the default Wikimedia download limit.")
    args = parser.parse_args()

    settings = get_settings()
    runtime_root = Path(settings.runtime_root)
    legacy_static = get_legacy_project_root() / "static"

    report = prepare_generation_dataset(
        settings=settings,
        public_roots=_existing([runtime_root / "datasets" / "external"]),
        local_roots=_existing([legacy_static]),
        external_roots=[],
        include_public_downloads=not args.skip_public_downloads,
        provider_limits={
            key: value
            for key, value in {
                "openverse": args.openverse_limit,
                "wikimedia": args.wikimedia_limit,
            }.items()
            if value is not None
        }
        or None,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
