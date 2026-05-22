from __future__ import annotations

import csv
import json
import shutil
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path

import yaml

IMAGE_SUFFIXES = (".jpg", ".jpeg", ".png", ".bmp", ".webp")
DEFAULT_SCORING_TARGET_CLASSES = [
    "substation_primary",
    "transmission_tower",
    "insulator_string",
    "wind_turbine",
    "solar_panel",
    "dam",
]
DEFAULT_IMAGE2_TO_SCORING_CLASS_MAPPING = {
    "photovoltaic_farm": "solar_panel",
    "transmission_tower": "transmission_tower",
    "wind_turbine": "wind_turbine",
    "dam": "dam",
    "substation": "substation_primary",
}
MANIFEST_SOURCE_NAME_BY_PREFIX = {
    "0": "substation-object-detection-yolo",
    "1": "powerline-components-and-faults",
    "2": "dior-superclasses",
    "3": "wind-turbine-aerial",
    "4": "solar-plants-brazil-yolo",
}
EXACT_SOURCE_NAME_BY_PREFIX = {
    "0": "substation-object-detection",
    "1": "powerline-components-and-faults",
    "2": "dior-superclasses",
    "3": "wind-turbine-aerial",
    "4": "solar-plants-brazil-yolo",
}


def canonicalize_yolo_label_line(raw_line: str) -> tuple[str | None, dict[str, int]]:
    stats = {
        "lines_seen": 1,
        "lines_kept": 0,
        "lines_dropped": 0,
        "dropped_bad_format": 0,
        "dropped_parse_error": 0,
        "dropped_zero_area": 0,
        "boxes_clipped": 0,
    }

    line = raw_line.strip()
    if not line:
        stats["lines_dropped"] += 1
        stats["dropped_bad_format"] += 1
        return None, stats

    parts = line.split()
    if len(parts) != 5:
        stats["lines_dropped"] += 1
        stats["dropped_bad_format"] += 1
        return None, stats

    try:
        class_id = int(float(parts[0]))
        center_x, center_y, width, height = (float(value) for value in parts[1:])
    except ValueError:
        stats["lines_dropped"] += 1
        stats["dropped_parse_error"] += 1
        return None, stats

    if class_id < 0 or width <= 0.0 or height <= 0.0:
        stats["lines_dropped"] += 1
        stats["dropped_zero_area"] += 1
        return None, stats

    min_x = center_x - width / 2.0
    min_y = center_y - height / 2.0
    max_x = center_x + width / 2.0
    max_y = center_y + height / 2.0

    clipped_min_x = min(max(min_x, 0.0), 1.0)
    clipped_min_y = min(max(min_y, 0.0), 1.0)
    clipped_max_x = min(max(max_x, 0.0), 1.0)
    clipped_max_y = min(max(max_y, 0.0), 1.0)

    if (
        clipped_min_x != min_x
        or clipped_min_y != min_y
        or clipped_max_x != max_x
        or clipped_max_y != max_y
    ):
        stats["boxes_clipped"] += 1

    clipped_width = clipped_max_x - clipped_min_x
    clipped_height = clipped_max_y - clipped_min_y
    if clipped_width <= 0.0 or clipped_height <= 0.0:
        stats["lines_dropped"] += 1
        stats["dropped_zero_area"] += 1
        return None, stats

    clipped_center_x = clipped_min_x + clipped_width / 2.0
    clipped_center_y = clipped_min_y + clipped_height / 2.0

    stats["lines_kept"] += 1
    return (
        f"{class_id} {clipped_center_x:.6f} {clipped_center_y:.6f} {clipped_width:.6f} {clipped_height:.6f}",
        stats,
    )


