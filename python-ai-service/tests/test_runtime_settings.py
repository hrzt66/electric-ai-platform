from pathlib import Path
import subprocess
import sys

from requests.exceptions import ChunkedEncodingError


def test_settings_default_to_g_drive_runtime(monkeypatch):
    monkeypatch.delenv("ELECTRIC_AI_RUNTIME_ROOT", raising=False)

    from app.core.settings import DEFAULT_RUNTIME_ROOT, Settings

    settings = Settings()

    assert settings.runtime_root == DEFAULT_RUNTIME_ROOT
    assert settings.output_image_dir == DEFAULT_RUNTIME_ROOT / "image"
    assert settings.output_image_check_dir == DEFAULT_RUNTIME_ROOT / "image_check"
    assert settings.hf_home == DEFAULT_RUNTIME_ROOT / "hf-home"


def test_runtime_paths_probe_report_marks_missing_directories(tmp_path):
    from app.core.runtime_paths import RuntimePaths

    paths = RuntimePaths(tmp_path)
    report = paths.build_probe_report()

    assert report["runtime_root"] == str(tmp_path)
    assert report["directories"]["models_generation"]["exists"] is False
    assert report["directories"]["outputs_images"]["exists"] is False
    assert report["directories"]["outputs_image_checks"]["exists"] is False


def test_download_manifest_contains_generation_and_scoring_entries():
    from scripts.download_models import get_model_manifest

    manifest = get_model_manifest()

    assert manifest["sd15-electric"]["target"] == "generation"
    assert manifest["ssd1b-electric"]["target"] == "generation"
    assert manifest["ssd1b-electric"]["repo_id"] == "segmind/SSD-1B"
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


def test_download_manifest_uses_public_aesthetic_source_when_local_weight_missing(monkeypatch, tmp_path):
    from app.core.settings import Settings
    from scripts.download_models import DEFAULT_AESTHETIC_WEIGHT_URL, get_model_manifest

    legacy_root = tmp_path / "missing-legacy"
    monkeypatch.setenv("ELECTRIC_AI_LEGACY_ROOT", str(legacy_root))

    manifest = get_model_manifest(Settings(runtime_root=tmp_path / "runtime"))

    assert manifest["aesthetic-predictor"]["local_source"] == DEFAULT_AESTHETIC_WEIGHT_URL


def test_runtime_probe_script_runs_from_cli():
    from app.core.settings import DEFAULT_RUNTIME_ROOT

    result = subprocess.run(
        [sys.executable, "scripts/runtime_probe.py"],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert f'"runtime_root": "{str(DEFAULT_RUNTIME_ROOT)}"' in result.stdout


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


def test_copy_local_weight_downloads_remote_source(monkeypatch, tmp_path):
    from scripts.download_models import _copy_local_weight

    calls: list[tuple[str, str]] = []

    def fake_urlretrieve(source: str, destination: str):
        calls.append((source, destination))
        Path(destination).write_text("stub-weight", encoding="utf-8")
        return destination, None

    monkeypatch.setattr("scripts.download_models.urlretrieve", fake_urlretrieve)

    destination_dir = tmp_path / "aesthetic-predictor"
    result = _copy_local_weight(
        {
            "local_source": "https://example.com/sac+logos+ava1-l14-linearMSE.pth",
            "local_dir": str(destination_dir),
        }
    )

    assert result["status"] == "downloaded"
    assert calls == [
        (
            "https://example.com/sac+logos+ava1-l14-linearMSE.pth",
            str(destination_dir / "sac+logos+ava1-l14-linearMSE.pth"),
        )
    ]


def test_copy_local_weight_decodes_remote_filename(monkeypatch, tmp_path):
    from scripts.download_models import _copy_local_weight

    calls: list[tuple[str, str]] = []

    def fake_urlretrieve(source: str, destination: str):
        calls.append((source, destination))
        Path(destination).write_text("stub-weight", encoding="utf-8")
        return destination, None

    monkeypatch.setattr("scripts.download_models.urlretrieve", fake_urlretrieve)

    destination_dir = tmp_path / "aesthetic-predictor"
    result = _copy_local_weight(
        {
            "local_source": "https://example.com/sac%2Blogos%2Bava1-l14-linearMSE.pth",
            "local_dir": str(destination_dir),
        }
    )

    assert result["destination"] == str(destination_dir / "sac+logos+ava1-l14-linearMSE.pth")


def test_settings_read_runtime_tuning_flags_from_env(monkeypatch, tmp_path):
    from app.core.settings import Settings

    monkeypatch.setenv("ELECTRIC_AI_RUNTIME_ROOT", str(tmp_path / "runtime"))
    monkeypatch.setenv("ELECTRIC_AI_UNIPIC2_OFFLOAD_MODE", "none")
    monkeypatch.setenv("ELECTRIC_AI_SCORING_RELEASE_AFTER_BATCH", "false")

    settings = Settings.from_env()

    assert settings.runtime_root == tmp_path / "runtime"
    assert settings.unipic2_offload_mode == "none"
    assert settings.scoring_release_after_batch is False


def test_settings_reads_dotenv_local_from_working_directory(monkeypatch, tmp_path):
    from app.core.settings import Settings

    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.delenv("TASK_SERVICE_BASE_URL", raising=False)

    env_file = tmp_path / ".env.local"
    env_file.write_text(
        "\n".join(
            [
                "REDIS_URL=redis://127.0.0.1:6380/0",
                "TASK_SERVICE_BASE_URL=http://127.0.0.1:8083",
            ]
        ),
        encoding="utf-8",
    )

    settings = Settings.from_env()

    assert settings.redis_url == "redis://127.0.0.1:6380/0"
    assert settings.task_service_base_url == "http://127.0.0.1:8083"
