from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class ScoringTrainingConfig:
    runtime_type: str = "hybrid"
    bundle_name: str = "electric-score-v3"
    source_detector_bundle_name: str = "electric-score-v2"
    targets: list[str] = field(
        default_factory=lambda: [
            "visual_fidelity",
            "text_consistency",
            "physical_plausibility",
            "composition_aesthetics",
        ]
    )
    total_weights: dict[str, float] = field(
        default_factory=lambda: {
            "visual_fidelity": 0.21,
            "text_consistency": 0.37,
            "physical_plausibility": 0.24,
            "composition_aesthetics": 0.18,
        }
    )
    classes: list[str] = field(
        default_factory=lambda: [
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
        ]
    )
    score_bands: list[dict[str, float | str]] = field(
        default_factory=lambda: [
            {"min": 0.0, "max": 30.0, "label": "E"},
            {"min": 30.0, "max": 50.0, "label": "D"},
            {"min": 50.0, "max": 70.0, "label": "C"},
            {"min": 70.0, "max": 85.0, "label": "B"},
            {"min": 85.0, "max": 100.0, "label": "A"},
        ]
    )

    def bundle_payload(self) -> dict[str, object]:
        return {
            "runtime_type": self.runtime_type,
            "targets": self.targets,
            "classes": self.classes,
            "total_weights": self.total_weights,
            "score_bands": self.score_bands,
            "teacher_models": {
                "text_consistency": "ImageReward-v1.0",
                "visual_fidelity": "CLIP-IQA/visual_fidelity",
                "physical_plausibility": "CLIP-IQA/physical_plausibility",
                "composition_aesthetics": "Aesthetic Predictor (CLIP-L14)",
            },
        }
