from __future__ import annotations

from dataclasses import dataclass
import re


PROMPT_ARRAY_PATTERN = re.compile(r"RECOMMENDED_POSITIVE_PROMPTS\s*=\s*\[(?P<body>.*?)\]\s*as const", re.DOTALL)
NEGATIVE_PROMPT_PATTERN = re.compile(
    r"RECOMMENDED_NEGATIVE_PROMPT\s*=\s*'(?P<value>(?:\\.|[^'])*)'",
    re.DOTALL,
)
SINGLE_QUOTED_STRING_PATTERN = re.compile(r"'((?:\\.|[^'])*)'")
TRAINING_STEP_PATTERN = re.compile(
    r"Steps:\s+\d+%\|.*?\|\s*(?P<step>\d+)/(?P<total>\d+)\s+\[.*?lr=(?P<lr>[\deE.+-]+),\s*step_loss=(?P<loss>[\deE.+-]+)\]",
)
MONITOR_HISTORY_PATTERN = re.compile(
    r"\[(?P<timestamp>[^]]+)\]\s+status=running\s+step=(?P<step>\d+)/(?P<total>\d+)\s+progress=(?P<progress>[\d.]+)%\s+eta=(?P<eta>\S+)"
)


@dataclass(frozen=True)
class PromptSet:
    positive_prompts: list[str]
    negative_prompt: str


def parse_prompt_module_text(text: str) -> PromptSet:
    array_match = PROMPT_ARRAY_PATTERN.search(text)
    negative_match = NEGATIVE_PROMPT_PATTERN.search(text)
    if array_match is None or negative_match is None:
        raise ValueError("could not locate recommended prompt constants")

    prompts = [_unescape_js_single_quoted(value) for value in SINGLE_QUOTED_STRING_PATTERN.findall(array_match.group("body"))]
    negative_prompt = _unescape_js_single_quoted(negative_match.group("value"))
    if not prompts:
        raise ValueError("recommended positive prompt list is empty")
    return PromptSet(positive_prompts=prompts, negative_prompt=negative_prompt)


def parse_generation_training_log(text: str) -> list[dict[str, float | int]]:
    latest_rows: dict[int, dict[str, float | int]] = {}
    for match in TRAINING_STEP_PATTERN.finditer(text):
        step = int(match.group("step"))
        latest_rows[step] = {
            "step": step,
            "total_steps": int(match.group("total")),
            "lr": float(match.group("lr")),
            "step_loss": float(match.group("loss")),
        }
    return [latest_rows[key] for key in sorted(latest_rows)]


def parse_monitor_history(text: str) -> list[dict[str, float | int | str]]:
    rows: list[dict[str, float | int | str]] = []
    for match in MONITOR_HISTORY_PATTERN.finditer(text):
        rows.append(
            {
                "timestamp": match.group("timestamp"),
                "step": int(match.group("step")),
                "total_steps": int(match.group("total")),
                "progress_pct": float(match.group("progress")),
                "eta": match.group("eta"),
            }
        )
    return rows


def summarize_benchmark_rows(rows: list[dict[str, float | int | str]]) -> list[dict[str, float | int | str]]:
    grouped: dict[tuple[str, str], list[dict[str, float | int | str]]] = {}
    for row in rows:
        key = (str(row["generation_model"]), str(row["scoring_model"]))
        grouped.setdefault(key, []).append(row)

    summary_rows: list[dict[str, float | int | str]] = []
    for generation_model, scoring_model in sorted(grouped):
        items = grouped[(generation_model, scoring_model)]
        summary_rows.append(
            {
                "generation_model": generation_model,
                "scoring_model": scoring_model,
                "sample_count": len(items),
                "avg_total_score": _rounded_average(items, "total_score"),
                "avg_visual_fidelity": _rounded_average(items, "visual_fidelity"),
                "avg_text_consistency": _rounded_average(items, "text_consistency"),
                "avg_physical_plausibility": _rounded_average(items, "physical_plausibility"),
                "avg_composition_aesthetics": _rounded_average(items, "composition_aesthetics"),
                "avg_generation_seconds": _rounded_average(items, "generation_seconds"),
            }
        )
    return summary_rows


def _rounded_average(rows: list[dict[str, float | int | str]], key: str) -> float:
    return round(sum(float(item[key]) for item in rows) / max(len(rows), 1), 2)


def _unescape_js_single_quoted(value: str) -> str:
    return value.replace("\\'", "'").replace("\\n", "\n").replace("\\\\", "\\")
