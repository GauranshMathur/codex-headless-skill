"""Stopping a run that will not stop itself.

codex has been observed hanging without emitting a terminal event
(openai/codex#41984). There is no `timeout` binary on macOS, and killing only
the direct child would orphan codex's own children — which would keep editing
files after the caller believes the run ended. So the wrapper owns this.
"""

import os

import pytest

from codex_run import decide_outcome, run_codex


def test_wall_clock_timeout_stops_a_run_that_overruns(tmp_path, fake_codex):
    binary = fake_codex([{"type": "thread.started", "thread_id": "th_1"}], then_sleep=30)

    result = run_codex([binary], run_dir=tmp_path / "run", timeout=1)

    assert result.timed_out == "wall_clock"
    # Partial progress still has to survive, or an interrupted run is unresumable.
    assert result.thread_id == "th_1"


def test_idle_timeout_stops_a_run_that_goes_quiet(tmp_path, fake_codex):
    binary = fake_codex([{"type": "thread.started", "thread_id": "th_2"}], then_sleep=30)

    result = run_codex([binary], run_dir=tmp_path / "run", idle_timeout=1)

    assert result.timed_out == "idle"


def test_nothing_is_left_running_after_a_timeout(tmp_path, fake_codex):
    binary = fake_codex([{"type": "thread.started", "thread_id": "th_3"}], then_sleep=30)

    result = run_codex([binary], run_dir=tmp_path / "run", timeout=1)

    with pytest.raises(ProcessLookupError):
        os.killpg(result.pgid, 0)


def test_a_timed_out_run_is_classified_as_such(tmp_path, fake_codex):
    binary = fake_codex([{"type": "thread.started", "thread_id": "th_4"}], then_sleep=30)

    result = run_codex([binary], run_dir=tmp_path / "run", timeout=1)
    outcome = decide_outcome(result.exit_code, result.events, timed_out=result.timed_out)

    assert outcome.status == "timeout"
    assert outcome.exit_code == 12
