import json

from PIL import Image

from app.runtimes.scorers.power_score_runtime import DEFAULT_TOTAL_WEIGHTS, PowerScoreRuntime


def test_self_trained_runtime_uses_text_consistency_priority_weights() -> None:
    assert DEFAULT_TOTAL_WEIGHTS == {
        "visual_fidelity": 0.21,
        "text_consistency": 0.37,
        "physical_plausibility": 0.24,
        "composition_aesthetics": 0.18,
    }


class FixedTeacher:
    def __init__(self, score: float) -> None:
        self.score = score

    def score_image(self, image_path: str, prompt: str, mode: str | None = None) -> float:
        return self.score


class FixedDetector:
    def __init__(self, detections: list[dict[str, float | str | list[float]]]) -> None:
        self.detections = detections

    def predict(self, image_path: str) -> list[dict[str, float | str | list[float]]]:
        return list(self.detections)


def _write_hybrid_bundle(tmp_path, overrides: dict | None = None):
    bundle_dir = tmp_path / "electric-score-v3"
    bundle_dir.mkdir()
    config = {
        "runtime_type": "hybrid",
        "classes": [
            "wind_turbine",
            "transformer",
            "breaker",
            "switch",
            "insulator",
            "arrester",
            "tower",
            "conductor",
            "busbar",
            "frame",
        ],
        "total_weights": DEFAULT_TOTAL_WEIGHTS,
    }
    if overrides:
        config.update(overrides)
    (bundle_dir / "bundle_config.json").write_text(json.dumps(config), encoding="utf-8")
    return bundle_dir


def test_human_aligned_v3_bundle_scores_without_student_checkpoint(tmp_path) -> None:
    image_path = tmp_path / "sample.png"
    Image.new("RGB", (96, 96), color=(128, 132, 140)).save(image_path)
    bundle_dir = _write_hybrid_bundle(tmp_path)

    runtime = PowerScoreRuntime(
        bundle_dir,
        device="cpu",
        text_runtime=FixedTeacher(82.0),
        visual_runtime=FixedTeacher(76.0),
        physical_runtime=FixedTeacher(74.0),
        aesthetics_runtime=FixedTeacher(71.0),
        yolo_runtime=FixedDetector(
            [
                {"class_name": "transformer", "confidence": 0.94, "bbox": [0.48, 0.55, 0.28, 0.24]},
                {"class_name": "busbar", "confidence": 0.88, "bbox": [0.46, 0.43, 0.42, 0.12]},
                {"class_name": "insulator", "confidence": 0.84, "bbox": [0.65, 0.42, 0.08, 0.08]},
            ]
        ),
    )

    scores = runtime.score_image(str(image_path), "realistic substation transformer and busbar")

    assert set(scores) == {
        "visual_fidelity",
        "text_consistency",
        "physical_plausibility",
        "composition_aesthetics",
        "total_score",
    }
    assert all(0.0 <= scores[key] <= 100.0 for key in scores)
    assert scores["total_score"] == round(
        scores["visual_fidelity"] * 0.21
        + scores["text_consistency"] * 0.37
        + scores["physical_plausibility"] * 0.24
        + scores["composition_aesthetics"] * 0.18,
        2,
    )


def test_human_aligned_v3_penalizes_missing_expected_electric_components(tmp_path) -> None:
    image_path = tmp_path / "sample.png"
    Image.new("RGB", (96, 96), color=(156, 158, 160)).save(image_path)
    bundle_dir = _write_hybrid_bundle(tmp_path)

    base_kwargs = {
        "device": "cpu",
        "text_runtime": FixedTeacher(84.0),
        "visual_runtime": FixedTeacher(78.0),
        "physical_runtime": FixedTeacher(79.0),
        "aesthetics_runtime": FixedTeacher(70.0),
    }
    matched_runtime = PowerScoreRuntime(
        bundle_dir,
        yolo_runtime=FixedDetector(
            [
                {"class_name": "transformer", "confidence": 0.95, "bbox": [0.50, 0.52, 0.26, 0.28]},
                {"class_name": "busbar", "confidence": 0.90, "bbox": [0.50, 0.38, 0.44, 0.10]},
                {"class_name": "frame", "confidence": 0.85, "bbox": [0.50, 0.50, 0.58, 0.52]},
            ]
        ),
        **base_kwargs,
    )
    missing_runtime = PowerScoreRuntime(
        bundle_dir,
        yolo_runtime=FixedDetector([]),
        **base_kwargs,
    )

    prompt = "realistic substation with transformer and busbar"
    matched = matched_runtime.score_image(str(image_path), prompt)
    missing = missing_runtime.score_image(str(image_path), prompt)

    assert matched["text_consistency"] > missing["text_consistency"]
    assert matched["physical_plausibility"] > missing["physical_plausibility"]
