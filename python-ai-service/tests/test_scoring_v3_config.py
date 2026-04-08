def test_scoring_v3_keeps_required_weights() -> None:
    from training.scoring.config import ScoringTrainingConfig

    config = ScoringTrainingConfig()

    assert config.total_weights["visual_fidelity"] == 0.21
    assert config.total_weights["text_consistency"] == 0.37
    assert config.total_weights["physical_plausibility"] == 0.24
    assert config.total_weights["composition_aesthetics"] == 0.18


def test_scoring_v3_pipeline_builds_hybrid_bundle(tmp_path) -> None:
    import json

    from app.core.settings import Settings
    from training.scoring.pipeline import run_scoring_training

    runtime_root = tmp_path
    source_bundle = runtime_root / "models" / "scoring" / "electric-score-v2"
    source_bundle.mkdir(parents=True)
    (source_bundle / "yolo_aux.pt").write_bytes(b"fake-yolo")

    settings = Settings(runtime_root=runtime_root)

    paths = run_scoring_training(settings=settings)

    target_bundle = runtime_root / "models" / "scoring" / "electric-score-v3"
    bundle_config = json.loads((target_bundle / "bundle_config.json").read_text(encoding="utf-8"))
    bundle_manifest = json.loads((target_bundle / "bundle_manifest.json").read_text(encoding="utf-8"))
    metrics = json.loads((target_bundle / "metrics.json").read_text(encoding="utf-8"))

    assert paths.scoring_training_root == runtime_root / "training" / "scoring" / "electric-score-v3"
    assert bundle_config["runtime_type"] == "hybrid"
    assert bundle_config["total_weights"]["text_consistency"] == 0.37
    assert (target_bundle / "yolo_aux.pt").read_bytes() == b"fake-yolo"
    assert bundle_manifest["export_root"] == str(target_bundle)
    assert metrics["bundle_dir"] == str(target_bundle)


def test_train_scoring_v3_script_runs_from_direct_path(tmp_path) -> None:
    import json
    import os
    import subprocess
    import sys
    from pathlib import Path

    project_root = Path(__file__).resolve().parents[1]
    source_bundle = tmp_path / "models" / "scoring" / "electric-score-v2"
    source_bundle.mkdir(parents=True)
    (source_bundle / "yolo_aux.pt").write_bytes(b"fake-yolo")

    env = os.environ.copy()
    env["ELECTRIC_AI_RUNTIME_ROOT"] = str(tmp_path)

    result = subprocess.run(
        [sys.executable, str(project_root / "scripts" / "train_scoring_v3.py")],
        cwd=str(project_root),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["scoring_model_root"] == str(tmp_path / "models" / "scoring" / "electric-score-v3")
