"""Shared fixtures.

The integration tests drive a stand-in `codex` executable rather than the real
one, so they cost nothing, need no network or auth, and can reproduce failure
modes (a hang, a clean exit that did no work) on demand.
"""

import json
import textwrap

import pytest


@pytest.fixture
def fake_codex(tmp_path):
    """Build a stand-in codex that emits the given events then exits."""

    def _make(events, exit_code=0, delay=0.0, then_sleep=0.0, name="fake_codex"):
        payload = "\n".join(json.dumps(event) for event in events)
        script = tmp_path / name
        script.write_text(
            textwrap.dedent(
                f"""\
                #!/usr/bin/env python3
                import sys, time
                from pathlib import Path
                for line in {payload!r}.splitlines():
                    print(line, flush=True)
                    time.sleep({delay})
                # Stand in for a codex that stops emitting but never exits
                # (openai/codex#41984).
                time.sleep({then_sleep})
                if "-o" in sys.argv:
                    Path(sys.argv[sys.argv.index("-o") + 1]).write_text("Final message from fake codex\\n")
                sys.exit({exit_code})
                """
            )
        )
        script.chmod(0o755)
        return str(script)

    return _make
