from pathlib import Path
import subprocess
import sys


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
    assert manifest["image-reward"]["target"] == "scoring"


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
