#!/usr/bin/env python3
"""Run OpenAI Codex CLI headlessly and stream its progress.

Stdlib only, on purpose: this ships inside a Claude Code plugin, so installing
the plugin must not require installing anything else.
"""

from __future__ import annotations

import argparse
import json
import os
import queue
import signal
import subprocess
import sys
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path


class CatalogUnavailable(RuntimeError):
    """codex's model catalog could not be read at all."""


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
DEFAULT_SANDBOX = "workspace-write"

# Single characters so a run touching several files still fits on one line.
CHANGE_MARKERS = {"add": "+", "update": "~", "delete": "-"}

# Ordered weakest to strongest. Used to step down when a model does not offer
# the requested rung.
EFFORT_LADDER = ["low", "medium", "high", "xhigh", "max", "ultra"]


class UnsupportedEffort(ValueError):
    """No reasoning effort at or below the requested one exists for this model."""



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
    supported = [level["effort"] for level in model["supported_reasoning_levels"]]

    if wanted in supported:
        return EffortChoice(effort=wanted, requested=wanted)

    # Degrade rather than fail: not every model reaches the top rungs, and a run
    # at the next level down is far more useful than an aborted one.
    below = EFFORT_LADDER[: EFFORT_LADDER.index(wanted)] if wanted in EFFORT_LADDER else []
    for candidate in reversed(below):
        if candidate in supported:
            return EffortChoice(
                effort=candidate,
                requested=wanted,
                warning=(
                    f"{model['slug']} does not support effort {wanted!r}; "
                    f"using {candidate!r} instead."
                ),
            )

    raise UnsupportedEffort(
        f"{model['slug']} supports no effort at or below {wanted!r}. "
        f"Supported: {', '.join(supported)}"
    )


# Exit codes the wrapper itself returns, chosen so a caller can branch on the
# failure mode without reading the message.
EXIT_NO_TURN_COMPLETED = 10
EXIT_TURN_FAILED = 11
EXIT_TIMEOUT = 12
EXIT_IDLE_TIMEOUT = 13


@dataclass(frozen=True)
class Outcome:
    """How a run ended, and the process exit code that reports it.

    Distinct exit codes let the caller branch on the failure mode without
    parsing prose.
    """

    status: str
    exit_code: int
    detail: str | None = None


def decide_outcome(
    exit_code: int,
    events: list[dict],
    timed_out: str | None = None,
) -> Outcome:
    """Classify a finished run.

    Success needs both a clean exit *and* an observed terminal event, because
    codex can exit 0 without having done any work.
    """
    # A run we stopped ourselves is reported as such whatever the process did on
    # its way out; the exit code of a killed process says nothing useful.
    if timed_out:
        return Outcome(
            status="timeout",
            exit_code=EXIT_TIMEOUT if timed_out == "wall_clock" else EXIT_IDLE_TIMEOUT,
            detail=f"run stopped after the {timed_out.replace('_', ' ')} limit was reached.",
        )

    seen = {event.get("type") for event in events}

    # A failed turn is authoritative however the process exited. Note this looks
    # only at `turn.failed`: top-level `error` events also carry retry notices
    # such as "Reconnecting... 1/5", so they are logged, not treated as fatal.
    failure = next((e for e in events if e.get("type") == "turn.failed"), None)
    if failure is not None:
        return Outcome(
            status="turn_failed",
            exit_code=EXIT_TURN_FAILED,
            detail=failure.get("error", {}).get("message"),
        )

    if exit_code == 0 and "turn.completed" in seen:
        return Outcome(status="success", exit_code=0)

    if exit_code == 0:
        return Outcome(
            status="no_turn_completed",
            exit_code=EXIT_NO_TURN_COMPLETED,
            detail="codex exited cleanly without completing a turn; no work was done.",
        )

    return Outcome(status="unknown", exit_code=1)


