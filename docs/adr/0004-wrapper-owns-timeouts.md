# 4. The wrapper enforces its own timeouts and kills the process group

Date: 2026-09-10

## Status

Accepted

## Context

`codex exec` can hang without emitting a terminal event (openai/codex#41984).
Three constraints shape the response:

- **macOS ships no `timeout` binary.** Neither `timeout` nor `gtimeout` exists on
  this machine, so the common `timeout 600 codex …` idiom is unavailable.
- **A wall-clock limit alone does not detect a hang.** A run stuck at nine
  minutes and a run legitimately working for nine minutes look identical to it.
- **Killing the direct child orphans the rest.** codex spawns MCP servers and
  shell children in its session; terminating only the child leaves them running,
  which means codex can keep editing files after the caller believes it stopped.

## Decision

The wrapper enforces two deadlines itself, in Python:

- `--timeout` (wall clock), defaulting below Claude Code's own 600s Bash ceiling
  so the wrapper terminates cleanly and writes a complete record before the
  harness intervenes.
- `--idle-timeout`, measured from the last event on stdout. This is the one that
  catches a hang.

Output is drained on a separate thread so both deadlines can be enforced while a
read is outstanding. On expiry the whole process group gets SIGTERM, then SIGKILL
if it has not exited within the grace period. Liveness is judged by reaping the
direct child rather than probing the group with signal 0 — between SIGTERM and
the reap the child is a zombie, and probing then reports EPERM rather than the
"no such process" the check is looking for.

## Consequences

A hung run stops on its own and leaves nothing running behind it. Partial
progress, including the thread id, survives a timeout, so an interrupted run
stays resumable rather than being lost.