def clean_yolo_dataset(merged_root: Path) -> dict[str, int]:
    stats = {
        "files_scanned": 0,
        "files_changed": 0,
        "label_files_removed": 0,
        "images_removed": 0,
        "duplicates_removed": 0,
        "lines_seen": 0,
        "lines_kept": 0,
        "lines_dropped": 0,
        "dropped_bad_format": 0,
        "dropped_parse_error": 0,
        "dropped_zero_area": 0,
        "boxes_clipped": 0,
    }

    for split in ("train", "val", "test"):
        label_dir = merged_root / "labels" / split
        if not label_dir.exists():
            continue
        for label_path in sorted(label_dir.glob("*.txt")):
            stats["files_scanned"] += 1
            original_lines = [line.strip() for line in label_path.read_text(encoding="utf-8").splitlines() if line.strip()]
            cleaned_lines: list[str] = []
            seen_lines: set[str] = set()

            for raw_line in original_lines:
                cleaned_line, line_stats = canonicalize_yolo_label_line(raw_line)
                _merge_stats(stats, line_stats)
                if cleaned_line is None:
                    continue
                if cleaned_line in seen_lines:
                    stats["duplicates_removed"] += 1
                    continue
                seen_lines.add(cleaned_line)
                cleaned_lines.append(cleaned_line)

            if not cleaned_lines:
                image_path = _find_related_image(label_path)
                label_path.unlink(missing_ok=True)
                stats["label_files_removed"] += 1
                stats["files_changed"] += 1
                if image_path is not None and image_path.exists():
                    image_path.unlink()
                    stats["images_removed"] += 1
                continue

            if cleaned_lines != original_lines:
                label_path.write_text("\n".join(cleaned_lines), encoding="utf-8")
                stats["files_changed"] += 1

    return stats


