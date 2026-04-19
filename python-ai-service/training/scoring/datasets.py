from __future__ import annotations

import hashlib
import json
import random
import shutil
import urllib.request
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import yaml
from datasets import load_dataset
from PIL import Image

from training.common.jsonl import write_jsonl
from training.scoring.modeling import (
    GENERIC_ELECTRIC_TERMS,
    PROMPT_CLASS_ALIASES,
    clamp_score,
)

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
CLASS_COMPONENT_ALIASES = {
    "busbar": "bus",
    "connecting port": "bus",
    "conductor": "line",
    "wire": "line",
    "dx": "line",
    "tower": "tower",
    "frame": "frame",
    "insulator": "insulator",
    "arrester": "arrester",
    "breaker": "breaker",
    "switch": "switch",
    "pipe": "pipe",
    "bushing": "bushing",
    "filter": "filter",
    "capacitor": "capacitor",
    "gis": "gis",
    "pt": "pt",
    "ct": "ct",
}
CLASSIFICATION_COMPONENT_PREFIX = {
    "blq": "arrester",
    "czjyz": "insulator",
    "dx": "line",
    "fhjyz": "insulator",
    "gydxjd": "line",
    "jj": "line",
    "jyspbg": "insulator",
    "nw": "line",
    "yw": "line",
    "yxdk": "line",
}


def download_dataset_archives(dataset_root: Path, sources: list[dict[str, str | bool]]) -> list[dict[str, str]]:
    archive_root = dataset_root / "raw" / "archives"
    archive_root.mkdir(parents=True, exist_ok=True)
    downloaded: list[dict[str, str]] = []
    for source in sources:
        if not bool(source.get("enabled", True)):
            continue
        if "url" not in source or "archive_name" not in source:
            continue
        archive_path = archive_root / str(source["archive_name"])
        if not archive_path.exists():
            urllib.request.urlretrieve(str(source["url"]), archive_path)
        downloaded.append(
            {
                "name": str(source["name"]),
                "kind": str(source["kind"]),
                "archive_path": str(archive_path),
            }
        )
    return downloaded


def extract_archives(dataset_root: Path, archives: list[dict[str, str]]) -> list[dict[str, str]]:
    extracted_root = dataset_root / "raw" / "extracted"
    extracted_root.mkdir(parents=True, exist_ok=True)
    extracted: list[dict[str, str]] = []
    for archive in archives:
        source_name = archive["name"]
        target_root = extracted_root / source_name
        stamp = target_root / ".extract-complete"
        if not stamp.exists():
            if target_root.exists():
                shutil.rmtree(target_root)
            target_root.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(archive["archive_path"]) as zf:
                zf.extractall(target_root)
            _extract_nested_archives(target_root)
            stamp.write_text("ok", encoding="utf-8")
        extracted.append(
            {
                "name": source_name,
                "kind": archive["kind"],
                "root": str(target_root),
            }
        )
    return extracted


def materialize_hf_detection_datasets(
    *,
    dataset_root: Path,
    sources: list[dict[str, object]],
    power_classes: list[str],
) -> list[dict[str, str]]:
    materialized_root = dataset_root / "raw" / "hf"
    materialized_root.mkdir(parents=True, exist_ok=True)
    extracted: list[dict[str, str]] = []
    for source in sources:
        if not bool(source.get("enabled", True)):
            continue
        kind = str(source.get("kind", ""))
        dataset_id = source.get("dataset_id")
        if not kind.startswith("hf_detection") or not isinstance(dataset_id, str):
            continue

        source_name = str(source["name"])
        export_root = materialized_root / source_name
        stamp = export_root / ".materialize-complete"
        if not stamp.exists():
            if export_root.exists():
                shutil.rmtree(export_root)
            export_root.mkdir(parents=True, exist_ok=True)
            if kind == "hf_detection_bboxes_labels":
                _export_hf_bboxes_labels_dataset(
                    export_root=export_root,
                    dataset_id=dataset_id,
                    source_name=source_name,
                    power_classes=power_classes,
                    label_map={str(key): str(value) for key, value in dict(source.get("label_map", {})).items()},
                )
            else:
                raise ValueError(f"unsupported hf detection source kind: {kind}")
            stamp.write_text("ok", encoding="utf-8")

        extracted.append({"name": source_name, "kind": "detection", "root": str(export_root)})
    return extracted


