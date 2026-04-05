from pathlib import Path
import subprocess
import sys

from requests.exceptions import ChunkedEncodingError


def test_settings_default_to_g_drive_runtime(monkeypatch):
    monkeypatch.delenv("ELECTRIC_AI_RUNTIME_ROOT", raising=False)

    from app.core.settings import Settings

    settings = Settings()

    assert settings.runtime_root == Path(r"G:\electric-ai-runtime")
    assert settings.output_image_dir == Path(r"G:\electric-ai-runtime\outputs\images")
    assert settings.hf_home == Path(r"G:\electric-ai-runtime\hf-home")


def test_runtime_paths_probe_report_marks_missing_directories(tmp_path):
    from app.core.runtime_paths import RuntimePaths

    paths = RuntimePaths(tmp_path)
    report = paths.build_probe_report()

    assert report["runtime_root"] == str(tmp_path)
    assert report["directories"]["models_generation"]["exists"] is False
    assert report["directories"]["outputs_images"]["exists"] is False


def test_download_manifest_contains_generation_and_scoring_entries():
    from scripts.download_models import get_model_manifest

    manifest = get_model_manifest()

    assert manifest["sd15-electric"]["target"] == "generation"
    assert manifest["unipic2-kontext"]["target"] == "generation"
    assert manifest["unipic2-kontext"]["repo_id"] == "Skywork/UniPic2-SD3.5M-Kontext-2B"
    assert manifest["image-reward"]["target"] == "scoring"


def test_download_manifest_prefers_configured_legacy_root(monkeypatch, tmp_path):
    from app.core.settings import Settings
    from scripts.download_models import get_model_manifest

    legacy_root = tmp_path / "legacy"
    legacy_root.mkdir()
    weight_file = legacy_root / "sac+logos+ava1-l14-linearMSE.pth"
    weight_file.write_text("stub", encoding="utf-8")
    monkeypatch.setenv("ELECTRIC_AI_LEGACY_ROOT", str(legacy_root))

    manifest = get_model_manifest(Settings(runtime_root=tmp_path / "runtime"))

    assert manifest["aesthetic-predictor"]["local_source"] == str(weight_file)


def test_runtime_probe_script_runs_from_cli():
    result = subprocess.run(
        [sys.executable, "scripts/runtime_probe.py"],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert '"runtime_root": "G:\\\\electric-ai-runtime"' in result.stdout


def test_download_models_script_check_runs_from_cli():
    result = subprocess.run(
        [sys.executable, "scripts/download_models.py", "--all", "--check"],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert '"sd15-electric"' in result.stdout


def test_download_huggingface_retries_after_chunk_error(tmp_path):
    from scripts.download_models import _download_huggingface

    attempts = {"count": 0}

    def fake_snapshot_download(**kwargs):
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise ChunkedEncodingError("broken stream")

    result = _download_huggingface(
        {
            "repo_id": "example/model",
            "local_dir": str(tmp_path / "model"),
        },
        snapshot_download_fn=fake_snapshot_download,
        max_workers=1,
        retry_attempts=2,
    )

    assert result["status"] == "downloaded"
    assert attempts["count"] == 2


def test_settings_read_runtime_tuning_flags_from_env(monkeypatch, tmp_path):
    from app.core.settings import Settings

    monkeypatch.setenv("ELECTRIC_AI_RUNTIME_ROOT", str(tmp_path / "runtime"))
    monkeypatch.setenv("ELECTRIC_AI_UNIPIC2_OFFLOAD_MODE", "none")
    monkeypatch.setenv("ELECTRIC_AI_SCORING_RELEASE_AFTER_BATCH", "false")

    settings = Settings.from_env()

    assert settings.runtime_root == tmp_path / "runtime"
    assert settings.unipic2_offload_mode == "none"
    assert settings.scoring_release_after_batch is False
