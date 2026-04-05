from __future__ import annotations

import gc
from pathlib import Path

import torch
from PIL import Image


class ClipIQARuntime:
    POSITIVE_PROMPTS = {
        "visual_fidelity": [
            "sharp substation photograph with legible busbars insulators and conductors",
            "high fidelity industrial scene with realistic transformer and switchgear details",
            "well exposed electrical yard photo with natural metal texture and clean edges",
            "credible power equipment image without painterly blur or melted structures",
        ],
        "physical_plausibility": [
            "electrical equipment connected through believable terminals and support structures",
            "insulator strings carrying conductors with realistic sag and anchor points",
            "substation geometry that respects clearance spacing and structural stability",
            "power scene with grounded equipment and physically consistent cable routing",
        ],
    }
    NEGATIVE_PROMPTS = {
        "visual_fidelity": [
            "blurry synthetic image with smeared electrical details",
            "artifact heavy industrial render with warped conductors and noisy edges",
            "oversmoothed scene where insulators busbars and terminals melt together",
            "low fidelity power photo with distorted textures and broken silhouettes",
        ],
        "physical_plausibility": [
            "floating electrical equipment with impossible support geometry",
            "conductors that do not attach to insulators or terminals",
            "unsafe clearance spacing and impossible substation topology",
            "deformed structure with physically impossible cable routing",
        ],
    }

    def __init__(self, *, mode: str, device: str | None = None, clip_model_id: str = "openai/clip-vit-large-patch14") -> None:
        self.mode = mode
        self.device = device
        self.clip_model_id = clip_model_id
        self._clip_model = None
        self._clip_processor = None

    def normalize_probability_score(self, avg_positive: float, avg_negative: float) -> float:
        total = avg_positive + avg_negative
        if total <= 0:
            return 50.0
        return round((avg_positive / total) * 100.0, 2)

    def _resolve_device(self) -> str:
        if self.device:
            return self.device
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        return self.device

    def _load_models(self) -> None:
        if self._clip_model is not None and self._clip_processor is not None:
            return

        from transformers import CLIPModel, CLIPProcessor

        device = self._resolve_device()
        self._clip_model = CLIPModel.from_pretrained(self.clip_model_id).to(device)
        self._clip_model.eval()
        self._clip_processor = CLIPProcessor.from_pretrained(self.clip_model_id)

    def score_image(self, image_path: str, prompt: str = "", mode: str | None = None) -> float:
        self._load_models()
        image = Image.open(Path(image_path)).convert("RGB")

        active_mode = mode or self.mode
        positive_prompts = self.POSITIVE_PROMPTS[active_mode]
        negative_prompts = self.NEGATIVE_PROMPTS[active_mode]
        all_prompts = positive_prompts + negative_prompts

        inputs = self._clip_processor(text=all_prompts, images=image, return_tensors="pt", padding=True)
        inputs = {key: value.to(self._resolve_device()) for key, value in inputs.items()}

        with torch.no_grad():
            outputs = self._clip_model(**inputs)
            probabilities = outputs.logits_per_image.softmax(dim=-1)[0]

        positive_probs = probabilities[: len(positive_prompts)]
        negative_probs = probabilities[len(positive_prompts) :]
        return self.normalize_probability_score(float(positive_probs.mean().item()), float(negative_probs.mean().item()))

    def unload(self) -> None:
        for attr in ("_clip_model", "_clip_processor"):
            value = getattr(self, attr)
            if value is not None:
                del value
                setattr(self, attr, None)
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
