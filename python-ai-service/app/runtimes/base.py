from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class GeneratedImageRecord:
    file_path: str
    seed: int
    width: int
    height: int
    model_name: str
