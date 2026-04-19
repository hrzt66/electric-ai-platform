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


class BundleScorer:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []
        self.unloaded = False

    def score_image(self, image_path: str, prompt: str) -> dict[str, float]:
        self.calls.append((image_path, prompt))
        return {
            "visual_fidelity": 81.0,
            "text_consistency": 82.0,
            "physical_plausibility": 83.0,
            "composition_aesthetics": 84.0,
            "total_score": 82.5,
            "checked_image_path": "model/image_check/job-3.png",
            "score_explanation": {
                "checked_image_path": "model/image_check/job-3.png",
                "dimensions": {
                    "text_consistency": {
                        "uses_yolo": True,
                        "summary": "matched objects",
                        "formula": "demo",
                        "details": ["matched"],
                    }
                },
            },
        }

    def unload(self) -> None:
        self.unloaded = True


class RoutedBundleScorer:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str]] = []

    def score_image_for_model(self, scoring_model_name: str, image_path: str, prompt: str) -> dict[str, float]:
        self.calls.append((scoring_model_name, image_path, prompt))
        return {
            "visual_fidelity": 71.0,
            "text_consistency": 72.0,
            "physical_plausibility": 73.0,
            "composition_aesthetics": 74.0,
            "total_score": 72.5,
            "checked_image_path": "model/image_check/job-3.png",
            "score_explanation": {
                "checked_image_path": "model/image_check/job-3.png",
                "dimensions": {
                    "total_score": {
                        "uses_yolo": False,
                        "summary": "weighted total",
                        "formula": "weights",
                        "details": ["demo"],
                    }
                },
            },
        }


def build_job(*, scoring_model_name: str = "electric-score-v1"):
    from app.schemas.jobs import GenerateJob

    return GenerateJob(
        job_id=3,
        prompt="inspection robot in substation",
        negative_prompt="artifact",
        model_name="sd15-electric",
        scoring_model_name=scoring_model_name,
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


def test_scoring_service_uses_self_trained_bundle_runtime_when_requested(tmp_path):
    from app.services.scoring_service import ScoringService

    image_path = tmp_path / "job-3.png"
    image_path.write_bytes(b"fake")

    bundle_runtime = BundleScorer()
    service = ScoringService(
        text_runtime=FixedScorer(90),
        aesthetics_runtime=FixedScorer(60),
        shared_clip_runtime=FixedScorer(60),
        bundle_runtime=bundle_runtime,
    )

    items = service.score_batch(
        job=build_job(scoring_model_name="electric-score-v2"),
        images=[{"file_path": str(image_path), "seed": 101}],
    )

    assert bundle_runtime.calls == [(str(image_path), "inspection robot in substation")]
    assert items[0]["total_score"] == 82.5
    assert items[0]["checked_image_path"] == "model/image_check/job-3.png"
    assert items[0]["score_explanation"]["checked_image_path"] == "model/image_check/job-3.png"


def test_scoring_service_releases_bundle_runtime_after_batch_when_enabled(tmp_path):
    from app.services.scoring_service import ScoringService

    image_path = tmp_path / "job-3.png"
    image_path.write_bytes(b"fake")

    bundle_runtime = BundleScorer()
    service = ScoringService(
        bundle_runtime=bundle_runtime,
        release_after_batch=True,
    )

    service.score_batch(
        job=build_job(scoring_model_name="electric-score-v2"),
        images=[{"file_path": str(image_path), "seed": 101}],
    )

    assert bundle_runtime.unloaded is True


def test_scoring_service_routes_bundle_by_scoring_model_name(tmp_path):
    from app.services.scoring_service import ScoringService

    image_path = tmp_path / "job-3.png"
    image_path.write_bytes(b"fake")

    bundle_runtime = RoutedBundleScorer()
    service = ScoringService(bundle_runtime=bundle_runtime)

    items = service.score_batch(
        job=build_job(scoring_model_name="electric-score-v2"),
        images=[{"file_path": str(image_path), "seed": 101}],
    )

    assert bundle_runtime.calls == [("electric-score-v2", str(image_path), "inspection robot in substation")]
    assert items[0]["total_score"] == 72.5
    assert items[0]["score_explanation"]["dimensions"]["total_score"]["summary"] == "weighted total"
