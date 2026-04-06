from __future__ import annotations

"""ImageReward 评分运行时，主要负责文本一致性评估。"""

import gc
import math
from pathlib import Path

from app.core.settings import get_settings
from app.core.torch_cuda import best_effort_cleanup_cuda


class ImageRewardRuntime:
    def __init__(
        self,
        *,
        device: str | None = None,
        model_name: str = "ImageReward-v1.0",
        download_root: Path | None = None,
    ) -> None:
        """记录模型名称、目标设备和模型下载目录。"""
        self.device = device
        self.model_name = model_name
        self.download_root = Path(download_root) if download_root else None
        self._model = None

    def normalize_score(self, raw_score: float) -> float:
        """把 ImageReward 原始分值压到 0-100 便于和其它维度统一展示。"""
        return round(max(0.0, min(100.0, 100.0 / (1.0 + math.exp(-raw_score)))), 2)

    def _resolve_device(self) -> str:
        """自动选择评分设备，优先 CUDA，其次 CPU。"""
        if self.device:
            return self.device

        import torch

        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        return self.device

    def _resolve_download_root(self) -> Path:
        """确定 ImageReward 权重的本地缓存目录。"""
        if self.download_root is None:
            settings = get_settings()
            self.download_root = settings.scoring_model_dir / "image-reward"
        self.download_root.mkdir(parents=True, exist_ok=True)
        return self.download_root

    def _load_model(self):
        """懒加载 ImageReward 模型，避免服务启动时直接下载或占用显存。"""
        if self._model is None:
            import ImageReward as reward

            self._model = reward.load(
                self.model_name,
                device=self._resolve_device(),
                download_root=str(self._resolve_download_root()),
            )
        return self._model

    def score_image(self, image_path: str, prompt: str) -> float:
        """对单张图片执行文图一致性评分，并返回归一化后的结果。"""
        model = self._load_model()
        raw_score = float(model.score(prompt, image_path))
        return self.normalize_score(raw_score)

    def unload(self) -> None:
        """释放 ImageReward 模型实例及 CUDA 缓存。"""
        if self._model is not None:
            del self._model
            self._model = None
        gc.collect()
        best_effort_cleanup_cuda(label="image-reward-unload")
