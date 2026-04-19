from __future__ import annotations

import json
import random
import shutil
from pathlib import Path

import torch
import yaml
from PIL import Image
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms
from ultralytics import YOLO

from app.core.settings import Settings, get_settings
from training.common.jsonl import read_jsonl
from training.common.paths import TrainingPaths
from training.scoring.config import ScoringTrainingConfig
from training.scoring.datasets import (
    build_scoring_manifests,
    download_dataset_archives,
    extract_archives,
    materialize_hf_detection_datasets,
    select_supported_power_classes,
)
from training.scoring.modeling import (
    FourDimScoreModel,
    choose_training_device,
    configure_image_backbone_trainability,
    encode_prompt,
)


class ScoreManifestDataset(Dataset):
    def __init__(
        self,
        rows: list[dict[str, object]],
        *,
        vocab: dict[str, int],
        image_size: int,
        targets: list[str],
    ) -> None:
        self._rows = rows
        self._vocab = vocab
        self._targets = targets
        interpolation = transforms.InterpolationMode.BICUBIC
        self._transform = transforms.Compose(
            [
                transforms.Resize((image_size, image_size), interpolation=interpolation),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            ]
        )

    def __len__(self) -> int:
        return len(self._rows)

    def __getitem__(self, index: int) -> dict[str, object]:
        row = self._rows[index]
        image = Image.open(row["image_path"]).convert("RGB")
        return {
            "image": self._transform(image),
            "prompt_ids": encode_prompt(str(row["prompt"]), self._vocab),
            "yolo_features": torch.tensor(row["yolo_features"], dtype=torch.float32),
            "targets": torch.tensor([float(row["targets"][name]) for name in self._targets], dtype=torch.float32),
        }


def _collate_batch(batch: list[dict[str, object]]) -> dict[str, torch.Tensor]:
    images = torch.stack([item["image"] for item in batch])
    yolo_features = torch.stack([item["yolo_features"] for item in batch])
    targets = torch.stack([item["targets"] for item in batch])
    merged_prompt_ids: list[int] = []
    offsets: list[int] = []
    cursor = 0
    for item in batch:
        offsets.append(cursor)
        prompt_ids = item["prompt_ids"]
        merged_prompt_ids.extend(prompt_ids)
        cursor += len(prompt_ids)
    return {
        "images": images,
        "prompt_ids": torch.tensor(merged_prompt_ids, dtype=torch.long),
        "prompt_offsets": torch.tensor(offsets, dtype=torch.long),
        "yolo_features": yolo_features,
        "targets": targets,
    }