def rebuild_yolo_merged_artifacts(training_root: Path) -> dict[str, object]:
    merged_root = training_root / "yolo-merged"
    manifest_csv = training_root / "yolo_merged_image_manifest.csv"
    exact_csv = training_root / "yolo_merged_exact_images_current_run.csv"
    source_summary_json = training_root / "yolo_merged_source_summary.json"
    exact_summary_json = training_root / "yolo_merged_exact_images_current_run_summary.json"

    manifest_metadata = {
        _normalize_path_key(str(row.get("merged_image", ""))): row
        for row in _filter_rows_to_existing_examples(_read_csv_rows(manifest_csv))
    }
    exact_metadata = {
        _normalize_path_key(str(row.get("merged_image", ""))): row
        for row in _filter_rows_to_existing_examples(_read_csv_rows(exact_csv))
    }
    actual_examples = _scan_existing_examples(merged_root)

    manifest_rows = [_build_manifest_row(example, manifest_metadata.get(example["merged_image_key"])) for example in actual_examples]
    exact_rows = [_build_exact_row(example, exact_metadata.get(example["merged_image_key"])) for example in actual_examples]

    _write_csv_rows(
        manifest_csv,
        fieldnames=["split", "merged_image", "dataset_index", "source_name", "original_image", "original_label"],
        rows=_sorted_rows(manifest_rows),
    )
    _write_csv_rows(
        exact_csv,
        fieldnames=["split", "merged_image", "prefix", "source_name", "original_image", "original_label"],
        rows=_sorted_rows(exact_rows),
    )

    active_classes = _read_active_classes(merged_root / "dataset.yaml")
    counts_by_source = _build_counts_by_source(manifest_rows)
    exact_counts_by_source = _build_counts_by_source(exact_rows)
    counts_total = _build_counts_total(manifest_rows)
    source_datasets = _build_source_dataset_entries(manifest_rows)

    source_summary = {
        "merged_root": str(merged_root),
        "active_classes": active_classes,
        "yolo_datasets": source_datasets,
        "counts_by_source": counts_by_source,
        "counts_total": counts_total,
        "manifest_csv": str(manifest_csv),
    }
    source_summary_json.write_text(json.dumps(source_summary, ensure_ascii=False, indent=2), encoding="utf-8")

    exact_summary = {
        "merged_root": str(merged_root / "images"),
        "csv": str(exact_csv),
        "counts_by_source": exact_counts_by_source,
        "total_rows": len(exact_rows),
    }
    exact_summary_json.write_text(json.dumps(exact_summary, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "merged_root": str(merged_root),
        "active_classes": active_classes,
        "counts_total": counts_total,
        "counts_by_source": counts_by_source,
        "manifest_rows": len(manifest_rows),
        "exact_rows": len(exact_rows),
    }


def import_yolo_dataset_with_class_mapping(
    *,
    source_yaml: Path,
    target_root: Path,
    source_tag: str,
    target_classes: list[str],
    class_mapping: dict[str, str],
) -> dict[str, object]:
    source_payload = yaml.safe_load(source_yaml.read_text(encoding="utf-8")) or {}
    source_root = Path(source_payload.get("path") or source_yaml.resolve().parent)
    if not source_root.is_absolute():
        source_root = (source_yaml.resolve().parent / source_root).resolve()
    source_class_names = _read_active_classes(source_yaml)
    target_class_ids = {class_name: index for index, class_name in enumerate(target_classes)}
    source_to_target_ids: dict[int, int] = {}
    for source_index, source_name in enumerate(source_class_names):
        mapped_name = class_mapping.get(source_name)
        if mapped_name is None or mapped_name not in target_class_ids:
            continue
        source_to_target_ids[source_index] = target_class_ids[mapped_name]

    if target_root.exists():
        shutil.rmtree(target_root)
    for split in ("train", "val", "test"):
        (target_root / "images" / split).mkdir(parents=True, exist_ok=True)
        (target_root / "labels" / split).mkdir(parents=True, exist_ok=True)

    report = {
        "source_yaml": str(source_yaml.resolve()),
        "source_root": str(source_root),
        "target_root": str(target_root),
        "source_tag": source_tag,
        "target_classes": list(target_classes),
        "copied_images": 0,
        "dropped_images": 0,
        "kept_boxes": 0,
        "dropped_boxes": 0,
        "mapped_counts_by_target": {},
    }
    mapped_counts_by_target: dict[str, int] = defaultdict(int)

    for split in ("train", "val", "test"):
        image_dir = source_root / "images" / split
        if not image_dir.exists():
            continue

        for image_path in sorted(image_dir.iterdir()):
            if not image_path.is_file():
                continue
            if image_path.suffix.lower() not in IMAGE_SUFFIXES:
                continue

            label_path = source_root / "labels" / split / f"{image_path.stem}.txt"
            if not label_path.exists():
                continue

            kept_lines: list[str] = []
            for raw_line in label_path.read_text(encoding="utf-8").splitlines():
                cleaned_line, _ = canonicalize_yolo_label_line(raw_line)
                if cleaned_line is None:
                    report["dropped_boxes"] += 1
                    continue

                parts = cleaned_line.split()
                source_class_id = int(parts[0])
                target_class_id = source_to_target_ids.get(source_class_id)
                if target_class_id is None:
                    report["dropped_boxes"] += 1
                    continue

                target_class_name = target_classes[target_class_id]
                mapped_counts_by_target[target_class_name] += 1
                kept_lines.append(" ".join([str(target_class_id), *parts[1:]]))
                report["kept_boxes"] += 1

            if not kept_lines:
                report["dropped_images"] += 1
                continue

            target_stem = f"{source_tag}_{image_path.stem}"
            target_image_path = target_root / "images" / split / f"{target_stem}{image_path.suffix.lower()}"
            target_label_path = target_root / "labels" / split / f"{target_stem}.txt"
            shutil.copy2(image_path, target_image_path)
            target_label_path.write_text("\n".join(kept_lines), encoding="utf-8")
            report["copied_images"] += 1

    dataset_yaml = target_root / "dataset.yaml"
    dataset_yaml.write_text(
        "\n".join(
            [
                f"path: {target_root}",
                "train: images/train",
                "val: images/val",
                "test: images/test",
                "names:",
                *[f"  - {class_name}" for class_name in target_classes],
            ]
        ),
        encoding="utf-8",
    )

    report["mapped_counts_by_target"] = dict(sorted(mapped_counts_by_target.items()))
    (target_root / "import_summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def import_external_image2_yolo_run_for_scoring(
    *,
    source_run_dir: Path,
    target_roots: list[Path],
    bundle_dir: Path,
    target_classes: list[str] | None = None,
    class_mapping: dict[str, str] | None = None,
) -> dict[str, object]:
    resolved_source_run_dir = source_run_dir.resolve()
    source_yaml = resolved_source_run_dir / "dataset.yaml"
    best_weight_path = resolved_source_run_dir / "best.pt"

    if not source_yaml.exists():
        raise FileNotFoundError(f"missing dataset.yaml under external YOLO run: {source_yaml}")
    if not best_weight_path.exists():
        raise FileNotFoundError(f"missing best.pt under external YOLO run: {best_weight_path}")

    source_payload = yaml.safe_load(source_yaml.read_text(encoding="utf-8")) or {}
    source_dataset_root = Path(source_payload.get("path") or source_yaml.parent)
    if not source_dataset_root.is_absolute():
        source_dataset_root = (source_yaml.parent / source_dataset_root).resolve()

    mapped_classes = list(target_classes or DEFAULT_SCORING_TARGET_CLASSES)
    mapping_rules = dict(class_mapping or DEFAULT_IMAGE2_TO_SCORING_CLASS_MAPPING)
    source_tag = resolved_source_run_dir.name

    dataset_reports = [
        import_yolo_dataset_with_class_mapping(
            source_yaml=source_yaml,
            target_root=target_root,
            source_tag=source_tag,
            target_classes=mapped_classes,
            class_mapping=mapping_rules,
        )
        for target_root in target_roots
    ]

    bundle_dir.mkdir(parents=True, exist_ok=True)
    archived_weight_path = bundle_dir / f"yolo_aux.{source_tag}.pt"
    active_weight_path = bundle_dir / "yolo_aux.pt"
    shutil.copy2(best_weight_path, archived_weight_path)
    shutil.copy2(best_weight_path, active_weight_path)

    report = {
        "source_run_dir": str(resolved_source_run_dir),
        "source_dataset_yaml": str(source_yaml.resolve()),
        "source_dataset_root": str(source_dataset_root),
        "source_weight_path": str(best_weight_path.resolve()),
        "archived_weight_path": str(archived_weight_path.resolve()),
        "active_weight_path": str(active_weight_path.resolve()),
        "target_classes": mapped_classes,
        "class_mapping": mapping_rules,
        "dataset_reports": dataset_reports,
    }
    return report


def build_high_map_variant(
    *,
    merged_root: Path,
    variant_root: Path,
    max_repeat_by_class: dict[str, int],
    min_box_area: float,
    variant_name: str = "high_map_v1",
) -> dict[str, object]:
    clean_yolo_dataset(merged_root)

    if variant_root.exists():
        shutil.rmtree(variant_root)
    for split in ("train", "val", "test"):
        (variant_root / "images" / split).mkdir(parents=True, exist_ok=True)
        (variant_root / "labels" / split).mkdir(parents=True, exist_ok=True)

    class_names = _read_active_classes(merged_root / "dataset.yaml")
    bounded_repeats = {
        class_name: max(1, int(max_repeat_by_class.get(class_name, 1)))
        for class_name in class_names
    }
    split_counts = {"train": 0, "val": 0, "test": 0}
    original_train_image_count = 0

    for split in ("train", "val", "test"):
        image_dir = merged_root / "images" / split
        if not image_dir.exists():
            continue
        for image_path in sorted(image_dir.iterdir()):
            if not image_path.is_file():
                continue
            label_path = _label_path_for_image(image_path)
            if not label_path.exists():
                continue

            filter_small_boxes = split == "train"
            label_lines = _read_variant_label_lines(label_path, min_box_area=min_box_area, filter_small_boxes=filter_small_boxes)
            if not label_lines:
                continue

            repeat_count = 1
            if split == "train":
                original_train_image_count += 1
                class_ids = _read_class_ids(label_lines)
                repeat_count = max((bounded_repeats.get(class_names[class_id], 1) for class_id in class_ids if class_id < len(class_names)), default=1)

            for copy_index in range(repeat_count):
                stem_suffix = "" if copy_index == 0 else f"__r{copy_index + 1}"
                target_image = variant_root / "images" / split / f"{image_path.stem}{stem_suffix}{image_path.suffix}"
                target_label = variant_root / "labels" / split / f"{image_path.stem}{stem_suffix}.txt"
                shutil.copy2(image_path, target_image)
                target_label.write_text("\n".join(label_lines), encoding="utf-8")
                split_counts[split] += 1

    dataset_yaml = variant_root / "dataset.yaml"
    dataset_yaml.write_text(
        "\n".join(
            [
                f"path: {variant_root}",
                "train: images/train",
                "val: images/val",
                "test: images/test",
                "names:",
                *[f"  - {class_name}" for class_name in class_names],
            ]
        ),
        encoding="utf-8",
    )
    report = {
        "variant_name": variant_name,
        "merged_root": str(merged_root),
        "variant_root": str(variant_root),
        "dataset_yaml": str(dataset_yaml),
        "original_train_image_count": original_train_image_count,
        "train_image_count": split_counts["train"],
        "val_image_count": split_counts["val"],
        "test_image_count": split_counts["test"],
        "repeat_factors": bounded_repeats,
        "min_box_area": min_box_area,
    }
    (variant_root / "high_map_variant_summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def _find_related_image(label_path: Path) -> Path | None:
    image_dir = label_path.parent.parent.parent / "images" / label_path.parent.name
    for suffix in IMAGE_SUFFIXES:
        candidate = image_dir / f"{label_path.stem}{suffix}"
        if candidate.exists():
            return candidate
    return None


def _merge_stats(target: dict[str, int], delta: dict[str, int]) -> None:
    for key, value in delta.items():
        target[key] = int(target.get(key, 0)) + int(value)


def _read_variant_label_lines(label_path: Path, *, min_box_area: float, filter_small_boxes: bool) -> list[str]:
    kept: list[str] = []
    for raw_line in label_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) != 5:
            continue
        if filter_small_boxes:
            try:
                width = float(parts[3])
                height = float(parts[4])
            except ValueError:
                continue
            if width * height < min_box_area:
                continue
        kept.append(line)
    return kept


def _read_class_ids(label_lines: list[str]) -> set[int]:
    class_ids: set[int] = set()
    for line in label_lines:
        parts = line.split()
        if not parts:
            continue
        try:
            class_ids.add(int(float(parts[0])))
        except ValueError:
            continue
    return class_ids


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as file:
        return [dict(row) for row in csv.DictReader(file)]


def _write_csv_rows(path: Path, *, fieldnames: list[str], rows: Iterable[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in fieldnames})


def _filter_rows_to_existing_examples(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    kept: list[dict[str, str]] = []
    for row in rows:
        image_path = Path(str(row.get("merged_image", "")))
        if not image_path.exists():
            continue
        label_path = _label_path_for_image(image_path)
        if not label_path.exists():
            continue
        if not label_path.read_text(encoding="utf-8").strip():
            continue
        kept.append(row)
    return kept


def _scan_existing_examples(merged_root: Path) -> list[dict[str, str]]:
    examples: list[dict[str, str]] = []
    for split in ("train", "val", "test"):
        image_dir = merged_root / "images" / split
        if not image_dir.exists():
            continue
        for image_path in sorted(image_dir.iterdir()):
            if not image_path.is_file():
                continue
            label_path = _label_path_for_image(image_path)
            if not label_path.exists():
                continue
            if not label_path.read_text(encoding="utf-8").strip():
                continue
            prefix, _, remainder = image_path.stem.partition("_")
            examples.append(
                {
                    "split": split,
                    "merged_image": str(image_path.resolve()),
                    "merged_image_key": _normalize_path_key(str(image_path)),
                    "prefix": prefix,
                    "stem_remainder": remainder,
                }
            )
    return examples


def _build_manifest_row(example: dict[str, str], metadata: dict[str, str] | None) -> dict[str, str]:
    source_name = _pick_source_name(example, metadata, source_name_by_prefix=MANIFEST_SOURCE_NAME_BY_PREFIX)
    return {
        "split": example["split"],
        "merged_image": example["merged_image"],
        "dataset_index": str((metadata or {}).get("dataset_index") or example["prefix"]),
        "source_name": source_name,
        "original_image": str((metadata or {}).get("original_image") or ""),
        "original_label": str((metadata or {}).get("original_label") or ""),
    }


def _build_exact_row(example: dict[str, str], metadata: dict[str, str] | None) -> dict[str, str]:
    source_name = _pick_source_name(example, metadata, source_name_by_prefix=EXACT_SOURCE_NAME_BY_PREFIX)
    return {
        "split": example["split"],
        "merged_image": example["merged_image"],
        "prefix": str((metadata or {}).get("prefix") or example["prefix"]),
        "source_name": source_name,
        "original_image": str((metadata or {}).get("original_image") or ""),
        "original_label": str((metadata or {}).get("original_label") or ""),
    }


def _pick_source_name(
    example: dict[str, str],
    metadata: dict[str, str] | None,
    *,
    source_name_by_prefix: dict[str, str],
) -> str:
    prefix = str(example.get("prefix", ""))
    source_name = str((metadata or {}).get("source_name") or "").strip()
    if source_name and _metadata_has_source_provenance(metadata):
        return source_name

    if prefix in source_name_by_prefix:
        return source_name_by_prefix[prefix]

    if source_name:
        return source_name

    remainder = example.get("stem_remainder", "")
    if remainder:
        inferred = remainder.rsplit("_", 1)[0]
        if inferred and not inferred.isdigit():
            return inferred
    return f"prefix-{example['prefix']}"


def _metadata_has_source_provenance(metadata: dict[str, str] | None) -> bool:
    if metadata is None:
        return False
    return bool(str(metadata.get("original_image") or "").strip() or str(metadata.get("original_label") or "").strip())


def _sorted_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    split_order = {"train": 0, "val": 1, "test": 2}
    return sorted(rows, key=lambda row: (split_order.get(str(row.get("split", "")), 99), str(row.get("merged_image", ""))))


def _normalize_path_key(raw_path: str) -> str:
    if not raw_path:
        return ""
    return str(Path(raw_path).expanduser().resolve(strict=False))


def _label_path_for_image(image_path: Path) -> Path:
    return image_path.parent.parent.parent / "labels" / image_path.parent.name / f"{image_path.stem}.txt"


def _read_active_classes(dataset_yaml: Path) -> list[str]:
    if not dataset_yaml.exists():
        return []
    payload = yaml.safe_load(dataset_yaml.read_text(encoding="utf-8")) or {}
    names = payload.get("names", [])
    if isinstance(names, dict):
        return [str(names[index]) for index in sorted(names)]
    return [str(item) for item in names]


def _build_counts_by_source(rows: list[dict[str, str]]) -> dict[str, dict[str, int]]:
    counts: dict[str, dict[str, int]] = {}
    for row in rows:
        source_name = str(row.get("source_name", "unknown"))
        split = str(row.get("split", "train"))
        counts.setdefault(source_name, {"train": 0, "val": 0, "test": 0})
        counts[source_name][split] = counts[source_name].get(split, 0) + 1
    return counts


def _build_counts_total(rows: list[dict[str, str]]) -> dict[str, int]:
    totals = {"train": 0, "val": 0, "test": 0}
    for row in rows:
        split = str(row.get("split", "train"))
        totals[split] = totals.get(split, 0) + 1
    return totals


def _build_source_dataset_entries(rows: list[dict[str, str]]) -> list[dict[str, str | int | None]]:
    grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[(str(row.get("dataset_index", "")), str(row.get("source_name", "")))].append(row)

    entries: list[dict[str, str | int | None]] = []
    for (dataset_index, source_name), grouped_rows in sorted(grouped.items(), key=lambda item: item[0][0]):
        sample_row = grouped_rows[0]
        dataset_yaml = _find_dataset_yaml(sample_row)
        dataset_root = str(dataset_yaml.parent) if dataset_yaml is not None else None
        entry: dict[str, str | int | None] = {
            "dataset_index": int(dataset_index) if dataset_index.isdigit() else dataset_index,
            "dataset_yaml": str(dataset_yaml) if dataset_yaml is not None else None,
            "dataset_root": dataset_root,
            "source_name": source_name,
            "train_rel": _infer_split_relative(sample_row=grouped_rows, dataset_root=dataset_root, split="train"),
            "val_rel": _infer_split_relative(sample_row=grouped_rows, dataset_root=dataset_root, split="val"),
            "test_rel": _infer_split_relative(sample_row=grouped_rows, dataset_root=dataset_root, split="test"),
        }
        entries.append(entry)
    return entries


def _find_dataset_yaml(row: dict[str, str]) -> Path | None:
    for key in ("original_image", "original_label"):
        value = row.get(key)
        if not value:
            continue
        current = Path(value).parent
        for parent in (current, *current.parents):
            for candidate_name in ("dataset.yaml", "data.yaml"):
                candidate = parent / candidate_name
                if candidate.exists():
                    return candidate
    return None


def _infer_split_relative(*, sample_row: list[dict[str, str]], dataset_root: str | None, split: str) -> str | None:
    if dataset_root is None:
        return None
    root = Path(dataset_root)
    for row in sample_row:
        if str(row.get("split")) != split:
            continue
        image_path = Path(str(row.get("original_image", "")))
        try:
            return str(image_path.parent.relative_to(root))
        except ValueError:
            return None
    return None
