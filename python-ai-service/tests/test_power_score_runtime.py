import json

import torch
from PIL import Image

from app.runtimes.scorers.power_score_runtime import (
    DEFAULT_TOTAL_WEIGHTS,
    PowerScoreRuntime,
    calibrate_student_scores,
)
from training.scoring.modeling import FourDimScoreModel


def _write_student_bundle(tmp_path):
    bundle_dir = tmp_path / "electric-score-v2"
    bundle_dir.mkdir()
    config = {
        "runtime_type": "student",
        "image_size": 96,
        "targets": [
            "visual_fidelity",
            "text_consistency",
            "physical_plausibility",
            "composition_aesthetics",
        ],
        "classes": [
            "capacitor",
            "bus",
            "pipe",
            "filter",
            "gis",
            "bushing",
            "switch",
            "line",
            "pt",
            "breaker",
            "arrester",
            "insulator",
            "ct",
            "tower",
            "frame",
        ],
        "total_weights": DEFAULT_TOTAL_WEIGHTS,
        "yolo_feature_dim": 34,
    }
    (bundle_dir / "bundle_config.json").write_text(json.dumps(config), encoding="utf-8")
    (bundle_dir / "vocab.json").write_text(json.dumps({"<unk>": 0, "electric": 1, "tower": 2, "insulator": 3}), encoding="utf-8")

    model = FourDimScoreModel(vocab_size=4, yolo_feature_dim=34, target_dim=4)
    torch.save(model.state_dict(), bundle_dir / "student_best.pt")
    return bundle_dir


class FixedStudentModel:
    def __init__(self, outputs: list[float]) -> None:
        self._outputs = torch.tensor([outputs], dtype=torch.float32)

    def __call__(self, images, prompt_ids, prompt_offsets, yolo_features):
        return self._outputs


class DictDetectionYolo:
    def __init__(self, detections: list[dict]) -> None:
        self._detections = detections
        self.calls: list[dict] = []

    def predict(self, **kwargs):
        self.calls.append(kwargs)
        return list(self._detections)


def _build_runtime_with_injected_student(tmp_path, *, detections: list[dict], outputs: list[float]) -> tuple[PowerScoreRuntime, str]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    image_path = tmp_path / "sample.png"
    Image.new("RGB", (96, 96), color=(128, 132, 140)).save(image_path)
    bundle_dir = _write_student_bundle(tmp_path)
    runtime = PowerScoreRuntime(
        bundle_dir,
        device="cpu",
        yolo_runtime=DictDetectionYolo(detections),
        image_check_dir=tmp_path / "image_check",
    )
    runtime._config = json.loads((bundle_dir / "bundle_config.json").read_text(encoding="utf-8"))
    runtime._vocab = {
        "<unk>": 0,
        "electric": 1,
        "tower": 2,
        "insulator": 3,
        "line": 4,
        "bus": 5,
        "switch": 6,
    }
    runtime._transform = lambda image: torch.zeros((3, 96, 96), dtype=torch.float32)
    runtime._model = FixedStudentModel(outputs)
    return runtime, str(image_path)


def test_self_trained_runtime_uses_text_consistency_priority_weights() -> None:
    assert DEFAULT_TOTAL_WEIGHTS == {
        "visual_fidelity": 0.21,
        "text_consistency": 0.37,
        "physical_plausibility": 0.24,
        "composition_aesthetics": 0.18,
    }


def test_student_score_calibration_lifts_low_mid_band_scores() -> None:
    raw_scores = {
        "visual_fidelity": 48.01,
        "text_consistency": 35.17,
        "physical_plausibility": 32.91,
        "composition_aesthetics": 65.85,
    }

    calibrated = calibrate_student_scores(raw_scores, DEFAULT_TOTAL_WEIGHTS)

    assert calibrated["visual_fidelity"] > raw_scores["visual_fidelity"]
    assert calibrated["text_consistency"] > raw_scores["text_consistency"]
    assert calibrated["physical_plausibility"] > raw_scores["physical_plausibility"]
    assert calibrated["composition_aesthetics"] >= raw_scores["composition_aesthetics"]
    assert calibrated["visual_fidelity"] >= 56.0
    assert calibrated["composition_aesthetics"] >= 69.9
    assert calibrated["total_score"] > 50.0
    assert calibrated["total_score"] == round(
        calibrated["visual_fidelity"] * 0.21
        + calibrated["text_consistency"] * 0.37
        + calibrated["physical_plausibility"] * 0.24
        + calibrated["composition_aesthetics"] * 0.18,
        2,
    )


