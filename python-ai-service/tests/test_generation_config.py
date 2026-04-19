from pathlib import Path


def test_generation_training_config_defaults_fit_6gb_gpu() -> None:
    from training.generation.config import GenerationTrainingConfig

    config = GenerationTrainingConfig()

    assert config.resolution == 512
    assert config.train_batch_size == 1
    assert config.gradient_accumulation_steps >= 4
    assert config.rank in {16, 32}
    assert config.output_model_name == "sd15-electric-specialized"
    assert config.num_train_epochs == 100
    assert config.max_train_steps is None
    assert config.mixed_precision == "no"
    assert config.report_to == "all"
    assert config.enable_training_validation is False


def test_generation_training_config_prefers_legacy_generation_model_root_when_present(tmp_path: Path) -> None:
    from app.core.settings import Settings
    from training.generation.config import GenerationTrainingConfig

    settings = Settings(runtime_root=tmp_path)
    legacy_base_model_dir = tmp_path / "generation" / "sd15-electric"
    legacy_base_model_dir.mkdir(parents=True)
    (legacy_base_model_dir / "model_index.json").write_text("{}", encoding="utf-8")

    config = GenerationTrainingConfig()

    assert config.resolve_base_model_source(settings) == str(legacy_base_model_dir)
    assert config.resolve_output_model_dir(settings) == tmp_path / "generation" / "sd15-electric-specialized"
