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

    def _make(events, exit_code=0, delay=0.0, name="fake_codex"):
        payload = "\n".join(json.dumps(event) for event in events)
        script = tmp_path / name
        script.write_text(
            textwrap.dedent(
                f"""\
                #!/usr/bin/env python3
                import sys, time
                for line in {payload!r}.splitlines():
                    print(line, flush=True)
                    time.sleep({delay})
                sys.exit({exit_code})
                """
            )
        )
        script.chmod(0o755)
        return str(script)

    return _make
