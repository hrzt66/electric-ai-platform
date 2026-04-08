from __future__ import annotations

import json

try:
    from scripts.bootstrap import ensure_project_root_on_path
except ImportError:  # pragma: no cover - direct script execution path
    from bootstrap import ensure_project_root_on_path

ensure_project_root_on_path()

from training.scoring.pipeline import run_scoring_training


def main() -> int:
    paths = run_scoring_training()
    print(
        json.dumps(
            {
                "scoring_training_root": str(paths.scoring_training_root),
                "scoring_model_root": str(paths.runtime_root / "models" / "scoring" / "electric-score-v3"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
