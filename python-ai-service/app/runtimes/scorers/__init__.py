from __future__ import annotations

from importlib import import_module

__all__ = [
    "AestheticRuntime",
    "ClipIQARuntime",
    "DEFAULT_SCORING_MODEL_NAME",
    "ImageRewardRuntime",
    "PowerScoreRuntime",
    "SELF_TRAINED_SCORING_MODEL_NAME",
]

_LAZY_IMPORTS = {
    "AestheticRuntime": "app.runtimes.scorers.aesthetic_runtime",
    "ClipIQARuntime": "app.runtimes.scorers.clip_iqa_runtime",
    "ImageRewardRuntime": "app.runtimes.scorers.image_reward_runtime",
    "PowerScoreRuntime": "app.runtimes.scorers.power_score_runtime",
    "DEFAULT_SCORING_MODEL_NAME": "app.runtimes.scorers.power_score_runtime",
    "SELF_TRAINED_SCORING_MODEL_NAME": "app.runtimes.scorers.power_score_runtime",
}


def __getattr__(name: str):
    module_name = _LAZY_IMPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module(module_name)
    value = getattr(module, name)
    globals()[name] = value
    return value
