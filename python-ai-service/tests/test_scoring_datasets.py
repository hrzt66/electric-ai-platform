from __future__ import annotations

from pathlib import Path

from PIL import Image


class _FakeClassLabel:
    def __init__(self, names: list[str]) -> None:
        self.names = names

    def int2str(self, value: int) -> str:
        return self.names[value]


class _FakeListFeature:
    def __init__(self, feature) -> None:
        self.feature = feature


class _FakeSplit(list):
    def __init__(self, rows: list[dict[str, object]], label_names: list[str]) -> None:
        super().__init__(rows)
        self.features = {"labels": _FakeListFeature(_FakeClassLabel(label_names))}


def test_materialize_hf_detection_dataset_exports_yolo_structure(monkeypatch, tmp_path: Path) -> None:
    from training.scoring.datasets import materialize_hf_detection_datasets

    label_names = ["Broken Cable", "Broken Insulator", "Cable", "Insulators", "Tower", "Vegetation"]
    image = Image.new("RGB", (100, 50), color=(128, 140, 152))
    fake_dataset = {
        "train": _FakeSplit(
            [
                {
                    "image": image,
                    "bboxes": [[10.0, 5.0, 60.0, 30.0], [40.0, 10.0, 90.0, 40.0]],
                    "labels": [2, 4],
                }
            ],
            label_names,
        ),
        "validation": _FakeSplit(
            [
                {
                    "image": image,
                    "bboxes": [[20.0, 8.0, 50.0, 25.0]],
                    "labels": [1],
                }
            ],
            label_names,
        ),
        "test": _FakeSplit([], label_names),
    }

    monkeypatch.setattr("training.scoring.datasets.load_dataset", lambda dataset_id: fake_dataset)

    extracted = materialize_hf_detection_datasets(
        dataset_root=tmp_path,
        sources=[
            {
                "name": "powerline-components-and-faults",
                "dataset_id": "docmhvr/powerline-components-and-faults",
                "kind": "hf_detection_bboxes_labels",
                "enabled": True,
                "label_map": {
                    "Broken Cable": "line",
                    "Broken Insulator": "insulator",
                    "Cable": "line",
                    "Insulators": "insulator",
                    "Tower": "tower",
                },
            }
        ],
        power_classes=["line", "insulator", "tower"],
    )

    assert len(extracted) == 1
    export_root = Path(extracted[0]["root"])
    assert (export_root / "dataset.yaml").exists()
    assert (export_root / "images" / "train").exists()
    assert (export_root / "labels" / "train").exists()
    train_labels = sorted((export_root / "labels" / "train").glob("*.txt"))
    val_labels = sorted((export_root / "labels" / "val").glob("*.txt"))
    assert len(train_labels) == 1
    assert len(val_labels) == 1
    train_lines = train_labels[0].read_text(encoding="utf-8").splitlines()
    val_lines = val_labels[0].read_text(encoding="utf-8").splitlines()
    assert train_lines[0].startswith("0 ")
    assert train_lines[1].startswith("2 ")
    assert val_lines[0].startswith("1 ")


def test_collect_detection_rows_supports_pascal_voc_layout(tmp_path: Path) -> None:
    from training.scoring.datasets import _collect_detection_rows

    root = tmp_path / "voc-source"
    image_dir = root / "voc1" / "JPEGImages"
    annotation_dir = root / "voc1" / "Annotations"
    image_dir.mkdir(parents=True, exist_ok=True)
    annotation_dir.mkdir(parents=True, exist_ok=True)

    image_path = image_dir / "sample.jpg"
    Image.new("RGB", (200, 100), color=(130, 140, 150)).save(image_path)
    (annotation_dir / "sample.xml").write_text(
        """<annotation>
<filename>sample.jpg</filename>
<size><width>200</width><height>100</height><depth>3</depth></size>
<object>
  <name>tower</name>
  <bndbox><xmin>20</xmin><ymin>10</ymin><xmax>100</xmax><ymax>80</ymax></bndbox>
</object>
<object>
  <name>insulator</name>
  <bndbox><xmin>120</xmin><ymin>18</ymin><xmax>170</xmax><ymax>72</ymax></bndbox>
</object>
</annotation>""",
        encoding="utf-8",
    )

    rows, yolo_yaml = _collect_detection_rows(
        root=root,
        source_name="voc-unit-test",
        power_classes=["tower", "insulator", "line"],
    )

    assert len(rows) == 1
    assert rows[0]["detections"][0]["class_name"] == "tower"
    assert rows[0]["detections"][1]["class_name"] == "insulator"
    assert yolo_yaml is not None
    assert yolo_yaml.exists()


def test_select_supported_power_classes_drops_extreme_long_tail(monkeypatch, tmp_path: Path) -> None:
    from training.scoring.datasets import select_supported_power_classes

    def _fake_rows(split: str, class_name: str, count: int) -> list[dict[str, object]]:
        rows = []
        for index in range(count):
            rows.append(
                {
                    "image_path": str(tmp_path / f"{split}_{class_name}_{index}.jpg"),
                    "prompt": f"{class_name} inspection",
                    "split": split,
                    "source_name": "det-unit-test",
                    "detections": [{"class_name": class_name, "confidence": 1.0, "bbox": [0.5, 0.5, 0.3, 0.3]}],
                    "yolo_features": [],
                    "targets": {},
                }
            )
        return rows

    fake_rows = (
        _fake_rows("train", "line", 60)
        + _fake_rows("val", "line", 12)
        + _fake_rows("train", "tower", 55)
        + _fake_rows("val", "tower", 10)
        + _fake_rows("train", "breaker", 8)
        + _fake_rows("val", "breaker", 3)
    )

    monkeypatch.setattr(
        "training.scoring.datasets._collect_detection_rows",
        lambda **kwargs: (fake_rows, None),
    )

    selection = select_supported_power_classes(
        extracted=[
            {"name": "det-unit-test", "kind": "detection", "root": str(tmp_path / "det")},
            {"name": "cls-unit-test", "kind": "classification", "root": str(tmp_path / "cls")},
        ],
        power_classes=["line", "tower", "breaker"],
        min_train_instances=50,
        min_val_instances=10,
    )

    assert selection["classes"] == ["line", "tower"]
    assert selection["dropped_classes"] == ["breaker"]
    assert selection["all_train_counts"]["breaker"] == 8
    assert selection["all_val_counts"]["tower"] == 10


def test_find_image_for_label_prefers_matching_split_over_duplicate_stems(tmp_path: Path) -> None:
    from training.scoring.datasets import _find_image_for_label

    dataset_root = tmp_path / "hf-like"
    train_image_dir = dataset_root / "images" / "train"
    val_image_dir = dataset_root / "images" / "val"
    val_label_dir = dataset_root / "labels" / "val"
    train_image_dir.mkdir(parents=True, exist_ok=True)
    val_image_dir.mkdir(parents=True, exist_ok=True)
    val_label_dir.mkdir(parents=True, exist_ok=True)

    train_image = train_image_dir / "duplicate.jpg"
    val_image = val_image_dir / "duplicate.jpg"
    label_path = val_label_dir / "duplicate.txt"

    Image.new("RGB", (64, 64), color=(100, 110, 120)).save(train_image)
    Image.new("RGB", (64, 64), color=(130, 140, 150)).save(val_image)
    label_path.write_text("0 0.5 0.5 0.25 0.25", encoding="utf-8")

    resolved = _find_image_for_label(label_path)

    assert resolved == val_image