def run_scoring_training(
    *,
    settings: Settings | None = None,
    config: ScoringTrainingConfig | None = None,
) -> dict[str, object]:
    runtime_settings = settings or get_settings()
    training_config = config or ScoringTrainingConfig()
    paths = TrainingPaths.from_settings(runtime_settings)
    paths.ensure_directories()

    random.seed(training_config.seed)
    torch.manual_seed(training_config.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(training_config.seed)

    archives = download_dataset_archives(paths.scoring_dataset_root, training_config.dataset_sources)
    extracted = extract_archives(paths.scoring_dataset_root, archives)
    extracted.extend(
        materialize_hf_detection_datasets(
            dataset_root=paths.scoring_dataset_root,
            sources=training_config.dataset_sources,
            power_classes=training_config.power_classes,
        )
    )
    class_support = select_supported_power_classes(
        extracted=extracted,
        power_classes=training_config.power_classes,
        min_train_instances=training_config.yolo_min_train_instances,
        min_val_instances=training_config.yolo_min_val_instances,
    )
    active_power_classes = [str(item) for item in class_support["classes"]]
    manifest_summary = build_scoring_manifests(
        dataset_root=paths.scoring_dataset_root,
        extracted=extracted,
        power_classes=active_power_classes,
        max_train_samples=training_config.max_train_samples,
        max_val_samples=training_config.max_val_samples,
        max_test_samples=training_config.max_test_samples,
    )

    train_rows = list(read_jsonl(Path(manifest_summary["manifests"]["train"])))
    val_rows = list(read_jsonl(Path(manifest_summary["manifests"]["val"])))
    test_rows = list(read_jsonl(Path(manifest_summary["manifests"]["test"])))
    if not train_rows:
        raise RuntimeError("scoring training manifest did not contain any training samples")
    vocab = _build_vocab(train_rows)
    yolo_feature_dim = len(train_rows[0]["yolo_features"]) if train_rows else len(active_power_classes) * 2 + 4
    device = choose_training_device(training_config.device_preference)

    bundle_dir = runtime_settings.scoring_model_dir / training_config.bundle_name
    bundle_dir.mkdir(parents=True, exist_ok=True)
    yolo_report = _train_yolo_auxiliary(
        training_root=paths.scoring_training_root,
        bundle_dir=bundle_dir,
        manifest_summary=manifest_summary,
        config=training_config,
        device=device,
        active_classes=active_power_classes,
    )

    train_dataset = ScoreManifestDataset(train_rows, vocab=vocab, image_size=training_config.image_size, targets=training_config.targets)
    val_dataset = ScoreManifestDataset(val_rows, vocab=vocab, image_size=training_config.image_size, targets=training_config.targets)
    test_dataset = ScoreManifestDataset(test_rows, vocab=vocab, image_size=training_config.image_size, targets=training_config.targets)

    loader_kwargs = {
        "num_workers": training_config.num_workers,
        "pin_memory": device.type == "cuda",
        "collate_fn": _collate_batch,
    }
    train_loader = DataLoader(train_dataset, batch_size=training_config.train_batch_size, shuffle=True, **loader_kwargs)
    val_loader = DataLoader(val_dataset, batch_size=training_config.eval_batch_size, shuffle=False, **loader_kwargs)
    test_loader = DataLoader(test_dataset, batch_size=training_config.eval_batch_size, shuffle=False, **loader_kwargs)

    model = FourDimScoreModel(
        len(vocab),
        yolo_feature_dim,
        len(training_config.targets),
        pretrained_backbone=training_config.use_pretrained_image_backbone,
    ).to(device)
    configure_image_backbone_trainability(
        model.image_backbone,
        trainable_stages=training_config.image_backbone_trainable_stages,
    )
    optimizer = torch.optim.AdamW(model.parameters(), lr=training_config.learning_rate, weight_decay=training_config.weight_decay)
    loss_fn = torch.nn.SmoothL1Loss(beta=4.0)

    history: list[dict[str, float | int]] = []
    best_state: dict[str, torch.Tensor] | None = None
    best_val_mae = float("inf")

    for epoch in range(1, training_config.epochs + 1):
        train_loss = _run_epoch(model=model, loader=train_loader, device=device, optimizer=optimizer, loss_fn=loss_fn)
        val_metrics = _evaluate(model=model, loader=val_loader, device=device, targets=training_config.targets)
        history.append(
            {
                "epoch": epoch,
                "train_loss": round(train_loss, 6),
                "val_mae": round(val_metrics["mae"], 6),
            }
        )
        paths.scoring_training_root.mkdir(parents=True, exist_ok=True)
        (paths.scoring_training_root / "history.json").write_text(
            json.dumps(history, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(
            json.dumps(
                {
                    "epoch": epoch,
                    "epochs": training_config.epochs,
                    "train_loss": round(train_loss, 6),
                    "val_mae": round(val_metrics["mae"], 6),
                },
                ensure_ascii=False,
            ),
            flush=True,
        )
        if val_metrics["mae"] <= best_val_mae:
            best_val_mae = val_metrics["mae"]
            best_state = {key: value.detach().cpu() for key, value in model.state_dict().items()}

    if best_state is None:
        best_state = {key: value.detach().cpu() for key, value in model.state_dict().items()}
    torch.save(best_state, bundle_dir / "student_best.pt")

    with torch.no_grad():
        model.load_state_dict(best_state)
    test_metrics = _evaluate(model=model, loader=test_loader, device=device, targets=training_config.targets)

    bundle_payload = training_config.bundle_payload()
    bundle_payload["classes"] = active_power_classes
    bundle_payload["yolo_feature_dim"] = yolo_feature_dim
    (bundle_dir / "bundle_config.json").write_text(json.dumps(bundle_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (bundle_dir / "vocab.json").write_text(json.dumps(vocab, ensure_ascii=False, indent=2), encoding="utf-8")
    (bundle_dir / "metrics.json").write_text(
        json.dumps(
            {
                "device": str(device),
                "epochs": training_config.epochs,
                "best_val_mae": round(best_val_mae, 6),
                "test_metrics": test_metrics,
                "yolo": yolo_report,
                "active_classes": active_power_classes,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    training_report = {
        "runtime_root": str(paths.runtime_root),
        "scoring_dataset_root": str(paths.scoring_dataset_root),
        "scoring_training_root": str(paths.scoring_training_root),
        "scoring_model_root": str(bundle_dir),
        "epochs": training_config.epochs,
        "device": str(device),
        "history_path": str(paths.scoring_training_root / "history.json"),
        "bundle_config_path": str(bundle_dir / "bundle_config.json"),
        "train_count": len(train_rows),
        "val_count": len(val_rows),
        "test_count": len(test_rows),
        "active_classes": active_power_classes,
        "class_support": class_support,
        "yolo": yolo_report,
    }
    paths.scoring_training_root.mkdir(parents=True, exist_ok=True)
    (paths.scoring_training_root / "history.json").write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")
    (paths.scoring_training_root / "training_report.json").write_text(json.dumps(training_report, ensure_ascii=False, indent=2), encoding="utf-8")
    return training_report


def _run_epoch(*, model, loader, device, optimizer, loss_fn) -> float:
    model.train()
    total_loss = 0.0
    total_batches = 0
    for batch in loader:
        optimizer.zero_grad(set_to_none=True)
        outputs = model(
            batch["images"].to(device),
            batch["prompt_ids"].to(device),
            batch["prompt_offsets"].to(device),
            batch["yolo_features"].to(device),
        )
        loss = loss_fn(outputs, batch["targets"].to(device))
        loss.backward()
        optimizer.step()
        total_loss += float(loss.detach().cpu())
        total_batches += 1
    return total_loss / max(total_batches, 1)


def _evaluate(*, model, loader, device, targets: list[str]) -> dict[str, object]:
    model.eval()
    mae_total = 0.0
    count = 0
    per_target = {name: 0.0 for name in targets}
    with torch.no_grad():
        for batch in loader:
            outputs = model(
                batch["images"].to(device),
                batch["prompt_ids"].to(device),
                batch["prompt_offsets"].to(device),
                batch["yolo_features"].to(device),
            )
            diff = (outputs - batch["targets"].to(device)).abs().detach().cpu()
            mae_total += float(diff.mean())
            count += 1
            for index, name in enumerate(targets):
                per_target[name] += float(diff[:, index].mean())
    metrics = {
        "mae": round(mae_total / max(count, 1), 6),
        "per_target_mae": {
            name: round(value / max(count, 1), 6)
            for name, value in per_target.items()
        },
    }
    return metrics


def _build_vocab(rows: list[dict[str, object]]) -> dict[str, int]:
    vocab = {"<unk>": 0}
    for row in rows:
        for token in str(row["prompt"]).lower().replace(",", " ").split():
            token = token.strip()
            if token and token not in vocab:
                vocab[token] = len(vocab)
    return vocab


def _train_yolo_auxiliary(
    *,
    training_root: Path,
    bundle_dir: Path,
    manifest_summary: dict[str, object],
    config: ScoringTrainingConfig,
    device: torch.device,
    active_classes: list[str] | None = None,
) -> dict[str, object]:
    if not manifest_summary.get("yolo_datasets"):
        return {"status": "skipped", "reason": "no-detection-dataset"}

    primary_yaml = _prepare_yolo_training_dataset(
        training_root=training_root,
        yolo_datasets=[str(item) for item in manifest_summary["yolo_datasets"]],
        active_classes=active_classes,
    )
    yolo_output_root = training_root / "yolo-aux"
    yolo_output_root.mkdir(parents=True, exist_ok=True)

    try:
        model = YOLO(config.yolo_model_name)
        train_result = model.train(
            data=str(primary_yaml),
            epochs=config.yolo_epochs,
            imgsz=config.yolo_image_size,
            batch=config.yolo_batch_size,
            device=str(device),
            project=str(yolo_output_root),
            name="electric-score-v2",
            exist_ok=True,
            verbose=False,
            val=config.yolo_validate_each_epoch,
            rect=True,
            plots=False,
        )
        best_path = Path(train_result.save_dir) / "weights" / "best.pt"
        if best_path.exists():
            shutil.copy2(best_path, bundle_dir / "yolo_aux.pt")
            report = {
                "status": "trained",
                "weights": str(bundle_dir / "yolo_aux.pt"),
                "dataset": str(primary_yaml),
                "dataset_count": len(manifest_summary["yolo_datasets"]),
            }
            if config.yolo_run_final_validation:
                try:
                    validation = model.val(
                        data=str(primary_yaml),
                        imgsz=config.yolo_image_size,
                        batch=config.yolo_batch_size,
                        device=str(device),
                        split="val",
                        rect=True,
                        plots=False,
                        verbose=False,
                    )
                    metrics = _extract_yolo_metrics(validation)
                    if metrics:
                        report["validation"] = metrics
                except Exception as exc:  # pragma: no cover - runtime fallback
                    report["validation_error"] = str(exc)
            return report
        return {"status": "missing-best-weight", "save_dir": str(train_result.save_dir)}
    except Exception as exc:  # pragma: no cover - runtime fallback
        return {"status": "failed", "error": str(exc)}


def _prepare_yolo_training_dataset(
    *,
    training_root: Path,
    yolo_datasets: list[str],
    active_classes: list[str] | None = None,
) -> Path:
    dataset_paths = [Path(item) for item in yolo_datasets]
    target_names = [str(item) for item in active_classes] if active_classes else None

    if len(dataset_paths) == 1 and target_names is None:
        return dataset_paths[0]

    merged_root = training_root / "yolo-merged"
    if merged_root.exists():
        shutil.rmtree(merged_root)

    for split in ("train", "val", "test"):
        (merged_root / "images" / split).mkdir(parents=True, exist_ok=True)
        (merged_root / "labels" / split).mkdir(parents=True, exist_ok=True)

    merged_names: list[str] | None = target_names
    for dataset_index, dataset_yaml in enumerate(dataset_paths):
        payload = yaml.safe_load(dataset_yaml.read_text(encoding="utf-8")) or {}
        dataset_root = Path(payload.get("path") or dataset_yaml.parent)
        source_names = payload.get("names", [])
        source_names = [str(item) for item in source_names.values()] if isinstance(source_names, dict) else [str(item) for item in source_names]
        if merged_names is None:
            merged_names = list(source_names)
        class_mapping = {
            source_index: merged_names.index(class_name)
            for source_index, class_name in enumerate(source_names)
            if class_name in merged_names
        }

        for split in ("train", "val", "test"):
            image_rel = payload.get(split)
            if not image_rel:
                continue
            image_dir = dataset_root / str(image_rel)
            label_dir = dataset_root / str(image_rel).replace("images", "labels", 1)
            if not image_dir.exists() or not label_dir.exists():
                continue
            for image_path in image_dir.iterdir():
                if not image_path.is_file():
                    continue
                label_path = label_dir / f"{image_path.stem}.txt"
                if not label_path.exists():
                    continue

                remapped_lines: list[str] = []
                for raw_line in label_path.read_text(encoding="utf-8").splitlines():
                    line = raw_line.strip()
                    if not line:
                        continue
                    parts = line.split()
                    try:
                        class_id = int(parts[0])
                    except ValueError:
                        continue
                    if class_id not in class_mapping:
                        continue
                    coordinates: list[str] = []
                    parse_failed = False
                    for value in parts[1:]:
                        try:
                            coordinates.append(f"{float(value):.6f}")
                        except ValueError:
                            parse_failed = True
                            break
                    if parse_failed:
                        continue
                    remapped_lines.append(" ".join([str(class_mapping[class_id]), *coordinates]))

                if not remapped_lines:
                    continue

                target_stem = f"{dataset_index}_{image_path.stem}"
                shutil.copy2(image_path, merged_root / "images" / split / f"{target_stem}{image_path.suffix}")
                (merged_root / "labels" / split / f"{target_stem}.txt").write_text(
                    "\n".join(remapped_lines),
                    encoding="utf-8",
                )

    dataset_yaml = merged_root / "dataset.yaml"
    dataset_yaml.write_text(
        yaml.safe_dump(
            {
                "path": str(merged_root),
                "train": "images/train",
                "val": "images/val",
                "test": "images/test",
                "names": merged_names or [],
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return dataset_yaml


def _extract_yolo_metrics(metrics) -> dict[str, float]:
    results = getattr(metrics, "results_dict", None)
    if not isinstance(results, dict):
        return {}

    payload: dict[str, float] = {}
    for key, value in results.items():
        try:
            payload[str(key)] = round(float(value), 6)
        except (TypeError, ValueError):
            continue
    return payload
