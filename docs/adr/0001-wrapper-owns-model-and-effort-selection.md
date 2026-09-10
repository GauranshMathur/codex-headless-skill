# 1. The wrapper selects the model and effort, never codex's own config

Date: 2026-09-10

## Status

Accepted

## Context

`codex exec` takes its model from `~/.codex/config.toml` when `-m` is not passed.
Two properties of that fallback make it unsafe for automation:

- A slug that no longer exists is **not rejected**. This machine's config pinned
  `model = "gpt-5-codex"`, which is absent from the 0.153.4 binary; codex accepts
  it and falls back to generic base instructions rather than model-tuned ones.
  Nothing in the output says this happened.
- The most capable model, `gpt-6-astra`, ships `default_reasoning_level: "low"`.
  There is no `--reasoning-effort` flag; effort is only settable through
  `-c model_reasoning_effort=`. So the default pairing is the strongest model at
  its weakest setting.

A hardcoded model list was rejected: the `model_catalog_json` config key can
replace the catalog wholesale, and any fixed list goes stale as models ship.

## Decision

The wrapper resolves both itself and always passes them explicitly.

- Model: `--model` flag, then `CODEX_HEADLESS_MODEL`, then the lowest-`priority`
  entry with `visibility == "list"` from `codex debug models`. An explicitly
  requested slug is validated against the catalog and rejected by name if absent.
- Effort: defaults to `high` rather than the model's own default, and steps down
  the ladder when a model does not offer the requested rung.

## Consequences

Reading the catalog at runtime keeps model selection correct as new models ship
and honours a `model_catalog_json` override, at the cost of one ~20ms subprocess
call per run. A run that could not read the catalog records that it fell back, so
a degraded run is visible rather than looking identical to a healthy one.
