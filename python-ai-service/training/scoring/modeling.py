from __future__ import annotations

import re

import torch
import torch.nn as nn
from torchvision.models import MobileNet_V3_Small_Weights, mobilenet_v3_small

TOKEN_PATTERN = re.compile(r"[a-z0-9_]+")
DEFAULT_TARGET_COLUMNS = [
    "visual_fidelity",
    "text_consistency",
    "physical_plausibility",
    "composition_aesthetics",
]
DEFAULT_TOTAL_WEIGHTS = {
    "visual_fidelity": 0.21,
    "text_consistency": 0.37,
    "physical_plausibility": 0.24,
    "composition_aesthetics": 0.18,
}
PROMPT_CLASS_ALIASES = {
    "substation": {"bus", "frame", "breaker", "switch", "arrester", "insulator", "tower"},
    "transformer": {"bushing", "frame", "switch"},
    "breaker": {"breaker"},
    "switch": {"switch"},
    "arrester": {"arrester"},
    "insulator": {"insulator"},
    "line": {"line", "tower", "insulator"},
    "transmission line": {"line", "tower", "insulator"},
    "tower": {"tower", "line", "insulator"},
    "busbar": {"bus"},
    "capacitor": {"capacitor"},
    "pipe": {"pipe"},
}
GENERIC_ELECTRIC_TERMS = {
    "electric",
    "electrical",
    "power",
    "substation",
    "transmission",
    "line",
    "tower",
    "insulator",
    "breaker",
    "switch",
    "arrester",
    "bus",
    "capacitor",
    "frame",
    "inspection",
}


def choose_training_device(preferred: str | None = None) -> torch.device:
    if preferred:
        normalized = preferred.strip().lower()
        if normalized == "cuda" and torch.cuda.is_available():
            return torch.device("cuda")
        if normalized == "mps" and getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
            return torch.device("mps")
        if normalized == "cpu":
            return torch.device("cpu")

    if torch.cuda.is_available():
        return torch.device("cuda")
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def encode_prompt(prompt: str, vocab: dict[str, int]) -> list[int]:
    tokens = [vocab.get(token, vocab["<unk>"]) for token in TOKEN_PATTERN.findall(prompt.lower())]
    return tokens or [vocab["<unk>"]]


def clamp_score(value: float) -> float:
    return round(max(0.0, min(100.0, float(value))), 2)


class FourDimScoreModel(nn.Module):
    def __init__(
        self,
        vocab_size: int,
        yolo_feature_dim: int,
        target_dim: int,
        *,
        pretrained_backbone: bool = False,
    ) -> None:
        super().__init__()
        backbone = mobilenet_v3_small(weights=MobileNet_V3_Small_Weights.DEFAULT if pretrained_backbone else None)
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
            nn.Linear(576 + 64 + 32, 256),
            nn.SiLU(),
            nn.Dropout(0.18),
            nn.Linear(256, 160),
            nn.SiLU(),
            nn.Dropout(0.12),
        )
        self.heads = nn.ModuleList([nn.Linear(160, 1) for _ in range(target_dim)])

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


def configure_image_backbone_trainability(backbone: nn.Sequential, trainable_stages: int) -> None:
    stages = list(backbone.children())
    keep_trainable = max(0, min(len(stages), int(trainable_stages)))

    for parameter in backbone.parameters():
        parameter.requires_grad = False

    if keep_trainable == 0:
        return

    for stage in stages[-keep_trainable:]:
        for parameter in stage.parameters():
            parameter.requires_grad = True
