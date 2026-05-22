from __future__ import annotations

from pathlib import Path

from PIL import Image


def _write_sample_yolo_pair(root: Path, *, split: str, stem: str, class_id: int) -> None:
    image_dir = root / "images" / split
    label_dir = root / "labels" / split
    image_dir.mkdir(parents=True, exist_ok=True)
    label_dir.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (128, 128), color=(220, 228, 236)).save(image_dir / f"{stem}.png")
    (label_dir / f"{stem}.txt").write_text(f"{class_id} 0.5 0.5 0.4 0.4\n", encoding="utf-8")


def test_exports_selected_source_images_for_physical_part_annotation(tmp_path) -> None:
    from scripts.prepare_physical_part_annotation_dataset import export_source_images

    source_root = tmp_path / "yolo-image2-remapped-scoring-6class-v1"
    _write_sample_yolo_pair(source_root, split="train", stem="wind_a", class_id=3)
    _write_sample_yolo_pair(source_root, split="train", stem="tower_a", class_id=1)
    _write_sample_yolo_pair(source_root, split="val", stem="dam_a", class_id=5)

    output_root = tmp_path / "yolo-physical-parts-v1"
    summary = export_source_images(
        source_root=source_root,
        output_root=output_root,
        per_class_limit=2,
    )

    train_files = sorted(path.name for path in (output_root / "images" / "train").iterdir())
    val_files = sorted(path.name for path in (output_root / "images" / "val").iterdir())
    assert "wind_a.png" in train_files
    assert "tower_a.png" in train_files
    assert "dam_a.png" in val_files
    assert summary["copied_count"] == 3


def test_converts_annotation_jsonl_to_yolo_labels(tmp_path) -> None:
    from scripts.prepare_physical_part_annotation_dataset import convert_annotations_to_yolo_labels

    dataset_root = tmp_path / "yolo-physical-parts-v1"
    image_dir = dataset_root / "images" / "train"
    image_dir.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (200, 100), color=(220, 228, 236)).save(image_dir / "wind_a.png")
    annotation_path = dataset_root / "annotations.jsonl"
    annotation_path.write_text(
        '{"image_name":"wind_a.png","annotations":[{"class_name":"wind_blade","bbox_xyxy":[20,10,60,30]}]}\n',
        encoding="utf-8",
    )

    summary = convert_annotations_to_yolo_labels(dataset_root=dataset_root, annotation_path=annotation_path)

    label_path = dataset_root / "labels" / "train" / "wind_a.txt"
    assert label_path.exists()
    lines = [line.strip() for line in label_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(lines) == 1
    assert lines[0].startswith("0 ")
    assert summary["written_label_count"] == 1
