from __future__ import annotations

from pathlib import Path

from scripts.batch_generate_image2_dataset import (
    CATEGORY_SPECS,
    MODEL_TARGETS,
    BatchPlanner,
    ExistingAsset,
    classify_asset_category,
    iter_batch_seeds,
    next_output_path,
)


def test_model_targets_match_requested_distribution() -> None:
    assert MODEL_TARGETS == {
        "sd15-electric": 50,
        "ssd1b-electric": 50,
        "sd15-electric-specialized": 50,
        "gpt-image-2": 15,
    }
    assert len(CATEGORY_SPECS) == 7
    assert sum(MODEL_TARGETS.values()) == 165


def test_classify_asset_category_handles_prompt_variants() -> None:
    assert classify_asset_category("wind turbines") == "wind_turbine"
    assert classify_asset_category("Thermal Power Plant, realistic utility scene") == "thermal_power_plant"
    assert classify_asset_category("photovoltaic farm aerial inspection") == "photovoltaic_farm"
    assert classify_asset_category("unknown scene") is None


def test_next_output_path_uses_stable_numbering(tmp_path: Path) -> None:
    category = "substation"
    model = "sd15-electric"
    first = tmp_path / category / model / "substation_sd15-electric_001.png"
    second = tmp_path / category / model / "substation_sd15-electric_002.png"
    first.parent.mkdir(parents=True)
    first.write_bytes(b"existing")

    assert next_output_path(tmp_path, category, model) == second


def test_batch_planner_prefers_existing_output_then_asset() -> None:
    planner = BatchPlanner(output_root=Path("/dataset"))
    existing_output = Path("/dataset/dam/gpt-image-2/dam_gpt-image-2_001.png")
    assets = [
        ExistingAsset(
            category="dam",
            model_name="gpt-image-2",
            file_path=Path("/runtime/image/dam.png"),
            positive_prompt="dam",
            seed=42,
        )
    ]

    plan = planner.plan(
        category="dam",
        model_name="gpt-image-2",
        target_count=15,
        existing_outputs=[existing_output],
        reusable_assets=assets,
    )

    assert plan.existing_count == 1
    assert plan.copy_count == 1
    assert plan.generate_count == 13


def test_iter_batch_seeds_is_deterministic_and_sized() -> None:
    first = iter_batch_seeds(
        seed_base=20260509,
        category="dam",
        model_name="sd15-electric",
        start_count=2,
        batch_size=4,
    )
    second = iter_batch_seeds(
        seed_base=20260509,
        category="dam",
        model_name="sd15-electric",
        start_count=2,
        batch_size=4,
    )

    assert first == second
    assert len(first) == 4
    assert len(set(first)) == 4
