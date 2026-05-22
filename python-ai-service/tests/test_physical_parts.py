from training.scoring.physical_parts import PHYSICAL_PART_CLASS_NAMES, PHYSICAL_PARTS_BY_PARENT


def test_physical_part_specs_cover_core_parent_classes() -> None:
    assert set(PHYSICAL_PARTS_BY_PARENT) == {"wind_turbine"}


def test_physical_part_specs_include_expected_core_parts() -> None:
    assert "wind_blade" in PHYSICAL_PART_CLASS_NAMES
    assert PHYSICAL_PART_CLASS_NAMES == ["wind_blade"]
