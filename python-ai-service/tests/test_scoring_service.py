from pathlib import Path


class FixedScorer:
    def __init__(self, score: float) -> None:
        self.score = score

    def score_image(self, image_path: str, prompt: str) -> float:
        return self.score


class ReleasableFixedScorer(FixedScorer):
    def __init__(self, score: float) -> None:
        super().__init__(score)
        self.unloaded = False

    def unload(self) -> None:
        self.unloaded = True


def build_job():
    from app.schemas.jobs import GenerateJob

    return GenerateJob(
        job_id=3,
        prompt="inspection robot in substation",
        negative_prompt="artifact",
        model_name="sd15-electric",
        seed=101,
        steps=30,
        guidance_scale=7.5,
        width=512,
        height=512,
        num_images=1,
    )


def test_scoring_service_builds_weighted_total():
    from app.services.scoring_service import ScoringService

    service = ScoringService()
    result = service.combine_scores(
        visual_fidelity=60,
        text_consistency=90,
        physical_plausibility=55,
        composition_aesthetics=60,
    )

    assert result["total_score"] == 69.9


def test_scoring_service_scores_batch_with_fixed_runtimes(tmp_path):
    from app.services.scoring_service import ScoringService

    image_path = tmp_path / "job-3.png"
    image_path.write_bytes(b"fake")

    service = ScoringService(
        visual_runtime=FixedScorer(60),
        text_runtime=FixedScorer(90),
        physical_runtime=FixedScorer(55),
        aesthetics_runtime=FixedScorer(60),
    )

    items = service.score_batch(
        job=build_job(),
        images=[{"file_path": str(image_path), "seed": 101}],
    )

    assert len(items) == 1
    assert items[0]["model_name"] == "sd15-electric"
    assert items[0]["total_score"] == 69.9


def test_scoring_service_rebalances_industrial_scores():
    from app.services.scoring_service import ScoringService

    service = ScoringService()
    result = service.combine_scores(
        visual_fidelity=99.98,
        text_consistency=39.52,
        physical_plausibility=75.65,
        composition_aesthetics=63.47,
    )

    assert result["visual_fidelity"] < 90.0
    assert result["text_consistency"] > 39.52
    assert result["physical_plausibility"] < 75.65
    assert result["composition_aesthetics"] <= 63.47
    assert result["total_score"] < 69.07


def test_scoring_service_releases_runtimes_after_batch_when_enabled(tmp_path):
    from app.services.scoring_service import ScoringService

    image_path = tmp_path / "job-3.png"
    image_path.write_bytes(b"fake")

    visual_runtime = ReleasableFixedScorer(60)
    text_runtime = ReleasableFixedScorer(90)
    physical_runtime = ReleasableFixedScorer(55)
    aesthetics_runtime = ReleasableFixedScorer(60)
    service = ScoringService(
        visual_runtime=visual_runtime,
        text_runtime=text_runtime,
        physical_runtime=physical_runtime,
        aesthetics_runtime=aesthetics_runtime,
        release_after_batch=True,
    )

    service.score_batch(
        job=build_job(),
        images=[{"file_path": str(image_path), "seed": 101}],
    )

    assert visual_runtime.unloaded is True
    assert text_runtime.unloaded is True
    assert physical_runtime.unloaded is True
    assert aesthetics_runtime.unloaded is True
