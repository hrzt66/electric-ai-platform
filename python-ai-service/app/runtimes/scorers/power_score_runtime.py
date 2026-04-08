from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.nn as nn
from PIL import Image
from torchvision import transforms
from torchvision.models import efficientnet_b0
from ultralytics import YOLO

from app.runtimes.scorers.aesthetic_runtime import AestheticRuntime
from app.runtimes.scorers.clip_iqa_runtime import ClipIQARuntime
from app.runtimes.scorers.image_reward_runtime import ImageRewardRuntime

DEFAULT_SCORING_MODEL_NAME = "electric-score-v1"
SELF_TRAINED_SCORING_MODEL_NAME = "electric-score-v2"
SELF_TRAINED_SCORING_MODEL_NAMES = {
    "electric-score-v2",
    "electric-score-v3",
}
HYBRID_RUNTIME_TYPE = "hybrid"
TOKEN_PATTERN = re.compile(r"[a-z0-9_]+")
DEFAULT_TARGET_COLUMNS = [
    "text_consistency",
    "visual_fidelity",
    "composition_aesthetics",
    "physical_plausibility",
]
DEFAULT_TOTAL_WEIGHTS = {
    "visual_fidelity": 0.21,
    "text_consistency": 0.37,
    "physical_plausibility": 0.24,
    "composition_aesthetics": 0.18,
}
PROMPT_CLASS_ALIASES = {
    "substation": {"transformer", "busbar", "frame", "insulator"},
    "transformer": {"transformer"},
    "transformers": {"transformer"},
    "busbar": {"busbar"},
    "busbars": {"busbar"},
    "tower": {"tower", "conductor", "insulator"},
    "towers": {"tower", "conductor", "insulator"},
    "transmission line": {"tower", "conductor", "insulator"},
    "transmission lines": {"tower", "conductor", "insulator"},
    "conductor": {"conductor"},
    "conductors": {"conductor"},
    "insulator": {"insulator"},
    "insulators": {"insulator"},
    "switch": {"switch"},
    "switches": {"switch"},
    "breaker": {"breaker"},
    "breakers": {"breaker"},
    "arrester": {"arrester"},
    "arresters": {"arrester"},
    "frame": {"frame"},
    "frames": {"frame"},
    "wind turbine": {"wind_turbine"},
    "wind turbines": {"wind_turbine"},
    "wind farm": {"wind_turbine"},
    "wind farms": {"wind_turbine"},
}
GENERIC_ELECTRIC_TERMS = {
    "electric",
    "electrical",
    "power",
    "substation",
    "transformer",
    "tower",
    "transmission",
    "conductor",
    "insulator",
    "breaker",
    "switch",
    "busbar",
    "arrester",
    "wind",
    "turbine",
}


def encode_prompt(prompt: str, vocab: dict[str, int]) -> list[int]:
    tokens = [vocab.get(token, vocab["<unk>"]) for token in TOKEN_PATTERN.findall(prompt.lower())]
    return tokens or [vocab["<unk>"]]


def clamp_score(value: float) -> float:
    return round(max(0.0, min(100.0, float(value))), 2)


