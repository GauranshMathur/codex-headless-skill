# 1. The wrapper selects the model and effort, never codex's own config

Date: 2026-09-10

## Status

Accepted. Amended 2026-10-01 to match the code: the bundled catalog is read
first, and the run manifest records where the model came from (#18).

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
  entry with `visibility == "list"` in the catalog. The catalog is read with
  `codex debug models --bundled`, which needs no network, and with
  `codex debug models` only if that fails. An explicitly requested slug is
  validated against the catalog and rejected by name if absent.
- Effort: defaults to `high` rather than the model's own default, and steps down
  the ladder when a model does not offer the requested rung.

## Consequences

Reading the catalog at runtime keeps model selection correct as new models ship,
at the cost of one ~20ms subprocess call per run.

A `model_catalog_json` override is a known gap. Only the refreshed catalog picks
it up, and the refreshed catalog is read only when the bundled read fails. So on
a working install the override is not honoured.

There is no silent fallback. A run that cannot read either catalog stops with
`CatalogUnavailable` rather than guessing a model. Each run's `manifest.json`
records where its model came from (`model_source`: `flag`, `env` or `catalog`)
and any step down in effort. A run that did not get what was asked for is
therefore visible after the fact, rather than looking identical to one that did.
