from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.core.settings import Settings


@dataclass(slots=True)
class TrainingPaths:
    runtime_root: Path
    generation_dataset_root: Path
    scoring_dataset_root: Path
    generation_training_root: Path
    scoring_training_root: Path

    @classmethod
    def from_settings(cls, settings: Settings) -> "TrainingPaths":
        runtime_root = Path(settings.runtime_root)
        return cls(
            runtime_root=runtime_root,
            generation_dataset_root=runtime_root / "datasets" / "generation-v3",
            scoring_dataset_root=runtime_root / "datasets" / "scoring-v2",
            generation_training_root=runtime_root / "training" / "generation" / "sd15-electric-specialized-v2",
            scoring_training_root=runtime_root / "training" / "scoring" / "electric-score-v2",
        )

    def ensure_directories(self) -> None:
        for path in (
            self.generation_dataset_root,
            self.scoring_dataset_root,
            self.generation_training_root,
            self.scoring_training_root,
        ):
            path.mkdir(parents=True, exist_ok=True)
