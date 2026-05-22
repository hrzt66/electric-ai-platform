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
            "substation_primary",
            "transmission_tower",
            "insulator_string",
            "wind_turbine",
            "solar_panel",
            "dam",
        ],
        "total_weights": DEFAULT_TOTAL_WEIGHTS,
        "yolo_feature_dim": 16,
    }
    (bundle_dir / "bundle_config.json").write_text(json.dumps(config), encoding="utf-8")
    (bundle_dir / "vocab.json").write_text(json.dumps({"<unk>": 0, "electric": 1, "tower": 2, "insulator": 3}), encoding="utf-8")

    model = FourDimScoreModel(vocab_size=4, yolo_feature_dim=16, target_dim=4)
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


class FakePhysicalGptRuntime:
    def __init__(self, result: dict) -> None:
        self._result = result
        self.calls: list[dict] = []

    def annotate_image(self, *, image_path: str, prompt: str) -> dict:
        self.calls.append({"image_path": image_path, "prompt": prompt})
        return dict(self._result)


def _build_runtime_with_injected_student(
    tmp_path,
    *,
    detections: list[dict],
    outputs: list[float],
    physical_part_detections: list[dict] | None = None,
    physical_gpt_runtime=None,
) -> tuple[PowerScoreRuntime, str]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    image_path = tmp_path / "sample.png"
    Image.new("RGB", (96, 96), color=(128, 132, 140)).save(image_path)
    bundle_dir = _write_student_bundle(tmp_path)
    runtime = PowerScoreRuntime(
        bundle_dir,
        device="cpu",
        yolo_runtime=DictDetectionYolo(detections),
        physical_part_yolo_runtime=DictDetectionYolo(physical_part_detections or []),
        physical_gpt_runtime=physical_gpt_runtime,
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


def test_student_score_calibration_only_clamps_and_recomputes_total() -> None:
    raw_scores = {
        "visual_fidelity": 48.01,
        "text_consistency": 35.17,
        "physical_plausibility": 32.91,
        "composition_aesthetics": 65.85,
    }

    calibrated = calibrate_student_scores(raw_scores, DEFAULT_TOTAL_WEIGHTS)

    assert calibrated["visual_fidelity"] == raw_scores["visual_fidelity"]
    assert calibrated["text_consistency"] == raw_scores["text_consistency"]
    assert calibrated["physical_plausibility"] == raw_scores["physical_plausibility"]
    assert calibrated["composition_aesthetics"] == raw_scores["composition_aesthetics"]
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


def test_student_runtime_physical_explanation_includes_rule_breakdown(tmp_path) -> None:
    runtime, image_path = _build_runtime_with_injected_student(
        tmp_path / "wind",
        detections=[
            {"class_name": "wind_turbine", "confidence": 0.93, "bbox": [0.50, 0.52, 0.24, 0.70]},
        ],
        outputs=[58.0, 74.0, 70.0, 63.0],
    )

    scores = runtime.score_image(image_path, "realistic electric power inspection photo with wind_turbine")
    details = scores["score_explanation"]["dimensions"]["physical_plausibility"]["details"]

    assert any("叶片辐射结构" in item for item in details)
    assert any("塔身支撑关系" in item for item in details)


def test_student_runtime_exposes_physical_part_detections_when_available(tmp_path) -> None:
    runtime, image_path = _build_runtime_with_injected_student(
        tmp_path / "parts",
        detections=[
            {"class_name": "wind_turbine", "confidence": 0.93, "bbox": [0.50, 0.52, 0.24, 0.70]},
        ],
        physical_part_detections=[
            {"class_name": "blade", "confidence": 0.88, "bbox": [0.50, 0.24, 0.18, 0.12]},
            {"class_name": "tower_body", "confidence": 0.91, "bbox": [0.50, 0.67, 0.10, 0.42]},
        ],
        outputs=[58.0, 74.0, 70.0, 63.0],
    )

    scores = runtime.score_image(image_path, "realistic electric power inspection photo with wind_turbine")
    physical = scores["score_explanation"]["dimensions"]["physical_plausibility"]

    assert len(physical["physical_part_detections"]) == 2
    assert physical["physical_part_detections"][0]["class_name"] == "blade"


def test_student_runtime_uses_physical_part_detections_to_raise_physical_score(tmp_path) -> None:
    prompt = "realistic electric power inspection photo with wind_turbine"
    with_parts_runtime, image_path = _build_runtime_with_injected_student(
        tmp_path / "with_parts",
        detections=[
            {"class_name": "wind_turbine", "confidence": 0.93, "bbox": [0.50, 0.52, 0.24, 0.70]},
        ],
        physical_part_detections=[
            {"class_name": "wind_blade", "confidence": 0.92, "bbox": [0.50, 0.24, 0.18, 0.12]},
            {"class_name": "wind_blade", "confidence": 0.90, "bbox": [0.38, 0.32, 0.16, 0.12]},
            {"class_name": "wind_blade", "confidence": 0.91, "bbox": [0.62, 0.32, 0.16, 0.12]},
        ],
        outputs=[58.0, 74.0, 70.0, 63.0],
    )
    without_parts_runtime, _ = _build_runtime_with_injected_student(
        tmp_path / "without_parts",
        detections=[
            {"class_name": "wind_turbine", "confidence": 0.93, "bbox": [0.50, 0.52, 0.24, 0.70]},
        ],
        physical_part_detections=[],
        outputs=[58.0, 74.0, 70.0, 63.0],
    )

    with_parts = with_parts_runtime.score_image(image_path, prompt)
    without_parts = without_parts_runtime.score_image(image_path, prompt)

    assert with_parts["physical_plausibility"] > without_parts["physical_plausibility"] + 5.0


def test_student_runtime_uses_gpt_physical_annotation_score_when_available(tmp_path) -> None:
    runtime, image_path = _build_runtime_with_injected_student(
        tmp_path / "gpt_physical",
        detections=[
            {"class_name": "wind_turbine", "confidence": 0.93, "bbox": [0.50, 0.52, 0.24, 0.70]},
        ],
        outputs=[58.0, 74.0, 70.0, 63.0],
        physical_gpt_runtime=FakePhysicalGptRuntime(
            {
                "score": 91.0,
                "target_class": "wind_turbine",
                "reason": "风机叶片完整，塔身与机舱关系合理。",
                "present_elements": ["blade", "tower", "nacelle"],
                "missing_elements": [],
                "rule_checks": [
                    {"label": "叶片数量", "passed": True, "detail": "检测到 3 片叶片"},
                    {"label": "塔身支撑", "passed": True, "detail": "塔身与机舱连接正常"},
                ],
            }
        ),
    )

    scores = runtime.score_image(image_path, "realistic electric power inspection photo with wind_turbine")
    physical = scores["score_explanation"]["dimensions"]["physical_plausibility"]

    assert scores["physical_plausibility"] == 91.0
    assert physical["uses_gpt"] is True
    assert physical["gpt_physical_annotation"]["target_class"] == "wind_turbine"
    assert physical["gpt_physical_annotation"]["missing_elements"] == []


def test_student_runtime_caps_gpt_physical_score_when_critical_wind_rule_fails(tmp_path) -> None:
    runtime, image_path = _build_runtime_with_injected_student(
        tmp_path / "gpt_physical_capped",
        detections=[
            {"class_name": "wind_turbine", "confidence": 0.93, "bbox": [0.50, 0.52, 0.24, 0.70]},
        ],
        outputs=[58.0, 74.0, 70.0, 63.0],
        physical_gpt_runtime=FakePhysicalGptRuntime(
            {
                "score": 92.0,
                "target_class": "wind_turbine",
                "reason": "主体存在，但部分风机叶片数量不对，连接关系也不稳定。",
                "present_elements": ["tower", "nacelle"],
                "missing_elements": ["完整三叶片结构"],
                "rule_checks": [
                    {"label": "叶片数量", "passed": False, "detail": "部分风机少于 3 片叶片"},
                    {"label": "叶片是否从机舱中心发出", "passed": False, "detail": "连接中心不清晰"},
                    {"label": "塔身是否支撑机舱", "passed": True, "detail": "支撑关系基本正常"},
                ],
            }
        ),
    )

    scores = runtime.score_image(image_path, "realistic electric power inspection photo with wind_turbine")
    physical = scores["score_explanation"]["dimensions"]["physical_plausibility"]

    assert scores["physical_plausibility"] <= 69.0
    assert physical["gpt_physical_annotation"]["score_band"] == "50-69"


def test_student_runtime_gives_low_gpt_physical_score_when_prompt_target_is_not_detected(tmp_path) -> None:
    runtime, image_path = _build_runtime_with_injected_student(
        tmp_path / "gpt_physical_missing_detection",
        detections=[],
        outputs=[58.0, 74.0, 70.0, 63.0],
        physical_gpt_runtime=FakePhysicalGptRuntime(
            {
                "score": 90.0,
                "target_class": "wind_turbine",
                "reason": "视觉上像风机，但当前检测模型没有检出目标。",
                "present_elements": ["tower", "blade"],
                "missing_elements": [],
                "rule_checks": [
                    {"label": "叶片数量", "passed": True, "detail": "看起来接近 3 片"},
                    {"label": "塔身是否支撑机舱", "passed": True, "detail": "支撑关系看起来成立"},
                ],
            }
        ),
    )

    scores = runtime.score_image(image_path, "realistic wind_turbine")
    physical = scores["score_explanation"]["dimensions"]["physical_plausibility"]

    assert scores["physical_plausibility"] <= 49.0
    assert physical["gpt_physical_annotation"]["score_band"] == "0-49"
    assert physical["inputs"]["detection_gate_triggered"] is True


def test_student_runtime_allows_gpt_physical_score_above_95_only_when_all_rules_pass(tmp_path) -> None:
    runtime, image_path = _build_runtime_with_injected_student(
        tmp_path / "gpt_physical_perfect",
        detections=[
            {"class_name": "transmission_tower", "confidence": 0.95, "bbox": [0.48, 0.46, 0.18, 0.72]},
        ],
        outputs=[58.0, 74.0, 70.0, 63.0],
        physical_gpt_runtime=FakePhysicalGptRuntime(
            {
                "score": 98.0,
                "target_class": "transmission_tower",
                "reason": "塔体、横担、绝缘子、导线关系完全正确。",
                "present_elements": ["tower_body", "crossarm", "insulator", "wire"],
                "missing_elements": [],
                "rule_checks": [
                    {"label": "塔体对称且向上收敛", "passed": True, "detail": "结构稳定"},
                    {"label": "横担位置是否合理", "passed": True, "detail": "位置正确"},
                    {"label": "绝缘子串是否挂在横担附近", "passed": True, "detail": "连接正确"},
                    {"label": "导线是否连接塔体且方向自然", "passed": True, "detail": "走向自然"},
                    {"label": "导线不能反重力乱飞", "passed": True, "detail": "弧垂自然"},
                ],
            }
        ),
    )

    scores = runtime.score_image(image_path, "realistic transmission_tower")
    physical = scores["score_explanation"]["dimensions"]["physical_plausibility"]

    assert scores["physical_plausibility"] == 98.0
    assert physical["gpt_physical_annotation"]["score_band"] == "95-100"


def test_student_runtime_normalizes_substation_alias_to_six_class_target(tmp_path) -> None:
    runtime, image_path = _build_runtime_with_injected_student(
        tmp_path / "gpt_substation_alias",
        detections=[
            {"class_name": "substation_primary", "confidence": 0.95, "bbox": [0.50, 0.54, 0.62, 0.52]},
        ],
        outputs=[58.0, 74.0, 70.0, 63.0],
        physical_gpt_runtime=FakePhysicalGptRuntime(
            {
                "score": 90.0,
                "target_class": "substation",
                "reason": "主体更接近变电站主设备区域。",
                "present_elements": ["主变", "母线", "套管", "构架"],
                "missing_elements": [],
                "rule_checks": [
                    {"label": "设备连接关系", "passed": True, "detail": "主设备连接成立"},
                    {"label": "母线支架套管相对位置", "passed": True, "detail": "相对位置合理"},
                ],
            }
        ),
    )

    scores = runtime.score_image(image_path, "realistic substation_primary")
    physical = scores["score_explanation"]["dimensions"]["physical_plausibility"]

    assert physical["gpt_physical_annotation"]["target_class"] == "substation_primary"


def test_student_runtime_normalizes_insulator_like_target_to_transmission_tower(tmp_path) -> None:
    runtime, image_path = _build_runtime_with_injected_student(
        tmp_path / "gpt_insulator_alias",
        detections=[
            {"class_name": "transmission_tower", "confidence": 0.92, "bbox": [0.52, 0.40, 0.10, 0.20]},
        ],
        outputs=[58.0, 74.0, 70.0, 63.0],
        physical_gpt_runtime=FakePhysicalGptRuntime(
            {
                "score": 88.0,
                "target_class": "insulator_string",
                "reason": "绝缘子近景统一归到铁塔主类别。",
                "present_elements": ["绝缘子盘片"],
                "missing_elements": [],
                "rule_checks": [
                    {"label": "绝缘子串位置", "passed": True, "detail": "串体可见"},
                    {"label": "绝缘子串是否挂在横担附近", "passed": True, "detail": "挂点关系可成立"},
                ],
            }
        ),
    )

    scores = runtime.score_image(image_path, "realistic insulator string close-up")
    physical = scores["score_explanation"]["dimensions"]["physical_plausibility"]

    assert physical["gpt_physical_annotation"]["target_class"] == "transmission_tower"


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
    assert explanation["dimensions"]["visual_fidelity"]["uses_yolo"] is True
    assert explanation["dimensions"]["text_consistency"]["matched_classes"] == ["transmission_tower"]
    assert explanation["dimensions"]["text_consistency"]["missing_classes"] == []
    assert explanation["dimensions"]["text_consistency"]["detections"][0]["class_name"] == "transmission_tower"
    assert "keyword_coverage" in explanation["dimensions"]["text_consistency"]["inputs"]
    assert "sharpness" in explanation["dimensions"]["visual_fidelity"]["inputs"]
    assert "按主类使用 5 套规则" in explanation["dimensions"]["visual_fidelity"]["formula"]
    assert any("主判类别" in item for item in explanation["dimensions"]["visual_fidelity"]["details"])
    assert "检测匹配召回" in explanation["dimensions"]["text_consistency"]["formula"]
    assert "GPT-5.4" in explanation["dimensions"]["physical_plausibility"]["formula"] or "结构规则" in explanation["dimensions"]["physical_plausibility"]["formula"]
    assert "主体布局规则" in explanation["dimensions"]["composition_aesthetics"]["formula"]
    assert "0.21" in explanation["dimensions"]["total_score"]["formula"]
