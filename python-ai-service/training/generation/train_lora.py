from __future__ import annotations

import os
import subprocess
import urllib.request
from pathlib import Path

from app.core.settings import Settings
from training.generation.config import GenerationTrainingConfig


def download_diffusers_lora_script(destination_dir: Path, ref: str) -> Path:
    destination_dir.mkdir(parents=True, exist_ok=True)
    target_path = destination_dir / "train_text_to_image_lora.py"
    url = (
        "https://raw.githubusercontent.com/huggingface/diffusers/"
        f"{ref}/examples/text_to_image/train_text_to_image_lora.py"
    )
    urllib.request.urlretrieve(url, target_path)
    return target_path


def build_lora_train_command(
    *,
    config: GenerationTrainingConfig,
    train_script_path: Path,
    curated_dataset_dir: Path,
    lora_output_dir: Path,
    settings: Settings,
    python_executable: str,
    enable_validation: bool = True,
) -> list[str]:
    command = [
        python_executable,
        str(train_script_path),
        "--pretrained_model_name_or_path",
        config.resolve_base_model_source(settings),
        "--train_data_dir",
        str(curated_dataset_dir),
        "--caption_column",
        "text",
        "--resolution",
        str(config.resolution),
        "--train_batch_size",
        str(config.train_batch_size),
        "--gradient_accumulation_steps",
        str(config.gradient_accumulation_steps),
        "--learning_rate",
        str(config.learning_rate),
        "--lr_scheduler",
        config.lr_scheduler,
        "--lr_warmup_steps",
        str(config.lr_warmup_steps),
        "--checkpointing_steps",
        str(config.checkpointing_steps),
        "--rank",
        str(config.rank),
        "--dataloader_num_workers",
        str(config.dataloader_num_workers),
        "--seed",
        str(config.seed),
        "--report_to",
        config.report_to,
        "--output_dir",
        str(lora_output_dir),
        "--logging_dir",
        "logs",
        "--mixed_precision",
        config.mixed_precision,
    ]
    if config.max_train_steps is not None:
        command.extend(["--max_train_steps", str(config.max_train_steps)])
    else:
        command.extend(["--num_train_epochs", str(config.num_train_epochs)])
    if enable_validation and config.enable_training_validation and config.validation_prompts:
        command.extend(
            [
                "--validation_prompt",
                config.validation_prompts[0],
                "--validation_epochs",
                str(config.validation_epochs),
                "--num_validation_images",
                str(config.num_validation_images),
            ]
        )
    if config.center_crop:
        command.append("--center_crop")
    if config.random_flip:
        command.append("--random_flip")
    if config.gradient_checkpointing:
        command.append("--gradient_checkpointing")
    if config.use_8bit_adam:
        command.append("--use_8bit_adam")
    if config.allow_tf32:
        command.append("--allow_tf32")
    if config.max_train_samples is not None:
        command.extend(["--max_train_samples", str(config.max_train_samples)])
    return command


def run_lora_training(
    *,
    command: list[str],
    workdir: Path,
    settings: Settings,
    extra_env: dict[str, str] | None = None,
) -> None:
    env = os.environ.copy()
    env.setdefault("HF_HOME", str(settings.hf_home))
    env.setdefault("TRANSFORMERS_CACHE", str(settings.hf_home / "transformers"))
    env.setdefault("HF_DATASETS_CACHE", str(settings.hf_home / "datasets"))
    env.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")
    env.setdefault("ACCELERATE_USE_MPS_DEVICE", "true")
    if extra_env:
        env.update(extra_env)

    subprocess.run(command, cwd=workdir, env=env, check=True)
