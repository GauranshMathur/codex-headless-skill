# When a run goes wrong

| Symptom | Cause | Fix |
|---|---|---|
| `OUTCOME=turn_failed`, message mentions refresh or access tokens | codex's stored credentials are stale. `codex login status` still reports "Logged in" — it does not verify the token | Ask the user to run `codex login`, then retry |
| `codex: command not found` | Claude's shell does not inherit your interactive PATH | `--codex-bin /opt/homebrew/bin/codex`, or set `CODEX_BIN` |
| `EXIT=10`, no files changed | codex exited cleanly without completing a turn (openai/codex#19309) | Re-run. If it repeats, the brief is probably being read as a question — make the Goal an imperative outcome |
| A plan came back, no edits | The run was read-only | `--sandbox workspace-write` (the wrapper's default; something overrode it) |
| `EXIT=13` idle timeout | codex stopped emitting events but never exited (openai/codex#41984) | Re-run; raise `--idle-timeout` only if the task legitimately has long silent stretches |
| `EXIT=12` wall-clock timeout | The task is bigger than one run | Split the brief, or dispatch `codex-headless:codex-runner` which is not bound by the foreground ceiling |
| Run hangs early, before any event | An MCP server is starting, or is waiting on an approval (openai/codex#24135) | MCP is off by default; if you passed `--mcp`, drop it |
| codex asked a question instead of working | The brief left a genuine ambiguity | Resume the thread with the decision. Then fix the brief's Context so the next run does not need to ask |
| Diff includes files you did not expect | No out-of-scope section, or the tree was already dirty | Check `git status` from before the run; add an Out of scope section |
| Changes vanished or history moved | codex ran a destructive git command | Check `git reflog`. Add an explicit prohibition to the brief |

## Reading the artifacts

Every run writes to `RUN_DIR` (printed in the summary, outside the repo by
design — see `docs/adr/0002`):

| File | What it is for |
|---|---|
| `events.jsonl` | the raw stream; the ground truth when a rendered line looks wrong |
| `stderr.log` | codex's own human-readable progress and any startup errors |
| `last-message.md` | codex's final reply |
| `prompt.md` | the brief exactly as codex received it |
| `manifest.json` | the model and where it came from, effort requested and used, sandbox, argv without the brief, timings, outcome, and thread id. `"outcome": "running"` on a finished process means the wrapper was killed before it could record the end |

When the summary and the diff disagree, `events.jsonl` settles it — the
`file_change` events record what codex actually wrote.
