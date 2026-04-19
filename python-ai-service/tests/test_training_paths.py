from pathlib import Path

from app.core.settings import Settings


def test_training_paths_build_expected_runtime_directories(tmp_path: Path) -> None:
    from training.common.paths import TrainingPaths

    settings = Settings(runtime_root=tmp_path)

    paths = TrainingPaths.from_settings(settings)

    assert paths.generation_dataset_root == tmp_path / "datasets" / "generation-v3"
    assert paths.scoring_dataset_root == tmp_path / "datasets" / "scoring-v2"
    assert paths.generation_training_root == tmp_path / "training" / "generation" / "sd15-electric-specialized-v2"
    assert paths.scoring_training_root == tmp_path / "training" / "scoring" / "electric-score-v2"
