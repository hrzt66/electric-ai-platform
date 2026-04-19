from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import torch
from PIL import Image, ImageDraw, ImageFont
from torchvision import transforms
from ultralytics import YOLO

from training.scoring.modeling import (
    DEFAULT_TARGET_COLUMNS,
    DEFAULT_TOTAL_WEIGHTS,
    GENERIC_ELECTRIC_TERMS,
    PROMPT_CLASS_ALIASES,
    FourDimScoreModel,
    TOKEN_PATTERN,
    choose_training_device,
    clamp_score,
    encode_prompt,
)

DEFAULT_SCORING_MODEL_NAME = "electric-score-v1"
SELF_TRAINED_SCORING_MODEL_NAME = "electric-score-v2"
SELF_TRAINED_SCORING_MODEL_NAMES = {SELF_TRAINED_SCORING_MODEL_NAME}
DEFAULT_STUDENT_SCORE_CALIBRATION = {
    "visual_fidelity": {"target": 64.0, "gain": 0.50},
    "text_consistency": {"target": 58.0, "gain": 0.65},
    "physical_plausibility": {"target": 54.0, "gain": 0.60},
    "composition_aesthetics": {"target": 76.0, "gain": 0.40},
}
DIMENSION_TITLES = {
    "visual_fidelity": "视觉保真",
    "text_consistency": "文本一致",
    "physical_plausibility": "物理合理",
    "composition_aesthetics": "构图美学",
    "total_score": "总分",
}


def calibrate_student_scores(
    raw_scores: dict[str, float],
    total_weights: dict[str, float],
    calibration: dict[str, dict[str, float]] | None = None,
) -> dict[str, float]:
    active_calibration = calibration or DEFAULT_STUDENT_SCORE_CALIBRATION
    calibrated: dict[str, float] = {}
    for name, value in raw_scores.items():
        rule = active_calibration.get(name)
        if rule is None:
            calibrated[name] = clamp_score(value)
            continue
        calibrated[name] = _lift_low_band(
            value,
            target=float(rule.get("target", value)),
            gain=float(rule.get("gain", 0.0)),
        )
    calibrated["total_score"] = round(
        sum(calibrated.get(name, 0.0) * total_weights.get(name, 0.0) for name in total_weights),
        2,
    )
    return calibrated


def recompute_total_score(
    component_scores: dict[str, float],
    total_weights: dict[str, float],
) -> dict[str, float]:
    updated = dict(component_scores)
    updated["total_score"] = round(
        sum(updated.get(name, 0.0) * total_weights.get(name, 0.0) for name in total_weights),
        2,
    )
    return updated


def _lift_low_band(score: float, *, target: float, gain: float) -> float:
    bounded = max(0.0, min(100.0, float(score)))
    if bounded >= target:
        return round(bounded, 2)
    return round(min(100.0, bounded + (target - bounded) * gain), 2)


