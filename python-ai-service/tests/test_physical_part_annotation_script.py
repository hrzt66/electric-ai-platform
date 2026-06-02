from __future__ import annotations

import json
from pathlib import Path

from PIL import Image


class _FakeResponseClient:
    def __init__(self, payload: dict) -> None:
        self.payload = payload
        self.calls: list[dict] = []
        self.responses = self

    def create(self, **kwargs):
        self.calls.append(kwargs)
        text = json.dumps(self.payload, ensure_ascii=False)
        return type(
            "FakeResponse",
            (),
            {
                "output_text": text,
            },
        )()


class _FakeSequentialResponseClient:
    def __init__(self, payloads: list[str]) -> None:
        self.payloads = list(payloads)
        self.calls: list[dict] = []
        self.responses = self

    def create(self, **kwargs):
        self.calls.append(kwargs)
        text = self.payloads.pop(0)
        return type(
            "FakeResponse",
            (),
            {
                "output_text": text,
            },
        )()


def test_builds_physical_part_dataset_and_writes_jsonl(tmp_path) -> None:
    from scripts.annotate_physical_parts_with_gpt import annotate_directory

    image_dir = tmp_path / "images"
    image_dir.mkdir()
    image_path = image_dir / "wind.png"
    Image.new("RGB", (128, 128), color=(230, 236, 242)).save(image_path)

    client = _FakeResponseClient(
        {
            "items": [
                {
                    "image_name": "wind.png",
                    "annotations": [
                        {"class_name": "wind_blade", "bbox_xyxy": [36, 20, 74, 42]},
                    ],
                }
            ]
        }
    )

    output_root = tmp_path / "physical-parts"
    summary = annotate_directory(
        image_dir=image_dir,
        output_root=output_root,
        client=client,
        model="gpt-5.4",
        batch_size=1,
    )

    annotation_path = output_root / "annotations.jsonl"
    assert annotation_path.exists()
    rows = [json.loads(line) for line in annotation_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(rows) == 1
    assert rows[0]["image_name"] == "wind.png"
    assert rows[0]["annotations"][0]["class_name"] == "wind_blade"
    assert summary["record_count"] == 1
    assert client.calls


def test_rejects_unknown_physical_part_class_from_model(tmp_path) -> None:
    from scripts.annotate_physical_parts_with_gpt import annotate_directory

    image_dir = tmp_path / "images"
    image_dir.mkdir()
    image_path = image_dir / "tower.png"
    Image.new("RGB", (128, 128), color=(230, 236, 242)).save(image_path)

    client = _FakeResponseClient(
        {
            "items": [
                {
                    "image_name": "tower.png",
                    "annotations": [
                        {"class_name": "not_a_real_part", "bbox_xyxy": [10, 10, 40, 40]},
                    ],
                }
            ]
        }
    )

    try:
        annotate_directory(
            image_dir=image_dir,
            output_root=tmp_path / "physical-parts",
            client=client,
            model="gpt-5.4",
            batch_size=1,
        )
    except ValueError as exc:
        message = str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected unknown class to be rejected")

    assert "not_a_real_part" in message


def test_supports_custom_annotation_filename(tmp_path) -> None:
    from scripts.annotate_physical_parts_with_gpt import annotate_directory

    image_dir = tmp_path / "images"
    image_dir.mkdir()
    Image.new("RGB", (128, 128), color=(230, 236, 242)).save(image_dir / "wind.png")
    client = _FakeResponseClient(
        {
            "items": [
                {
                    "image_name": "wind.png",
                    "annotations": [],
                }
            ]
        }
    )

    output_root = tmp_path / "physical-parts"
    summary = annotate_directory(
        image_dir=image_dir,
        output_root=output_root,
        client=client,
        model="gpt-5.4",
        batch_size=1,
        annotation_filename="train_annotations.jsonl",
    )

    assert (output_root / "train_annotations.jsonl").exists()
    assert summary["annotation_path"].endswith("train_annotations.jsonl")


def test_resumes_and_appends_without_rewriting_existing_rows(tmp_path) -> None:
    from scripts.annotate_physical_parts_with_gpt import annotate_directory

    image_dir = tmp_path / "images"
    image_dir.mkdir()
    Image.new("RGB", (128, 128), color=(230, 236, 242)).save(image_dir / "a.png")
    Image.new("RGB", (128, 128), color=(230, 236, 242)).save(image_dir / "b.png")
    output_root = tmp_path / "physical-parts"
    output_root.mkdir()
    (output_root / "train_annotations.jsonl").write_text(
        '{"image_name":"a.png","annotations":[]}\n',
        encoding="utf-8",
    )

    client = _FakeResponseClient(
        {
            "items": [
                {
                    "image_name": "b.png",
                    "annotations": [],
                }
            ]
        }
    )

    summary = annotate_directory(
        image_dir=image_dir,
        output_root=output_root,
        client=client,
        model="gpt-5.4",
        batch_size=1,
        annotation_filename="train_annotations.jsonl",
    )

    rows = [
        json.loads(line)
        for line in (output_root / "train_annotations.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(rows) == 2
    assert [row["image_name"] for row in rows] == ["a.png", "b.png"]
    assert summary["record_count"] == 2


def test_recovers_json_payload_from_markdown_wrapped_response(tmp_path) -> None:
    from scripts.annotate_physical_parts_with_gpt import annotate_directory

    image_dir = tmp_path / "images"
    image_dir.mkdir()
    Image.new("RGB", (128, 128), color=(230, 236, 242)).save(image_dir / "wind.png")
    client = _FakeSequentialResponseClient(
        [
            '```json\n{"items":[{"image_name":"wind.png","annotations":[]}]}\n```',
        ]
    )

    summary = annotate_directory(
        image_dir=image_dir,
        output_root=tmp_path / "physical-parts",
        client=client,
        model="gpt-5.4",
        batch_size=1,
    )

    assert summary["record_count"] == 1


def test_retries_when_first_response_is_invalid_json(tmp_path) -> None:
    from scripts.annotate_physical_parts_with_gpt import annotate_directory

    image_dir = tmp_path / "images"
    image_dir.mkdir()
    Image.new("RGB", (128, 128), color=(230, 236, 242)).save(image_dir / "wind.png")
    client = _FakeSequentialResponseClient(
        [
            '{"items":[{"image_name":"wind.png","annotations":[}',  # invalid
            '{"items":[{"image_name":"wind.png","annotations":[]}]}',
        ]
    )

    summary = annotate_directory(
        image_dir=image_dir,
        output_root=tmp_path / "physical-parts",
        client=client,
        model="gpt-5.4",
        batch_size=1,
    )

    assert summary["record_count"] == 1
    assert len(client.calls) == 2


def test_default_openai_client_does_not_duplicate_v1_suffix(monkeypatch) -> None:
    from scripts.annotate_physical_parts_with_gpt import _default_openai_client

    captured: dict[str, object] = {}

    class FakeOpenAI:
        def __init__(self, **kwargs) -> None:
            captured.update(kwargs)

    monkeypatch.setattr("openai.OpenAI", FakeOpenAI)

    _default_openai_client(
        api_key="test-key",
        base_url="https://geekspace.cloud/v1",
    )

    assert captured["api_key"] == "test-key"
    assert captured["base_url"] == "https://geekspace.cloud/v1"
