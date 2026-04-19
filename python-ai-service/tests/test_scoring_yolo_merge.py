from __future__ import annotations

from pathlib import Path

from PIL import Image
import yaml


def _write_tiny_yolo_dataset(root: Path, name: str) -> Path:
    dataset_root = root / name
    for split in ("train", "val", "test"):
        (dataset_root / "images" / split).mkdir(parents=True, exist_ok=True)
        (dataset_root / "labels" / split).mkdir(parents=True, exist_ok=True)
        image_path = dataset_root / "images" / split / f"{name}_{split}.jpg"
        label_path = dataset_root / "labels" / split / f"{name}_{split}.txt"
        Image.new("RGB", (64, 64), color=(140, 150, 160)).save(image_path)
        label_path.write_text("0 0.5 0.5 0.25 0.25", encoding="utf-8")
    dataset_yaml = dataset_root / "dataset.yaml"
    dataset_yaml.write_text(
        "\n".join(
            [
                f"path: {dataset_root}",
                "train: images/train",
                "val: images/val",
                "test: images/test",
                "names:",
                "  - tower",
            ]
        ),
        encoding="utf-8",
    )
    return dataset_yaml


def test_prepare_yolo_training_dataset_merges_multiple_sources(tmp_path: Path) -> None:
    from training.scoring.pipeline import _prepare_yolo_training_dataset

    first_yaml = _write_tiny_yolo_dataset(tmp_path, "first")
    second_yaml = _write_tiny_yolo_dataset(tmp_path, "second")

    merged_yaml = _prepare_yolo_training_dataset(
        training_root=tmp_path / "training",
        yolo_datasets=[str(first_yaml), str(second_yaml)],
    )

    merged_root = merged_yaml.parent
    assert merged_yaml.exists()
    assert len(list((merged_root / "images" / "train").glob("*.jpg"))) == 2
    assert len(list((merged_root / "labels" / "val").glob("*.txt"))) == 2


def test_prepare_yolo_training_dataset_filters_and_remaps_active_classes(tmp_path: Path) -> None:
    from training.scoring.pipeline import _prepare_yolo_training_dataset

    dataset_root = tmp_path / "source"
    for split in ("train", "val", "test"):
        (dataset_root / "images" / split).mkdir(parents=True, exist_ok=True)
        (dataset_root / "labels" / split).mkdir(parents=True, exist_ok=True)
        image_path = dataset_root / "images" / split / f"{split}.jpg"
        label_path = dataset_root / "labels" / split / f"{split}.txt"
        Image.new("RGB", (64, 64), color=(120, 130, 140)).save(image_path)
        label_path.write_text("0 0.5 0.5 0.25 0.25\n2 0.4 0.4 0.2 0.2", encoding="utf-8")

    dataset_yaml = dataset_root / "dataset.yaml"
    dataset_yaml.write_text(
        "\n".join(
            [
                f"path: {dataset_root}",
                "train: images/train",
                "val: images/val",
                "test: images/test",
                "names:",
                "  - line",
                "  - breaker",
                "  - tower",
            ]
        ),
        encoding="utf-8",
    )

    merged_yaml = _prepare_yolo_training_dataset(
        training_root=tmp_path / "training",
        yolo_datasets=[str(dataset_yaml)],
        active_classes=["line", "tower"],
    )

    merged_payload = yaml.safe_load(merged_yaml.read_text(encoding="utf-8"))
    assert merged_payload["names"] == ["line", "tower"]

    label_text = (merged_yaml.parent / "labels" / "train" / "0_train.txt").read_text(encoding="utf-8").splitlines()
    assert label_text == [
        "0 0.500000 0.500000 0.250000 0.250000",
        "1 0.400000 0.400000 0.200000 0.200000",
    ]
