from PIL import Image, ImageDraw

from training.scoring.rubric import (
    build_prompt_expectation,
    score_composition_aesthetics,
    score_physical_plausibility,
    score_physical_plausibility_with_details,
    score_text_consistency,
    score_visual_fidelity,
)


def _make_wind_turbine_image(*, blade_count: int, include_tower: bool) -> Image.Image:
    image = Image.new("RGB", (256, 256), color=(235, 242, 248))
    draw = ImageDraw.Draw(image)
    hub = (128, 92)
    if include_tower:
        draw.rectangle((118, 96, 138, 226), fill=(86, 92, 102))
    draw.ellipse((116, 80, 140, 104), fill=(88, 96, 106))
    blade_vectors = [
        (0, -62),
        (-54, 28),
        (54, 28),
    ]
    for dx, dy in blade_vectors[:blade_count]:
        draw.line((hub[0], hub[1], hub[0] + dx, hub[1] + dy), fill=(255, 255, 255), width=8)
    return image


def _make_transmission_tower_image(*, with_crossarm: bool, with_wires: bool) -> Image.Image:
    image = Image.new("RGB", (256, 256), color=(238, 244, 248))
    draw = ImageDraw.Draw(image)
    tower_color = (72, 78, 86)
    draw.line((128, 34, 86, 214), fill=tower_color, width=5)
    draw.line((128, 34, 170, 214), fill=tower_color, width=5)
    draw.line((86, 214, 170, 214), fill=tower_color, width=5)
    draw.line((106, 124, 150, 124), fill=tower_color, width=4)
    if with_crossarm:
        draw.line((64, 90, 192, 90), fill=tower_color, width=6)
        draw.line((88, 90, 98, 120), fill=tower_color, width=3)
        draw.line((168, 90, 158, 120), fill=tower_color, width=3)
    if with_wires:
        draw.line((0, 84, 88, 90), fill=(52, 58, 62), width=2)
        draw.line((168, 90, 255, 84), fill=(52, 58, 62), width=2)
    return image


def test_text_consistency_prefers_yolo_core_match_over_semantic_prior() -> None:
    prompt = "realistic transmission tower with visible insulator strings under blue sky"
    missing = score_text_consistency(
        prompt=prompt,
        detections=[{"class_name": "solar_panel", "confidence": 0.94, "bbox": [0.5, 0.5, 0.4, 0.3]}],
        semantic_prior=96.0,
    )
    matched = score_text_consistency(
        prompt=prompt,
        detections=[
            {"class_name": "transmission_tower", "confidence": 0.96, "bbox": [0.48, 0.50, 0.18, 0.72]},
            {"class_name": "insulator_string", "confidence": 0.89, "bbox": [0.57, 0.38, 0.10, 0.18]},
        ],
        semantic_prior=72.0,
    )

    assert missing <= 49.0
    assert matched >= 85.0
    assert matched > missing + 30.0


def test_prompt_expectation_recognizes_underscore_style_target_names() -> None:
    expectation = build_prompt_expectation(
        "realistic electric power inspection photo with wind_turbine and transmission_tower",
        detections=[],
    )

    assert expectation.expected_classes == {"wind_turbine", "transmission_tower"}

    missing = score_text_consistency(
        prompt="realistic electric power inspection photo with wind_turbine",
        detections=[],
        semantic_prior=57.97,
    )

    assert missing < 52.0


def test_text_consistency_rewards_high_confidence_match_more_than_low_confidence_match() -> None:
    prompt = "realistic electric power inspection photo with wind_turbine"
    low_confidence = score_text_consistency(
        prompt=prompt,
        detections=[{"class_name": "wind_turbine", "confidence": 0.24, "bbox": [0.5, 0.5, 0.4, 0.6]}],
        semantic_prior=60.0,
    )
    high_confidence = score_text_consistency(
        prompt=prompt,
        detections=[{"class_name": "wind_turbine", "confidence": 0.92, "bbox": [0.5, 0.5, 0.4, 0.6]}],
        semantic_prior=60.0,
    )

    assert low_confidence < high_confidence
    assert high_confidence - low_confidence >= 20.0


