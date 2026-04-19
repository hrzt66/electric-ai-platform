from __future__ import annotations

import re
from pathlib import Path


TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
STYLE_PREFIX = "realistic utility inspection photography"

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


def build_caption_from_texts(*parts: str, fallback: str = "electric industrial scene") -> str:
    tokens = set(TOKEN_PATTERN.findall(" ".join(part for part in parts if part).lower()))
    caption_parts: list[str] = [STYLE_PREFIX]
    _append_matching_phrases(PRIMARY_PHRASES, tokens, caption_parts)
    _append_matching_phrases(DETAIL_PHRASES, tokens, caption_parts)
    _append_matching_phrases(STYLE_PHRASES, tokens, caption_parts)
    if len(caption_parts) == 1:
        caption_parts.append(fallback)
    return ", ".join(caption_parts)


def apply_stub_caption(row: dict) -> dict:
    enriched = dict(row)
    if enriched.get("caption"):
        existing = str(enriched["caption"]).strip()
        if existing.lower().startswith(STYLE_PREFIX):
            enriched["caption"] = existing
        else:
            enriched["caption"] = f"{STYLE_PREFIX}, {existing}"
        return enriched

    path = Path(enriched["path"])
    enriched["caption"] = build_caption_from_texts(path.as_posix(), path.stem, str(enriched["filename"]))
    return enriched
