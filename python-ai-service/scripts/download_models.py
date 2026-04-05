from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

try:
    from scripts.bootstrap import ensure_project_root_on_path
except ImportError:  # pragma: no cover - direct script execution path
    from bootstrap import ensure_project_root_on_path

ensure_project_root_on_path()

from app.core.runtime_paths import RuntimePaths
from app.core.settings import Settings, get_settings
from app.schemas.runtime import RuntimeModelManifestEntry

OLD_AESTHETIC_WEIGHT = Path(r"E:\毕业设计\源代码\Project\sac+logos+ava1-l14-linearMSE.pth")


def get_model_manifest(settings: Settings | None = None) -> dict[str, dict[str, str | None]]:
    runtime_settings = settings or get_settings()
    paths = RuntimePaths(runtime_settings.runtime_root)

    manifest = {
        "sd15-electric": RuntimeModelManifestEntry(
            name="sd15-electric",
            target="generation",
            source="huggingface",
            repo_id="runwayml/stable-diffusion-v1-5",
            local_dir=str(paths.models_generation / "sd15-electric"),
            description="Stable Diffusion 1.5 baseline runtime",
        ),
        "unipic2-kontext": RuntimeModelManifestEntry(
            name="unipic2-kontext",
            target="generation",
            source="huggingface",
            repo_id="powerlmp/unipic2-kontext",
            local_dir=str(paths.models_generation / "unipic2-kontext"),
            description="UniPic2 electric scene runtime",
        ),
        "image-reward": RuntimeModelManifestEntry(
            name="image-reward",
            target="scoring",
            source="huggingface",
            repo_id="THUDM/ImageReward",
            local_dir=str(paths.models_scoring / "image-reward"),
            description="Text-image alignment scoring runtime",
        ),
        "aesthetic-predictor": RuntimeModelManifestEntry(
            name="aesthetic-predictor",
            target="scoring",
            source="local-copy",
            local_source=str(OLD_AESTHETIC_WEIGHT),
            local_dir=str(paths.models_scoring / "aesthetic-predictor"),
            description="LAION aesthetic linear head",
        ),
    }
    return {name: entry.model_dump() for name, entry in manifest.items()}


def _copy_local_weight(entry: dict[str, str | None]) -> dict[str, object]:
    source = Path(entry["local_source"] or "")
    destination_dir = Path(entry["local_dir"])
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination_path = destination_dir / source.name

    if not source.exists():
        return {
            "status": "missing-source",
            "source": str(source),
            "destination": str(destination_path),
        }

    shutil.copy2(source, destination_path)
    return {
        "status": "copied",
        "source": str(source),
        "destination": str(destination_path),
    }


def _download_huggingface(entry: dict[str, str | None]) -> dict[str, object]:
    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        return {
            "status": "dependency-missing",
            "repo_id": entry["repo_id"],
            "local_dir": entry["local_dir"],
        }

    local_dir = Path(entry["local_dir"] or "")
    local_dir.mkdir(parents=True, exist_ok=True)
    snapshot_download(repo_id=entry["repo_id"], local_dir=local_dir, local_dir_use_symlinks=False)
    return {
        "status": "downloaded",
        "repo_id": entry["repo_id"],
        "local_dir": str(local_dir),
    }


def execute_download_plan(selected_models: list[str], check_only: bool = False) -> dict[str, object]:
    settings = get_settings()
    paths = RuntimePaths(settings.runtime_root)
    paths.ensure_directories()
    manifest = get_model_manifest(settings)

    results: dict[str, object] = {}
    for model_name in selected_models:
        entry = manifest[model_name]
        local_dir = Path(entry["local_dir"] or "")

        if check_only:
            results[model_name] = {
                "status": "present" if local_dir.exists() and any(local_dir.iterdir()) else "missing",
                "target": entry["target"],
                "local_dir": str(local_dir),
            }
            continue

        if entry["source"] == "local-copy":
            results[model_name] = _copy_local_weight(entry)
            continue

        results[model_name] = _download_huggingface(entry)

    return {
        "runtime_root": str(settings.runtime_root),
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Download or check Electric AI runtime models.")
    parser.add_argument("--all", action="store_true", help="Operate on all manifest models.")
    parser.add_argument("--model", action="append", default=[], help="Model name from manifest.")
    parser.add_argument("--check", action="store_true", help="Only check whether files are present.")
    args = parser.parse_args()

    manifest = get_model_manifest()
    selected_models = list(manifest) if args.all or not args.model else args.model
    report = execute_download_plan(selected_models=selected_models, check_only=args.check)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
