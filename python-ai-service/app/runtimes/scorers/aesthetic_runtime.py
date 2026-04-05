from __future__ import annotations

"""构图美学评分运行时，使用 CLIP 特征配合 MLP 回归器输出美学分。"""

import gc
import shutil
from pathlib import Path
from pathlib import PureWindowsPath

import torch
import torch.nn as nn
from PIL import Image

from app.core.settings import get_settings

OLD_AESTHETIC_WEIGHT = Path(r"E:\毕业设计\源代码\Project\sac+logos+ava1-l14-linearMSE.pth")
AESTHETIC_WEIGHT_FILENAME = "sac+logos+ava1-l14-linearMSE.pth"


def _extract_weight_filename(path_like: str | Path) -> str:
    """兼容 Windows 路径和普通路径，提取最终权重文件名。"""
    raw_value = str(path_like)
    return PureWindowsPath(raw_value).name or Path(raw_value).name or AESTHETIC_WEIGHT_FILENAME


class AestheticPredictor(nn.Module):
    """旧项目迁移过来的美学回归头，输入 CLIP 特征，输出原始美学分。"""

    def __init__(self) -> None:
        """构建多层感知机结构，用于回归单一美学分值。"""
        super().__init__()
        self.layer0 = nn.Linear(1024, 128)
        self.layer2 = nn.Linear(128, 64)
        self.layer4 = nn.Linear(64, 16)
        self.layer6 = nn.Linear(16, 1)

    def forward(self, x):
        """执行前向传播，把 CLIP 特征映射为单维原始美学分。"""
        x = nn.functional.relu(self.layer0(x))
        x = nn.functional.dropout(x, p=0.2, training=self.training)
        x = nn.functional.relu(self.layer2(x))
        x = nn.functional.dropout(x, p=0.2, training=self.training)
        x = self.layer4(x)
        return self.layer6(x)


class AestheticRuntime:
    def __init__(
        self,
        *,
        device: str | None = None,
        clip_model_id: str = "openai/clip-vit-large-patch14",
        weight_path: Path | None = None,
    ) -> None:
        """初始化设备、CLIP 模型标识和可选的权重路径。"""
        self.device = device
        self.clip_model_id = clip_model_id
        self.weight_path = Path(weight_path) if weight_path else None
        self._clip_model = None
        self._clip_processor = None
        self._predictor = None

    def normalize_score(self, raw_score: float) -> float:
        """把原始美学回归分映射到 0-100，更贴近前端展示需求。"""
        if raw_score < 5.0:
            score = 10.0 + (raw_score - 1.0) * (50.0 / 4.0)
        else:
            score = 60.0 + (raw_score - 5.0) * (40.0 / 3.5)
        return round(max(0.0, min(100.0, score)), 2)

    def _resolve_device(self) -> str:
        """自动解析当前可用设备。"""
        if self.device:
            return self.device
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        return self.device

    def _resolve_weight_path(self) -> Path:
        """确定美学模型权重路径，并在必要时从旧项目复制到新目录。"""
        if self.weight_path is None:
            settings = get_settings()
            filename = _extract_weight_filename(OLD_AESTHETIC_WEIGHT)
            self.weight_path = settings.scoring_model_dir / "aesthetic-predictor" / filename
        self.weight_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.weight_path.exists() and OLD_AESTHETIC_WEIGHT.exists():
            shutil.copy2(OLD_AESTHETIC_WEIGHT, self.weight_path)
        return self.weight_path

    def _load_models(self) -> None:
        """懒加载 CLIP 与美学回归器，并完成旧权重到新结构的参数映射。"""
        if self._clip_model is not None and self._predictor is not None:
            return

        from transformers import CLIPModel, CLIPProcessor

        device = self._resolve_device()
        self._clip_model = CLIPModel.from_pretrained(self.clip_model_id).to(device)
        self._clip_model.eval()
        self._clip_processor = CLIPProcessor.from_pretrained(self.clip_model_id)

        state_dict = torch.load(self._resolve_weight_path(), map_location=device)
        mapped_state = {
            "layer0.weight": state_dict["layers.2.weight"],
            "layer0.bias": state_dict["layers.2.bias"],
            "layer2.weight": state_dict["layers.4.weight"],
            "layer2.bias": state_dict["layers.4.bias"],
            "layer4.weight": state_dict["layers.6.weight"],
            "layer4.bias": state_dict["layers.6.bias"],
            "layer6.weight": state_dict["layers.7.weight"],
            "layer6.bias": state_dict["layers.7.bias"],
        }

        self._predictor = AestheticPredictor().to(device)
        self._predictor.load_state_dict(mapped_state, strict=True)
        self._predictor.eval()

    def score_image(self, image_path: str, prompt: str = "") -> float:
        """提取图像特征并输出归一化后的构图美学分。"""
        self._load_models()
        image = Image.open(image_path).convert("RGB")
        inputs = self._clip_processor(images=image, return_tensors="pt")
        pixel_values = inputs["pixel_values"].to(self._resolve_device())

        with torch.no_grad():
            outputs = self._clip_model.vision_model(pixel_values=pixel_values)
            image_features = outputs.pooler_output
            image_features = image_features / image_features.norm(dim=-1, keepdim=True)
            raw_score = float(self._predictor(image_features).item())

        return self.normalize_score(raw_score)

    def unload(self) -> None:
        """释放 CLIP 与回归头权重，回收 CPU / GPU 内存。"""
        for attr in ("_clip_model", "_clip_processor", "_predictor"):
            value = getattr(self, attr)
            if value is not None:
                del value
                setattr(self, attr, None)
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