def build_argv(
    *,
    model: str,
    effort: str,
    prompt: str,
    sandbox: str = DEFAULT_SANDBOX,
    cwd: str | None = None,
    last_message_path: str | None = None,
    mcp_servers: list[str] | None = None,
    codex_bin: str = "codex",
    resume: str | None = None,
) -> list[str]:
    """Assemble the `codex exec` command line.

    The model is always passed explicitly. Leaving it out lets the user's
    ~/.codex/config.toml choose, and codex accepts a stale slug there without
    complaint.
    """
    # --color never: we render the run ourselves from the JSONL stream, and stray
    # escape sequences only make the captured stderr log harder to read.
    argv = [codex_bin, "exec"]
    if resume:
        # codex exec resume [OPTIONS] [SESSION_ID] [PROMPT] — options first.
        argv.append("resume")
    argv += ["--json", "--color", "never", "-m", model]

    # Always explicit: codex exec defaults to read-only, so an implementation
    # task without this produces a plan and no edits.
    argv += ["-s", sandbox]

    argv += ["-c", f"model_reasoning_effort={effort}"]
    # Reasoning summaries are what populate the live progress stream; codex
    # suppresses `reasoning` items entirely when this is "none".
    argv += ["-c", "model_reasoning_summary=auto"]
    # A configured notify hook fires on every turn end. Arrays replace on
    # override (unlike tables, which merge), so an empty list clears it.
    argv += ["-c", "notify=[]"]

    # `-c mcp_servers={}` does NOT work: tables deep-merge, so an empty table
    # changes nothing and every server stays enabled. Disable them by name.
    for server in mcp_servers or []:
        argv += ["-c", f"mcp_servers.{server}.enabled=false"]

    if cwd:
        argv += ["-C", cwd]
    if last_message_path:
        argv += ["-o", last_message_path]

    if resume:
        argv.append(resume)

    argv.append(prompt)
    return argv


def render_event(event: dict) -> str | None:
    """Render one JSONL event as a single progress line.

    Returns None for events that should not produce a line, so the caller can
    simply skip falsy results.
    """
    kind = event.get("type")
    item = event.get("item", {})
    item_kind = item.get("type")

    if kind == "item.started" and item_kind == "command_execution":
        return f"exec  {item.get('command', '')}"

    if kind == "item.completed":
        if item_kind == "command_execution":
            exit_code = item.get("exit_code")
            status = "ok   " if exit_code == 0 else f"exit{exit_code}"
            return f"{status} {item.get('command', '')}"

        if item_kind == "file_change":
            changes = " ".join(
                f"{CHANGE_MARKERS.get(c.get('kind'), '?')} {c.get('path')}"
                for c in item.get("changes", [])
            )
            return f"edit  {changes}"

    return None


@dataclass
class RunResult:
    """What a finished codex process left behind."""

    exit_code: int
    events: list[dict]
    thread_id: str | None = None
    timed_out: str | None = None
    pgid: int | None = None


def _terminate_group(pgid: int, process: subprocess.Popen, grace: float = 10.0) -> None:
    """Kill the whole process group, escalating if it does not go quietly.

    Killing only the direct child would orphan codex's own children, which then
    keep editing files after the caller believes the run has stopped.

    Liveness is judged by reaping the direct child rather than by probing the
    group with signal 0: between SIGTERM and the reap the child is a zombie, and
    probing a group whose only member is a zombie reports EPERM rather than the
    "no such process" this wants to detect.
    """
    try:
        os.killpg(pgid, signal.SIGTERM)
    except ProcessLookupError:
        return

    try:
        process.wait(timeout=grace)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(pgid, signal.SIGKILL)
        except ProcessLookupError:
            pass


