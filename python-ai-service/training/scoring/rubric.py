from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np
from PIL import Image

try:
    import cv2
except Exception:  # pragma: no cover - optional runtime dependency guard
    cv2 = None

from training.scoring.modeling import (
    GENERIC_ELECTRIC_TERMS,
    TOKEN_PATTERN,
    clamp_score,
    score_detected_topology,
)

PROMPT_CORE_CLASS_ALIASES = {
    "substation": {"substation_primary"},
    "switchyard": {"substation_primary"},
    "transformer": {"substation_primary"},
    "busbar": {"substation_primary"},
    "transmission line": {"transmission_tower"},
    "transmission tower": {"transmission_tower"},
    "tower": {"transmission_tower"},
    "insulator": {"transmission_tower"},
    "insulator string": {"transmission_tower"},
    "wind turbine": {"wind_turbine"},
    "wind farm": {"wind_turbine"},
    "photovoltaic": {"solar_panel"},
    "solar panel": {"solar_panel"},
    "solar farm": {"solar_panel"},
    "dam": {"dam"},
    "hydroelectric": {"dam"},
}

DETECTION_CLASS_ALIASES = {
    "substation": "substation_primary",
    "transformer": "substation_primary",
    "bus": "substation_primary",
    "busbar": "substation_primary",
    "bushing": "substation_primary",
    "breaker": "substation_primary",
    "switch": "substation_primary",
    "arrester": "substation_primary",
    "capacitor": "substation_primary",
    "ct": "substation_primary",
    "frame": "substation_primary",
    "tower": "transmission_tower",
    "pylon": "transmission_tower",
    "pole": "transmission_tower",
    "line": "transmission_tower",
    "photovoltaic farm": "solar_panel",
    "solar farm": "solar_panel",
    "solar array": "solar_panel",
    "insulator": "insulator_string",
    "insulators": "insulator_string",
}

TARGET_CLASS_PRIORITY = {
    "transmission_tower": 0,
    "wind_turbine": 1,
    "substation_primary": 2,
    "solar_panel": 3,
    "dam": 4,
}


@dataclass(slots=True)
class PromptExpectation:
    expected_classes: set[str]
    detected_classes: set[str]
    matched_classes: set[str]
    generic_electric_prompt: bool


@dataclass(slots=True)
class PhysicalRuleCheck:
    key: str
    label: str
    score: float
    detail: str


@dataclass(slots=True)
class PhysicalPlausibilityResult:
    score: float
    target_class: str | None
    summary: str
    rule_score: float
    topology: float
    matched_quality: float
    geometry_penalty: float
    expectation: PromptExpectation
    checks: list[PhysicalRuleCheck]


def canonicalize_detection_class_name(class_name: str) -> str:
    lower_name = class_name.strip().lower().replace("-", " ").replace("_", " ")
    alias = DETECTION_CLASS_ALIASES.get(lower_name)
    if alias is not None:
        return alias
    return lower_name.replace(" ", "_")


def build_prompt_expectation(prompt: str, detections: list[dict[str, object]]) -> PromptExpectation:
    lower_prompt = prompt.lower()
    normalized_prompt = lower_prompt.replace("_", " ").replace("-", " ")
    prompt_tokens = set(TOKEN_PATTERN.findall(lower_prompt))
    expected_classes: set[str] = set()
    for phrase, aliases in PROMPT_CORE_CLASS_ALIASES.items():
        if phrase in normalized_prompt:
            expected_classes.update(aliases)

    detected_classes = {
        canonicalize_detection_class_name(str(item["class_name"]))
        for item in detections
        if float(item.get("confidence", 0.0)) >= 0.20
    }
    return PromptExpectation(
        expected_classes=expected_classes,
        detected_classes=detected_classes,
        matched_classes=expected_classes & detected_classes,
        generic_electric_prompt=bool(prompt_tokens & GENERIC_ELECTRIC_TERMS),
    )


def _normalized_confidence(value: float) -> float:
    return max(0.0, min(1.0, (float(value) - 0.20) / 0.80))


def _build_class_confidence(detections: list[dict[str, object]]) -> dict[str, float]:
    class_confidence: dict[str, float] = {}
    for item in detections:
        confidence = float(item.get("confidence", 0.0))
        if confidence < 0.20:
            continue
        class_name = canonicalize_detection_class_name(str(item["class_name"]))
        class_confidence[class_name] = max(class_confidence.get(class_name, 0.0), confidence)
    return class_confidence


def _detection_area(item: dict[str, object]) -> float:
    _, _, width, height = item["bbox"]
    return max(0.0, min(1.0, float(width) * float(height)))


def _select_focus_detection(detections: list[dict[str, object]], target_class: str) -> dict[str, object] | None:
    matched = [
        item
        for item in detections
        if canonicalize_detection_class_name(str(item["class_name"])) == target_class
    ]
    if not matched:
        return None
    return max(matched, key=lambda item: float(item.get("confidence", 0.0)) * 0.7 + _detection_area(item) * 0.3)


def _edge_strength(gray: np.ndarray) -> float:
    if gray.size == 0:
        return 0.0
    gx = np.abs(np.diff(gray, axis=1)).mean() if gray.shape[1] > 1 else 0.0
    gy = np.abs(np.diff(gray, axis=0)).mean() if gray.shape[0] > 1 else 0.0
    return float((gx + gy) * 0.5)