def test_visual_fidelity_rewards_sharp_and_well_exposed_images() -> None:
    degraded = score_visual_fidelity(
        image_metrics={
            "sharpness": 18.0,
            "exposure": 34.0,
            "contrast": 28.0,
        },
        detections=[{"class_name": "wind_turbine", "confidence": 0.92, "bbox": [0.5, 0.5, 0.40, 0.72]}],
        semantic_prior=58.0,
    )
    crisp = score_visual_fidelity(
        image_metrics={
            "sharpness": 72.0,
            "exposure": 82.0,
            "contrast": 66.0,
        },
        detections=[{"class_name": "wind_turbine", "confidence": 0.92, "bbox": [0.5, 0.5, 0.40, 0.72]}],
        semantic_prior=86.0,
    )

    assert degraded < 70.0
    assert crisp >= 85.0
    assert crisp > degraded + 20.0


def test_visual_fidelity_rewards_clean_bright_scene_even_with_moderate_sharpness_proxy() -> None:
    clean_scene = score_visual_fidelity(
        image_metrics={
            "sharpness": 38.99,
            "exposure": 94.07,
            "contrast": 81.53,
        },
        detections=[{"class_name": "wind_turbine", "confidence": 0.67, "bbox": [0.285, 0.387, 0.218, 0.672]}],
        semantic_prior=55.75,
    )

    assert clean_scene >= 80.0


def test_visual_fidelity_does_not_overreward_blurry_scene_with_good_exposure() -> None:
    blurry = score_visual_fidelity(
        image_metrics={
            "sharpness": 18.0,
            "exposure": 94.07,
            "contrast": 81.53,
        },
        detections=[{"class_name": "wind_turbine", "confidence": 0.67, "bbox": [0.285, 0.387, 0.218, 0.672]}],
        semantic_prior=55.75,
    )

    assert blurry < 70.0


def test_visual_fidelity_rewards_clear_transmission_tower_scene() -> None:
    crisp = score_visual_fidelity(
        image_metrics={
            "sharpness": 42.0,
            "exposure": 88.0,
            "contrast": 76.0,
        },
        detections=[{"class_name": "transmission_tower", "confidence": 0.86, "bbox": [0.32, 0.54, 0.18, 0.78]}],
        semantic_prior=52.0,
    )

    assert crisp >= 78.0


def test_visual_fidelity_rewards_dense_substation_detail() -> None:
    crisp = score_visual_fidelity(
        image_metrics={
            "sharpness": 40.0,
            "exposure": 85.0,
            "contrast": 74.0,
        },
        detections=[{"class_name": "substation_primary", "confidence": 0.92, "bbox": [0.50, 0.58, 0.68, 0.46]}],
        semantic_prior=58.0,
    )

    assert crisp >= 78.0


def test_visual_fidelity_rewards_clean_solar_array_scene() -> None:
    crisp = score_visual_fidelity(
        image_metrics={
            "sharpness": 32.0,
            "exposure": 90.0,
            "contrast": 82.0,
        },
        detections=[{"class_name": "photovoltaic_farm", "confidence": 0.91, "bbox": [0.56, 0.64, 0.72, 0.22]}],
        semantic_prior=54.0,
    )

    assert crisp >= 80.0


def test_visual_fidelity_rewards_clear_dam_scene() -> None:
    crisp = score_visual_fidelity(
        image_metrics={
            "sharpness": 30.0,
            "exposure": 86.0,
            "contrast": 72.0,
        },
        detections=[{"class_name": "dam", "confidence": 0.88, "bbox": [0.50, 0.56, 0.78, 0.32]}],
        semantic_prior=56.0,
    )

    assert crisp >= 76.0


