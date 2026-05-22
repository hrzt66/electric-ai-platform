from __future__ import annotations

import json
from pathlib import Path


def test_clean_physical_part_annotations_drops_invalid_and_clips_boxes(tmp_path) -> None:
    from scripts.clean_physical_part_annotations import clean_annotation_file

    annotation_path = tmp_path / "train_annotations.jsonl"
    annotation_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "image_name": "sample.png",
                        "annotations": [
                            {"class_name": "tower_wire", "bbox_xyxy": [-10, 5, 600, 520]},
                            {"class_name": "tower_crossarm", "bbox_xyxy": [50, 50, 50, 90]},
                            {"class_name": "wind_blade", "bbox_xyxy": [10, 20, 80, 40]},
                        ],
                    },
                    ensure_ascii=False,
                )
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    report = clean_annotation_file(annotation_path=annotation_path, image_size=(512, 512))

    rows = [json.loads(line) for line in annotation_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(rows) == 1
    annotations = rows[0]["annotations"]
    assert len(annotations) == 2
    assert annotations[0]["bbox_xyxy"] == [0, 5, 511, 511]
    assert annotations[1]["class_name"] == "wind_blade"
    assert report["clipped_boxes"] == 1
    assert report["dropped_boxes"] == 1