def test_student_bundle_scores_without_yolo_checkpoint(tmp_path) -> None:
    image_path = tmp_path / "sample.png"
    Image.new("RGB", (96, 96), color=(128, 132, 140)).save(image_path)
    bundle_dir = _write_student_bundle(tmp_path)

    runtime = PowerScoreRuntime(bundle_dir, device="cpu")
    scores = runtime.score_image(str(image_path), "realistic electric tower and insulator")

    assert {
        "visual_fidelity",
        "text_consistency",
        "physical_plausibility",
        "composition_aesthetics",
        "total_score",
    }.issubset(set(scores))
    assert "score_explanation" in scores
    assert all(0.0 <= scores[key] <= 100.0 for key in DEFAULT_TOTAL_WEIGHTS)
    assert scores["total_score"] == round(
        scores["visual_fidelity"] * 0.21
        + scores["text_consistency"] * 0.37
        + scores["physical_plausibility"] * 0.24
        + scores["composition_aesthetics"] * 0.18,
        2,
    )


def test_student_runtime_requires_checkpoint_and_vocab(tmp_path) -> None:
    bundle_dir = tmp_path / "electric-score-v2"
    bundle_dir.mkdir()
    (bundle_dir / "bundle_config.json").write_text(json.dumps({"runtime_type": "student", "yolo_feature_dim": 34}), encoding="utf-8")

    runtime = PowerScoreRuntime(bundle_dir, device="cpu")

    try:
        runtime.score_image(str(tmp_path / "missing.png"), "tower")
    except FileNotFoundError as exc:
        message = str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected runtime to reject an incomplete bundle")

    assert "vocab.json" in message
    assert "student_best.pt" in message


def test_student_runtime_uses_bundle_yolo_config_and_mps_device(tmp_path) -> None:
    image_path = tmp_path / "sample.png"
    Image.new("RGB", (96, 96), color=(128, 132, 140)).save(image_path)
    bundle_dir = _write_student_bundle(tmp_path)

    config = json.loads((bundle_dir / "bundle_config.json").read_text(encoding="utf-8"))
    config.update({"yolo_imgsz": 320, "yolo_conf": 0.22, "yolo_iou": 0.33})
    (bundle_dir / "bundle_config.json").write_text(json.dumps(config), encoding="utf-8")

    class FakeBoxes:
        cls = torch.tensor([0.0])
        conf = torch.tensor([0.9])
        xywhn = torch.tensor([[0.5, 0.5, 0.2, 0.2]])

    class FakeResult:
        names = {0: "capacitor"}
        boxes = FakeBoxes()

    class FakeYolo:
        def __init__(self) -> None:
            self.calls = []

        def predict(self, **kwargs):
            self.calls.append(kwargs)
            return [FakeResult()]

    fake_yolo = FakeYolo()
    runtime = PowerScoreRuntime(bundle_dir, device="mps", yolo_runtime=fake_yolo)

    runtime.score_image(str(image_path), "electric capacitor")

    assert fake_yolo.calls
    first_call = fake_yolo.calls[0]
    assert first_call["imgsz"] == 320
    assert first_call["conf"] == 0.22
    assert first_call["iou"] == 0.33
    assert first_call["device"] == "mps"


def test_student_runtime_caps_detection_grounded_scores_when_prompt_objects_are_missing(tmp_path) -> None:
    runtime, image_path = _build_runtime_with_injected_student(
        tmp_path,
        detections=[
            {"class_name": "bus", "confidence": 0.93, "bbox": [0.52, 0.55, 0.36, 0.18]},
            {"class_name": "switch", "confidence": 0.74, "bbox": [0.61, 0.49, 0.18, 0.12]},
        ],
        outputs=[58.0, 96.0, 94.0, 63.0],
    )

    scores = runtime.score_image(image_path, "realistic transmission line tower with insulator strings")

    assert scores["text_consistency"] < 70.0
    assert scores["physical_plausibility"] < 70.0


