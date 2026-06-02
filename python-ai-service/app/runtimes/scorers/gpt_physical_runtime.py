from __future__ import annotations

import base64
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from httpx import Client as HttpxClient

from app.core.settings import get_settings
from training.scoring.rubric import build_prompt_expectation, canonicalize_detection_class_name

SUPPORTED_TARGET_CLASSES = {
    "substation_primary",
    "wind_turbine",
    "transmission_tower",
    "solar_panel",
    "dam",
    "unknown",
}

CRITICAL_RULE_LABEL_KEYWORDS = {
    "wind_turbine": ("叶片数量", "叶片是否从机舱中心发出", "塔身是否支撑机舱"),
    "transmission_tower": ("塔体对称", "横担位置", "绝缘子串", "导线是否连接塔体", "导线不能反重力"),
    "substation_primary": ("设备连接关系", "母线支架套管相对位置", "结构穿模重叠悬浮", "同类设备尺寸一致性"),
    "solar_panel": ("面板是否共面", "倾角是否基本一致", "阵列是否方向一致", "支架和地面关系"),
    "dam": ("坝体连续性", "与山体/地面接触关系", "与水体接触关系", "结构悬空或断裂"),
}


def _default_openai_client(*, api_key: str, base_url: str):
    from openai import OpenAI

    http_client = HttpxClient(trust_env=False, timeout=300)
    return OpenAI(
        api_key=api_key,
        base_url=base_url.rstrip("/"),
        http_client=http_client,
        max_retries=0,
    )


