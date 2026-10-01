# codex-headless

A Claude Code plugin that makes **OpenAI Codex** a delegation target: Claude
scopes the work and verifies the result, Codex writes the code, and you watch it
happen live in the terminal.

```
/codex-headless:exec add retry with exponential backoff to the S3 client;
                     tests/test_s3_client.py must pass
```

## Why this exists

Driving `codex exec` by hand is error-prone in ways that stay invisible until
they cost you a run. All four of these were found by testing against
`codex-cli 0.153.4` rather than reading docs:

| Trap | What actually happens |
|---|---|
| `codex exec` defaults to `read-only` | An implementation request comes back as a *plan*, with no edits and no error |
| A stale `model` in `~/.codex/config.toml` | Codex accepts a slug that no longer exists and silently degrades to generic instructions |
| The most capable model defaults to `low` effort | There is no `--reasoning-effort` flag; it is only settable via `-c model_reasoning_effort=` |
| Exit code `0` | Codex has been observed exiting cleanly having done no work at all |

The wrapper closes all four, and the skill keeps Claude out of the editor so the
resulting diff has a single author.

## Install

```
/plugin marketplace add GauranshMathur/codex-headless-skill
/plugin install codex-headless@gauransh
```

Requires the [Codex CLI](https://github.com/openai/codex) on your PATH and a
logged-in session (`codex login`). Python 3.11+ is used for the wrapper; it has
no third-party dependencies.

## How it works

1. **Claude scopes.** It reads and searches to build an accurate brief — but the
   skill grants no `Edit` or `Write`, so it cannot drift into doing the work.
2. **Codex implements.** The wrapper picks the most capable model, sets a real
   reasoning effort, forces an explicit sandbox, and streams progress:

   ```
   codex | exec  rg "validateToken" src/
   codex | ok    rg "validateToken" src/
   codex | edit  ~ src/auth.py + tests/test_auth.py
   codex | exit1 pytest -q
   ```

3. **Claude verifies.** It re-reads changed files, runs the definition-of-done
   command itself, and reads codex's stated assumptions — then resumes the same
   thread to fix anything wrong.

## Second opinions

`/codex-headless:advise` puts Codex (in a read-only sandbox) and a Fable 5.1
subagent to work as advisors in parallel. It runs only when you ask for it,
either with the command or by asking for "a second opinion" or to "ask codex and
fable". Claude sends both the same brief and merges their verdicts. When they
disagree, Claude shows both positions next to its own view and asks you to
decide.

There are two checkpoints: before Claude commits to an approach, and before it
calls the work done. Asking for advisors on the whole task covers both.
Otherwise your request covers the checkpoint you asked about, and Claude asks
you before it runs the other one.

## Data handling

**What goes to OpenAI.** Codex runs under your own Codex login and sends its
work to OpenAI. That work includes the brief Claude writes, the repository
files Codex reads, and the output of the commands it runs. How OpenAI keeps and
uses that data depends on the terms of your OpenAI account. `exec` sends data
only when you ask Claude to delegate a task, and `advise` only when you ask for
a second opinion. The Fable advisor is a Claude subagent, so it sends nothing to
OpenAI.

**What changes in your Codex setup.** The plugin never writes to
`~/.codex/config.toml`. Instead, each run passes `-c` overrides that apply to
that run only:

- `notify=[]` clears your `notify` hook, so it does not fire at the end of
  every turn.
- `mcp_servers.<name>.enabled=false`, one for each server in your
  `config.toml`, turns off all your MCP servers. Pass the wrapper `--mcp` to
  keep them on.
- The model, reasoning effort, sandbox, and `model_reasoning_summary=auto` are
  set explicitly, for the reasons in [Why this exists](#why-this-exists).

[ADR 0003](docs/adr/0003-headless-isolation.md) explains why the notify hook and
the MCP servers are turned off.

**What stays on your machine.** Each run writes a folder under
`~/.claude/codex-headless/runs/<repo>/<timestamp>/`:

- `events.jsonl` holds Codex's full event stream: its messages and reasoning
  summaries, the commands it ran and their output, and the paths of the files it
  changed.
- `stderr.log` holds Codex's own error output.
- `last-message.md` holds Codex's final reply.
- `prompt.md` holds the brief exactly as Codex received it.
- `manifest.json` records how the run was set up and how it ended: model,
  effort, sandbox, the command line without the brief, timings, outcome, and
  thread id.

These files can hold your code, your brief, and anything Codex printed. The plugin never
deletes them, so remove old runs when you no longer need them. To put a run's
files somewhere else, pass the wrapper `--run-dir`. The wrapper writes nothing
inside your repository, so the only changes there are the ones Codex makes.

Codex also keeps its own session history under `~/.codex/`, which is what lets
a thread be resumed. That is Codex's behaviour, not this plugin's.

## Choosing a model

The model list is read from codex at runtime, never hardcoded, so it stays
correct as new models ship:

```bash
python3 scripts/codex_run.py --list-models
```

```
gpt-6-astra  (default)
    efforts: low, medium, high, xhigh, max, ultra
gpt-5.6-sol
    efforts: low, medium, high, xhigh, max, ultra
...
```

Override for one run with `--model`, or for a session with
`CODEX_HEADLESS_MODEL`. An unknown slug is rejected by name rather than passed
through — which is what catches a stale config.

## Design decisions

Recorded as ADRs in [`docs/adr/`](docs/adr/):

- [0001](docs/adr/0001-wrapper-owns-model-and-effort-selection.md) — the wrapper
  selects model and effort, never codex's own config
- [0002](docs/adr/0002-run-artifacts-live-outside-the-repo.md) — run artifacts
  live outside the working repository
- [0003](docs/adr/0003-headless-isolation.md) — isolating headless runs from
  interactive configuration
- [0004](docs/adr/0004-wrapper-owns-timeouts.md) — the wrapper enforces its own
  timeouts and kills the process group

## Development

```bash
uv venv && uv pip install pytest
.venv/bin/python -m pytest          # the suite runs against a fake codex
claude plugin validate . --strict
claude --plugin-dir .               # load the plugin without installing it
```

Tests never call the real codex or the network: a stand-in executable emits
canned JSONL, which is also how the hang and did-nothing failure modes are
reproduced on demand.

Commits follow [Conventional Commits](https://www.conventionalcommits.org/).
Releases are cut by release-please: each push to `main` refreshes an open
release PR, and merging it tags the release, writes `CHANGELOG.md`, and bumps
the version everywhere it appears — `version.txt`, both plugin manifests, and
the skill's frontmatter.

## Licence

MIT