def build_scoring_manifests(
    *,
    dataset_root: Path,
    extracted: list[dict[str, str]],
    power_classes: list[str],
    max_train_samples: int | None = None,
    max_val_samples: int | None = None,
    max_test_samples: int | None = None,
) -> dict[str, object]:
    all_rows: list[dict[str, object]] = []
    yolo_datasets: list[str] = []
    for source in extracted:
        root = Path(source["root"])
        if source["kind"] == "detection":
            detection_rows, yolo_yaml = _collect_detection_rows(root=root, source_name=source["name"], power_classes=power_classes)
            all_rows.extend(detection_rows)
            if yolo_yaml is not None:
                yolo_datasets.append(str(yolo_yaml))
        elif source["kind"] == "classification":
            all_rows.extend(_collect_classification_rows(root=root, source_name=source["name"], power_classes=power_classes))

    manifests_root = dataset_root / "manifests"
    manifests_root.mkdir(parents=True, exist_ok=True)
    split_rows = _group_splits(all_rows)
    capped_splits = {
        "train": _cap_rows(split_rows["train"], max_train_samples),
        "val": _cap_rows(split_rows["val"], max_val_samples),
        "test": _cap_rows(split_rows["test"], max_test_samples),
    }
    for split_name, rows in capped_splits.items():
        write_jsonl(manifests_root / f"{split_name}.jsonl", rows)

    summary = {
        "train_count": len(capped_splits["train"]),
        "val_count": len(capped_splits["val"]),
        "test_count": len(capped_splits["test"]),
        "manifests": {name: str(manifests_root / f"{name}.jsonl") for name in capped_splits},
        "yolo_datasets": yolo_datasets,
    }
    (manifests_root / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def select_supported_power_classes(
    *,
    extracted: list[dict[str, str]],
    power_classes: list[str],
    min_train_instances: int,
    min_val_instances: int,
) -> dict[str, object]:
    train_counts = {name: 0 for name in power_classes}
    val_counts = {name: 0 for name in power_classes}

    for source in extracted:
        if source.get("kind") != "detection":
            continue
        rows, _ = _collect_detection_rows(
            root=Path(source["root"]),
            source_name=source["name"],
            power_classes=power_classes,
        )
        for row in rows:
            split = str(row.get("split") or "")
            if split not in {"train", "val"}:
                continue
            counter = train_counts if split == "train" else val_counts
            for detection in row.get("detections", []):
                class_name = str(detection.get("class_name") or "")
                if class_name in counter:
                    counter[class_name] += 1

    selected = [
        name
        for name in power_classes
        if train_counts.get(name, 0) >= min_train_instances and val_counts.get(name, 0) >= min_val_instances
    ]
    if not selected:
        selected = list(power_classes)

    dropped = [name for name in power_classes if name not in selected]
    return {
        "classes": selected,
        "dropped_classes": dropped,
        "all_train_counts": train_counts,
        "all_val_counts": val_counts,
    }


def _collect_detection_rows(*, root: Path, source_name: str, power_classes: list[str]) -> tuple[list[dict[str, object]], Path | None]:
    annotation_json = next(iter(root.rglob("annotation.json")), None)
    if annotation_json is not None:
        rows = _collect_via_rows(root=root, annotation_json=annotation_json, source_name=source_name, power_classes=power_classes)
        yolo_yaml = _export_via_to_yolo_dataset(
            root=root,
            annotation_json=annotation_json,
            source_name=source_name,
            power_classes=power_classes,
        )
        return rows, yolo_yaml

    pascal_voc_annotation = next(iter(root.rglob("Annotations/*.xml")), None)
    if pascal_voc_annotation is not None:
        rows = _collect_pascal_voc_rows(root=root, source_name=source_name, power_classes=power_classes)
        yolo_yaml = _export_pascal_voc_to_yolo_dataset(root=root, source_name=source_name, power_classes=power_classes)
        return rows, yolo_yaml

    yolo_yaml = next(iter(root.rglob("dataset.yaml")), None)
    if yolo_yaml is None:
        yolo_yaml = next(iter(root.rglob("data.yaml")), None)
    class_names = _load_class_names(yolo_yaml) if yolo_yaml is not None else []
    rows: list[dict[str, object]] = []
    for label_path in root.rglob("*.txt"):
        if label_path.name in {"classes.txt"}:
            continue
        image_path = _find_image_for_label(label_path)
        if image_path is None:
            continue
        detections = _parse_yolo_label_file(label_path, class_names, power_classes)
        if not detections:
            continue
        prompt = _build_prompt_from_detections(detections)
        split = _infer_split(image_path)
        rows.append(_build_row(image_path=image_path, prompt=prompt, detections=detections, split=split, source_name=source_name, power_classes=power_classes))
    return rows, yolo_yaml


def _collect_via_rows(*, root: Path, annotation_json: Path, source_name: str, power_classes: list[str]) -> list[dict[str, object]]:
    payload = json.loads(annotation_json.read_text(encoding="utf-8"))
    image_root = next(iter(root.rglob("images")), None)
    if image_root is None:
        return []

    rows: list[dict[str, object]] = []
    for item in payload.values():
        image_path = image_root / item["filename"]
        if not image_path.exists():
            continue
        detections: list[dict[str, object]] = []
        for region in item.get("regions", []):
            attrs = region.get("region_attributes", {})
            raw_class_name = str(attrs.get("type") or attrs.get("name") or "")
            normalized = _normalize_component(raw_class_name, power_classes)
            if normalized is None:
                continue
            bbox = _polygon_to_bbox(region.get("shape_attributes", {}))
            if bbox is None:
                continue
            detections.append({"class_name": normalized, "confidence": 1.0, "bbox": bbox})
        if not detections:
            continue
        prompt = _build_prompt_from_detections(detections)
        rows.append(_build_row(image_path=image_path, prompt=prompt, detections=detections, split=_infer_split(image_path), source_name=source_name, power_classes=power_classes))
    return rows


def _collect_pascal_voc_rows(*, root: Path, source_name: str, power_classes: list[str]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for annotation_path in root.rglob("Annotations/*.xml"):
        image_path, detections = _parse_pascal_voc_annotation(annotation_path, power_classes)
        if image_path is None or not detections:
            continue
        prompt = _build_prompt_from_detections(detections)
        rows.append(
            _build_row(
                image_path=image_path,
                prompt=prompt,
                detections=detections,
                split=_infer_split(image_path),
                source_name=source_name,
                power_classes=power_classes,
            )
        )
    return rows


def _export_pascal_voc_to_yolo_dataset(*, root: Path, source_name: str, power_classes: list[str]) -> Path | None:
    export_root = root / f"{source_name}-yolo"
    if export_root.exists():
        shutil.rmtree(export_root)
    class_index = {name: idx for idx, name in enumerate(power_classes)}

    for split in ("train", "val", "test"):
        (export_root / "images" / split).mkdir(parents=True, exist_ok=True)
        (export_root / "labels" / split).mkdir(parents=True, exist_ok=True)

    exported = 0
    for annotation_path in root.rglob("Annotations/*.xml"):
        image_path, detections = _parse_pascal_voc_annotation(annotation_path, power_classes)
        if image_path is None or not detections:
            continue
        split = _infer_split(image_path)
        label_lines = [
            f"{class_index[str(item['class_name'])]} {item['bbox'][0]:.6f} {item['bbox'][1]:.6f} {item['bbox'][2]:.6f} {item['bbox'][3]:.6f}"
            for item in detections
        ]
        target_image = export_root / "images" / split / image_path.name
        target_label = export_root / "labels" / split / f"{image_path.stem}.txt"
        shutil.copy2(image_path, target_image)
        target_label.write_text("\n".join(label_lines), encoding="utf-8")
        exported += 1

    if exported == 0:
        shutil.rmtree(export_root, ignore_errors=True)
        return None

    dataset_yaml = export_root / "dataset.yaml"
    dataset_yaml.write_text(
        yaml.safe_dump(
            {
                "path": str(export_root),
                "train": "images/train",
                "val": "images/val",
                "test": "images/test",
                "names": power_classes,
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return dataset_yaml


def _export_via_to_yolo_dataset(*, root: Path, annotation_json: Path, source_name: str, power_classes: list[str]) -> Path | None:
    payload = json.loads(annotation_json.read_text(encoding="utf-8"))
    image_root = next(iter(root.rglob("images")), None)
    if image_root is None:
        return None

    export_root = root / f"{source_name}-yolo"
    if export_root.exists():
        shutil.rmtree(export_root)
    class_index = {name: idx for idx, name in enumerate(power_classes)}

    for split in ("train", "val", "test"):
        (export_root / "images" / split).mkdir(parents=True, exist_ok=True)
        (export_root / "labels" / split).mkdir(parents=True, exist_ok=True)

    for item in payload.values():
        image_path = image_root / item["filename"]
        if not image_path.exists():
            continue
        split = _infer_split(image_path)
        label_lines: list[str] = []
        for region in item.get("regions", []):
            attrs = region.get("region_attributes", {})
            raw_class_name = str(attrs.get("type") or attrs.get("name") or "")
            normalized = _normalize_component(raw_class_name, power_classes)
            bbox = _polygon_to_bbox(region.get("shape_attributes", {}))
            if normalized is None or bbox is None:
                continue
            label_lines.append(
                f"{class_index[normalized]} {bbox[0]:.6f} {bbox[1]:.6f} {bbox[2]:.6f} {bbox[3]:.6f}"
            )
        if not label_lines:
            continue
        target_image = export_root / "images" / split / image_path.name
        target_label = export_root / "labels" / split / f"{image_path.stem}.txt"
        shutil.copy2(image_path, target_image)
        target_label.write_text("\n".join(label_lines), encoding="utf-8")

    dataset_yaml = export_root / "dataset.yaml"
    dataset_yaml.write_text(
        yaml.safe_dump(
            {
                "path": str(export_root),
                "train": "images/train",
                "val": "images/val",
                "test": "images/test",
                "names": power_classes,
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return dataset_yaml


def _collect_classification_rows(*, root: Path, source_name: str, power_classes: list[str]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for image_path in root.rglob("*"):
        if not image_path.is_file() or image_path.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        split = _infer_split(image_path)
        class_name = image_path.parent.name.lower()
        component = _map_classification_component(class_name)
        prompt = _build_prompt_for_classification(class_name, component)
        detections = [
            {
                "class_name": component,
                "confidence": 1.0,
                "bbox": [0.5, 0.5, 0.42, 0.42],
            }
        ]
        rows.append(_build_row(image_path=image_path, prompt=prompt, detections=detections, split=split, source_name=source_name, power_classes=power_classes))
    return rows


def _export_hf_bboxes_labels_dataset(
    *,
    export_root: Path,
    dataset_id: str,
    source_name: str,
    power_classes: list[str],
    label_map: dict[str, str],
) -> None:
    dataset = load_dataset(dataset_id)
    split_names = {"train": "train", "validation": "val", "test": "test", "val": "val"}
    class_index = {name: idx for idx, name in enumerate(power_classes)}
    label_feature = dataset["train"].features["labels"].feature

    for split in ("train", "val", "test"):
        (export_root / "images" / split).mkdir(parents=True, exist_ok=True)
        (export_root / "labels" / split).mkdir(parents=True, exist_ok=True)

    source_slug = source_name.replace("/", "-").replace(" ", "-")
    for split_name, rows in dataset.items():
        target_split = split_names.get(split_name)
        if target_split is None:
            continue
        for row_index, row in enumerate(rows):
            image = row["image"].convert("RGB")
            width, height = image.size
            label_lines: list[str] = []
            for bbox, raw_label_id in zip(row["bboxes"], row["labels"]):
                raw_label = label_feature.int2str(int(raw_label_id))
                normalized = _map_source_label(raw_label, label_map, power_classes)
                if normalized is None:
                    continue
                yolo_bbox = _xyxy_to_yolo_bbox(bbox, image_width=width, image_height=height)
                label_lines.append(
                    f"{class_index[normalized]} {yolo_bbox[0]:.6f} {yolo_bbox[1]:.6f} {yolo_bbox[2]:.6f} {yolo_bbox[3]:.6f}"
                )
            if not label_lines:
                continue
            file_stem = f"{source_slug}_{row_index:05d}"
            image_path = export_root / "images" / target_split / f"{file_stem}.jpg"
            label_path = export_root / "labels" / target_split / f"{file_stem}.txt"
            image.save(image_path, format="JPEG", quality=95)
            label_path.write_text("\n".join(label_lines), encoding="utf-8")

    (export_root / "dataset.yaml").write_text(
        yaml.safe_dump(
            {
                "path": str(export_root),
                "train": "images/train",
                "val": "images/val",
                "test": "images/test",
                "names": power_classes,
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def _load_class_names(yolo_yaml: Path) -> list[str]:
    payload = yaml.safe_load(yolo_yaml.read_text(encoding="utf-8")) or {}
    names = payload.get("names", [])
    if isinstance(names, dict):
        return [str(names[index]) for index in sorted(names)]
    return [str(item) for item in names]


def _find_image_for_label(label_path: Path) -> Path | None:
    stem = label_path.stem
    candidates: list[Path] = []

    parts = list(label_path.parts)
    for index, part in enumerate(parts[:-1]):
        if part != "labels":
            continue
        mirrored_dir = Path(*parts[:index], "images", *parts[index + 1 : -1])
        if mirrored_dir.exists():
            candidates.append(mirrored_dir)
        root_images = Path(*parts[:index], "images")
        if root_images.exists() and root_images not in candidates:
            candidates.append(root_images)
        break

    current = label_path.parent
    for ancestor in [current, *current.parents]:
        image_root = ancestor.parent / "images" if ancestor.name == "labels" else ancestor / "images"
        if image_root.exists() and image_root not in candidates:
            candidates.append(image_root)
    for image_root in candidates:
        for suffix in IMAGE_SUFFIXES:
            candidate = image_root / f"{stem}{suffix}"
            if candidate.exists():
                return candidate
        matches = list(image_root.rglob(f"{stem}.*"))
        for candidate in matches:
            if candidate.suffix.lower() in IMAGE_SUFFIXES:
                return candidate
    return None


def _extract_nested_archives(root: Path) -> None:
    pending = [path for path in root.rglob("*.zip")]
    while pending:
        archive_path = pending.pop(0)
        stamp = archive_path.with_suffix(".nested-extract")
        if stamp.exists():
            continue
        with zipfile.ZipFile(archive_path) as zf:
            zf.extractall(archive_path.parent)
        stamp.write_text("ok", encoding="utf-8")
        pending = [path for path in root.rglob("*.zip") if not path.with_suffix(".nested-extract").exists()]


def _parse_yolo_label_file(label_path: Path, class_names: list[str], power_classes: list[str]) -> list[dict[str, object]]:
    detections: list[dict[str, object]] = []
    for raw_line in label_path.read_text(encoding="utf-8").splitlines():
        parts = raw_line.strip().split()
        if len(parts) < 5:
            continue
        class_id = int(float(parts[0]))
        raw_class_name = class_names[class_id] if 0 <= class_id < len(class_names) else f"class_{class_id}"
        normalized = _normalize_component(raw_class_name, power_classes)
        if normalized is None:
            continue
        detections.append(
            {
                "class_name": normalized,
                "confidence": 1.0,
                "bbox": [float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4])],
            }
        )
    return detections


def _parse_pascal_voc_annotation(annotation_path: Path, power_classes: list[str]) -> tuple[Path | None, list[dict[str, object]]]:
    tree = ET.parse(annotation_path)
    root = tree.getroot()
    filename = root.findtext("filename")
    if not filename:
        return None, []

    image_path = annotation_path.parent.parent / "JPEGImages" / filename
    if not image_path.exists():
        alt = annotation_path.parent.parent / "images" / filename
        image_path = alt if alt.exists() else image_path
    if not image_path.exists():
        return None, []

    width = float(root.findtext("size/width", default="0") or 0)
    height = float(root.findtext("size/height", default="0") or 0)
    if width <= 0 or height <= 0:
        return None, []

    detections: list[dict[str, object]] = []
    for obj in root.findall("object"):
        raw_name = obj.findtext("name", default="")
        normalized = _normalize_component(raw_name, power_classes)
        if normalized is None:
            continue
        bbox_node = obj.find("bndbox")
        if bbox_node is None:
            continue
        xmin = float(bbox_node.findtext("xmin", default="0") or 0)
        ymin = float(bbox_node.findtext("ymin", default="0") or 0)
        xmax = float(bbox_node.findtext("xmax", default="0") or 0)
        ymax = float(bbox_node.findtext("ymax", default="0") or 0)
        detections.append(
            {
                "class_name": normalized,
                "confidence": 1.0,
                "bbox": _xyxy_to_yolo_bbox([xmin, ymin, xmax, ymax], image_width=int(width), image_height=int(height)),
            }
        )
    return image_path, detections


def _polygon_to_bbox(shape_attributes: dict[str, object]) -> list[float] | None:
    points_x = shape_attributes.get("all_points_x")
    points_y = shape_attributes.get("all_points_y")
    if not isinstance(points_x, list) or not isinstance(points_y, list) or not points_x or not points_y:
        return None
    min_x = min(float(value) for value in points_x)
    max_x = max(float(value) for value in points_x)
    min_y = min(float(value) for value in points_y)
    max_y = max(float(value) for value in points_y)
    width = max(max_x - min_x, 1.0)
    height = max(max_y - min_y, 1.0)

    # The original dataset images are 640x480.
    center_x = ((min_x + max_x) / 2.0) / 640.0
    center_y = ((min_y + max_y) / 2.0) / 480.0
    return [
        max(0.0, min(1.0, center_x)),
        max(0.0, min(1.0, center_y)),
        max(0.0, min(1.0, width / 640.0)),
        max(0.0, min(1.0, height / 480.0)),
    ]


def _normalize_component(raw_name: str, power_classes: list[str]) -> str | None:
    lower = raw_name.lower().replace("-", " ").replace("_", " ")
    tokens = [lower, *lower.split()]
    for token in tokens:
        alias = CLASS_COMPONENT_ALIASES.get(token)
        if alias in power_classes:
            return alias
    for candidate in power_classes:
        if candidate in lower:
            return candidate
    return None


def _map_source_label(raw_label: str, label_map: dict[str, str], power_classes: list[str]) -> str | None:
    if raw_label in label_map and label_map[raw_label] in power_classes:
        return label_map[raw_label]
    return _normalize_component(raw_label, power_classes)


def _xyxy_to_yolo_bbox(bbox: list[float], *, image_width: int, image_height: int) -> list[float]:
    min_x, min_y, max_x, max_y = (float(value) for value in bbox[:4])
    width = max(1.0, max_x - min_x)
    height = max(1.0, max_y - min_y)
    center_x = min_x + width / 2.0
    center_y = min_y + height / 2.0
    return [
        max(0.0, min(1.0, center_x / max(image_width, 1))),
        max(0.0, min(1.0, center_y / max(image_height, 1))),
        max(0.0, min(1.0, width / max(image_width, 1))),
        max(0.0, min(1.0, height / max(image_height, 1))),
    ]


def _map_classification_component(class_name: str) -> str:
    prefix = class_name.split("_", 1)[0]
    return CLASSIFICATION_COMPONENT_PREFIX.get(prefix, "line")


def _build_prompt_from_detections(detections: list[dict[str, object]]) -> str:
    classes = sorted({str(item["class_name"]) for item in detections})
    class_text = ", ".join(classes[:4])
    return f"realistic electric power inspection photo with {class_text}"


def _build_prompt_for_classification(class_name: str, component: str) -> str:
    clean_name = class_name.replace("_", " ")
    return f"electric transmission line inspection photo with {component} issue {clean_name}"


def _build_row(
    *,
    image_path: Path,
    prompt: str,
    detections: list[dict[str, object]],
    split: str,
    source_name: str,
    power_classes: list[str],
) -> dict[str, object]:
    with Image.open(image_path).convert("RGB") as image:
        image_features = _analyze_image(image=image, detections=detections)
    prompt_features = _analyze_prompt(prompt=prompt, detections=detections)
    targets = {
        "visual_fidelity": clamp_score(
            10.0
            + image_features["sharpness"] * 0.40
            + image_features["contrast"] * 0.20
            + image_features["exposure"] * 0.20
        ),
        "text_consistency": clamp_score(
            8.0
            + prompt_features["keyword_coverage"] * 0.58
            + prompt_features["electric_presence"] * 0.22
            + min(14.0, len(detections) * 2.0)
        ),
        "physical_plausibility": clamp_score(
            6.0
            + prompt_features["topology"] * 0.62
            + prompt_features["keyword_coverage"] * 0.16
            + min(12.0, len(detections) * 2.5)
        ),
        "composition_aesthetics": clamp_score(
            8.0
            + image_features["coverage"] * 0.28
            + image_features["balance"] * 0.28
            + image_features["contrast"] * 0.14
            + image_features["exposure"] * 0.16
        ),
    }
    return {
        "image_path": str(image_path),
        "prompt": prompt,
        "split": split,
        "source_name": source_name,
        "detections": detections,
        "yolo_features": _build_yolo_feature_vector(detections=detections, power_classes=power_classes),
        "targets": targets,
    }


def _build_yolo_feature_vector(*, detections: list[dict[str, object]], power_classes: list[str]) -> list[float]:
    class_index = {name: idx for idx, name in enumerate(power_classes)}
    counts = [0.0 for _ in power_classes]
    max_conf = [0.0 for _ in power_classes]
    areas: list[float] = []
    for item in detections:
        class_name = str(item["class_name"])
        if class_name not in class_index:
            continue
        idx = class_index[class_name]
        counts[idx] += 1.0
        max_conf[idx] = max(max_conf[idx], float(item["confidence"]))
        bbox = item["bbox"]
        areas.append(float(bbox[2]) * float(bbox[3]))
    max_count = max(sum(counts), 1.0)
    normalized_counts = [value / max_count for value in counts]
    coverage = float(sum(areas))
    mean_conf = float(sum(max_conf) / len(max_conf)) if max_conf else 0.0
    mean_area = float(sum(areas) / max(len(areas), 1))
    return normalized_counts + max_conf + [coverage, mean_conf, float(len(areas)), mean_area]


def _analyze_image(*, image: Image.Image, detections: list[dict[str, object]]) -> dict[str, float]:
    rgb = np.asarray(image.convert("RGB"), dtype=np.float32) / 255.0
    gray = rgb.mean(axis=2)
    sharpness_raw = float(np.mean(np.abs(np.diff(gray, axis=0))) + np.mean(np.abs(np.diff(gray, axis=1))))
    sharpness = clamp_score(min(100.0, sharpness_raw * 900.0))

    mean_luma = float(gray.mean())
    clipped_ratio = float(np.mean((gray < 0.03) | (gray > 0.97)))
    exposure = clamp_score(100.0 - abs(mean_luma - 0.52) * 180.0 - clipped_ratio * 180.0)
    contrast = clamp_score(min(100.0, float(gray.std()) * 400.0))

    if detections:
        weighted_area = 0.0
        weighted_x = 0.0
        weighted_y = 0.0
        for item in detections:
            _, _, width, height = item["bbox"]
            area = max(0.0, min(1.0, float(width) * float(height)))
            weight = area * max(0.3, float(item["confidence"]))
            weighted_area += area
            weighted_x += float(item["bbox"][0]) * weight
            weighted_y += float(item["bbox"][1]) * weight
        coverage_score = 100.0 - min(1.0, abs(weighted_area - 0.28) / 0.28) * 100.0
        centroid_x = weighted_x / max(weighted_area, 1e-6)
        centroid_y = weighted_y / max(weighted_area, 1e-6)
        center_offset = abs(centroid_x - 0.5) + abs(centroid_y - 0.5)
        balance_score = 100.0 - min(1.0, center_offset / 0.65) * 100.0
    else:
        coverage_score = 55.0
        balance_score = 60.0

    return {
        "sharpness": sharpness,
        "exposure": clamp_score(exposure),
        "contrast": contrast,
        "coverage": clamp_score(coverage_score),
        "balance": clamp_score(balance_score),
    }


def _analyze_prompt(*, prompt: str, detections: list[dict[str, object]]) -> dict[str, object]:
    lower_prompt = prompt.lower()
    prompt_tokens = set(token for token in lower_prompt.replace(",", " ").split() if token)
    expected_classes: set[str] = set()
    for phrase, aliases in PROMPT_CLASS_ALIASES.items():
        if phrase in lower_prompt:
            expected_classes.update(aliases)

    detected_classes = {
        str(item["class_name"])
        for item in detections
        if float(item.get("confidence", 0.0)) >= 0.20
    }
    matched_classes = expected_classes & detected_classes
    if expected_classes:
        keyword_coverage = 100.0 * len(matched_classes) / len(expected_classes)
    elif prompt_tokens & GENERIC_ELECTRIC_TERMS:
        keyword_coverage = 60.0 + min(40.0, len(detected_classes) * 10.0)
    else:
        keyword_coverage = 50.0

    electric_presence = 35.0 + min(55.0, len(detected_classes) * 8.0)
    topology = 35.0
    if {"tower", "line"}.issubset(detected_classes):
        topology += 24.0
    if {"tower", "insulator"}.issubset(detected_classes):
        topology += 14.0
    if {"breaker", "bus"}.issubset(detected_classes):
        topology += 16.0
    if {"frame", "switch"}.issubset(detected_classes):
        topology += 12.0
    topology += min(12.0, len(detected_classes) * 2.0)

    return {
        "expected_classes": sorted(expected_classes),
        "matched_classes": sorted(matched_classes),
        "keyword_coverage": clamp_score(keyword_coverage),
        "electric_presence": clamp_score(electric_presence if detected_classes else 30.0),
        "topology": clamp_score(topology if detected_classes else 28.0),
    }


def _group_splits(rows: list[dict[str, object]]) -> dict[str, list[dict[str, object]]]:
    grouped = {"train": [], "val": [], "test": []}
    for row in rows:
        split = str(row["split"])
        grouped.setdefault(split, []).append(row)
    return grouped


def _cap_rows(rows: list[dict[str, object]], limit: int | None) -> list[dict[str, object]]:
    if limit is None or len(rows) <= limit:
        return rows
    rng = random.Random(42)
    sampled = list(rows)
    rng.shuffle(sampled)
    return sampled[:limit]


def _infer_split(path: Path) -> str:
    lower_parts = [part.lower() for part in path.parts]
    if "train" in lower_parts:
        return "train"
    if "val" in lower_parts or "valid" in lower_parts or "validation" in lower_parts:
        return "val"
    if "test" in lower_parts:
        return "test"
    digest = int(hashlib.sha1(str(path).encode("utf-8")).hexdigest()[:8], 16) % 100
    if digest < 80:
        return "train"
    if digest < 90:
        return "val"
    return "test"