def test_composition_aesthetics_penalizes_off_balance_clutter() -> None:
    balanced = score_composition_aesthetics(
        image_metrics={
            "exposure": 78.0,
            "contrast": 62.0,
        },
        detections=[
            {"class_name": "wind_turbine", "confidence": 0.94, "bbox": [0.50, 0.52, 0.22, 0.64]},
            {"class_name": "wind_turbine", "confidence": 0.90, "bbox": [0.26, 0.54, 0.16, 0.52]},
            {"class_name": "wind_turbine", "confidence": 0.88, "bbox": [0.74, 0.53, 0.16, 0.50]},
        ],
        semantic_prior=82.0,
    )
    cluttered = score_composition_aesthetics(
        image_metrics={
            "exposure": 44.0,
            "contrast": 36.0,
        },
        detections=[
            {"class_name": "substation_primary", "confidence": 0.95, "bbox": [0.90, 0.15, 0.40, 0.50]},
            {"class_name": "transmission_tower", "confidence": 0.86, "bbox": [0.85, 0.20, 0.34, 0.56]},
            {"class_name": "insulator_string", "confidence": 0.80, "bbox": [0.82, 0.14, 0.18, 0.20]},
            {"class_name": "solar_panel", "confidence": 0.79, "bbox": [0.76, 0.18, 0.28, 0.24]},
        ],
        semantic_prior=61.0,
    )

    assert balanced >= 80.0
    assert cluttered < 70.0
    assert balanced > cluttered + 15.0


def test_composition_aesthetics_rewards_orderly_wind_farm_layout() -> None:
    orderly = score_composition_aesthetics(
        image_metrics={
            "exposure": 80.0,
            "contrast": 60.0,
        },
        detections=[
            {"class_name": "wind_turbine", "confidence": 0.95, "bbox": [0.50, 0.52, 0.20, 0.62]},
            {"class_name": "wind_turbine", "confidence": 0.92, "bbox": [0.28, 0.55, 0.14, 0.46]},
            {"class_name": "wind_turbine", "confidence": 0.90, "bbox": [0.72, 0.55, 0.14, 0.46]},
        ],
        semantic_prior=78.0,
    )
    chaotic = score_composition_aesthetics(
        image_metrics={
            "exposure": 80.0,
            "contrast": 60.0,
        },
        detections=[
            {"class_name": "wind_turbine", "confidence": 0.95, "bbox": [0.88, 0.18, 0.22, 0.70]},
            {"class_name": "wind_turbine", "confidence": 0.92, "bbox": [0.74, 0.82, 0.18, 0.58]},
            {"class_name": "wind_turbine", "confidence": 0.90, "bbox": [0.15, 0.24, 0.18, 0.52]},
        ],
        semantic_prior=78.0,
    )

    assert orderly >= 78.0
    assert chaotic < 65.0
    assert orderly > chaotic + 12.0


def test_composition_aesthetics_rewards_linear_transmission_tower_flow() -> None:
    aligned = score_composition_aesthetics(
        image_metrics={
            "exposure": 76.0,
            "contrast": 58.0,
        },
        detections=[
            {"class_name": "transmission_tower", "confidence": 0.95, "bbox": [0.22, 0.54, 0.12, 0.58]},
            {"class_name": "transmission_tower", "confidence": 0.94, "bbox": [0.50, 0.50, 0.14, 0.68]},
            {"class_name": "transmission_tower", "confidence": 0.92, "bbox": [0.80, 0.46, 0.12, 0.56]},
        ],
        semantic_prior=74.0,
    )
    messy = score_composition_aesthetics(
        image_metrics={
            "exposure": 76.0,
            "contrast": 58.0,
        },
        detections=[
            {"class_name": "transmission_tower", "confidence": 0.95, "bbox": [0.88, 0.18, 0.20, 0.68]},
            {"class_name": "transmission_tower", "confidence": 0.94, "bbox": [0.82, 0.78, 0.22, 0.62]},
            {"class_name": "transmission_tower", "confidence": 0.92, "bbox": [0.16, 0.20, 0.18, 0.58]},
        ],
        semantic_prior=74.0,
    )

    assert aligned >= 76.0
    assert messy < 65.0
    assert aligned > messy + 10.0


