# 2. Codex run artifacts live outside the working repository

Date: 2026-09-10

## Status

Accepted. Amended 2026-10-01 to match the code: the override flag is
`--run-dir`, and run folders are named by timestamp alone (#18).

## Context

Each run produces a JSONL event log, the final message, the exact prompt sent,
and a manifest. The obvious home is `.codex-runs/` in the repo being worked on.

Three problems with that:

1. **It poisons verification.** The workflow checks codex's work with
   `git status` and `git diff`. A directory of multi-megabyte logs is permanent
   noise in exactly the signal being read, and suppressing it means editing the
   user's `.gitignore` — a side effect the plugin has no business causing.
2. **It sits inside codex's write scope.** Under `workspace-write`, codex can
   modify its own audit log, and repo-wide globbing surfaces prior briefs and
   stale plans as though they were current project documents.
3. **There is no technical need.** `-o` is written by the codex process itself,
   which is not sandboxed; only model-generated shell commands are. The file can
   live anywhere.

The Claude session scratchpad was also rejected: it is session-scoped and
path-unstable, which breaks resuming a thread across sessions and post-hoc audit.

## Decision

Artifacts go to `~/.claude/codex-headless/runs/<repo>/<timestamp>/`, overridable
with `--run-dir`. The working repository is never written to by the wrapper.

## Consequences

`git status` stays clean, so diff review reflects only codex's actual changes.
Reading an artifact means an absolute path outside the working directory, which
may prompt for permission — mitigated by printing the important details inline in
the run summary so the common path needs no file read at all.
