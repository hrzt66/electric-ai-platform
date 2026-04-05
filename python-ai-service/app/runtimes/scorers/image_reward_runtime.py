from __future__ import annotations

import gc
import math
from pathlib import Path

from app.core.settings import get_settings


class ImageRewardRuntime:
    def __init__(
        self,
        *,
        device: str | None = None,
        model_name: str = "ImageReward-v1.0",
        download_root: Path | None = None,
    ) -> None:
        self.device = device
        self.model_name = model_name
        self.download_root = Path(download_root) if download_root else None
        self._model = None

    def normalize_score(self, raw_score: float) -> float:
        return round(max(0.0, min(100.0, 100.0 / (1.0 + math.exp(-raw_score)))), 2)

    def _resolve_device(self) -> str:
        if self.device:
            return self.device

        import torch

        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        return self.device

    def _resolve_download_root(self) -> Path:
        if self.download_root is None:
            settings = get_settings()
            self.download_root = settings.scoring_model_dir / "image-reward"
        self.download_root.mkdir(parents=True, exist_ok=True)
        return self.download_root

    def _load_model(self):
        if self._model is None:
            import ImageReward as reward

            self._model = reward.load(
                self.model_name,
                device=self._resolve_device(),
                download_root=str(self._resolve_download_root()),
            )
        return self._model

    def score_image(self, image_path: str, prompt: str) -> float:
        model = self._load_model()
        raw_score = float(model.score(prompt, image_path))
        return self.normalize_score(raw_score)

    def unload(self) -> None:
        if self._model is not None:
            del self._model
            self._model = None
        gc.collect()
        try:
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            return