def _encode_image(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".png":
        mime = "image/png"
    elif suffix == ".webp":
        mime = "image/webp"
    else:
        mime = "image/jpeg"
    content = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{content}"


def _extract_json_text(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start != -1 and end != -1 and end >= start:
        return stripped[start : end + 1]
    return stripped


class GPTPhysicalRuntime:
    def __init__(
        self,
        *,
        output_dir: Path,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str = "gpt-5.4",
        max_attempts: int = 3,
        client: Any | None = None,
    ) -> None:
        settings = get_settings()
        self._output_dir = Path(output_dir)
        self._api_key = api_key if api_key is not None else settings.openai_api_key
        self._base_url = base_url if base_url is not None else settings.openai_base_url
        self._model = model
        self._max_attempts = max(1, int(max_attempts))
        self._client = client

    def annotate_image(self, *, image_path: str, prompt: str) -> dict[str, Any]:
        if not self._api_key:
            raise RuntimeError("OPENAI_API_KEY is required for GPT physical scoring.")
        if not self._base_url:
            raise RuntimeError("OPENAI_BASE_URL is required for GPT physical scoring.")

        client = self._client or _default_openai_client(api_key=self._api_key, base_url=self._base_url)
        image_file = Path(image_path)
        prompt_expected_classes = sorted(build_prompt_expectation(prompt, []).expected_classes)
        normalized: dict[str, Any] | None = None
        raw_output_text = ""
        last_error: Exception | None = None

        for _ in range(self._max_attempts):
            try:
                response = client.responses.create(
                    model=self._model,
                    input=[
                        {
                            "role": "system",
                            "content": [{"type": "input_text", "text": self._system_prompt()}],
                        },
                        {
                            "role": "user",
                            "content": [
                                {"type": "input_text", "text": f"prompt={prompt}"},
                                {
                                    "type": "input_text",
                                    "text": f"text_consistency_expected_classes={','.join(prompt_expected_classes) if prompt_expected_classes else 'none'}",
                                },
                                {"type": "input_image", "image_url": _encode_image(image_file)},
                            ],
                        },
                    ],
                )
                raw_output_text = response.output_text
                payload = json.loads(_extract_json_text(raw_output_text))
                normalized = self.normalize_annotation_payload(payload)
                break
            except Exception as exc:
                last_error = exc

        if normalized is None:
            assert last_error is not None
            raise last_error

        saved_path = self._write_annotation_file(
            image_path=image_file,
            prompt=prompt,
            normalized=normalized,
            raw_output_text=raw_output_text,
        )
        normalized["saved_path"] = str(saved_path)
        normalized["model"] = self._model
        return normalized

    def _write_annotation_file(
        self,
        *,
        image_path: Path,
        prompt: str,
        normalized: dict[str, Any],
        raw_output_text: str,
    ) -> Path:
        self._output_dir.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha1(str(image_path.resolve()).encode("utf-8")).hexdigest()[:12]
        target = self._output_dir / f"{image_path.stem}_{digest}.json"
        payload = {
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "image_path": str(image_path.resolve()),
            "image_name": image_path.name,
            "prompt": prompt,
            "annotation": normalized,
            "raw_output_text": raw_output_text,
        }
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return target

    def write_failure_file(
        self,
        *,
        image_path: str,
        prompt: str,
        error_type: str,
        error_message: str,
    ) -> Path:
        image_file = Path(image_path)
        self._output_dir.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha1(str(image_file.resolve()).encode("utf-8")).hexdigest()[:12]
        target = self._output_dir / f"{image_file.stem}_{digest}.error.json"
        payload = {
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "image_path": str(image_file.resolve()),
            "image_name": image_file.name,
            "prompt": prompt,
            "error_type": error_type,
            "error_message": error_message,
            "model": self._model,
            "base_url": self._base_url,
        }
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return target

    @classmethod
    def normalize_annotation_payload(cls, payload: dict[str, Any]) -> dict[str, Any]:
        target_class = canonicalize_detection_class_name(str(payload.get("target_class") or "unknown"))
        if target_class == "insulator_string":
            target_class = "transmission_tower"
        if target_class not in SUPPORTED_TARGET_CLASSES:
            target_class = "unknown"

        raw_rule_checks = payload.get("rule_checks") or []
        rule_checks: list[dict[str, Any]] = []
        if isinstance(raw_rule_checks, list):
            for item in raw_rule_checks:
                if not isinstance(item, dict):
                    continue
                rule_checks.append(
                    {
                        "label": str(item.get("label") or "").strip(),
                        "passed": bool(item.get("passed", False)),
                        "detail": str(item.get("detail") or "").strip(),
                    }
                )

        def _string_list(value: Any) -> list[str]:
            if not isinstance(value, list):
                return []
            return [str(item).strip() for item in value if str(item).strip()]

        score = float(payload.get("score", 0.0))
        score = max(0.0, min(100.0, score))
        score, score_band = cls._apply_score_band_policy(
            target_class=target_class,
            score=score,
            missing_elements=_string_list(payload.get("missing_elements")),
            rule_checks=rule_checks,
        )

        return {
            "target_class": target_class,
            "score": round(score, 2),
            "score_band": score_band,
            "reason": str(payload.get("reason") or "").strip(),
            "present_elements": _string_list(payload.get("present_elements")),
            "missing_elements": _string_list(payload.get("missing_elements")),
            "rule_checks": rule_checks,
        }

    @staticmethod
    def _apply_score_band_policy(
        *,
        target_class: str,
        score: float,
        missing_elements: list[str],
        rule_checks: list[dict[str, Any]],
    ) -> tuple[float, str]:
        failed_checks = [item for item in rule_checks if not bool(item.get("passed"))]
        critical_keywords = CRITICAL_RULE_LABEL_KEYWORDS.get(target_class, ())
        critical_failures = [
            item
            for item in failed_checks
            if any(keyword in str(item.get("label") or "") for keyword in critical_keywords)
        ]
        missing_count = len(missing_elements)
        failed_count = len(failed_checks)

        if critical_failures:
            adjusted = min(score, 69.0)
            return adjusted, "50-69" if adjusted >= 50.0 else "0-49"

        if missing_count >= 2 or failed_count >= 3:
            adjusted = min(score, 69.0)
            return adjusted, "50-69" if adjusted >= 50.0 else "0-49"

        if missing_count >= 1 or failed_count >= 1:
            adjusted = min(score, 84.0)
            return adjusted, "70-84" if adjusted >= 70.0 else "50-69"

        if rule_checks:
            adjusted = min(score, 94.0)
            if failed_count == 0 and missing_count == 0 and all(bool(item.get("passed")) for item in rule_checks):
                critical_matched = 0
                for keyword in critical_keywords:
                    if any(keyword in str(item.get("label") or "") and bool(item.get("passed")) for item in rule_checks):
                        critical_matched += 1
                if target_class == "unknown" or critical_matched >= max(1, len(critical_keywords) - 1):
                    adjusted = score
            if adjusted >= 95.0:
                return adjusted, "95-100"
            return adjusted, "85-94"

        adjusted = min(score, 84.0)
        return adjusted, "70-84" if adjusted >= 70.0 else "50-69"

    @staticmethod
    def _system_prompt() -> str:
        return "\n".join(
            [
                "你是电力行业图像物理合理性评分助手。",
                "请结合用户 prompt 和图像内容，只评估 physical_plausibility 这一维。",
                "你的任务是识别主体设备是否存在、是否缺失关键结构、是否违反明显工程和物理规律，然后给出 0-100 分。",
                "当前评分只按 5 个主类别判断，请严格把主体归到以下 target_class 之一: substation_primary, transmission_tower, wind_turbine, solar_panel, dam。",
                "你必须遵循 text_consistency 同一套六类命名标准，不要输出 substation、switchyard、tower、insulator、wind turbine 这类非标准类名。",
                "如果图里主体更像变电站主设备、开关场、母线构架、主变压器区域，必须使用 substation_primary。",
                "如果图里主体更像绝缘子串本体或绝缘子串近景，也统一归到 transmission_tower，不再单独作为主类别评分。",
                "如果 prompt 中提供了 text_consistency_expected_classes，请优先在这些标准类名中判断主体归属。",
                "只有真的无法归到这 5 类时才允许使用 unknown。",
                "必须严格按照下面分段打分，不能因为‘整体看起来不错’就打高分。",
                "请重点检查以下规则：",
                "wind_turbine: 叶片数量是否为3；叶片是否从机舱中心发出；塔身是否支撑机舱；塔身和叶片比例是否离谱；风机是否悬浮或插地异常。",
                "transmission_tower: 塔体是否基本对称且向上收敛；横担位置是否合理；若画面中有绝缘子串，则绝缘子串是否挂在横担附近；导线是否连接塔体且方向自然；导线不能反重力乱飞；绝缘子近景也按这一类规则判断。",
                "substation_primary: 设备之间是否存在合理连接关系；母线、支架、套管相对位置是否合理；结构不能穿模、重叠、悬浮；同类设备尺寸不能极度失衡；不能把主变、套管、构架连接得不成立。",
                "solar_panel: 面板是否共面或近似共面；倾角是否基本一致；阵列是否方向一致；支架和地面关系是否合理。",
                "dam: 坝体是否连续；与山体/地面/水体是否有接触关系；结构不能悬空或断裂。",
                "评分标准：",
                "95-100: 完全符合电力设备的物理规律和工程标准。只有在关键规则全部通过、没有缺失关键结构、没有明显工程错误时才允许进入这个区间。",
                "85-94: 整体符合电力设备物理规律。可以有很轻微、很不显眼的小瑕疵，但不能有关键规则失败。",
                "70-84: 整体合理，但细节处存在轻微问题。只要出现轻微结构问题、轻微连接问题、轻微比例问题，就应落在这个区间。",
                "50-69: 存在明显的物理或工程错误。只要出现叶片数量错误、关键连接错误、明显结构异常、明显缺件，就必须落在这个区间或更低。",
                "0-49: 存在极其荒谬的物理规律破坏或严重工程错误，主体严重失真或几乎不符合电力工程常识。",
                "硬性约束：",
                "1. 对 wind_turbine，只要叶片数量不是3片，或叶片未清楚从机舱中心发出，分数不得高于69。",
                "2. 对 transmission_tower，只要横担、绝缘子串、导线连接关系出现明显错误，分数不得高于69。",
                "3. 对 substation_primary，只要出现明显悬浮、穿模、重叠、母线套管支架关系不成立、主设备连接不成立，分数不得高于69。",
                "4. 对 solar_panel，只要阵列不共面、方向明显混乱、支架落地关系错误，分数不得高于69。",
                "5. 对 dam，只要坝体不连续、悬空、断裂、与地面或水体关系错误，分数不得高于69。",
                "6. 只有当关键规则全部通过且没有 missing_elements 时，才允许给到 95 分以上。",
                "7. 只要任意 rule_checks 中存在明显关键失败，就不要给 85 分以上。",
                "8. 请尽量把 rule_checks 名称写成明确规则名，不要写空泛总结。",
                "输出必须是 JSON，且只能包含这些字段：",
                '{"target_class":"substation_primary","score":91,"reason":"...","present_elements":["..."],"missing_elements":["..."],"rule_checks":[{"label":"设备连接关系","passed":true,"detail":"母线与主设备连接成立"}]}',
                "不要输出 markdown，不要输出多余解释。",
            ]
        )
