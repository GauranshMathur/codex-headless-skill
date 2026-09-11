# 3. Isolate headless runs from interactive configuration

Date: 2026-09-10

## Status

Accepted

## Context

`codex exec` inherits the user's interactive configuration. Three parts of that
inheritance are actively harmful to an unattended run:

- **MCP servers.** Every configured server is started. On this machine that is
  five, one of which launches a binary out of `ChatGPT.app` with a 120s startup
  timeout. There is also an open upstream bug (openai/codex#24135) where an MCP
  tool call reaches for an approval on stdin and fails or hangs.
- **The `notify` hook.** It fires on every turn end; here it spawns a GUI helper.
- **stdin.** `codex exec --help` states that when stdin is piped *and* a prompt
  is supplied, stdin is appended to the prompt as a `<stdin>` block. Inheriting
  a pipe therefore corrupts the brief.

The obvious mitigation for MCP, `-c mcp_servers={}`, **does not work**. Verified
against 0.153.4: `codex mcp list -c 'mcp_servers={}'` still reports all five
servers. Config tables deep-merge, so an empty table merges no change. Arrays,
by contrast, replace.

## Decision

- Disable MCP servers individually: `-c mcp_servers.<name>.enabled=false`, one
  per server, with names read from `config.toml` at runtime. Verified to leave
  all five reporting `disabled`.
- Clear the notify hook with `-c notify=[]`, which works because arrays replace.
- Give codex `stdin=DEVNULL` always. The brief is read by the wrapper from *its*
  stdin before spawning, then passed as an argv argument.

`--ignore-user-config` was rejected as the default: it also discards profiles,
project trust levels, and the model, which is a much larger behaviour change
than this needs.

## Consequences

Headless runs are reproducible and cannot hang on an approval prompt. Anyone who
genuinely wants MCP tools available in a run opts back in explicitly. A server
name containing a dot cannot be expressed as a dotted override path and has to
fall back to `--ignore-user-config`; no such name exists today.
