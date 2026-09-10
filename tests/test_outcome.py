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
