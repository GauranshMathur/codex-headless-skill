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


def test_renders_file_changes_with_a_marker_per_kind():
    line = render_event(
        {
            "type": "item.completed",
            "item": {
                "id": "2",
                "type": "file_change",
                "status": "completed",
                "changes": [
                    {"path": "src/auth.py", "kind": "update"},
                    {"path": "tests/test_auth.py", "kind": "add"},
                    {"path": "src/old.py", "kind": "delete"},
                ],
            },
        }
    )

    assert "~ src/auth.py" in line
    assert "+ tests/test_auth.py" in line
    assert "- src/old.py" in line


def test_renders_a_failed_command_with_its_exit_code():
    line = render_event(
        {
            "type": "item.completed",
            "item": {
                "id": "3",
                "type": "command_execution",
                "command": "pytest -q",
                "exit_code": 1,
                "status": "failed",
            },
        }
    )

    assert "1" in line
    assert "pytest -q" in line


def test_ignores_events_that_are_not_worth_a_line():
    assert render_event({"type": "turn.started"}) is None
    assert render_event({"type": "item.updated", "item": {"type": "reasoning"}}) is None
