"""End to end over a fake codex: spawn, stream, capture, classify."""

from codex_run import run_codex


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
