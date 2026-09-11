# Models, effort, and the wrapper's flags

## Choosing a model

The wrapper reads codex's own catalog at runtime and picks the most capable
model on offer — currently `gpt-6-astra`. It is never hardcoded, because the
`model_catalog_json` config key can replace the catalog entirely and any fixed
list goes stale as models ship.

See what is available and which one is the default:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/codex_run.py" --list-models
```

Switch models three ways, in precedence order:

| How | When to use it |
|---|---|
| `--model <slug>` | one run |
| `CODEX_HEADLESS_MODEL=<slug>` | a whole session |
| nothing | you want the most capable one |

A slug the catalog does not know is rejected by name rather than passed through.
This matters: codex accepts an unknown slug without complaint and silently falls
back to generic instructions, which is how a stale `model = "gpt-5-codex"` in
`~/.codex/config.toml` costs a run without saying so.

## Choosing an effort

Every run uses `high` unless the user asks for a different effort. Do not pick
one yourself, up or down: the trade between cost and depth belongs to the user,
and a run that quietly drops to `low` or climbs to `max` spends their budget on
a decision they never made. `high` is deliberately not the model's own
default — `gpt-6-astra` ships `default_reasoning_level: "low"`, and the
strongest model at its weakest setting is the worst of both.

When the user does ask, pass `--effort <level>`. If they describe what they want
("go cheap on this", "think hard") rather than naming a level, map it with this
table:

| Effort | Suits |
|---|---|
| `low` / `medium` | mechanical, repetitive edits across many files |
| `high` | the default; ordinary feature and bug work |
| `xhigh` / `max` | concurrency, algorithms, several subtly interacting changes |
| `ultra` | rare; only on the hardest problems, and only worth it with a tight brief |

Not every model reaches every rung — `gpt-5.5` stops at `xhigh`. Asking for more
than a model offers steps down to its best supported rung and says so, rather
than failing the run.

`max` and `ultra` on a vague brief is the main way to spend a lot of money on a
bad diff. If a run at `high` falls short, tighten the brief first; if more effort
still seems warranted, suggest it to the user rather than raising it yourself.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | success — codex exited cleanly *and* completed a turn |
| 10 | exited 0 without completing a turn; no work was done |
| 11 | the turn failed; the reason is in `DETAIL` |
| 12 | wall-clock timeout |
| 13 | idle timeout — no event for `--idle-timeout` seconds |

Exit 0 alone is not proof of success, which is why 10 exists: codex has been
observed exiting cleanly having done nothing at all.

## Flags worth knowing

| Flag | Default | Notes |
|---|---|---|
| `--sandbox` | `workspace-write` | `codex exec` itself defaults to `read-only`, which produces a plan and no edits |
| `--timeout` | 570 | sits below Claude's 600s Bash ceiling so the wrapper finishes cleanly first |
| `--idle-timeout` | 300 | the one that catches a hang; a wall-clock limit cannot tell stuck from slow |
| `--resume THREAD` | — | continue a thread; the id is in the run summary |
| `--mcp` | off | leave codex's MCP servers enabled; off by default because they slow startup and can hang on approvals |
| `--codex-bin` | `codex` | when Claude's shell lacks your interactive PATH |
| `--dry-run` | — | print the assembled command and stop |
