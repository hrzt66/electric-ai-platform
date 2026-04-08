from __future__ import annotations

import re
from pathlib import Path


TOKEN_PATTERN = re.compile(r"[a-z0-9]+")

PRIMARY_PHRASES = [
    ({"transmission", "line"}, "electric power transmission line"),
    ({"substation"}, "electric power substation"),
    ({"wind", "turbine"}, "wind turbine"),
    ({"solar", "panel"}, "solar power equipment"),
]

DETAIL_PHRASES = [
    ({"insulator"}, "insulator equipment"),
    ({"transformer"}, "transformer equipment"),
    ({"breaker"}, "breaker equipment"),
    ({"switchgear"}, "switchgear equipment"),
    ({"tower"}, "transmission tower"),
    ({"pylon"}, "transmission tower"),
    ({"pole"}, "utility pole"),
    ({"conductor"}, "power conductor"),
    ({"cable"}, "power cable"),
    ({"busbar"}, "busbar equipment"),
    ({"disconnect"}, "disconnect switch"),
]

STYLE_PHRASES = [
    ({"uav"}, "aerial inspection view"),
    ({"drone"}, "aerial inspection view"),
    ({"remote", "sensing"}, "remote sensing view"),
    ({"detection"}, "inspection dataset image"),
    ({"classification"}, "equipment classification image"),
]


def _extract_tokens(row: dict) -> set[str]:
    path = Path(row["path"])
    token_source = " ".join([path.as_posix(), path.stem, row["filename"]])
    return set(TOKEN_PATTERN.findall(token_source.lower()))


def _append_matching_phrases(phrases: list[tuple[set[str], str]], tokens: set[str], parts: list[str]) -> None:
    for required_tokens, label in phrases:
        if required_tokens.issubset(tokens) and label not in parts:
            parts.append(label)


def apply_stub_caption(row: dict) -> dict:
    enriched = dict(row)
    tokens = _extract_tokens(enriched)
    caption_parts: list[str] = []
    _append_matching_phrases(PRIMARY_PHRASES, tokens, caption_parts)
    _append_matching_phrases(DETAIL_PHRASES, tokens, caption_parts)
    _append_matching_phrases(STYLE_PHRASES, tokens, caption_parts)
    enriched["caption"] = ", ".join(caption_parts) if caption_parts else "electric industrial scene"
    return enriched
