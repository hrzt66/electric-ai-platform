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
    assert Path(report["manifest_path"]) == manifest_path
    assert manifest_path.exists()
    assert report["count"] == 2


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
        [sys.executable, str(script_path)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr or result.stdout

    report = json.loads(result.stdout)
    manifest_path = runtime_root / "datasets" / "generation-v3" / "manifests" / "raw_manifest.jsonl"
    assert Path(report["manifest_path"]) == manifest_path
    assert report["count"] == 1
    assert manifest_path.exists()