def test_composition_aesthetics_rewards_regular_solar_array() -> None:
    regular = score_composition_aesthetics(
        image_metrics={
            "exposure": 78.0,
            "contrast": 64.0,
        },
        detections=[
            {"class_name": "solar_panel", "confidence": 0.95, "bbox": [0.50, 0.60, 0.58, 0.28]},
        ],
        semantic_prior=76.0,
    )
    awkward = score_composition_aesthetics(
        image_metrics={
            "exposure": 78.0,
            "contrast": 64.0,
        },
        detections=[
            {"class_name": "solar_panel", "confidence": 0.95, "bbox": [0.86, 0.22, 0.60, 0.26]},
        ],
        semantic_prior=76.0,
    )

    assert regular >= 74.0
    assert awkward < 64.0
    assert regular > awkward + 10.0


def test_composition_aesthetics_rewards_hero_wind_turbine_rule_of_thirds_layout() -> None:
    hero_layout = score_composition_aesthetics(
        image_metrics={
            "exposure": 94.07,
            "contrast": 81.53,
        },
        detections=[
            {"class_name": "wind_turbine", "confidence": 0.67, "bbox": [0.285, 0.387, 0.218, 0.672]},
        ],
        semantic_prior=47.0,
    )
    awkward_crop = score_composition_aesthetics(
        image_metrics={
            "exposure": 94.07,
            "contrast": 81.53,
        },
        detections=[
            {"class_name": "wind_turbine", "confidence": 0.67, "bbox": [0.10, 0.387, 0.218, 0.672]},
        ],
        semantic_prior=47.0,
    )

    assert hero_layout >= 72.0
    assert awkward_crop < 62.0
    assert hero_layout > awkward_crop + 12.0


def test_composition_aesthetics_rewards_hero_transmission_tower_layout() -> None:
    hero_layout = score_composition_aesthetics(
        image_metrics={
            "exposure": 90.0,
            "contrast": 74.0,
        },
        detections=[
            {"class_name": "transmission_tower", "confidence": 0.82, "bbox": [0.32, 0.54, 0.18, 0.78]},
        ],
        semantic_prior=46.0,
    )
    edge_crop = score_composition_aesthetics(
        image_metrics={
            "exposure": 90.0,
            "contrast": 74.0,
        },
        detections=[
            {"class_name": "transmission_tower", "confidence": 0.82, "bbox": [0.08, 0.54, 0.18, 0.78]},
        ],
        semantic_prior=46.0,
    )

    assert hero_layout >= 70.0
    assert edge_crop < 60.0
    assert hero_layout > edge_crop + 10.0


def test_composition_aesthetics_rewards_orderly_substation_layout() -> None:
    orderly = score_composition_aesthetics(
        image_metrics={
            "exposure": 84.0,
            "contrast": 60.0,
        },
        detections=[
            {"class_name": "substation_primary", "confidence": 0.90, "bbox": [0.50, 0.66, 0.70, 0.36]},
        ],
        semantic_prior=55.0,
    )
    awkward = score_composition_aesthetics(
        image_metrics={
            "exposure": 84.0,
            "contrast": 60.0,
        },
        detections=[
            {"class_name": "substation_primary", "confidence": 0.90, "bbox": [0.84, 0.24, 0.70, 0.36]},
        ],
        semantic_prior=55.0,
    )

    assert orderly >= 76.0
    assert awkward < 58.0
    assert orderly > awkward + 16.0


def test_composition_aesthetics_rewards_panorama_solar_layout() -> None:
    panorama = score_composition_aesthetics(
        image_metrics={
            "exposure": 88.0,
            "contrast": 70.0,
        },
        detections=[
            {"class_name": "solar_panel", "confidence": 0.90, "bbox": [0.56, 0.64, 0.72, 0.22]},
        ],
        semantic_prior=56.0,
    )
    awkward = score_composition_aesthetics(
        image_metrics={
            "exposure": 88.0,
            "contrast": 70.0,
        },
        detections=[
            {"class_name": "solar_panel", "confidence": 0.90, "bbox": [0.84, 0.22, 0.72, 0.22]},
        ],
        semantic_prior=56.0,
    )

    assert panorama >= 78.0
    assert awkward < 58.0
    assert panorama > awkward + 16.0


