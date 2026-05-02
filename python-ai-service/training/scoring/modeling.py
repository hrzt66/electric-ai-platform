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
    "substation": {"substation_primary", "bus", "bushing", "switch", "breaker", "arrester", "ct", "frame"},
    "switchyard": {"substation_primary"},
    "transformer": {"substation_primary", "bushing", "frame"},
    "breaker": {"substation_primary", "breaker"},
    "switch": {"substation_primary", "switch"},
    "busbar": {"substation_primary", "bus"},
    "capacitor": {"substation_primary", "capacitor"},
    "pipe": {"substation_primary", "pipe"},
    "transmission line": {"transmission_tower", "insulator_string", "tower", "insulator", "line"},
    "transmission tower": {"transmission_tower", "tower"},
    "tower": {"transmission_tower", "tower"},
    "insulator": {"insulator_string", "insulator"},
    "wind turbine": {"wind_turbine"},
    "wind farm": {"wind_turbine"},
    "photovoltaic": {"solar_panel"},
    "solar panel": {"solar_panel"},
    "solar farm": {"solar_panel"},
    "dam": {"dam"},
    "hydroelectric": {"dam"},
    "maintenance": {"maintenance_ppe"},
    "lineman": {"maintenance_ppe", "transmission_tower"},
    "linemen": {"maintenance_ppe", "transmission_tower"},
    "worker": {"maintenance_ppe"},
    "ppe": {"maintenance_ppe"},
    "helmet": {"maintenance_ppe"},
    "hardhat": {"maintenance_ppe"},
    "safety vest": {"maintenance_ppe"},
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
    "transformer",
    "switchyard",
    "wind",
    "turbine",
    "solar",
    "photovoltaic",
    "hydro",
    "dam",
    "lineman",
    "linemen",
    "maintenance",
    "ppe",
    "inspection",
}


def score_detected_topology(detected_classes: set[str]) -> float:
    if not detected_classes:
        return clamp_score(28.0)

    topology = 35.0

    if "substation_primary" in detected_classes or {"bus", "bushing"}.issubset(detected_classes):
        topology += 18.0
    if {"transmission_tower", "insulator_string"}.issubset(detected_classes) or {"tower", "insulator"}.issubset(detected_classes):
        topology += 24.0
    elif "transmission_tower" in detected_classes or "tower" in detected_classes:
        topology += 10.0
    elif "insulator_string" in detected_classes or "insulator" in detected_classes:
        topology += 8.0
    if "wind_turbine" in detected_classes:
        topology += 18.0
    if "solar_panel" in detected_classes:
        topology += 16.0
    if "dam" in detected_classes:
        topology += 18.0
    if "maintenance_ppe" in detected_classes:
        topology += 12.0
    if {"maintenance_ppe", "transmission_tower"}.issubset(detected_classes) or {"maintenance_ppe", "tower"}.issubset(detected_classes):
        topology += 12.0
    if {"tower", "line"}.issubset(detected_classes):
        topology += 12.0

    topology += min(10.0, len(detected_classes) * 2.0)
    return clamp_score(topology)


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