class FourDimScoreModel(nn.Module):
    def __init__(self, vocab_size: int, yolo_feature_dim: int, target_dim: int) -> None:
        super().__init__()
        backbone = efficientnet_b0(weights=None)
        self.image_backbone = backbone.features
        self.avgpool = nn.AdaptiveAvgPool2d(1)
        self.prompt_embedding = nn.EmbeddingBag(vocab_size, 64, mode="mean")
        self.yolo_encoder = nn.Sequential(
            nn.Linear(yolo_feature_dim, 64),
            nn.SiLU(),
            nn.Dropout(0.10),
            nn.Linear(64, 32),
            nn.SiLU(),
        )
        self.fusion = nn.Sequential(
            nn.Linear(1280 + 64 + 32, 512),
            nn.SiLU(),
            nn.Dropout(0.18),
            nn.Linear(512, 256),
            nn.SiLU(),
            nn.Dropout(0.12),
        )
        self.heads = nn.ModuleList([nn.Linear(256, 1) for _ in range(target_dim)])

    def forward(
        self,
        images: torch.Tensor,
        prompt_ids: torch.Tensor,
        prompt_offsets: torch.Tensor,
        yolo_features: torch.Tensor,
    ) -> torch.Tensor:
        image_features = self.image_backbone(images)
        image_features = self.avgpool(image_features).flatten(1)
        prompt_features = self.prompt_embedding(prompt_ids, prompt_offsets)
        encoded_yolo = self.yolo_encoder(yolo_features)
        fused = self.fusion(torch.cat([image_features, prompt_features, encoded_yolo], dim=1))
        return torch.cat([head(fused) for head in self.heads], dim=1)