def test_composition_aesthetics_rewards_centered_dam_span() -> None:
    centered = score_composition_aesthetics(
        image_metrics={
            "exposure": 82.0,
            "contrast": 58.0,
        },
        detections=[
            {"class_name": "dam", "confidence": 0.93, "bbox": [0.50, 0.56, 0.78, 0.32]},
        ],
        semantic_prior=57.0,
    )
    awkward = score_composition_aesthetics(
        image_metrics={
            "exposure": 82.0,
            "contrast": 58.0,
        },
        detections=[
            {"class_name": "dam", "confidence": 0.93, "bbox": [0.82, 0.22, 0.78, 0.32]},
        ],
        semantic_prior=57.0,
    )

    assert centered >= 74.0
    assert awkward < 58.0
    assert centered > awkward + 16.0


def test_physical_plausibility_rewards_electrical_topology_rules() -> None:
    plausible = score_physical_plausibility(
        prompt="realistic transmission tower with visible insulator strings",
        detections=[
            {"class_name": "transmission_tower", "confidence": 0.97, "bbox": [0.48, 0.50, 0.16, 0.70]},
            {"class_name": "insulator_string", "confidence": 0.91, "bbox": [0.57, 0.40, 0.10, 0.16]},
        ],
        semantic_prior=76.0,
    )
    implausible = score_physical_plausibility(
        prompt="realistic transmission tower with visible insulator strings",
        detections=[
            {"class_name": "transmission_tower", "confidence": 0.90, "bbox": [0.50, 0.52, 0.92, 0.96]},
        ],
        semantic_prior=78.0,
    )

    assert plausible >= 80.0
    assert implausible < 70.0
    assert plausible > implausible + 30.0


def test_physical_plausibility_rewards_single_object_dam_scene() -> None:
    plausible = score_physical_plausibility(
        prompt="realistic electric power inspection photo with dam",
        detections=[
            {"class_name": "dam", "confidence": 0.93, "bbox": [0.52, 0.56, 0.64, 0.46]},
        ],
        semantic_prior=58.0,
    )
    missing = score_physical_plausibility(
        prompt="realistic electric power inspection photo with dam",
        detections=[],
        semantic_prior=58.0,
    )

    assert plausible >= 75.0
    assert missing <= 45.0
    assert plausible > missing + 25.0


def test_physical_plausibility_rewards_single_object_substation_scene() -> None:
    plausible = score_physical_plausibility(
        prompt="realistic electric power inspection photo with substation_primary",
        detections=[
            {"class_name": "substation_primary", "confidence": 0.95, "bbox": [0.50, 0.54, 0.62, 0.52]},
        ],
        semantic_prior=62.0,
    )
    missing = score_physical_plausibility(
        prompt="realistic electric power inspection photo with substation_primary",
        detections=[],
        semantic_prior=62.0,
    )

    assert plausible >= 72.0
    assert missing <= 45.0
    assert plausible > missing + 25.0


def test_physical_plausibility_accepts_single_subject_dam_scene() -> None:
    plausible = score_physical_plausibility(
        prompt="realistic electric power inspection photo with dam",
        detections=[
            {"class_name": "dam", "confidence": 0.94, "bbox": [0.51, 0.56, 0.62, 0.54]},
        ],
        semantic_prior=41.63,
    )

    assert plausible >= 70.0


def test_physical_plausibility_accepts_single_subject_substation_scene() -> None:
    plausible = score_physical_plausibility(
        prompt="realistic electric power inspection photo with substation_primary",
        detections=[
            {"class_name": "substation_primary", "confidence": 0.95, "bbox": [0.50, 0.53, 0.58, 0.50]},
        ],
        semantic_prior=47.88,
    )

    assert plausible >= 72.0


def test_physical_plausibility_tolerates_large_extent_for_dam_scene() -> None:
    plausible = score_physical_plausibility(
        prompt="dam",
        detections=[
            {"class_name": "dam", "confidence": 0.513, "bbox": [0.5001, 0.4955, 0.9997, 0.9754]},
        ],
        semantic_prior=41.63,
    )

    assert plausible >= 70.0


