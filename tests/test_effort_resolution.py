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


# gpt-5.5 and gpt-5.2 really do stop at xhigh, while gpt-6-astra goes to ultra —
# so asking for "ultra" has to degrade rather than blow up on a lesser model.
NO_TOP_LEVELS = ["low", "medium", "high", "xhigh"]


@pytest.mark.parametrize(
    "requested,supported,expected",
    [
        ("ultra", ALL_LEVELS, "ultra"),
        ("ultra", NO_TOP_LEVELS, "xhigh"),
        ("max", NO_TOP_LEVELS, "xhigh"),
        ("high", NO_TOP_LEVELS, "high"),
        ("low", NO_TOP_LEVELS, "low"),
    ],
)
def test_unsupported_effort_walks_down_to_the_best_supported(
    requested, supported, expected
):
    choice = resolve_effort(_model(levels=supported), requested=requested)

    assert choice.effort == expected
    assert choice.requested == requested


def test_walking_down_explains_itself():
    choice = resolve_effort(_model(levels=NO_TOP_LEVELS), requested="ultra")

    assert choice.warning is not None
    assert "ultra" in choice.warning
    assert "xhigh" in choice.warning


def test_no_warning_when_the_request_is_honoured():
    assert resolve_effort(_model(), requested="ultra").warning is None
