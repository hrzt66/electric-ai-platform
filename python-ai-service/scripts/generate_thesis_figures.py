from __future__ import annotations

import argparse
import json

try:
    from scripts.bootstrap import ensure_project_root_on_path
except ImportError:  # pragma: no cover - direct script execution path
    from bootstrap import ensure_project_root_on_path

ensure_project_root_on_path()

from training.reporting.thesis_figure_rendering import generate_thesis_figure_package


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render thesis-ready generation and scoring figure package.")
    parser.add_argument("--runtime-root", default="model", help="Runtime root that contains generation, scoring, training, and image artifacts.")
    parser.add_argument("--output-dir", default="docs/image", help="Output directory for rendered thesis figures.")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    report = generate_thesis_figure_package(runtime_root=args.runtime_root, output_dir=args.output_dir)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