def run_codex(
    argv: list[str],
    *,
    run_dir: Path,
    on_line: Callable[[str], None] | None = None,
    timeout: float | None = None,
    idle_timeout: float | None = None,
) -> RunResult:
    """Spawn codex, stream its JSONL, and capture everything to `run_dir`.

    Events are rendered as they arrive rather than at the end, so a long run is
    visible while it happens. The raw stream is kept verbatim alongside, since a
    rendered line is lossy and post-hoc debugging needs the original.

    codex's own stdin is /dev/null: an inherited pipe gets appended to the prompt
    as a <stdin> block, and a closed stdin turns any approval read into an
    immediate EOF instead of a hang.

    Output is drained on a separate thread so the two deadlines can be enforced
    while a read is outstanding. `idle_timeout` is the one that catches a hung
    run — a wall-clock limit alone cannot distinguish a run that is stuck from
    one that is merely long.
    """
    run_dir.mkdir(parents=True, exist_ok=True)
    events: list[dict] = []
    thread_id: str | None = None
    timed_out: str | None = None

    with (
        open(run_dir / "events.jsonl", "w", encoding="utf-8") as raw,
        open(run_dir / "stderr.log", "wb") as errlog,
    ):
        process = subprocess.Popen(
            argv,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=errlog,
            text=True,
            encoding="utf-8",
            errors="replace",
            start_new_session=True,
        )
        pgid = os.getpgid(process.pid)

        inbox: queue.Queue[str | None] = queue.Queue()

        def drain() -> None:
            try:
                for line in process.stdout:
                    inbox.put(line)
            finally:
                inbox.put(None)

        threading.Thread(target=drain, daemon=True).start()

        started = time.monotonic()
        last_seen = started

        while True:
            now = time.monotonic()
            if timeout is not None and now - started >= timeout:
                timed_out = "wall_clock"
                break
            if idle_timeout is not None and now - last_seen >= idle_timeout:
                timed_out = "idle"
                break

            budgets = [
                deadline - elapsed
                for deadline, elapsed in (
                    (timeout, now - started),
                    (idle_timeout, now - last_seen),
                )
                if deadline is not None
            ]

            try:
                line = inbox.get(timeout=min(budgets) if budgets else None)
            except queue.Empty:
                continue

            if line is None:
                break

            raw.write(line)
            last_seen = time.monotonic()

            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                # A crashed codex can leave a truncated final line. One bad line
                # is not a reason to discard a whole run.
                continue

            events.append(event)
            if event.get("type") == "thread.started":
                thread_id = event.get("thread_id")

            if on_line is not None:
                rendered = render_event(event)
                if rendered:
                    on_line(rendered)

        if timed_out:
            _terminate_group(pgid, process)

        process.wait()

    return RunResult(
        exit_code=process.returncode,
        events=events,
        thread_id=thread_id,
        timed_out=timed_out,
        pgid=pgid,
    )


def load_catalog() -> dict:
    """Read codex's model catalog.

    The bundled catalog is the primary source: it needs no network, returns in
    milliseconds, and on the builds checked matches the refreshed one byte for
    byte. The network refresh is the fallback, since it is what picks up a
    `model_catalog_json` override or a server-side addition.
    """
    for command in (
        ["codex", "debug", "models", "--bundled"],
        ["codex", "debug", "models"],
    ):
        try:
            done = subprocess.run(command, capture_output=True, text=True, timeout=30)
        except (OSError, subprocess.SubprocessError):
            continue
        if done.returncode == 0:
            try:
                return json.loads(done.stdout)
            except json.JSONDecodeError:
                continue
    raise CatalogUnavailable(
        "Could not read the codex model catalog. Is codex installed and on PATH?"
    )


def read_prompt() -> str:
    """Read the brief from our own stdin.

    Taking the brief this way means the caller never needs a file-writing tool to
    hand over a long prompt — a bash heredoc is enough.
    """
    return sys.stdin.read()