def test_physical_plausibility_tolerates_large_extent_for_substation_scene() -> None:
    plausible = score_physical_plausibility(
        prompt="realistic electric power inspection photo with substation_primary",
        detections=[
            {"class_name": "substation", "confidence": 0.6051, "bbox": [0.5017, 0.5031, 0.9965, 0.9571]},
        ],
        semantic_prior=47.88,
    )

    assert plausible >= 70.0


def test_physical_plausibility_returns_rule_breakdown_for_wind_turbine() -> None:
    result = score_physical_plausibility_with_details(
        prompt="realistic electric power inspection photo with wind_turbine",
        detections=[
            {"class_name": "wind_turbine", "confidence": 0.91, "bbox": [0.50, 0.52, 0.22, 0.68]},
        ],
        semantic_prior=66.0,
    )

    assert result.target_class == "wind_turbine"
    assert result.checks
    assert any(item.key == "blade_count_proxy" for item in result.checks)
    assert any(item.key == "tower_support_proxy" for item in result.checks)


def test_physical_plausibility_rewards_detected_insulator_for_transmission_tower() -> None:
    with_insulator = score_physical_plausibility(
        prompt="realistic transmission tower with visible insulator strings",
        detections=[
            {"class_name": "transmission_tower", "confidence": 0.95, "bbox": [0.48, 0.50, 0.18, 0.72]},
            {"class_name": "insulator_string", "confidence": 0.89, "bbox": [0.57, 0.40, 0.10, 0.16]},
        ],
        semantic_prior=68.0,
    )
    without_insulator = score_physical_plausibility(
        prompt="realistic transmission tower with visible insulator strings",
        detections=[
            {"class_name": "transmission_tower", "confidence": 0.95, "bbox": [0.48, 0.50, 0.18, 0.72]},
        ],
        semantic_prior=68.0,
    )

    assert with_insulator > without_insulator


def test_physical_plausibility_prefers_complete_wind_turbine_structure() -> None:
    complete = score_physical_plausibility_with_details(
        prompt="realistic electric power inspection photo with wind_turbine",
        detections=[
            {"class_name": "wind_turbine", "confidence": 0.94, "bbox": [0.5, 0.52, 0.34, 0.78]},
        ],
        semantic_prior=68.0,
        image=_make_wind_turbine_image(blade_count=3, include_tower=True),
    )
    incomplete = score_physical_plausibility_with_details(
        prompt="realistic electric power inspection photo with wind_turbine",
        detections=[
            {"class_name": "wind_turbine", "confidence": 0.94, "bbox": [0.5, 0.52, 0.34, 0.78]},
        ],
        semantic_prior=68.0,
        image=_make_wind_turbine_image(blade_count=1, include_tower=False),
    )

    assert complete.score > incomplete.score
    complete_checks = {item.key: item.score for item in complete.checks}
    incomplete_checks = {item.key: item.score for item in incomplete.checks}
    assert complete_checks["tower_support_proxy"] > incomplete_checks["tower_support_proxy"]


def test_physical_plausibility_prefers_transmission_tower_with_crossarm_and_wires() -> None:
    complete = score_physical_plausibility_with_details(
        prompt="realistic transmission tower with visible insulator strings",
        detections=[
            {"class_name": "transmission_tower", "confidence": 0.95, "bbox": [0.5, 0.5, 0.48, 0.78]},
            {"class_name": "insulator_string", "confidence": 0.88, "bbox": [0.36, 0.35, 0.06, 0.10]},
        ],
        semantic_prior=70.0,
        image=_make_transmission_tower_image(with_crossarm=True, with_wires=True),
    )
    partial = score_physical_plausibility_with_details(
        prompt="realistic transmission tower with visible insulator strings",
        detections=[
            {"class_name": "transmission_tower", "confidence": 0.95, "bbox": [0.5, 0.5, 0.48, 0.78]},
        ],
        semantic_prior=70.0,
        image=_make_transmission_tower_image(with_crossarm=False, with_wires=False),
    )

    assert complete.score > partial.score
    complete_checks = {item.key: item.score for item in complete.checks}
    partial_checks = {item.key: item.score for item in partial.checks}
    assert complete_checks["insulator_support"] > partial_checks["insulator_support"]
