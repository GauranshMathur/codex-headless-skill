"""Turning JSONL events into the lines a human watches scroll past.

This is the part that satisfies "I want to see what codex is doing". Every line
is one event, rendered the moment it arrives.
"""

from codex_run import render_event


def test_renders_a_command_the_agent_is_running():
    line = render_event(
        {
            "type": "item.started",
            "item": {"id": "1", "type": "command_execution", "command": "pytest -q"},
        }
    )

    assert line is not None
    assert "pytest -q" in line
    assert "exec" in line
