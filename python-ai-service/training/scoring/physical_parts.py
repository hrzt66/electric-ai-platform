from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PhysicalPartSpec:
    class_name: str
    parent_class: str
    description: str


PHYSICAL_PART_SPECS: tuple[PhysicalPartSpec, ...] = (
    PhysicalPartSpec("wind_blade", "wind_turbine", "风机单个叶片"),
)


PHYSICAL_PART_CLASS_NAMES: list[str] = [item.class_name for item in PHYSICAL_PART_SPECS]


PHYSICAL_PARTS_BY_PARENT: dict[str, list[str]] = {}
for item in PHYSICAL_PART_SPECS:
    PHYSICAL_PARTS_BY_PARENT.setdefault(item.parent_class, []).append(item.class_name)
