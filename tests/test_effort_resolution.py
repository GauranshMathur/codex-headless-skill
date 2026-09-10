"""Reasoning effort — how hard the model thinks.

The trap this guards: gpt-6-astra ships default_reasoning_level "low". Reaching
for the most capable model and then running it at its weakest setting is the
worst of both worlds, so the wrapper picks the effort itself rather than
inheriting the model's default.
"""

import pytest

from codex_run import resolve_effort

ALL_LEVELS = ["low", "medium", "high", "xhigh", "max", "ultra"]


def _model(levels=ALL_LEVELS, default="low"):
    return {
        "slug": "a-model",
        "default_reasoning_level": default,
        "supported_reasoning_levels": [{"effort": e} for e in levels],
    }


def test_defaults_to_high_rather_than_the_models_own_default():
    choice = resolve_effort(_model(default="low"))

    assert choice.effort == "high"
