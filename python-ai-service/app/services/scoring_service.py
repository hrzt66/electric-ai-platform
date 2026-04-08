from __future__ import annotations

from pathlib import Path

from app.runtimes.scorers.power_score_runtime import (
    DEFAULT_SCORING_MODEL_NAME,
    SELF_TRAINED_SCORING_MODEL_NAME,
    SELF_TRAINED_SCORING_MODEL_NAMES,
)
from app.services.mock_scorer import score_from_prompt


class ScoringService:
    COMPONENT_WEIGHTS = {
        "visual_fidelity": 0.21,
        "text_consistency": 0.37,
        "physical_plausibility": 0.24,
        "composition_aesthetics": 0.18,
    }

    def __init__(
        self,
        *,
        visual_runtime=None,
        text_runtime=None,
        physical_runtime=None,
        aesthetics_runtime=None,
        shared_clip_runtime=None,
        bundle_runtime=None,
        release_after_batch: bool = False,
    ) -> None:
        self._visual_runtime = visual_runtime
        self._text_runtime = text_runtime
        self._physical_runtime = physical_runtime
        self._aesthetics_runtime = aesthetics_runtime
        self._shared_clip_runtime = shared_clip_runtime
        self._bundle_runtime = bundle_runtime
        self._release_after_batch = release_after_batch

    def combine_scores(
        self,
        *,
        visual_fidelity: float,
        text_consistency: float,
        physical_plausibility: float,
        composition_aesthetics: float,
    ) -> dict[str, float]:
        calibrated = {
            "visual_fidelity": self._compress_high_tail(visual_fidelity, knee=72.0, scale=0.38),
            "text_consistency": self._lift_low_band(text_consistency, target=52.0, gain=0.22),
            "physical_plausibility": self._compress_high_tail(physical_plausibility, knee=68.0, scale=0.45),
            "composition_aesthetics": self._compress_high_tail(composition_aesthetics, knee=70.0, scale=0.60),
        }
        total_score = round(
            sum(calibrated[name] * weight for name, weight in self.COMPONENT_WEIGHTS.items()),
            2,
        )
        return {
            **calibrated,
            "total_score": total_score,
        }

    def score_batch(self, job, images: list[dict]) -> list[dict]:
        scoring_model_name = getattr(job, "scoring_model_name", DEFAULT_SCORING_MODEL_NAME) or DEFAULT_SCORING_MODEL_NAME
        scored_items: list[dict] = []
        for image in images:
            image_path = image["file_path"]
            scores = self._score_image(
                image_path=image_path,
                prompt=job.prompt,
                scoring_model_name=scoring_model_name,
            )
            scored_items.append(
                {
                    "image_name": Path(image_path).name,
                    "file_path": image_path,
                    "model_name": job.model_name,
                    "scoring_model_name": scoring_model_name,
                    "positive_prompt": job.prompt,
                    "negative_prompt": job.negative_prompt,
                    "sampling_steps": job.steps,
                    "seed": image.get("seed", job.seed),
                    "guidance_scale": job.guidance_scale,
                    **scores,
                }
            )
        if self._release_after_batch:
            self.release_resources()
        return scored_items

    def _score_image(self, *, image_path: str, prompt: str, scoring_model_name: str) -> dict[str, float]:
        if scoring_model_name in SELF_TRAINED_SCORING_MODEL_NAMES:
            if self._bundle_runtime is None:
                raise RuntimeError("self-trained scoring runtime is not configured")
            if hasattr(self._bundle_runtime, "score_image_for_model"):
                return self._bundle_runtime.score_image_for_model(scoring_model_name, image_path, prompt)
            return self._bundle_runtime.score_image(image_path, prompt)

        if scoring_model_name != DEFAULT_SCORING_MODEL_NAME:
            raise ValueError(f"unsupported scoring model: {scoring_model_name}")

        return self._score_legacy_image(image_path=image_path, prompt=prompt)

    def _score_legacy_image(self, *, image_path: str, prompt: str) -> dict[str, float]:
        if self._text_runtime is None or self._aesthetics_runtime is None:
            return score_from_prompt(prompt)

        if self._shared_clip_runtime is not None:
            visual = float(self._shared_clip_runtime.score_image(image_path, prompt, mode="visual_fidelity"))
            physical = float(self._shared_clip_runtime.score_image(image_path, prompt, mode="physical_plausibility"))
        elif self._visual_runtime is not None and self._physical_runtime is not None:
            visual = float(self._visual_runtime.score_image(image_path, prompt))
            physical = float(self._physical_runtime.score_image(image_path, prompt))
        else:
            return score_from_prompt(prompt)

        text = float(self._text_runtime.score_image(image_path, prompt))
        aesthetics = float(self._aesthetics_runtime.score_image(image_path, prompt))
        return self.combine_scores(
            visual_fidelity=visual,
            text_consistency=text,
            physical_plausibility=physical,
            composition_aesthetics=aesthetics,
        )

    def release_resources(self) -> None:
        for runtime in (
            self._visual_runtime,
            self._text_runtime,
            self._physical_runtime,
            self._aesthetics_runtime,
            self._shared_clip_runtime,
            self._bundle_runtime,
        ):
            if runtime is not None and hasattr(runtime, "unload"):
                runtime.unload()

    @staticmethod
    def _compress_high_tail(score: float, *, knee: float, scale: float) -> float:
        bounded = max(0.0, min(100.0, float(score)))
        if bounded <= knee:
            return round(bounded, 2)
        return round(min(100.0, knee + (bounded - knee) * scale), 2)

    @staticmethod
    def _lift_low_band(score: float, *, target: float, gain: float) -> float:
        bounded = max(0.0, min(100.0, float(score)))
        if bounded >= target:
            return round(bounded, 2)
        return round(min(100.0, bounded + (target - bounded) * gain), 2)
