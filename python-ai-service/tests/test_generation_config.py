def test_generation_training_config_defaults_fit_6gb_gpu() -> None:
    from training.generation.config import GenerationTrainingConfig

    config = GenerationTrainingConfig()

    assert config.resolution == 512
    assert config.train_batch_size == 1
    assert config.gradient_accumulation_steps >= 4
    assert config.rank in {16, 32}
