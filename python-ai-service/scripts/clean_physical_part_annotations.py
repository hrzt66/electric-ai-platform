from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _normalize_box(bbox_xyxy: list[float], *, width: int, height: int) -> tuple[list[int] | None, bool]:
    x1, y1, x2, y2 = [int(round(float(value))) for value in bbox_xyxy]
    clipped = False
    if x1 < 0:
        x1 = 0
        clipped = True
    if y1 < 0:
        y1 = 0
        clipped = True
    if x2 >= width:
        x2 = width - 1
        clipped = True
    if y2 >= height:
        y2 = height - 1
        clipped = True
    if x2 <= x1 or y2 <= y1:
        return None, clipped
    return [x1, y1, x2, y2], clipped


def clean_annotation_file(*, annotation_path: Path, image_size: tuple[int, int]) -> dict[str, Any]:
    width, height = image_size
    cleaned_rows: list[dict[str, Any]] = []
    clipped_boxes = 0
    dropped_boxes = 0
    for raw_line in annotation_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        row = json.loads(line)
        annotations: list[dict[str, Any]] = []
        for annotation in row.get("annotations", []):
            normalized, clipped = _normalize_box(list(annotation["bbox_xyxy"]), width=width, height=height)
            if clipped:
                clipped_boxes += 1
            if normalized is None:
                dropped_boxes += 1
                continue
            annotations.append(
                {
                    "class_name": str(annotation["class_name"]),
                    "bbox_xyxy": normalized,
                }
            )
        cleaned_rows.append(
            {
                "image_name": str(row["image_name"]),
                "annotations": annotations,
            }
        )
    annotation_path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in cleaned_rows) + ("\n" if cleaned_rows else ""),
        encoding="utf-8",
    )
    return {
        "annotation_path": str(annotation_path),
        "row_count": len(cleaned_rows),
        "clipped_boxes": clipped_boxes,
        "dropped_boxes": dropped_boxes,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean GPT physical part annotations by clipping and dropping invalid boxes.")
    parser.add_argument("--annotation-path", required=True)
    parser.add_argument("--width", type=int, default=512)
    parser.add_argument("--height", type=int, default=512)
    args = parser.parse_args()
    report = clean_annotation_file(
        annotation_path=Path(args.annotation_path),
        image_size=(args.width, args.height),
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
