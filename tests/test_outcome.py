"""Deciding whether a run actually succeeded.

The trap this guards: `codex exec` has been observed exiting 0 having done
nothing (openai/codex#19309) and hanging without emitting a terminal event
(#41984). So a zero exit code on its own is not evidence of success — we also
require having seen the turn complete.
"""

from codex_run import decide_outcome


def test_exit_zero_with_a_completed_turn_is_success():
    outcome = decide_outcome(exit_code=0, events=[{"type": "turn.completed"}])

    assert outcome.status == "success"
    assert outcome.exit_code == 0


def test_exit_zero_without_a_completed_turn_is_not_success():
    """openai/codex#19309 — codex exits cleanly having done nothing at all."""
    outcome = decide_outcome(
        exit_code=0,
        events=[{"type": "thread.started", "thread_id": "abc"}, {"type": "turn.started"}],
    )

    assert outcome.status == "no_turn_completed"
    assert outcome.exit_code == 10


def test_turn_failed_is_fatal_and_surfaces_the_reason():
    outcome = decide_outcome(
        exit_code=1,
        events=[{"type": "turn.failed", "error": {"message": "model overloaded"}}],
    )

    assert outcome.status == "turn_failed"
    assert outcome.exit_code == 11
    assert "model overloaded" in outcome.detail


def test_transient_error_events_do_not_sink_an_otherwise_good_run():
    """Codex reports reconnect attempts on the same `error` channel as real
    failures, so treating the first one as fatal would fail healthy runs."""
    outcome = decide_outcome(
        exit_code=0,
        events=[
            {"type": "error", "message": "Reconnecting... 1/5"},
            {"type": "turn.completed"},
        ],
    )

    assert outcome.status == "success"