class PowerScoreRuntime:
    def __init__(
        self,
        bundle_dir: Path,
        device: str | None = None,
        *,
        text_runtime: Any | None = None,
        visual_runtime: Any | None = None,
        physical_runtime: Any | None = None,
        aesthetics_runtime: Any | None = None,
        yolo_runtime: Any | None = None,
    ) -> None:
        self.bundle_dir = Path(bundle_dir)
        self.device = torch.device(device or ("cuda" if torch.cuda.is_available() else "cpu"))
        self._config: dict[str, Any] | None = None
        self._runtime_type: str | None = None

        self._vocab: dict[str, int] | None = None
        self._model: FourDimScoreModel | None = None
        self._transform: transforms.Compose | None = None

        self._yolo = yolo_runtime
        self._text_runtime = text_runtime
        self._visual_runtime = visual_runtime
        self._physical_runtime = physical_runtime
        self._aesthetics_runtime = aesthetics_runtime

    def score_image(self, image_path: str, prompt: str) -> dict[str, float]:
        self._ensure_loaded()
        assert self._config is not None

        if self._runtime_type == HYBRID_RUNTIME_TYPE:
            return self._score_hybrid_image(image_path=image_path, prompt=prompt)
        return self._score_student_image(image_path=image_path, prompt=prompt)

    def unload(self) -> None:
        self._model = None
        self._vocab = None
        self._transform = None
        seen: set[int] = set()
        for runtime in (
            self._text_runtime,
            self._visual_runtime,
            self._physical_runtime,
            self._aesthetics_runtime,
        ):
            if runtime is None or id(runtime) in seen:
                continue
            seen.add(id(runtime))
            if hasattr(runtime, "unload"):
                runtime.unload()
        self._text_runtime = None
        self._visual_runtime = None
        self._physical_runtime = None
        self._aesthetics_runtime = None
        self._yolo = None
        if self.device.type == "cuda":
            torch.cuda.empty_cache()

    def _ensure_loaded(self) -> None:
        if self._config is None:
            config_path = self.bundle_dir / "bundle_config.json"
            if not config_path.exists():
                raise FileNotFoundError(f"self-trained scoring bundle is missing {config_path}")
            self._config = json.loads(config_path.read_text(encoding="utf-8"))
            self._runtime_type = self._config.get("runtime_type", "student")

        if self._runtime_type == HYBRID_RUNTIME_TYPE:
            self._ensure_hybrid_loaded()
            return
        self._ensure_student_loaded()

    def _ensure_hybrid_loaded(self) -> None:
        if self._text_runtime is None:
            self._text_runtime = ImageRewardRuntime()
        if self._visual_runtime is None:
            self._visual_runtime = ClipIQARuntime(mode="visual_fidelity")
        if self._physical_runtime is None:
            self._physical_runtime = self._visual_runtime
        if self._aesthetics_runtime is None:
            self._aesthetics_runtime = AestheticRuntime()
        if self._yolo is None:
            yolo_path = self.bundle_dir / "yolo_aux.pt"
            if yolo_path.exists():
                self._yolo = YOLO(str(yolo_path))

    def _ensure_student_loaded(self) -> None:
        if self._model is not None and self._yolo is not None and self._transform is not None:
            return

        assert self._config is not None
        vocab_path = self.bundle_dir / "vocab.json"
        model_path = self.bundle_dir / "student_best.pt"
        yolo_path = self.bundle_dir / "yolo_aux.pt"
        required = [vocab_path, model_path, yolo_path]
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
        self._yolo = YOLO(str(yolo_path))

    def _score_student_image(self, *, image_path: str, prompt: str) -> dict[str, float]:
        assert self._config is not None
        assert self._vocab is not None
        assert self._model is not None
        assert self._transform is not None

        image = Image.open(image_path).convert("RGB")
        image_tensor = self._transform(image).unsqueeze(0).to(self.device)
        prompt_ids = torch.tensor(encode_prompt(prompt, self._vocab), dtype=torch.long, device=self.device)
        prompt_offsets = torch.tensor([0], dtype=torch.long, device=self.device)
        yolo_features = torch.tensor([self._predict_yolo_features(image_path)], dtype=torch.float32, device=self.device)

        with torch.no_grad():
            output = self._model(image_tensor, prompt_ids, prompt_offsets, yolo_features)[0].detach().cpu().tolist()

        targets = self._config.get("targets", DEFAULT_TARGET_COLUMNS)
        values = {name: clamp_score(float(value)) for name, value in zip(targets, output)}
        total_weights = self._config.get("total_weights", DEFAULT_TOTAL_WEIGHTS)
        values["total_score"] = round(
            sum(values.get(name, 0.0) * total_weights.get(name, 0.0) for name in total_weights),
            2,
        )
        return values

    def _score_hybrid_image(self, *, image_path: str, prompt: str) -> dict[str, float]:
        assert self._config is not None
        image = Image.open(image_path).convert("RGB")
        detections = self._predict_detections(image_path)
        image_features = self._analyze_image(image=image, detections=detections)
        prompt_features = self._analyze_prompt(prompt=prompt, detections=detections)

        visual_base = self._call_runtime(self._visual_runtime, image_path, prompt, mode="visual_fidelity")
        physical_base = self._call_runtime(self._physical_runtime, image_path, prompt, mode="physical_plausibility")
        text_base = self._call_runtime(self._text_runtime, image_path, prompt)
        aesthetics_base = self._call_runtime(self._aesthetics_runtime, image_path, prompt)

        missing_expected = max(
            0,
            len(prompt_features["expected_classes"]) - len(prompt_features["matched_classes"]),
        )
        visual_fidelity = clamp_score(
            visual_base * 0.55
            + image_features["sharpness"] * 0.20
            + image_features["exposure"] * 0.15
            + image_features["contrast"] * 0.10
        )
        text_consistency = clamp_score(
            text_base * 0.72
            + prompt_features["keyword_coverage"] * 0.20
            + prompt_features["electric_presence"] * 0.08
            - min(18.0, missing_expected * 4.0)
        )
        physical_plausibility = clamp_score(
            physical_base * 0.55
            + prompt_features["topology"] * 0.25
            + prompt_features["keyword_coverage"] * 0.20
            - min(20.0, missing_expected * 5.0)
        )
        composition_aesthetics = clamp_score(
            aesthetics_base * 0.75
            + image_features["coverage"] * 0.15
            + image_features["balance"] * 0.10
        )

        values = {
            "visual_fidelity": visual_fidelity,
            "text_consistency": text_consistency,
            "physical_plausibility": physical_plausibility,
            "composition_aesthetics": composition_aesthetics,
        }
        total_weights = self._config.get("total_weights", DEFAULT_TOTAL_WEIGHTS)
        values["total_score"] = round(
            sum(values.get(name, 0.0) * total_weights.get(name, 0.0) for name in total_weights),
            2,
        )
        return values

    @staticmethod
    def _call_runtime(runtime: Any, image_path: str, prompt: str, mode: str | None = None) -> float:
        if runtime is None:
            return 50.0
        if mode is not None:
            try:
                return float(runtime.score_image(image_path, prompt, mode=mode))
            except TypeError:
                pass
        return float(runtime.score_image(image_path, prompt))

    def _predict_detections(self, image_path: str) -> list[dict[str, Any]]:
        if self._yolo is None:
            return []

        try:
            prediction = self._yolo.predict(
                source=image_path,
                imgsz=int(self._config.get("yolo_imgsz", 640)) if self._config else 640,
                conf=float(self._config.get("yolo_conf", 0.15)) if self._config else 0.15,
                iou=float(self._config.get("yolo_iou", 0.45)) if self._config else 0.45,
                device=0 if self.device.type == "cuda" else "cpu",
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
        if {"tower", "conductor"}.issubset(detected_classes):
            topology += 25.0
        if {"tower", "insulator"}.issubset(detected_classes):
            topology += 15.0
        if {"transformer", "busbar"}.issubset(detected_classes):
            topology += 20.0
        if {"transformer", "frame"}.issubset(detected_classes):
            topology += 12.0
        if {"transformer", "switch"}.issubset(detected_classes) or {"transformer", "breaker"}.issubset(detected_classes):
            topology += 10.0
        if "wind_turbine" in detected_classes:
            topology += 18.0
        topology += min(10.0, len(detected_classes) * 2.0)

        return {
            "expected_classes": expected_classes,
            "matched_classes": matched_classes,
            "keyword_coverage": clamp_score(keyword_coverage),
            "electric_presence": clamp_score(electric_presence if detected_classes else 30.0),
            "topology": clamp_score(topology if detected_classes else 28.0),
        }

    def _predict_yolo_features(self, image_path: str) -> list[float]:
        assert self._config is not None
        if self._yolo is None:
            classes = self._config.get("classes", [])
            return [0.0 for _ in range(len(classes) * 2 + 4)]

        classes = self._config.get("classes", [])
        class_index = {name: idx for idx, name in enumerate(classes)}
        result = self._yolo.predict(
            source=image_path,
            imgsz=640,
            conf=0.15,
            iou=0.45,
            device=0 if self.device.type == "cuda" else "cpu",
            verbose=False,
        )[0]

        counts = [0.0 for _ in classes]
        max_conf = [0.0 for _ in classes]
        areas: list[float] = []
        names = result.names or {}
        if result.boxes is not None:
            for cls_id, conf, xywhn in zip(
                result.boxes.cls.tolist(),
                result.boxes.conf.tolist(),
                result.boxes.xywhn.tolist(),
            ):
                class_name = names[int(cls_id)]
                if class_name not in class_index:
                    continue
                idx = class_index[class_name]
                counts[idx] += 1.0
                max_conf[idx] = max(max_conf[idx], float(conf))
                areas.append(float(xywhn[2] * xywhn[3]))

        max_count = max(sum(counts), 1.0)
        normalized_counts = [value / max_count for value in counts]
        coverage = float(sum(areas))
        mean_conf = float(sum(max_conf) / len(max_conf)) if max_conf else 0.0
        mean_area = float(sum(areas) / max(len(areas), 1))
        return normalized_counts + max_conf + [coverage, mean_conf, float(len(areas)), mean_area]


class PowerScoreRouter:
    def __init__(self, runtimes: dict[str, PowerScoreRuntime]) -> None:
        self._runtimes = dict(runtimes)

    def score_image_for_model(self, scoring_model_name: str, image_path: str, prompt: str) -> dict[str, float]:
        if scoring_model_name not in self._runtimes:
            raise ValueError(f"unsupported self-trained scoring model: {scoring_model_name}")
        return self._runtimes[scoring_model_name].score_image(image_path, prompt)

    def unload(self) -> None:
        for runtime in self._runtimes.values():
            runtime.unload()
