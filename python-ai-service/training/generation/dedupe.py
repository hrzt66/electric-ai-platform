from __future__ import annotations

import hashlib
from pathlib import Path


def compute_file_fingerprint(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def dedupe_rows_by_fingerprint(rows: list[dict]) -> list[dict]:
    seen_fingerprints: set[str] = set()
    deduped: list[dict] = []
    for row in rows:
        fingerprint = compute_file_fingerprint(Path(row["path"]))
        if fingerprint in seen_fingerprints:
            continue
        seen_fingerprints.add(fingerprint)
        enriched = dict(row)
        enriched["fingerprint"] = fingerprint
        deduped.append(enriched)
    return deduped
