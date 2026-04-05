import hashlib


def score_from_prompt(prompt: str) -> dict:
    digest = int(hashlib.md5(prompt.encode("utf-8")).hexdigest()[:8], 16)
    visual = 60 + digest % 20
    text = 65 + digest % 15
    physical = 62 + digest % 18
    aesthetics = 58 + digest % 22
    total = round(visual * 0.25 + text * 0.30 + physical * 0.30 + aesthetics * 0.15, 2)
    return {
        "visual_fidelity": float(visual),
        "text_consistency": float(text),
        "physical_plausibility": float(physical),
        "composition_aesthetics": float(aesthetics),
        "total_score": total,
    }
