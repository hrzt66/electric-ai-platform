import json
import os
import subprocess
import sys
from pathlib import Path

from app.core.settings import Settings


def test_prepare_generation_dataset_writes_manifest(tmp_path: Path) -> None:
    from training.generation.prepare_dataset import prepare_generation_dataset

    public_root = tmp_path / "public"
    public_root.mkdir(parents=True)
    (public_root / "substation.png").write_bytes(b"img-public")

    local_root = tmp_path / "local"
    local_root.mkdir(parents=True)
    (local_root / "tower.jpg").write_bytes(b"img-local")

    settings = Settings(runtime_root=tmp_path)

    report = prepare_generation_dataset(
        settings=settings,
        public_roots=[public_root],
        local_roots=[local_root],
        external_roots=[],
    )

    manifest_path = tmp_path / "datasets" / "generation-v3" / "manifests" / "raw_manifest.jsonl"
    attribution_manifest_path = tmp_path / "datasets" / "generation-v3" / "manifests" / "attribution_manifest.jsonl"
    assert Path(report["manifest_path"]) == manifest_path
    assert Path(report["attribution_manifest_path"]) == attribution_manifest_path
    assert manifest_path.exists()
    assert attribution_manifest_path.exists()
    assert report["count"] == 2


def test_prepare_generation_dataset_can_download_public_provider_rows(tmp_path: Path, monkeypatch) -> None:
    from training.generation.prepare_dataset import prepare_generation_dataset

    downloaded = tmp_path / "downloads"
    downloaded.mkdir(parents=True)
    image_path = downloaded / "substation.png"
    image_path.write_bytes(b"img-public-electric")

    def fake_collect_public_generation_dataset(**kwargs):
        return {
            "downloaded_rows": [
                {
                    "source_group": "public",
                    "provider": "openverse",
                    "path": str(image_path),
                    "filename": "substation.png",
                    "suffix": ".png",
                    "size_bytes": image_path.stat().st_size,
                    "caption": "electric power substation",
                    "license": "cc-by",
                    "source_url": "https://example.com/substation",
                    "author": "example-author",
                }
            ],
            "attribution_rows": [
                {
                    "provider": "openverse",
                    "license": "cc-by",
                    "source_url": "https://example.com/substation",
                }
            ],
            "provider_counts": {"openverse": 1, "wikimedia": 0},
        }

    monkeypatch.setattr(
        "training.generation.prepare_dataset.collect_public_generation_dataset",
        fake_collect_public_generation_dataset,
    )

    settings = Settings(runtime_root=tmp_path / "runtime")
    report = prepare_generation_dataset(
        settings=settings,
        public_roots=[],
        local_roots=[],
        external_roots=[],
        include_public_downloads=True,
    )

    assert report["count"] == 1
    assert report["public_download_count"] == 1
    assert report["attribution_count"] == 1
    assert Path(report["attribution_manifest_path"]).exists()


def test_prepare_generation_v3_dataset_script_bootstraps_project_root(tmp_path: Path) -> None:
    runtime_root = tmp_path / "runtime"
    legacy_root = tmp_path / "legacy"
    static_root = legacy_root / "static"
    static_root.mkdir(parents=True)
    (static_root / "tower.png").write_bytes(b"img")

    script_path = Path(__file__).resolve().parents[1] / "scripts" / "prepare_generation_v3_dataset.py"
    env = os.environ.copy()
    env["ELECTRIC_AI_RUNTIME_ROOT"] = str(runtime_root)
    env["ELECTRIC_AI_LEGACY_ROOT"] = str(legacy_root)
    env.pop("PYTHONPATH", None)

    result = subprocess.run(
        [sys.executable, str(script_path), "--skip-public-downloads"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr or result.stdout

    report = json.loads(result.stdout)
    manifest_path = runtime_root / "datasets" / "generation-v3" / "manifests" / "raw_manifest.jsonl"
    attribution_manifest_path = runtime_root / "datasets" / "generation-v3" / "manifests" / "attribution_manifest.jsonl"
    assert Path(report["manifest_path"]) == manifest_path
    assert Path(report["attribution_manifest_path"]) == attribution_manifest_path
    assert report["count"] == 1
    assert manifest_path.exists()
