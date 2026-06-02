from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path
import sys
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.settings import get_settings
from training.scoring.physical_parts import PHYSICAL_PART_CLASS_NAMES, PHYSICAL_PART_SPECS

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


def _image_paths(image_dir: Path) -> list[Path]:
    return sorted(path for path in image_dir.iterdir() if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES)


def _encode_image(path: Path) -> str:
    mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    content = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{content}"


def _physical_part_prompt() -> str:
    lines = [
        "你是电力行业图像标注助手。",
        "请只标注以下电力物理部件，输出 JSON，不要输出任何解释。",
        "返回格式:",
        '{"items":[{"image_name":"xxx","annotations":[{"class_name":"wind_blade","bbox_xyxy":[x1,y1,x2,y2]}]}]}',
        "只允许以下 class_name:",
    ]
    for item in PHYSICAL_PART_SPECS:
        lines.append(f"- {item.class_name}: {item.description} (parent={item.parent_class})")
    lines.extend(
        [
            "要求:",
            "1. bbox_xyxy 使用像素坐标，整数。",
            "2. 没有目标时 annotations 返回空数组。",
            "3. 不允许输出未在列表中的 class_name。",
            "4. 只标注清晰可见的部件，不要猜测。",
        ]
    )
    return "\n".join(lines)


def _validate_annotation_item(item: dict[str, Any], *, image_name: str) -> dict[str, Any]:
    class_name = str(item.get("class_name") or "").strip()
    if class_name not in PHYSICAL_PART_CLASS_NAMES:
        raise ValueError(f"unknown physical part class from model: {class_name}")
    bbox = item.get("bbox_xyxy")
    if not isinstance(bbox, list) or len(bbox) != 4:
        raise ValueError(f"invalid bbox for {image_name}: {bbox}")
    return {
        "class_name": class_name,
        "bbox_xyxy": [int(round(float(value))) for value in bbox],
    }


def _normalize_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    items = payload.get("items")
    if not isinstance(items, list):
        raise ValueError("model response missing items list")
    normalized: list[dict[str, Any]] = []
    for item in items:
        image_name = str(item.get("image_name") or "").strip()
        annotations = item.get("annotations") or []
        normalized.append(
            {
                "image_name": image_name,
                "annotations": [_validate_annotation_item(annotation, image_name=image_name) for annotation in annotations],
            }
        )
    return normalized


def _extract_json_text(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start != -1 and end != -1 and end >= start:
        return stripped[start : end + 1]
    return stripped


def _load_response_payload(response_text: str) -> dict[str, Any]:
    return json.loads(_extract_json_text(response_text))


def _default_openai_client(*, api_key: str, base_url: str):
    from openai import OpenAI

    return OpenAI(api_key=api_key, base_url=base_url.rstrip("/"))


def annotate_directory(
    *,
    image_dir: Path,
    output_root: Path,
    client: Any,
    model: str,
    batch_size: int = 4,
    annotation_filename: str = "annotations.jsonl",
    max_retries_per_batch: int = 2,
) -> dict[str, Any]:
    images = _image_paths(image_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    annotation_path = output_root / annotation_filename
    existing_rows: list[dict[str, Any]] = []
    completed_image_names: set[str] = set()
    if annotation_path.exists():
        for raw_line in annotation_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line:
                continue
            row = json.loads(line)
            existing_rows.append(row)
            completed_image_names.add(str(row.get("image_name") or "").strip())
    rows: list[dict[str, Any]] = list(existing_rows)
    pending_images = [path for path in images if path.name not in completed_image_names]

    for start in range(0, len(pending_images), max(1, batch_size)):
        batch = pending_images[start : start + max(1, batch_size)]
        input_items: list[dict[str, Any]] = [{"role": "system", "content": [{"type": "input_text", "text": _physical_part_prompt()}]}]
        for image_path in batch:
            input_items.append(
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": f"image_name={image_path.name}"},
                        {"type": "input_image", "image_url": _encode_image(image_path)},
                    ],
                }
            )
        last_error: Exception | None = None
        batch_rows: list[dict[str, Any]] | None = None
        for _ in range(max_retries_per_batch + 1):
            response = client.responses.create(model=model, input=input_items)
            try:
                payload = _load_response_payload(response.output_text)
                batch_rows = _normalize_payload(payload)
                break
            except (json.JSONDecodeError, ValueError) as exc:
                last_error = exc
                continue
        if batch_rows is None:
            assert last_error is not None
            raise last_error
        rows.extend(batch_rows)
        with annotation_path.open("a", encoding="utf-8") as handle:
            for row in batch_rows:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return {
        "annotation_path": str(annotation_path),
        "record_count": len(rows),
        "image_count": len(images),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Annotate electric physical parts with GPT-5.4 via OpenAI-compatible API.")
    parser.add_argument("--image-dir", required=True, help="Directory containing source images.")
    parser.add_argument("--output-root", required=True, help="Directory to write annotations.jsonl.")
    parser.add_argument("--model", default="gpt-5.4", help="OpenAI-compatible multimodal model name.")
    parser.add_argument("--batch-size", type=int, default=4, help="How many images to send per request.")
    parser.add_argument("--annotation-filename", default="annotations.jsonl", help="Output jsonl filename under output root.")
    parser.add_argument("--api-key", default=None, help="Override OpenAI-compatible API key.")
    parser.add_argument("--base-url", default=None, help="Override OpenAI-compatible base URL.")
    args = parser.parse_args()

    settings = get_settings()
    api_key = args.api_key or settings.openai_api_key
    base_url = args.base_url or settings.openai_base_url
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required for GPT physical part annotation.")
    if not base_url:
        raise RuntimeError("OPENAI_BASE_URL is required for GPT physical part annotation.")

    client = _default_openai_client(api_key=api_key, base_url=base_url)
    summary = annotate_directory(
        image_dir=Path(args.image_dir),
        output_root=Path(args.output_root),
        client=client,
        model=args.model,
        batch_size=args.batch_size,
        annotation_filename=args.annotation_filename,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
