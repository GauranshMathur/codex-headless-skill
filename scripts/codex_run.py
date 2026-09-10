#!/usr/bin/env python3
"""Run OpenAI Codex CLI headlessly and stream its progress.

Stdlib only, on purpose: this ships inside a Claude Code plugin, so installing
the plugin must not require installing anything else.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


class UnknownModel(ValueError):
    """A model slug was requested that this codex build does not know.

    Worth failing on rather than passing through: codex accepts an unknown slug
    without complaint and quietly falls back to generic base instructions.
    """


@dataclass(frozen=True)
class ModelChoice:
    """A resolved model, plus where the choice came from.

    `source` is recorded in the run manifest so a degraded run (one that fell
    back rather than reading the catalog) is visible after the fact instead of
    looking identical to a healthy one.
    """

    slug: str
    source: str


MODEL_ENV_VAR = "CODEX_HEADLESS_MODEL"


def resolve_model(
    catalog: dict,
    explicit: str | None = None,
    env: dict | None = None,
) -> ModelChoice:
    """Pick the model codex should run on.

    Precedence is flag, then environment, then the most capable model on offer.
    `priority` ranks capability with 1 as the most capable, and `visibility`
    marks which models are user-selectable rather than internal.

    `env` is injected rather than read from os.environ directly so the choice
    stays a pure function of its inputs.
    """
    env = os.environ if env is None else env
    listed = [m for m in catalog["models"] if m["visibility"] == "list"]

    requested, source = (explicit, "flag")
    if not requested:
        requested, source = (env.get(MODEL_ENV_VAR), "env")

    if requested:
        # Accept any slug the catalog knows, including hidden ones a power user
        # may deliberately want; only suggest the user-selectable ones.
        if requested not in {m["slug"] for m in catalog["models"]}:
            available = ", ".join(sorted(m["slug"] for m in listed))
            raise UnknownModel(
                f"{requested!r} is not a model this codex build knows. "
                f"Available: {available}"
            )
        return ModelChoice(slug=requested, source=source)

    best = min(listed, key=lambda m: m["priority"])
    return ModelChoice(slug=best["slug"], source="catalog")


DEFAULT_EFFORT = "high"


@dataclass(frozen=True)
class EffortChoice:
    """A resolved reasoning effort, and what was asked for before validation."""

    effort: str
    requested: str
    warning: str | None = None


def resolve_effort(model: dict, requested: str | None = None) -> EffortChoice:
    """Pick the reasoning effort for a run.

    Deliberately ignores the model's own `default_reasoning_level`: gpt-6-astra
    defaults to "low", and pairing the most capable model with its weakest
    reasoning setting defeats the point of choosing it.
    """
    wanted = requested or DEFAULT_EFFORT
    return EffortChoice(effort=wanted, requested=wanted)
