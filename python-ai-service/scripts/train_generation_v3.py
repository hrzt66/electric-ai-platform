from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path

try:
    from scripts.bootstrap import ensure_project_root_on_path
except ImportError:  # pragma: no cover - direct script execution path
    from bootstrap import ensure_project_root_on_path

ensure_project_root_on_path()

from training.generation.config import GenerationTrainingConfig
from training.generation.pipeline import run_generation_training


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare or train the electric specialized SD1.5 LoRA pipeline.")
    parser.add_argument("--prepare-only", action="store_true", help="Only prepare the curated dataset and training plan.")
    parser.add_argument("--skip-merge", action="store_true", help="Skip merging LoRA weights into a standalone model.")
    parser.add_argument("--skip-eval", action="store_true", help="Skip validation image generation after merge.")
    parser.add_argument("--num-train-epochs", type=int, default=None, help="Override the configured training epochs.")
    parser.add_argument("--max-train-steps", type=int, default=None, help="Override the configured training steps.")
    parser.add_argument("--max-train-samples", type=int, default=None, help="Limit the curated dataset size.")
    parser.add_argument("--python-executable", default=None, help="Python executable used to launch the LoRA trainer.")
    parser.add_argument("--train-script-path", default=None, help="Optional existing LoRA training script path.")
    args = parser.parse_args()

    config = GenerationTrainingConfig()
    if args.num_train_epochs is not None:
        config = replace(config, num_train_epochs=args.num_train_epochs)
    if args.max_train_steps is not None:
        config = replace(config, max_train_steps=args.max_train_steps)
    if args.max_train_samples is not None:
        config = replace(config, max_train_samples=args.max_train_samples)

    download_script_fn = None
    if args.train_script_path:
        train_script_path = Path(args.train_script_path)
        download_script_fn = lambda _: train_script_path

    report = run_generation_training(
        config=config,
        python_executable=args.python_executable,
        download_script_fn=download_script_fn,
        prepare_only=args.prepare_only,
        skip_merge=args.skip_merge,
        skip_eval=args.skip_eval,
    )

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
