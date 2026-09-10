#!/usr/bin/env python3
"""Run OpenAI Codex CLI headlessly and stream its progress.

Stdlib only, on purpose: this ships inside a Claude Code plugin, so installing
the plugin must not require installing anything else.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelChoice:
    """A resolved model, plus where the choice came from.

    `source` is recorded in the run manifest so a degraded run (one that fell
    back rather than reading the catalog) is visible after the fact instead of
    looking identical to a healthy one.
    """

    slug: str
    source: str


def resolve_model(catalog: dict, explicit: str | None = None) -> ModelChoice:
    """Pick the model codex should run on.

    An explicitly requested slug wins; otherwise take the most capable one on
    offer. `priority` ranks capability with 1 as the most capable, and
    `visibility` marks which models are user-selectable rather than internal.
    """
    if explicit:
        return ModelChoice(slug=explicit, source="flag")

    listed = [m for m in catalog["models"] if m["visibility"] == "list"]
    best = min(listed, key=lambda m: m["priority"])
    return ModelChoice(slug=best["slug"], source="catalog")
