"""End to end over a fake codex: spawn, stream, capture, classify."""

from codex_run import decide_outcome, run_codex


def test_streams_events_captures_them_and_records_the_thread_id(tmp_path, fake_codex):
    binary = fake_codex(
        [
            {"type": "thread.started", "thread_id": "th_123"},
            {"type": "turn.started"},
            {
                "type": "item.completed",
                "item": {
                    "type": "file_change",
                    "changes": [{"path": "a.py", "kind": "add"}],
                },
            },
            {"type": "turn.completed", "usage": {"output_tokens": 10}},
        ]
    )
    run_dir = tmp_path / "run"
    rendered = []

    result = run_codex([binary], run_dir=run_dir, on_line=rendered.append)

    assert result.exit_code == 0
    assert result.thread_id == "th_123"
    assert (run_dir / "events.jsonl").exists()
    assert any("a.py" in line for line in rendered)


def test_a_clean_exit_that_did_no_work_is_reported_as_a_failure(tmp_path, fake_codex):
    """The end-to-end version of openai/codex#19309: codex starts a thread, exits
    0, and never completes a turn. Nothing about the process signals a problem."""
    binary = fake_codex(
        [{"type": "thread.started", "thread_id": "th_9"}, {"type": "turn.started"}],
        exit_code=0,
    )

    result = run_codex([binary], run_dir=tmp_path / "run")
    outcome = decide_outcome(result.exit_code, result.events)

    assert result.exit_code == 0
    assert outcome.status == "no_turn_completed"
    assert outcome.exit_code == 10


def test_a_failed_turn_surfaces_the_reason(tmp_path, fake_codex):
    binary = fake_codex(
        [
            {"type": "thread.started", "thread_id": "th_10"},
            {"type": "error", "message": "Reconnecting... 1/5"},
            {"type": "turn.failed", "error": {"message": "context window exceeded"}},
        ],
        exit_code=1,
    )

    result = run_codex([binary], run_dir=tmp_path / "run")
    outcome = decide_outcome(result.exit_code, result.events)

    assert outcome.status == "turn_failed"
    assert "context window exceeded" in outcome.detail