class PowerScoreRuntime:
    def __init__(
        self,
        bundle_dir: Path,
        device: str | None = None,
        *,
        yolo_runtime: Any | None = None,
        image_check_dir: Path | None = None,
    ) -> None:
        self.bundle_dir = Path(bundle_dir)
        self.device = choose_training_device(device)
        self._config: dict[str, Any] | None = None

        self._vocab: dict[str, int] | None = None
        self._model: FourDimScoreModel | None = None
        self._transform: transforms.Compose | None = None

        self._yolo = yolo_runtime
        self._image_check_dir = Path(image_check_dir) if image_check_dir is not None else None

    def score_image(self, image_path: str, prompt: str) -> dict[str, Any]:
        self._ensure_loaded()
        return self._score_student_image(image_path=image_path, prompt=prompt)

    def unload(self) -> None:
        self._model = None
        self._vocab = None
        self._transform = None
        self._yolo = None
        if self.device.type == "cuda":
            torch.cuda.empty_cache()
        elif self.device.type == "mps" and hasattr(torch, "mps") and hasattr(torch.mps, "empty_cache"):
            torch.mps.empty_cache()

    def _ensure_loaded(self) -> None:
        if self._config is None:
            config_path = self.bundle_dir / "bundle_config.json"
            if not config_path.exists():
                raise FileNotFoundError(f"self-trained scoring bundle is missing {config_path}")
            self._config = json.loads(config_path.read_text(encoding="utf-8"))
        self._ensure_student_loaded()

    def _ensure_student_loaded(self) -> None:
        if self._model is not None and self._transform is not None:
            return

        assert self._config is not None
        vocab_path = self.bundle_dir / "vocab.json"
        model_path = self.bundle_dir / "student_best.pt"
        yolo_path = self.bundle_dir / "yolo_aux.pt"
        required = [vocab_path, model_path]
        missing = [str(path) for path in required if not path.exists()]
        if missing:
            raise FileNotFoundError(
                f"self-trained scoring bundle is incomplete under {self.bundle_dir}: {', '.join(missing)}"
            )

        self._vocab = json.loads(vocab_path.read_text(encoding="utf-8"))
        image_size = int(self._config.get("image_size", 320))
        interpolation = transforms.InterpolationMode.BICUBIC
        self._transform = transforms.Compose(
            [
                transforms.Resize((image_size, image_size), interpolation=interpolation),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            ]
        )

        yolo_feature_dim = int(self._config["yolo_feature_dim"])
        targets = self._config.get("targets", DEFAULT_TARGET_COLUMNS)
        self._model = FourDimScoreModel(len(self._vocab), yolo_feature_dim, len(targets)).to(self.device)
        state_dict = torch.load(model_path, map_location=self.device)
        self._model.load_state_dict(state_dict)
        self._model.eval()
        if self._yolo is None and yolo_path.exists():
            self._yolo = YOLO(str(yolo_path))

    def _score_student_image(self, *, image_path: str, prompt: str) -> dict[str, Any]:
        assert self._config is not None
        assert self._vocab is not None
        assert self._model is not None
        assert self._transform is not None

        image = Image.open(image_path).convert("RGB")
        image_tensor = self._transform(image).unsqueeze(0).to(self.device)
        prompt_ids = torch.tensor(encode_prompt(prompt, self._vocab), dtype=torch.long, device=self.device)
        prompt_offsets = torch.tensor([0], dtype=torch.long, device=self.device)
        detections = self._predict_detections(image_path)
        checked_image_path = self._write_checked_image(image=image, image_path=image_path, detections=detections)
        image_analysis = self._analyze_image(image, detections)
        prompt_analysis = self._analyze_prompt(prompt, detections)
        yolo_features = torch.tensor(
            [self._build_yolo_feature_vector(detections)],
            dtype=torch.float32,
            device=self.device,
        )

        with torch.no_grad():
            output = self._model(image_tensor, prompt_ids, prompt_offsets, yolo_features)[0].detach().cpu().tolist()

        targets = self._config.get("targets", DEFAULT_TARGET_COLUMNS)
        raw_values = {name: clamp_score(float(value)) for name, value in zip(targets, output)}
        total_weights = self._config.get("total_weights", DEFAULT_TOTAL_WEIGHTS)
        calibrated = calibrate_student_scores(
            raw_values,
            total_weights,
            self._config.get("score_calibration"),
        )
        grounded = self._ground_detection_sensitive_scores(
            calibrated,
            prompt_analysis=prompt_analysis,
            total_weights=total_weights,
        )
        result: dict[str, Any] = {
            **grounded,
            "score_explanation": self._build_score_explanation(
                checked_image_path=checked_image_path,
                raw_scores=raw_values,
                calibrated_scores=calibrated,
                final_scores=grounded,
                total_weights=total_weights,
                image_analysis=image_analysis,
                prompt_analysis=prompt_analysis,
                detections=detections,
            ),
        }
        if checked_image_path is not None:
            result["checked_image_path"] = checked_image_path
        return result

    def _predict_detections(self, image_path: str) -> list[dict[str, Any]]:
        if self._yolo is None:
            return []

        try:
            prediction = self._yolo.predict(
                source=image_path,
                imgsz=int(self._config.get("yolo_imgsz", 640)) if self._config else 640,
                conf=float(self._config.get("yolo_conf", 0.15)) if self._config else 0.15,
                iou=float(self._config.get("yolo_iou", 0.45)) if self._config else 0.45,
                device=self._yolo_device(),
                verbose=False,
            )
        except TypeError:
            prediction = self._yolo.predict(image_path)

        if isinstance(prediction, list) and prediction and isinstance(prediction[0], dict):
            return [self._normalize_detection(item) for item in prediction]
        if not prediction:
            return []

        result = prediction[0]
        names = result.names or {}
        detections: list[dict[str, Any]] = []
        if result.boxes is None:
            return detections
        for cls_id, conf, xywhn in zip(
            result.boxes.cls.tolist(),
            result.boxes.conf.tolist(),
            result.boxes.xywhn.tolist(),
        ):
            detections.append(
                {
                    "class_name": names.get(int(cls_id), str(int(cls_id))),
                    "confidence": float(conf),
                    "bbox": [float(xywhn[0]), float(xywhn[1]), float(xywhn[2]), float(xywhn[3])],
                }
            )
        return detections

    @staticmethod
    def _normalize_detection(item: dict[str, Any]) -> dict[str, Any]:
        bbox = item.get("bbox") or [0.5, 0.5, 0.0, 0.0]
        return {
            "class_name": str(item.get("class_name") or item.get("class") or ""),
            "confidence": float(item.get("confidence", 0.0)),
            "bbox": [float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])],
        }

    def _write_checked_image(
        self,
        *,
        image: Image.Image,
        image_path: str,
        detections: list[dict[str, Any]],
    ) -> str | None:
        if self._image_check_dir is None:
            return None

        self._image_check_dir.mkdir(parents=True, exist_ok=True)
        target_path = self._image_check_dir / Path(image_path).name
        checked = image.copy()

        if detections:
            draw = ImageDraw.Draw(checked)
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Unicode.ttf", 18)
            except Exception:
                font = ImageFont.load_default()

            width, height = checked.size
            for item in detections:
                center_x, center_y, box_width, box_height = item["bbox"]
                x1 = max(0.0, (float(center_x) - float(box_width) / 2.0) * width)
                y1 = max(0.0, (float(center_y) - float(box_height) / 2.0) * height)
                x2 = min(width, (float(center_x) + float(box_width) / 2.0) * width)
                y2 = min(height, (float(center_y) + float(box_height) / 2.0) * height)
                label = f"{item['class_name']} {float(item['confidence']):.3f}"

                draw.rectangle((x1, y1, x2, y2), outline=(255, 64, 64), width=4)
                tx1, ty1, tx2, ty2 = draw.textbbox((0, 0), label, font=font)
                label_height = ty2 - ty1
                label_width = tx2 - tx1
                label_top = max(0.0, y1 - label_height - 8)
                draw.rectangle(
                    (x1, label_top, x1 + label_width + 12, label_top + label_height + 8),
                    fill=(255, 64, 64),
                )
                draw.text((x1 + 6, label_top + 4), label, fill=(255, 255, 255), font=font)

        checked.save(target_path)
        return str(target_path)

    @staticmethod
    def _analyze_image(image: Image.Image, detections: list[dict[str, Any]]) -> dict[str, float]:
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
            if weighted_area > 0.0:
                centroid_x = weighted_x / max(weighted_area, 1e-6)
                centroid_y = weighted_y / max(weighted_area, 1e-6)
                center_offset = abs(centroid_x - 0.5) + abs(centroid_y - 0.5)
                balance_score = 100.0 - min(1.0, center_offset / 0.65) * 100.0
            else:
                balance_score = 60.0
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

    @staticmethod
    def _analyze_prompt(prompt: str, detections: list[dict[str, Any]]) -> dict[str, Any]:
        lower_prompt = prompt.lower()
        prompt_tokens = set(TOKEN_PATTERN.findall(lower_prompt))
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
        if {"tower", "insulator"}.issubset(detected_classes):
            topology += 16.0
        if {"tower", "line"}.issubset(detected_classes):
            topology += 24.0
        if {"line", "insulator"}.issubset(detected_classes):
            topology += 10.0
        if {"bus", "bushing"}.issubset(detected_classes):
            topology += 16.0
        if {"bus", "switch"}.issubset(detected_classes):
            topology += 12.0
        if {"bus", "frame"}.issubset(detected_classes):
            topology += 10.0
        if {"ct", "bus"}.issubset(detected_classes):
            topology += 10.0
        if {"capacitor", "bus"}.issubset(detected_classes):
            topology += 8.0
        if {"frame", "bushing"}.issubset(detected_classes):
            topology += 8.0
        topology += min(10.0, len(detected_classes) * 2.0)

        return {
            "expected_classes": expected_classes,
            "matched_classes": matched_classes,
            "detected_classes": detected_classes,
            "keyword_coverage": clamp_score(keyword_coverage),
            "electric_presence": clamp_score(electric_presence if detected_classes else 30.0),
            "topology": clamp_score(topology if detected_classes else 28.0),
        }

    def _ground_detection_sensitive_scores(
        self,
        base_scores: dict[str, float],
        *,
        prompt_analysis: dict[str, Any],
        total_weights: dict[str, float],
    ) -> dict[str, float]:
        keyword_coverage = float(prompt_analysis["keyword_coverage"])
        electric_presence = float(prompt_analysis["electric_presence"])
        topology = float(prompt_analysis["topology"])
        expected_classes = set(prompt_analysis["expected_classes"])
        matched_classes = set(prompt_analysis["matched_classes"])
        detected_classes = set(prompt_analysis["detected_classes"])

        grounded = dict(base_scores)

        detection_text_signal = keyword_coverage * 0.72 + electric_presence * 0.28
        text_score = grounded["text_consistency"] * 0.42 + detection_text_signal * 0.58
        if expected_classes:
            text_cap = 38.0 + keyword_coverage * 0.62
            if not matched_classes:
                text_cap = min(text_cap, 48.0)
            text_score = min(text_score, text_cap)
        elif not detected_classes:
            text_score = min(text_score, 45.0)
        grounded["text_consistency"] = clamp_score(text_score)

        detection_physical_signal = topology * 0.70 + electric_presence * 0.30
        physical_score = grounded["physical_plausibility"] * 0.45 + detection_physical_signal * 0.55
        if expected_classes:
            physical_cap = 32.0 + topology * 0.68 + keyword_coverage * 0.10
            physical_score = min(physical_score, physical_cap)
        if not detected_classes:
            physical_score = min(physical_score, 40.0)
        elif len(detected_classes) <= 1:
            physical_score = min(physical_score, 58.0)
        grounded["physical_plausibility"] = clamp_score(physical_score)

        return recompute_total_score(grounded, total_weights)

    def _build_score_explanation(
        self,
        *,
        checked_image_path: str | None,
        raw_scores: dict[str, float],
        calibrated_scores: dict[str, float],
        final_scores: dict[str, float],
        total_weights: dict[str, float],
        image_analysis: dict[str, float],
        prompt_analysis: dict[str, Any],
        detections: list[dict[str, Any]],
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "dimensions": {
                "visual_fidelity": self._build_visual_explanation(
                    raw_scores=raw_scores,
                    calibrated_scores=calibrated_scores,
                    final_scores=final_scores,
                    image_analysis=image_analysis,
                ),
                "text_consistency": self._build_text_explanation(
                    raw_scores=raw_scores,
                    calibrated_scores=calibrated_scores,
                    final_scores=final_scores,
                    prompt_analysis=prompt_analysis,
                    detections=detections,
                    checked_image_path=checked_image_path,
                ),
                "physical_plausibility": self._build_physical_explanation(
                    raw_scores=raw_scores,
                    calibrated_scores=calibrated_scores,
                    final_scores=final_scores,
                    prompt_analysis=prompt_analysis,
                    detections=detections,
                    checked_image_path=checked_image_path,
                ),
                "composition_aesthetics": self._build_composition_explanation(
                    raw_scores=raw_scores,
                    calibrated_scores=calibrated_scores,
                    final_scores=final_scores,
                    image_analysis=image_analysis,
                ),
                "total_score": self._build_total_explanation(
                    final_scores=final_scores,
                    total_weights=total_weights,
                ),
            }
        }
        if checked_image_path is not None:
            payload["checked_image_path"] = checked_image_path
        return payload

    def _build_visual_explanation(
        self,
        *,
        raw_scores: dict[str, float],
        calibrated_scores: dict[str, float],
        final_scores: dict[str, float],
        image_analysis: dict[str, float],
    ) -> dict[str, Any]:
        score = float(final_scores["visual_fidelity"])
        exposure = float(image_analysis["exposure"])
        sharpness = float(image_analysis["sharpness"])
        if exposure < 40.0:
            summary = "曝光明显偏弱，暗部细节损失较多，所以视觉保真被压低。"
        elif sharpness < 45.0:
            summary = "主体边缘不够锐利，细节解析度一般，因此视觉保真只能维持在中低档。"
        else:
            summary = "图像清晰度和层次基本在线，视觉保真主要由学生模型校准后的结果决定。"
        return {
            "title": DIMENSION_TITLES["visual_fidelity"],
            "score": score,
            "grade_label": self._score_grade_label(score),
            "uses_yolo": False,
            "summary": summary,
            "formula": "最终视觉保真 = 学生模型视觉输出经过低分段校准；该维度不叠加 YOLO 修正，说明项只展示与结果最相关的画质指标。",
            "details": [
                f"学生模型原始视觉分为 {raw_scores['visual_fidelity']:.2f}，校准后为 {calibrated_scores['visual_fidelity']:.2f}。",
                f"锐度为 {image_analysis['sharpness']:.2f}，数值越低通常意味着边缘和纹理更软。",
                f"曝光为 {image_analysis['exposure']:.2f}，夜景或暗部过重会削弱设备细节的可辨识度。",
                f"对比度为 {image_analysis['contrast']:.2f}，它支撑了主体层次，但不足以完全抵消曝光短板。",
            ],
            "inputs": {
                "raw_score": raw_scores["visual_fidelity"],
                "calibrated_score": calibrated_scores["visual_fidelity"],
                "final_score": final_scores["visual_fidelity"],
                "sharpness": image_analysis["sharpness"],
                "exposure": image_analysis["exposure"],
                "contrast": image_analysis["contrast"],
            },
        }

    def _build_text_explanation(
        self,
        *,
        raw_scores: dict[str, float],
        calibrated_scores: dict[str, float],
        final_scores: dict[str, float],
        prompt_analysis: dict[str, Any],
        detections: list[dict[str, Any]],
        checked_image_path: str | None,
    ) -> dict[str, Any]:
        score = float(final_scores["text_consistency"])
        expected_classes = sorted(str(item) for item in prompt_analysis["expected_classes"])
        matched_classes = sorted(str(item) for item in prompt_analysis["matched_classes"])
        detected_classes = sorted(str(item) for item in prompt_analysis["detected_classes"])
        missing_classes = [item for item in expected_classes if item not in matched_classes]
        if missing_classes:
            summary = "提示词要求的关键电力对象没有被充分检测到，文本一致性被 YOLO 语义约束明显拉低。"
        elif matched_classes:
            summary = "YOLO 检测结果和提示词目标对象较一致，因此文本一致性获得了明显支撑。"
        else:
            summary = "提示词中缺少明确电力目标或检测结果不足，文本一致性主要依赖基础学生模型分数。"
        return {
            "title": DIMENSION_TITLES["text_consistency"],
            "score": score,
            "grade_label": self._score_grade_label(score),
            "uses_yolo": True,
            "summary": summary,
            "formula": "最终文本一致 = 0.42 * 校准文本分 + 0.58 * (0.72 * keyword_coverage + 0.28 * electric_presence)，随后再按提示词目标覆盖率进行封顶。",
            "details": [
                f"学生模型原始文本分为 {raw_scores['text_consistency']:.2f}，校准后为 {calibrated_scores['text_consistency']:.2f}，落地后最终得分为 {final_scores['text_consistency']:.2f}。",
                f"提示词推断需要出现的对象为 {self._format_class_list(expected_classes)}。",
                f"实际检测到的对象为 {self._format_class_list(detected_classes)}。",
                f"成功匹配的对象为 {self._format_class_list(matched_classes)}，缺失对象为 {self._format_class_list(missing_classes)}。",
                f"keyword_coverage 为 {float(prompt_analysis['keyword_coverage']):.2f}，electric_presence 为 {float(prompt_analysis['electric_presence']):.2f}。",
            ],
            "checked_image_path": checked_image_path,
            "expected_classes": expected_classes,
            "matched_classes": matched_classes,
            "missing_classes": missing_classes,
            "detections": self._serialize_detections(detections),
            "inputs": {
                "raw_score": raw_scores["text_consistency"],
                "calibrated_score": calibrated_scores["text_consistency"],
                "final_score": final_scores["text_consistency"],
                "keyword_coverage": float(prompt_analysis["keyword_coverage"]),
                "electric_presence": float(prompt_analysis["electric_presence"]),
            },
        }

    def _build_physical_explanation(
        self,
        *,
        raw_scores: dict[str, float],
        calibrated_scores: dict[str, float],
        final_scores: dict[str, float],
        prompt_analysis: dict[str, Any],
        detections: list[dict[str, Any]],
        checked_image_path: str | None,
    ) -> dict[str, Any]:
        score = float(final_scores["physical_plausibility"])
        expected_classes = sorted(str(item) for item in prompt_analysis["expected_classes"])
        matched_classes = sorted(str(item) for item in prompt_analysis["matched_classes"])
        detected_classes = sorted(str(item) for item in prompt_analysis["detected_classes"])
        missing_classes = [item for item in expected_classes if item not in matched_classes]
        topology = float(prompt_analysis["topology"])
        if topology < 45.0:
            summary = "检测到的电力拓扑关系不足，说明结构连接和设备组合不完整，所以物理合理性偏低。"
        elif missing_classes:
            summary = "虽然识别到部分电力对象，但关键关系对象仍有缺失，因此物理合理性只能保持在中低档。"
        else:
            summary = "检测到的设备关系与提示词较一致，电力拓扑信号对物理合理性形成了正向支撑。"
        return {
            "title": DIMENSION_TITLES["physical_plausibility"],
            "score": score,
            "grade_label": self._score_grade_label(score),
            "uses_yolo": True,
            "summary": summary,
            "formula": "最终物理合理 = 0.45 * 校准物理分 + 0.55 * (0.70 * topology + 0.30 * electric_presence)，随后再按拓扑覆盖情况进行封顶。",
            "details": [
                f"学生模型原始物理分为 {raw_scores['physical_plausibility']:.2f}，校准后为 {calibrated_scores['physical_plausibility']:.2f}，落地后最终得分为 {final_scores['physical_plausibility']:.2f}。",
                f"拓扑信号 topology 为 {topology:.2f}，electric_presence 为 {float(prompt_analysis['electric_presence']):.2f}。",
                f"提示词期望对象为 {self._format_class_list(expected_classes)}，当前匹配到 {self._format_class_list(matched_classes)}。",
                f"仍然缺失的关键对象为 {self._format_class_list(missing_classes)}，这会削弱结构合理性判断。",
            ],
            "checked_image_path": checked_image_path,
            "expected_classes": expected_classes,
            "matched_classes": matched_classes,
            "missing_classes": missing_classes,
            "detections": self._serialize_detections(detections),
            "inputs": {
                "raw_score": raw_scores["physical_plausibility"],
                "calibrated_score": calibrated_scores["physical_plausibility"],
                "final_score": final_scores["physical_plausibility"],
                "topology": topology,
                "electric_presence": float(prompt_analysis["electric_presence"]),
            },
        }

    def _build_composition_explanation(
        self,
        *,
        raw_scores: dict[str, float],
        calibrated_scores: dict[str, float],
        final_scores: dict[str, float],
        image_analysis: dict[str, float],
    ) -> dict[str, Any]:
        score = float(final_scores["composition_aesthetics"])
        coverage = float(image_analysis["coverage"])
        balance = float(image_analysis["balance"])
        if coverage < 45.0:
            summary = "主体覆盖比例偏离理想区间，画面张力不足，因此构图美学只达到基础可用水平。"
        elif balance < 45.0:
            summary = "主体重心偏移较明显，虽然画面能看，但构图平衡性拖累了美学得分。"
        else:
            summary = "主体占比和画面平衡性整体稳定，所以构图美学主要跟随学生模型校准结果。"
        return {
            "title": DIMENSION_TITLES["composition_aesthetics"],
            "score": score,
            "grade_label": self._score_grade_label(score),
            "uses_yolo": False,
            "summary": summary,
            "formula": "最终构图美学 = 学生模型构图输出经过校准；说明项结合主体覆盖率与画面平衡性解释该结果。",
            "details": [
                f"学生模型原始构图分为 {raw_scores['composition_aesthetics']:.2f}，校准后为 {calibrated_scores['composition_aesthetics']:.2f}。",
                f"主体覆盖率指标为 {image_analysis['coverage']:.2f}，过高或过低都会削弱画面组织感。",
                f"平衡性指标为 {image_analysis['balance']:.2f}，它反映主体重心是否过度偏向某一侧。",
            ],
            "inputs": {
                "raw_score": raw_scores["composition_aesthetics"],
                "calibrated_score": calibrated_scores["composition_aesthetics"],
                "final_score": final_scores["composition_aesthetics"],
                "coverage": image_analysis["coverage"],
                "balance": image_analysis["balance"],
            },
        }

    def _build_total_explanation(
        self,
        *,
        final_scores: dict[str, float],
        total_weights: dict[str, float],
    ) -> dict[str, Any]:
        contributions = {
            key: round(float(final_scores[key]) * float(total_weights[key]), 2)
            for key in total_weights
        }
        weakest_dimension = min(total_weights, key=lambda item: float(final_scores[item]))
        summary = f"{DIMENSION_TITLES[weakest_dimension]} 是当前最低维度，它对总分形成了最明显的拖累。"
        return {
            "title": DIMENSION_TITLES["total_score"],
            "score": float(final_scores["total_score"]),
            "grade_label": self._score_grade_label(float(final_scores["total_score"])),
            "uses_yolo": False,
            "summary": summary,
            "formula": "总分 = 0.21 * 视觉保真 + 0.37 * 文本一致 + 0.24 * 物理合理 + 0.18 * 构图美学。",
            "details": [
                f"视觉保真贡献 {contributions['visual_fidelity']:.2f} = {final_scores['visual_fidelity']:.2f} * {total_weights['visual_fidelity']:.2f}",
                f"文本一致贡献 {contributions['text_consistency']:.2f} = {final_scores['text_consistency']:.2f} * {total_weights['text_consistency']:.2f}",
                f"物理合理贡献 {contributions['physical_plausibility']:.2f} = {final_scores['physical_plausibility']:.2f} * {total_weights['physical_plausibility']:.2f}",
                f"构图美学贡献 {contributions['composition_aesthetics']:.2f} = {final_scores['composition_aesthetics']:.2f} * {total_weights['composition_aesthetics']:.2f}",
            ],
            "inputs": {
                "weights": {
                    "visual_fidelity": total_weights["visual_fidelity"],
                    "text_consistency": total_weights["text_consistency"],
                    "physical_plausibility": total_weights["physical_plausibility"],
                    "composition_aesthetics": total_weights["composition_aesthetics"],
                },
                "contributions": contributions,
            },
        }

    @staticmethod
    def _serialize_detections(detections: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "class_name": str(item.get("class_name", "")),
                "confidence": round(float(item.get("confidence", 0.0)), 4),
                "bbox": [round(float(value), 4) for value in item.get("bbox", [])],
            }
            for item in detections
        ]

    @staticmethod
    def _format_class_list(items: list[str]) -> str:
        if not items:
            return "无"
        return ", ".join(items)

    @staticmethod
    def _score_grade_label(score: float) -> str:
        value = max(0.0, min(100.0, float(score)))
        if value < 30.0:
            return "待改进"
        if value < 50.0:
            return "偏低"
        if value < 70.0:
            return "达标"
        if value < 85.0:
            return "良好"
        return "优秀"

    def _build_yolo_feature_vector(self, detections: list[dict[str, Any]]) -> list[float]:
        assert self._config is not None
        classes = self._config.get("classes", [])
        if not detections:
            return [0.0 for _ in range(len(classes) * 2 + 4)]

        class_index = {name: idx for idx, name in enumerate(classes)}
        counts = [0.0 for _ in classes]
        max_conf = [0.0 for _ in classes]
        areas: list[float] = []
        for item in detections:
            class_name = str(item["class_name"])
            if class_name not in class_index:
                continue
            idx = class_index[class_name]
            counts[idx] += 1.0
            max_conf[idx] = max(max_conf[idx], float(item["confidence"]))
            _, _, width, height = item["bbox"]
            areas.append(float(width) * float(height))

        max_count = max(sum(counts), 1.0)
        normalized_counts = [value / max_count for value in counts]
        coverage = float(sum(areas))
        mean_conf = float(sum(max_conf) / len(max_conf)) if max_conf else 0.0
        mean_area = float(sum(areas) / max(len(areas), 1))
        return normalized_counts + max_conf + [coverage, mean_conf, float(len(areas)), mean_area]

    def _yolo_device(self) -> str | int:
        if self.device.type == "cuda":
            return 0
        if self.device.type == "mps":
            return "mps"
        return "cpu"


class PowerScoreRouter:
    def __init__(self, runtimes: dict[str, PowerScoreRuntime]) -> None:
        self._runtimes = dict(runtimes)

    def score_image_for_model(self, scoring_model_name: str, image_path: str, prompt: str) -> dict[str, Any]:
        if scoring_model_name not in self._runtimes:
            raise ValueError(f"unsupported self-trained scoring model: {scoring_model_name}")
        return self._runtimes[scoring_model_name].score_image(image_path, prompt)

    def unload(self) -> None:
        for runtime in self._runtimes.values():
            runtime.unload()
