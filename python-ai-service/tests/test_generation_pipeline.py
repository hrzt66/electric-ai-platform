import json
import os
import subprocess
import sys
from pathlib import Path

from app.core.settings import Settings


def test_prepare_generation_training_workspace_exports_curated_dataset_and_command(tmp_path: Path) -> None:
    from training.generation.config import GenerationTrainingConfig
    from training.generation.pipeline import prepare_generation_training_workspace
    from training.generation.prepare_dataset import prepare_generation_dataset

    runtime_root = tmp_path / "runtime"
    settings = Settings(runtime_root=runtime_root)

    public_root = tmp_path / "public" / "substation"
    public_root.mkdir(parents=True)
    (public_root / "yard.png").write_bytes(b"img-1")

    local_root = tmp_path / "local" / "transmission_line"
    local_root.mkdir(parents=True)
    (local_root / "tower.png").write_bytes(b"img-2")

    prepare_generation_dataset(
        settings=settings,
        public_roots=[tmp_path / "public"],
        local_roots=[tmp_path / "local"],
        external_roots=[],
    )

    script_path = tmp_path / "train_text_to_image_lora.py"
    script_path.write_text("# placeholder", encoding="utf-8")

    report = prepare_generation_training_workspace(
        settings=settings,
        config=GenerationTrainingConfig(max_train_steps=12),
        python_executable="python",
        download_script_fn=lambda _: script_path,
    )

    curated_root = runtime_root / "datasets" / "generation-v3" / "curated"
    metadata_path = curated_root / "metadata.jsonl"
    records = [json.loads(line) for line in metadata_path.read_text(encoding="utf-8").splitlines()]

    assert Path(report["train_script_path"]) == script_path
    assert Path(report["curated_dataset_dir"]) == curated_root
    assert len(records) == 2
    assert {record["text"] for record in records} == {
        "realistic utility inspection photography, electric power substation",
        "realistic utility inspection photography, electric power transmission line, transmission tower",
    }
    assert report["train_command"][:2] == ["python", str(script_path)]
    assert "--train_data_dir" in report["train_command"]
    assert str(curated_root) in report["train_command"]


def test_prepare_generation_training_workspace_builds_epoch_based_command(tmp_path: Path) -> None:
    from training.generation.config import GenerationTrainingConfig
    from training.generation.pipeline import prepare_generation_training_workspace
    from training.generation.prepare_dataset import prepare_generation_dataset

    runtime_root = tmp_path / "runtime"
    settings = Settings(runtime_root=runtime_root)

    public_root = tmp_path / "public" / "wind_turbine"
    public_root.mkdir(parents=True)
    (public_root / "farm.png").write_bytes(b"img-epoch")

    prepare_generation_dataset(
        settings=settings,
        public_roots=[tmp_path / "public"],
        local_roots=[],
        external_roots=[],
    )

    script_path = tmp_path / "train_text_to_image_lora.py"
    script_path.write_text("# placeholder", encoding="utf-8")

    report = prepare_generation_training_workspace(
        settings=settings,
        config=GenerationTrainingConfig(num_train_epochs=100),
        python_executable="python",
        download_script_fn=lambda _: script_path,
    )

    assert "--num_train_epochs" in report["train_command"]
    assert "100" in report["train_command"]
    assert "--max_train_steps" not in report["train_command"]
    assert "--report_to" in report["train_command"]
    report_to_index = report["train_command"].index("--report_to")
    assert report["train_command"][report_to_index + 1] == "all"
    assert "--validation_prompt" not in report["train_command"]
    assert "--validation_epochs" not in report["train_command"]
    assert "--num_validation_images" not in report["train_command"]


def test_train_generation_v3_script_prepare_only_bootstraps_project_root(tmp_path: Path) -> None:
    from training.generation.prepare_dataset import prepare_generation_dataset

    runtime_root = tmp_path / "runtime"
    settings = Settings(runtime_root=runtime_root)

    public_root = tmp_path / "public" / "substation"
    public_root.mkdir(parents=True)
    (public_root / "yard.png").write_bytes(b"img-1")

    prepare_generation_dataset(
        settings=settings,
        public_roots=[tmp_path / "public"],
        local_roots=[],
        external_roots=[],
    )

    placeholder_script = tmp_path / "train_text_to_image_lora.py"
    placeholder_script.write_text("# placeholder", encoding="utf-8")
    cli_script = Path(__file__).resolve().parents[1] / "scripts" / "train_generation_v3.py"

    env = os.environ.copy()
    env["ELECTRIC_AI_RUNTIME_ROOT"] = str(runtime_root)
    env.pop("PYTHONPATH", None)

    result = subprocess.run(
        [
            sys.executable,
            str(cli_script),
            "--prepare-only",
            "--train-script-path",
            str(placeholder_script),
            "--python-executable",
            "python",
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr or result.stdout
    report = json.loads(result.stdout)
    assert report["status"] == "prepared"
    assert Path(report["train_script_path"]) == placeholder_script


def test_run_generation_training_prepare_only_skip_eval_omits_diffusers_validation_flags(
    tmp_path: Path,
) -> None:
    from training.generation.config import GenerationTrainingConfig
    from training.generation.pipeline import run_generation_training
    from training.generation.prepare_dataset import prepare_generation_dataset

    runtime_root = tmp_path / "runtime"
    settings = Settings(runtime_root=runtime_root)

    public_root = tmp_path / "public" / "substation"
    public_root.mkdir(parents=True)
    (public_root / "yard.png").write_bytes(b"img-1")

    prepare_generation_dataset(
        settings=settings,
        public_roots=[tmp_path / "public"],
        local_roots=[],
        external_roots=[],
    )

    placeholder_script = tmp_path / "train_text_to_image_lora.py"
    placeholder_script.write_text("# placeholder", encoding="utf-8")

    report = run_generation_training(
        settings=settings,
        config=GenerationTrainingConfig(max_train_steps=12),
        python_executable="python",
        download_script_fn=lambda _: placeholder_script,
        prepare_only=True,
        skip_eval=True,
    )

    command = report["train_command"]
    assert "--validation_prompt" not in command
    assert "--validation_epochs" not in command
    assert "--num_validation_images" not in command


def test_remove_obsolete_specialized_artifacts_removes_old_training_and_model_dirs(tmp_path: Path) -> None:
    from training.generation.pipeline import remove_obsolete_specialized_artifacts

    settings = Settings(runtime_root=tmp_path / "runtime")
    targets = [
        settings.runtime_root / "training" / "generation" / "sd15-electric-specialized",
        settings.generation_model_dir / "sd15-electric-specialized",
        settings.runtime_root / "generation" / "sd15-electric-specialized",
    ]
    unique_targets = list(dict.fromkeys(targets))
    for target in unique_targets:
        target.mkdir(parents=True)

    report = remove_obsolete_specialized_artifacts(settings)

    assert report["removed_paths"] == [str(target) for target in unique_targets]
    assert all(not target.exists() for target in unique_targets)


def test_select_best_generation_checkpoint_prefers_highest_checkpoint_number(tmp_path: Path) -> None:
    from training.generation.pipeline import select_best_generation_checkpoint

    output_dir = tmp_path / "lora-output"
    (output_dir / "checkpoint-500").mkdir(parents=True)
    (output_dir / "checkpoint-1500").mkdir(parents=True)
    (output_dir / "checkpoint-1000").mkdir(parents=True)

    best = select_best_generation_checkpoint(lora_output_dir=output_dir)

    assert best == output_dir / "checkpoint-1500"