def _crop_focus_region(image: Image.Image | None, detection: dict[str, object] | None) -> np.ndarray | None:
    if image is None or detection is None:
        return None
    width, height = image.size
    center_x, center_y, box_width, box_height = [float(value) for value in detection["bbox"]]
    x1 = max(0, int((center_x - box_width / 2.0) * width))
    y1 = max(0, int((center_y - box_height / 2.0) * height))
    x2 = min(width, int((center_x + box_width / 2.0) * width))
    y2 = min(height, int((center_y + box_height / 2.0) * height))
    if x2 <= x1 or y2 <= y1:
        return None
    return np.asarray(image.crop((x1, y1, x2, y2)).convert("RGB"), dtype=np.uint8)


def _gray_region(image: Image.Image | None, detection: dict[str, object] | None) -> np.ndarray | None:
    region = _crop_focus_region(image, detection)
    if region is None:
        return None
    if cv2 is not None:
        return cv2.cvtColor(region, cv2.COLOR_RGB2GRAY)
    return region.mean(axis=2).astype(np.uint8)


def _priority_target_class(classes: set[str]) -> str | None:
    if not classes:
        return None
    return sorted(classes, key=lambda item: (TARGET_CLASS_PRIORITY.get(item, 99), item))[0]


def _score_wind_turbine_rules(
    *,
    image: Image.Image | None,
    detection: dict[str, object],
) -> list[PhysicalRuleCheck]:
    _, _, width, height = [float(value) for value in detection["bbox"]]
    aspect = height / max(width, 1e-6)
    gray = _gray_region(image, detection)
    blade_bins: set[int] = set()
    tower_lines = 0
    radial_balance = 0.0
    if gray is not None and cv2 is not None:
        edges = cv2.Canny(gray, 20, 60)
        lines = cv2.HoughLinesP(
            edges,
            1,
            np.pi / 180,
            threshold=16,
            minLineLength=max(10, gray.shape[0] // 8),
            maxLineGap=8,
        )
        hub_x = gray.shape[1] * 0.5
        hub_y = gray.shape[0] * 0.24
        hub_radius = max(10.0, min(gray.shape) * 0.14)
        if lines is not None:
            for line in lines[:, 0, :]:
                x1, y1, x2, y2 = [float(v) for v in line]
                angle = abs(math.degrees(math.atan2(y2 - y1, x2 - x1)))
                length = math.hypot(x2 - x1, y2 - y1)
                d1 = math.hypot(x1 - hub_x, y1 - hub_y)
                d2 = math.hypot(x2 - hub_x, y2 - hub_y)
                near_hub = min(d1, d2) <= hub_radius
                far_from_hub = max(d1, d2) >= hub_radius * 1.6
                if (
                    near_hub
                    and far_from_hub
                    and angle <= 75.0
                    and y1 < gray.shape[0] * 0.55
                    and y2 < gray.shape[0] * 0.55
                    and length >= max(12.0, gray.shape[0] * 0.10)
                ):
                    blade_bins.add(int(angle // 25.0))
                mid_x = (x1 + x2) * 0.5
                mid_y = (y1 + y2) * 0.5
                if 78.0 <= angle <= 102.0 and mid_y >= gray.shape[0] * 0.42 and abs(mid_x - gray.shape[1] * 0.5) <= gray.shape[1] * 0.18:
                    tower_lines += 1
        if blade_bins:
            radial_balance = min(1.0, len(blade_bins) / 3.0)
    return [
        PhysicalRuleCheck(
            key="blade_count_proxy",
            label="叶片辐射结构",
            score=90.0 if len(blade_bins) >= 3 else 68.0 if len(blade_bins) == 2 else 40.0,
            detail=f"检测到 {len(blade_bins)} 组叶片方向证据，越接近 3 组越符合三叶片风机。",
        ),
        PhysicalRuleCheck(
            key="hub_tower_ratio",
            label="塔身与叶轮比例",
            score=90.0 if 1.4 <= aspect <= 5.5 else 64.0 if 1.0 <= aspect <= 7.0 else 35.0,
            detail=f"主体纵横比为 {aspect:.2f}，用于约束塔身和叶轮比例是否离谱。",
        ),
        PhysicalRuleCheck(
            key="tower_support_proxy",
            label="塔身支撑关系",
            score=88.0 if tower_lines >= 2 else 62.0 if tower_lines == 1 else 34.0,
            detail="下半部检测到连续竖向支撑线。" if tower_lines >= 2 else "下半部竖向支撑线不足，存在悬浮或塔身不清风险。",
        ),
        PhysicalRuleCheck(
            key="hub_center_proxy",
            label="机舱中心辐射",
            score=88.0 if radial_balance >= 0.95 else 66.0 if radial_balance >= 0.65 else 42.0,
            detail="叶片方向分布接近围绕机舱中心展开。" if radial_balance >= 0.95 else "叶片与机舱中心的辐射关系不够稳定。",
        ),
    ]


def _score_transmission_tower_rules(
    *,
    image: Image.Image | None,
    detection: dict[str, object],
    expectation: PromptExpectation,
) -> list[PhysicalRuleCheck]:
    _, _, width, height = [float(value) for value in detection["bbox"]]
    aspect = height / max(width, 1e-6)
    symmetry_score = 0.0
    upper_taper_score = 0.0
    crossarm_score = 0.0
    wire_score = 0.0
    gray = _gray_region(image, detection)
    if gray is not None and gray.shape[1] >= 6:
        mid = gray.shape[1] // 2
        left = gray[:, :mid]
        right = np.fliplr(gray[:, gray.shape[1] - mid :])
        if left.size and right.size:
            diff = np.mean(np.abs(left.astype(np.float32) - right.astype(np.float32)))
            symmetry_score = max(0.0, 1.0 - diff / 80.0)
        top = gray[: max(1, gray.shape[0] // 3), :]
        bottom = gray[-max(1, gray.shape[0] // 3) :, :]
        top_cols = float(np.mean(top < 160))
        bottom_cols = float(np.mean(bottom < 160))
        upper_taper_score = max(0.0, min(1.0, bottom_cols / max(top_cols, 1e-6) - 0.3))
        if cv2 is not None:
            edges = cv2.Canny(gray, 24, 72)
            lines = cv2.HoughLinesP(
                edges,
                1,
                np.pi / 180,
                threshold=20,
                minLineLength=max(12, gray.shape[1] // 5),
                maxLineGap=10,
            )
            if lines is not None:
                for line in lines[:, 0, :]:
                    x1, y1, x2, y2 = [float(v) for v in line]
                    angle = abs(math.degrees(math.atan2(y2 - y1, x2 - x1)))
                    length = math.hypot(x2 - x1, y2 - y1)
                    mid_y = (y1 + y2) * 0.5
                    min_x = min(x1, x2)
                    max_x = max(x1, x2)
                    if angle <= 16.0 and mid_y <= gray.shape[0] * 0.48 and length >= gray.shape[1] * 0.30:
                        crossarm_score = max(crossarm_score, min(1.0, length / max(gray.shape[1] * 0.65, 1.0)))
                    if angle <= 12.0 and length >= gray.shape[1] * 0.22 and (min_x <= gray.shape[1] * 0.08 or max_x >= gray.shape[1] * 0.92):
                        wire_score = max(wire_score, min(1.0, length / max(gray.shape[1] * 0.45, 1.0)))
    insulator_present = "insulator_string" in expectation.detected_classes
    return [
        PhysicalRuleCheck(
            key="tower_aspect",
            label="塔体收敛比例",
            score=90.0 if aspect >= 2.0 else 64.0 if aspect >= 1.3 else 28.0,
            detail=f"塔体纵横比为 {aspect:.2f}，较高的竖向细长比更接近输电塔结构。",
        ),
        PhysicalRuleCheck(
            key="tower_symmetry",
            label="塔体对称性",
            score=88.0 if symmetry_score >= 0.78 else 66.0 if symmetry_score >= 0.58 else 38.0,
            detail="塔体左右纹理较对称。" if symmetry_score >= 0.78 else "塔体对称性不足，可能存在结构歪斜或拼接异常。",
        ),
        PhysicalRuleCheck(
            key="tower_taper",
            label="向上收敛趋势",
            score=84.0 if upper_taper_score >= 0.85 else 63.0 if upper_taper_score >= 0.55 else 35.0,
            detail="主体呈现较明显的上收轮廓。" if upper_taper_score >= 0.85 else "上收趋势不明显，塔体几何可能偏离常见工程形态。",
        ),
        PhysicalRuleCheck(
            key="crossarm_position",
            label="横担位置关系",
            score=88.0 if crossarm_score >= 0.9 else 64.0 if crossarm_score >= 0.55 else 36.0,
            detail="检测到位于塔体上部的横向横担结构。" if crossarm_score >= 0.9 else "横担证据较弱，合理挂点位置不够明确。",
        ),
        PhysicalRuleCheck(
            key="insulator_support",
            label="绝缘子挂点关系",
            score=90.0 if insulator_present and crossarm_score >= 0.55 else 64.0 if insulator_present else 38.0,
            detail="检测到绝缘子串且横担位置合理，符合挂点关系。" if insulator_present and crossarm_score >= 0.55 else "绝缘子或横担证据不足，难以证明挂点合理。",
        ),
        PhysicalRuleCheck(
            key="wire_direction",
            label="导线自然走向",
            score=86.0 if wire_score >= 0.85 else 62.0 if wire_score >= 0.45 else 40.0,
            detail="检测到延伸至边缘的导线走向，符合自然出线关系。" if wire_score >= 0.85 else "导线方向证据偏弱，难以证明其自然连接塔体。",
        ),
    ]


def _score_substation_rules(
    *,
    image: Image.Image | None,
    detection: dict[str, object],
) -> list[PhysicalRuleCheck]:
    _, cy, width, height = [float(value) for value in detection["bbox"]]
    area = width * height
    gray = _gray_region(image, detection)
    horizontal_edge = 0.0
    vertical_edge = 0.0
    if gray is not None:
        horizontal_edge = float(np.abs(np.diff(gray, axis=1)).mean()) if gray.shape[1] > 1 else 0.0
        vertical_edge = float(np.abs(np.diff(gray, axis=0)).mean()) if gray.shape[0] > 1 else 0.0
    edge_balance = min(horizontal_edge, vertical_edge) / max(max(horizontal_edge, vertical_edge), 1e-6)
    return [
        PhysicalRuleCheck(
            key="layout_density",
            label="设备连接密度",
            score=88.0 if 0.18 <= area <= 0.95 else 58.0 if 0.10 <= area <= 0.98 else 35.0,
            detail=f"主体覆盖面积为 {area:.2f}，用于近似约束站内设备密度和连接关系。",
        ),
        PhysicalRuleCheck(
            key="structural_orthogonality",
            label="母线支架正交关系",
            score=84.0 if edge_balance >= 0.72 else 62.0 if edge_balance >= 0.48 else 36.0,
            detail="水平与垂直结构边缘较均衡。" if edge_balance >= 0.72 else "结构边缘分布失衡，可能存在穿模或部件关系异常。",
        ),
        PhysicalRuleCheck(
            key="ground_contact",
            label="与地面接触关系",
            score=82.0 if cy >= 0.40 else 55.0,
            detail="主体位置接近地面区域。" if cy >= 0.40 else "主体整体偏高，存在轻微悬浮风险。",
        ),
    ]


def _score_solar_panel_rules(
    *,
    image: Image.Image | None,
    detection: dict[str, object],
) -> list[PhysicalRuleCheck]:
    _, cy, width, height = [float(value) for value in detection["bbox"]]
    aspect = width / max(height, 1e-6)
    gray = _gray_region(image, detection)
    orientation_consistency = 0.0
    if gray is not None and cv2 is not None:
        edges = cv2.Canny(gray, 60, 140)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=24, minLineLength=max(8, gray.shape[1] // 5), maxLineGap=8)
        if lines is not None and len(lines) > 1:
            angles = []
            for line in lines[:, 0, :]:
                x1, y1, x2, y2 = [int(v) for v in line]
                angle = abs(math.degrees(math.atan2(y2 - y1, x2 - x1)))
                angles.append(angle)
            angle_std = float(np.std(angles)) if angles else 90.0
            orientation_consistency = max(0.0, 1.0 - angle_std / 35.0)
    return [
        PhysicalRuleCheck(
            key="panel_aspect",
            label="面板铺展比例",
            score=88.0 if aspect >= 1.2 else 60.0 if aspect >= 0.8 else 34.0,
            detail=f"主体横纵比为 {aspect:.2f}，更宽的主体更接近成组光伏阵列。",
        ),
        PhysicalRuleCheck(
            key="panel_orientation",
            label="阵列方向一致性",
            score=86.0 if orientation_consistency >= 0.74 else 62.0 if orientation_consistency >= 0.48 else 40.0,
            detail="边缘主方向较一致，接近共面阵列。" if orientation_consistency >= 0.74 else "边缘方向离散，阵列共面性和朝向一致性偏弱。",
        ),
        PhysicalRuleCheck(
            key="panel_ground_relation",
            label="支架地面关系",
            score=82.0 if cy >= 0.42 else 56.0,
            detail="主体位置接近地面区域。" if cy >= 0.42 else "主体整体偏高，支架与地面关系不够明确。",
        ),
    ]


def _score_dam_rules(
    *,
    image: Image.Image | None,
    detection: dict[str, object],
) -> list[PhysicalRuleCheck]:
    _, cy, width, height = [float(value) for value in detection["bbox"]]
    gray = _gray_region(image, detection)
    continuity = 0.0
    lower_contact = 0.0
    if gray is not None:
        row_profile = np.mean(gray < 170, axis=1)
        continuity = float(np.max(row_profile)) if row_profile.size else 0.0
        lower_contact = float(np.mean(gray[int(gray.shape[0] * 0.75) :, :] < 180)) if gray.shape[0] > 4 else 0.0
    area = width * height
    return [
        PhysicalRuleCheck(
            key="dam_continuity",
            label="坝体连续性",
            score=90.0 if continuity >= 0.72 else 66.0 if continuity >= 0.50 else 38.0,
            detail="存在连续的大尺度结构轮廓。" if continuity >= 0.72 else "连续结构特征偏弱，可能存在断裂或主体不完整。",
        ),
        PhysicalRuleCheck(
            key="dam_ground_contact",
            label="坝体接触关系",
            score=86.0 if lower_contact >= 0.34 and cy >= 0.40 else 60.0 if cy >= 0.34 else 36.0,
            detail="主体下部与地表/水体接触较明显。" if lower_contact >= 0.34 and cy >= 0.40 else "下部接触关系不够强，存在悬空或脱离环境风险。",
        ),
        PhysicalRuleCheck(
            key="dam_scale",
            label="坝体尺度合理性",
            score=88.0 if area >= 0.35 else 62.0 if area >= 0.18 else 34.0,
            detail=f"坝体覆盖面积为 {area:.2f}，大尺度连续主体更接近真实坝体。",
        ),
    ]


def _score_generic_structure_rules(
    *,
    detection: dict[str, object],
) -> list[PhysicalRuleCheck]:
    _, cy, width, height = [float(value) for value in detection["bbox"]]
    area = width * height
    return [
        PhysicalRuleCheck(
            key="generic_scale",
            label="主体尺度",
            score=84.0 if 0.05 <= area <= 0.95 else 52.0,
            detail=f"主体面积占比为 {area:.2f}。",
        ),
        PhysicalRuleCheck(
            key="generic_ground_relation",
            label="场景接触关系",
            score=80.0 if cy >= 0.34 else 54.0,
            detail="主体位置接近合理地面区域。" if cy >= 0.34 else "主体位置偏高，存在悬浮风险。",
        ),
    ]


def _score_target_structure_rules(
    *,
    prompt: str,
    detections: list[dict[str, object]],
    image: Image.Image | None,
) -> tuple[str | None, list[PhysicalRuleCheck]]:
    expectation = build_prompt_expectation(prompt, detections)
    target_class = _priority_target_class(expectation.expected_classes)
    if target_class is None:
        target_class = _priority_target_class(expectation.detected_classes)
    if target_class is None:
        return None, []
    detection = _select_focus_detection(detections, target_class)
    if detection is None:
        return target_class, []
    if target_class == "wind_turbine":
        return target_class, _score_wind_turbine_rules(image=image, detection=detection)
    if target_class == "transmission_tower":
        return target_class, _score_transmission_tower_rules(image=image, detection=detection, expectation=expectation)
    if target_class == "substation_primary":
        return target_class, _score_substation_rules(image=image, detection=detection)
    if target_class == "solar_panel":
        return target_class, _score_solar_panel_rules(image=image, detection=detection)
    if target_class == "dam":
        return target_class, _score_dam_rules(image=image, detection=detection)
    return target_class, _score_generic_structure_rules(detection=detection)


def _score_physical_parts_rules(
    *,
    target_class: str | None,
    physical_part_detections: list[dict[str, object]] | None,
) -> list[PhysicalRuleCheck]:
    if target_class is None or not physical_part_detections:
        return []

    counts: dict[str, int] = {}
    confidence: dict[str, float] = {}
    for item in physical_part_detections:
        class_name = str(item.get("class_name") or "").strip()
        if not class_name:
            continue
        counts[class_name] = counts.get(class_name, 0) + 1
        confidence[class_name] = max(confidence.get(class_name, 0.0), float(item.get("confidence", 0.0)))

    if target_class == "wind_turbine":
        blade_count = counts.get("wind_blade", 0)
        return [
            PhysicalRuleCheck(
                key="part_blade_count",
                label="叶片数量证据",
                score=96.0 if blade_count == 3 else 72.0 if blade_count == 2 else 38.0,
                detail=f"检测到 {blade_count} 个风机叶片部件，越接近 3 个越符合标准三叶片风机。",
            ),
            PhysicalRuleCheck(
                key="part_blade_presence",
                label="叶片主体证据",
                score=90.0 if blade_count >= 3 else 68.0 if blade_count >= 1 else 36.0,
                detail="检测到清晰叶片主体，能为风机结构提供直接证据。" if blade_count >= 1 else "未检测到清晰叶片主体，风机结构证据不足。",
            ),
        ]

    if target_class == "transmission_tower":
        has_body = counts.get("tower_body", 0) > 0
        has_crossarm = counts.get("tower_crossarm", 0) > 0
        has_wire = counts.get("tower_wire", 0) > 0
        has_hang = counts.get("tower_insulator_hang", 0) > 0
        return [
            PhysicalRuleCheck(
                key="part_tower_body",
                label="塔身部件证据",
                score=90.0 if has_body else 40.0,
                detail="检测到塔身主体部件。" if has_body else "未检测到塔身主体部件。",
            ),
            PhysicalRuleCheck(
                key="part_crossarm",
                label="横担部件证据",
                score=92.0 if has_crossarm else 36.0,
                detail="检测到横担部件。" if has_crossarm else "未检测到横担部件。",
            ),
            PhysicalRuleCheck(
                key="part_wire",
                label="导线部件证据",
                score=88.0 if has_wire else 42.0,
                detail="检测到导线部件。" if has_wire else "未检测到导线部件。",
            ),
            PhysicalRuleCheck(
                key="part_insulator_hang",
                label="绝缘子挂点证据",
                score=90.0 if has_hang else 44.0,
                detail="检测到绝缘子挂点部件。" if has_hang else "未检测到绝缘子挂点部件。",
            ),
        ]

    return []


def score_text_consistency(
    *,
    prompt: str,
    detections: list[dict[str, object]],
    semantic_prior: float,
) -> float:
    expectation = build_prompt_expectation(prompt, detections)
    detected_count = len(expectation.detected_classes)
    class_confidence: dict[str, float] = {}
    for item in detections:
        confidence = float(item.get("confidence", 0.0))
        if confidence < 0.20:
            continue
        class_name = canonicalize_detection_class_name(str(item["class_name"]))
        class_confidence[class_name] = max(class_confidence.get(class_name, 0.0), confidence)

    if expectation.expected_classes:
        recall = len(expectation.matched_classes) / max(len(expectation.expected_classes), 1)
        matched_quality = 0.0
        for class_name in expectation.expected_classes:
            confidence = class_confidence.get(class_name, 0.0)
            normalized_confidence = max(0.0, min(1.0, (confidence - 0.20) / 0.80))
            matched_quality += normalized_confidence
        matched_quality /= max(len(expectation.expected_classes), 1)

        score = 12.0 + recall * 50.0 + matched_quality * 30.0
        if not expectation.matched_classes:
            score -= 18.0
        score += min(6.0, detected_count * 2.0)
    elif expectation.generic_electric_prompt:
        score = 52.0 + min(30.0, detected_count * 7.0)
    else:
        score = 35.0 + semantic_prior * 0.45

    if expectation.expected_classes and len(expectation.matched_classes) < len(expectation.expected_classes):
        missing = len(expectation.expected_classes) - len(expectation.matched_classes)
        score -= missing * 8.0

    blended = score * 0.95 + semantic_prior * 0.05
    return clamp_score(blended)


def score_visual_fidelity(
    *,
    image_metrics: dict[str, float],
    detections: list[dict[str, object]],
    semantic_prior: float,
) -> float:
    sharpness = float(image_metrics.get("sharpness", 0.0))
    exposure = float(image_metrics.get("exposure", 0.0))
    contrast = float(image_metrics.get("contrast", 0.0))
    clarity_support = min(100.0, exposure * 0.55 + contrast * 0.45)
    expectation = build_prompt_expectation("", detections)
    target_class = _priority_target_class(expectation.detected_classes)
    focus_detection = _select_focus_detection(detections, target_class) if target_class is not None else None
    confidence = float(focus_detection.get("confidence", 0.0)) if focus_detection is not None else 0.0
    confidence_score = _normalized_confidence(confidence) * 100.0
    width = float(focus_detection["bbox"][2]) if focus_detection is not None else 0.0
    height = float(focus_detection["bbox"][3]) if focus_detection is not None else 0.0
    area = width * height

    if target_class == "wind_turbine":
        detail_proxy = max(sharpness, clarity_support * 0.70 if sharpness >= 28.0 else sharpness)
        structure_scale = min(100.0, (height / 0.55) * 70.0 + (area / 0.12) * 30.0)
        score = 10.0 + (
            detail_proxy * 0.42
            + exposure * 0.22
            + contrast * 0.16
            + structure_scale * 0.12
            + confidence_score * 0.08
            + semantic_prior * 0.04
        )
    elif target_class == "transmission_tower":
        detail_proxy = max(sharpness, clarity_support * 0.56 if sharpness >= 34.0 else sharpness)
        vertical_presence = min(100.0, height / 0.72 * 100.0)
        score = 8.0 + (
            detail_proxy * 0.48
            + exposure * 0.18
            + contrast * 0.16
            + vertical_presence * 0.10
            + confidence_score * 0.10
            + semantic_prior * 0.04
        )
    elif target_class == "substation_primary":
        detail_proxy = max(sharpness, clarity_support * 0.60 if sharpness >= 30.0 else sharpness)
        dense_equipment_presence = min(100.0, area / 0.28 * 100.0)
        score = 8.0 + (
            detail_proxy * 0.42
            + exposure * 0.20
            + contrast * 0.20
            + dense_equipment_presence * 0.10
            + confidence_score * 0.10
            + semantic_prior * 0.06
        )
    elif target_class == "solar_panel":
        detail_proxy = max(sharpness, clarity_support * 0.72 if sharpness >= 26.0 else sharpness)
        wide_presence = min(100.0, (width / max(height, 1e-6)) / 3.0 * 100.0)
        array_coverage = min(100.0, area / 0.18 * 100.0)
        score = 8.0 + (
            detail_proxy * 0.34
            + exposure * 0.22
            + contrast * 0.22
            + wide_presence * 0.08
            + array_coverage * 0.08
            + confidence_score * 0.10
            + semantic_prior * 0.04
        )
    elif target_class == "dam":
        detail_proxy = max(sharpness, clarity_support * 0.66 if sharpness >= 24.0 else sharpness)
        wide_presence = min(100.0, (width / max(height, 1e-6)) / 2.8 * 100.0)
        mass_presence = min(100.0, area / 0.22 * 100.0)
        score = 8.0 + (
            detail_proxy * 0.30
            + exposure * 0.24
            + contrast * 0.20
            + wide_presence * 0.10
            + mass_presence * 0.08
            + confidence_score * 0.10
            + semantic_prior * 0.08
        )
    else:
        local_detail_bonus = min(8.0, len(detections) * 2.0)
        detail_proxy = max(sharpness, clarity_support * 0.62 if sharpness >= 28.0 else sharpness)
        score = 6.0 + (
            detail_proxy * 0.58
            + exposure * 0.22
            + contrast * 0.16
            + semantic_prior * 0.06
            + local_detail_bonus
        )

    if sharpness < 25.0:
        score -= 10.0
    if exposure < 35.0:
        score -= 6.0
    if contrast < 22.0:
        score -= 4.0
    return clamp_score(score)


def score_composition_aesthetics(
    *,
    image_metrics: dict[str, float],
    detections: list[dict[str, object]],
    semantic_prior: float,
) -> float:
    exposure = float(image_metrics.get("exposure", 0.0))
    contrast = float(image_metrics.get("contrast", 0.0))

    expectation = build_prompt_expectation("", detections)
    detected_classes = expectation.detected_classes
    if detections:
        weighted_area = 0.0
        weighted_x = 0.0
        weighted_y = 0.0
        centers_x: list[float] = []
        centers_y: list[float] = []
        widths: list[float] = []
        heights: list[float] = []
        edge_margins: list[float] = []
        for item in detections:
            cx, cy, width, height = item["bbox"]
            area = max(0.0, min(1.0, float(width) * float(height)))
            weight = area * max(0.3, float(item.get("confidence", 0.0)))
            weighted_area += area
            weighted_x += float(cx) * weight
            weighted_y += float(cy) * weight
            centers_x.append(float(cx))
            centers_y.append(float(cy))
            widths.append(float(width))
            heights.append(float(height))
            edge_margins.append(
                min(
                    float(cx) - float(width) / 2.0,
                    1.0 - (float(cx) + float(width) / 2.0),
                    float(cy) - float(height) / 2.0,
                    1.0 - (float(cy) + float(height) / 2.0),
                )
            )
        centroid_x = weighted_x / max(weighted_area, 1e-6)
        centroid_y = weighted_y / max(weighted_area, 1e-6)
        center_offset = abs(centroid_x - 0.5) + abs(centroid_y - 0.5)
        balance = 100.0 - min(1.0, center_offset / 0.60) * 100.0
        coverage = 100.0 - min(1.0, abs(weighted_area - 0.30) / 0.30) * 100.0
        clutter_penalty = max(0.0, len(detections) - 3) * 5.0
        x_span = max(centers_x) - min(centers_x) if len(centers_x) >= 2 else 0.0
        y_span = max(centers_y) - min(centers_y) if len(centers_y) >= 2 else 0.0
        mean_width = sum(widths) / max(len(widths), 1)
        mean_height = sum(heights) / max(len(heights), 1)
        edge_clearance = min(100.0, max(0.0, (sum(edge_margins) / max(len(edge_margins), 1) + 0.02) / 0.18 * 100.0))
    else:
        balance = 45.0
        coverage = 40.0
        clutter_penalty = 12.0
        x_span = 0.0
        y_span = 0.0
        mean_width = 0.0
        mean_height = 0.0
        edge_clearance = 32.0

    subject_layout = 58.0
    balance_component = balance
    if "wind_turbine" in detected_classes:
        if len(detections) == 1:
            cx = centers_x[0]
            cy = centers_y[0]
            height = heights[0]
            thirds_anchor = 100.0 - min(
                1.0,
                min(abs(cx - 0.30), abs(cx - 0.70)) / 0.20,
            ) * 100.0
            skyline_anchor = 100.0 - min(1.0, abs(cy - 0.42) / 0.22) * 100.0
            hero_scale = min(100.0, max(0.0, height / 0.60 * 100.0))
            subject_layout = (
                thirds_anchor * 0.40
                + skyline_anchor * 0.20
                + hero_scale * 0.20
                + edge_clearance * 0.20
            )
            balance_component = max(balance, thirds_anchor * 0.78)
        else:
            centered_subject = 100.0 - min(1.0, abs((sum(centers_x) / max(len(centers_x), 1)) - 0.5) / 0.45) * 100.0 if detections else 40.0
            horizontal_distribution = min(100.0, x_span / 0.55 * 100.0)
            vertical_stability = 100.0 - min(100.0, y_span / 0.30 * 100.0)
            subject_layout = (
                centered_subject * 0.30
                + horizontal_distribution * 0.25
                + vertical_stability * 0.25
                + edge_clearance * 0.20
            )
    elif "transmission_tower" in detected_classes:
        if len(detections) == 1:
            cx = centers_x[0]
            cy = centers_y[0]
            height = heights[0]
            thirds_anchor = 100.0 - min(
                1.0,
                min(abs(cx - 0.32), abs(cx - 0.68)) / 0.22,
            ) * 100.0
            grounded_vertical = 100.0 - min(1.0, abs(cy - 0.54) / 0.22) * 100.0
            structure_scale = min(100.0, max(0.0, height / 0.72 * 100.0))
            subject_layout = (
                thirds_anchor * 0.34
                + grounded_vertical * 0.20
                + structure_scale * 0.26
                + edge_clearance * 0.20
            )
            balance_component = max(balance_component, thirds_anchor * 0.74)
        else:
            line_flow = min(100.0, x_span / 0.60 * 100.0)
            horizon_consistency = 100.0 - min(100.0, y_span / 0.28 * 100.0)
            central_anchor = 100.0 - min(1.0, abs(centroid_x - 0.5) / 0.50) * 100.0
            subject_layout = line_flow * 0.28 + horizon_consistency * 0.28 + central_anchor * 0.24 + edge_clearance * 0.20
    elif "substation_primary" in detected_classes:
        width_emphasis = min(100.0, mean_width / 0.55 * 100.0)
        ground_anchor = min(100.0, max(0.0, (centroid_y - 0.35) / 0.35) * 100.0)
        symmetry = balance
        subject_layout = width_emphasis * 0.34 + ground_anchor * 0.26 + symmetry * 0.40
    elif "solar_panel" in detected_classes:
        wide_array = min(100.0, mean_width / max(mean_height, 1e-6) / 3.0 * 100.0)
        lower_half_anchor = min(100.0, max(0.0, (centroid_y - 0.35) / 0.30) * 100.0)
        central_anchor = 100.0 - min(1.0, abs(centroid_x - 0.5) / 0.45) * 100.0
        subject_layout = wide_array * 0.42 + lower_half_anchor * 0.33 + central_anchor * 0.25
    elif "dam" in detected_classes:
        wide_structure = min(100.0, mean_width / max(mean_height, 1e-6) / 3.2 * 100.0)
        center_mass = 100.0 - min(1.0, abs(centroid_x - 0.5) / 0.42) * 100.0
        lower_anchor = min(100.0, max(0.0, (centroid_y - 0.38) / 0.30) * 100.0)
        subject_layout = wide_structure * 0.42 + center_mass * 0.28 + lower_anchor * 0.30

    score = subject_layout * 0.46 + balance_component * 0.18 + coverage * 0.14 + exposure * 0.10 + contrast * 0.05 + semantic_prior * 0.07
    score -= clutter_penalty
    return clamp_score(score)


def score_physical_plausibility_with_details(
    *,
    prompt: str,
    detections: list[dict[str, object]],
    semantic_prior: float,
    image: Image.Image | None = None,
    physical_part_detections: list[dict[str, object]] | None = None,
) -> PhysicalPlausibilityResult:
    expectation = build_prompt_expectation(prompt, detections)
    topology = score_detected_topology(expectation.detected_classes)
    class_confidence = _build_class_confidence(detections)
    target_class, checks = _score_target_structure_rules(prompt=prompt, detections=detections, image=image)
    part_checks = _score_physical_parts_rules(target_class=target_class, physical_part_detections=physical_part_detections)
    all_checks = [*checks, *part_checks]
    rule_score = float(sum(item.score for item in all_checks) / max(len(all_checks), 1)) if all_checks else 36.0

    score = 6.0 + topology * 0.24 + semantic_prior * 0.12 + rule_score * 0.52 + min(8.0, len(detections) * 2.0)
    matched_quality = 0.0

    if expectation.expected_classes:
        matched_ratio = len(expectation.matched_classes) / max(len(expectation.expected_classes), 1)
        for class_name in expectation.matched_classes:
            matched_quality += _normalized_confidence(class_confidence.get(class_name, 0.0))
        matched_quality /= max(len(expectation.matched_classes), 1)

        score += matched_ratio * 14.0 + matched_quality * 8.0
        if len(expectation.expected_classes) == 1 and len(expectation.matched_classes) == 1:
            single_subject_bonus = {
                "dam": 8.0,
                "substation_primary": 7.0,
                "wind_turbine": 6.0,
                "solar_panel": 5.0,
            }
            expected_class = next(iter(expectation.expected_classes))
            score += single_subject_bonus.get(expected_class, 0.0)

        if not expectation.matched_classes:
            score -= 14.0
        elif len(expectation.matched_classes) < len(expectation.expected_classes):
            score -= (len(expectation.expected_classes) - len(expectation.matched_classes)) * 6.0

    large_extent_allowed = bool(expectation.matched_classes & {"dam", "substation_primary"})
    geometry_penalty = 0.0
    for item in detections:
        _, _, width, height = item["bbox"]
        width = float(width)
        height = float(height)
        area = max(0.0, min(1.0, width * height))
        if width > 0.85 or height > 0.92:
            geometry_penalty += 4.0 if large_extent_allowed else 18.0
        if area > 0.72:
            geometry_penalty += 2.0 if large_extent_allowed else 10.0
    score -= geometry_penalty

    if {"transmission_tower", "insulator_string"}.issubset(expectation.matched_classes):
        score += 10.0
    if "wind_turbine" in expectation.matched_classes:
        score += 3.0
    if "substation_primary" in expectation.matched_classes:
        score += 2.0

    final_score = clamp_score(score)
    if final_score >= 85.0:
        summary = "主体结构关系完整，关键工程规则基本成立。"
    elif final_score >= 70.0:
        summary = "主体结构整体合理，但局部工程关系仍有弱项。"
    elif final_score >= 50.0:
        summary = "主体可辨认，但结构规则命中不足，存在明显物理疑点。"
    else:
        summary = "结构关系较弱，难以证明其符合电力工程常识。"
    return PhysicalPlausibilityResult(
        score=final_score,
        target_class=target_class,
        summary=summary,
        rule_score=clamp_score(rule_score),
        topology=clamp_score(topology),
        matched_quality=round(matched_quality, 4),
        geometry_penalty=round(geometry_penalty, 4),
        expectation=expectation,
        checks=all_checks,
    )


def score_physical_plausibility(
    *,
    prompt: str,
    detections: list[dict[str, object]],
    semantic_prior: float,
    image: Image.Image | None = None,
    physical_part_detections: list[dict[str, object]] | None = None,
) -> float:
    return score_physical_plausibility_with_details(
        prompt=prompt,
        detections=detections,
        semantic_prior=semantic_prior,
        image=image,
        physical_part_detections=physical_part_detections,
    ).score