def _mcp_server_names(codex_home: Path | None = None) -> list[str]:
    """Names of every MCP server configured for codex.

    Needed because servers can only be switched off one at a time; there is no
    working way to clear them all at once.
    """
    home = codex_home or Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
    config = home / "config.toml"
    if not config.exists():
        return []
    try:
        import tomllib

        with open(config, "rb") as handle:
            return list(tomllib.load(handle).get("mcp_servers", {}).keys())
    except Exception:
        return []


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="codex_run.py",
        description="Run Codex headless with a sane model, effort and sandbox.",
    )
    parser.add_argument("--model", help="model slug; defaults to the most capable")
    parser.add_argument("--effort", help=f"reasoning effort (default {DEFAULT_EFFORT})")
    parser.add_argument("--sandbox", default=DEFAULT_SANDBOX)
    parser.add_argument("--cwd", help="workspace root for the run")
    parser.add_argument("--timeout", type=float, default=570.0)
    parser.add_argument("--idle-timeout", type=float, default=300.0)
    parser.add_argument("--run-dir", help="where to write this run's artifacts")
    parser.add_argument(
        "--resume",
        metavar="THREAD",
        help="continue an existing codex thread instead of starting a new one",
    )
    parser.add_argument("--mcp", action="store_true", help="leave MCP servers enabled")
    parser.add_argument(
        "--codex-bin",
        default=os.environ.get("CODEX_BIN", "codex"),
        help="path to the codex executable, when it is not on PATH",
    )
    parser.add_argument("--list-models", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(
    argv: list[str] | None = None,
    *,
    catalog_loader: Callable[[], dict] = load_catalog,
    prompt_reader: Callable[[], str] = read_prompt,
) -> int:
    args = build_parser().parse_args(argv)
    catalog = catalog_loader()

    if args.list_models:
        default = resolve_model(catalog, env={})
        listed = sorted(
            (m for m in catalog["models"] if m.get("visibility") == "list"),
            key=lambda m: m.get("priority", 9999),
        )
        for model in listed:
            marker = "  (default)" if model["slug"] == default.slug else ""
            efforts = ", ".join(
                level["effort"] for level in model.get("supported_reasoning_levels", [])
            )
            print(f"{model['slug']}{marker}\n    efforts: {efforts}")
        return 0

    model = resolve_model(catalog, explicit=args.model)
    spec = next(m for m in catalog["models"] if m["slug"] == model.slug)
    effort = resolve_effort(spec, requested=args.effort)
    if effort.warning:
        print(f"warning: {effort.warning}", file=sys.stderr)

    run_dir = Path(args.run_dir) if args.run_dir else _default_run_dir(args.cwd)
    argv_out = build_argv(
        model=model.slug,
        effort=effort.effort,
        prompt=prompt_reader(),
        sandbox=args.sandbox,
        cwd=args.cwd,
        last_message_path=str(run_dir / "last-message.md"),
        mcp_servers=[] if args.mcp else _mcp_server_names(),
        codex_bin=args.codex_bin,
        resume=args.resume,
    )

    if args.dry_run:
        print(" ".join(argv_out[:-1]))
        return 0

    started = time.monotonic()

    result = run_codex(
        argv_out,
        run_dir=run_dir,
        on_line=lambda line: print(f"codex | {line}", file=sys.stderr, flush=True),
        timeout=args.timeout,
        idle_timeout=args.idle_timeout,
    )
    outcome = decide_outcome(result.exit_code, result.events, timed_out=result.timed_out)

    # Summary on stdout, progress on stderr: the caller parses one and watches
    # the other. THREAD is here so an interrupted run stays resumable.
    print("=== codex run summary ===")
    print(f"OUTCOME={outcome.status}  EXIT={outcome.exit_code}")
    print(f"MODEL={model.slug}/{effort.effort}  SANDBOX={args.sandbox}")
    print(f"DURATION={time.monotonic() - started:.1f}s")
    print(f"THREAD={result.thread_id or '-'}")
    print(f"RUN_DIR={run_dir}")
    if outcome.detail:
        print(f"DETAIL={outcome.detail}")

    return outcome.exit_code


def _default_run_dir(cwd: str | None) -> Path:
    """Artifacts live outside the working repo — see docs/adr/0002."""
    repo = Path(cwd or Path.cwd()).resolve().name
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    return Path.home() / ".claude" / "codex-headless" / "runs" / repo / stamp


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