def test_student_runtime_raises_text_and_physical_scores_when_yolo_matches_prompt_topology(tmp_path) -> None:
    prompt = "realistic transmission line tower with insulator strings"
    matched_runtime, image_path = _build_runtime_with_injected_student(
        tmp_path / "matched",
        detections=[
            {"class_name": "tower", "confidence": 0.95, "bbox": [0.48, 0.46, 0.18, 0.72]},
            {"class_name": "line", "confidence": 0.88, "bbox": [0.52, 0.28, 0.92, 0.06]},
            {"class_name": "insulator", "confidence": 0.84, "bbox": [0.46, 0.41, 0.08, 0.13]},
        ],
        outputs=[58.0, 78.0, 74.0, 63.0],
    )
    missing_runtime, _ = _build_runtime_with_injected_student(
        tmp_path / "missing",
        detections=[
            {"class_name": "bus", "confidence": 0.93, "bbox": [0.52, 0.55, 0.36, 0.18]},
        ],
        outputs=[58.0, 78.0, 74.0, 63.0],
    )

    matched_scores = matched_runtime.score_image(image_path, prompt)
    missing_scores = missing_runtime.score_image(image_path, prompt)

    assert matched_scores["text_consistency"] > missing_scores["text_consistency"] + 10.0
    assert matched_scores["physical_plausibility"] > missing_scores["physical_plausibility"] + 10.0


def test_student_runtime_writes_checked_image_to_image_check_directory(tmp_path) -> None:
    runtime, image_path = _build_runtime_with_injected_student(
        tmp_path,
        detections=[
            {"class_name": "tower", "confidence": 0.95, "bbox": [0.48, 0.46, 0.18, 0.72]},
        ],
        outputs=[58.0, 78.0, 74.0, 63.0],
    )

    runtime.score_image(image_path, "realistic transmission line tower")

    checked_image = tmp_path / "image_check" / "sample.png"
    assert checked_image.exists()


def test_student_runtime_writes_unboxed_copy_when_no_detection_is_found(tmp_path) -> None:
    runtime, image_path = _build_runtime_with_injected_student(
        tmp_path,
        detections=[],
        outputs=[58.0, 78.0, 74.0, 63.0],
    )

    runtime.score_image(image_path, "realistic transmission line tower")

    checked_image = tmp_path / "image_check" / "sample.png"
    assert checked_image.exists()


def test_student_runtime_returns_structured_score_explanation_for_history_detail(tmp_path) -> None:
    runtime, image_path = _build_runtime_with_injected_student(
        tmp_path,
        detections=[
            {"class_name": "tower", "confidence": 0.91, "bbox": [0.48, 0.46, 0.18, 0.72]},
        ],
        outputs=[57.7365, 40.3206, 35.9270, 59.2171],
    )

    scores = runtime.score_image(
        image_path,
        "linemen performing night maintenance on transmission tower with visible insulator strings and power lines",
    )

    assert scores["checked_image_path"].endswith("image_check/sample.png")
    explanation = scores["score_explanation"]
    assert explanation["checked_image_path"].endswith("image_check/sample.png")
    assert explanation["dimensions"]["text_consistency"]["uses_yolo"] is True
    assert explanation["dimensions"]["physical_plausibility"]["uses_yolo"] is True
    assert explanation["dimensions"]["visual_fidelity"]["uses_yolo"] is False
    assert explanation["dimensions"]["text_consistency"]["matched_classes"] == ["tower"]
    assert explanation["dimensions"]["text_consistency"]["missing_classes"] == ["insulator", "line"]
    assert explanation["dimensions"]["text_consistency"]["detections"][0]["class_name"] == "tower"
    assert "keyword_coverage" in explanation["dimensions"]["text_consistency"]["inputs"]
    assert "sharpness" in explanation["dimensions"]["visual_fidelity"]["inputs"]
    assert "0.21" in explanation["dimensions"]["total_score"]["formula"]
