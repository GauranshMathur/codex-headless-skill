"""The command line the skill and the subagent actually call."""

from codex_run import main

CATALOG = {
    "models": [
        {
            "slug": "most-capable",
            "priority": 1,
            "visibility": "list",
            "default_reasoning_level": "low",
            "supported_reasoning_levels": [
                {"effort": e} for e in ("low", "medium", "high", "xhigh", "max", "ultra")
            ],
        },
        {
            "slug": "cheaper",
            "priority": 12,
            "visibility": "list",
            "default_reasoning_level": "medium",
            "supported_reasoning_levels": [
                {"effort": e} for e in ("low", "medium", "high", "xhigh")
            ],
        },
        {"slug": "internal-only", "priority": 2, "visibility": "hide"},
    ]
}


def test_list_models_ranks_them_and_marks_the_default(capsys):
    code = main(["--list-models"], catalog_loader=lambda: CATALOG)

    out = capsys.readouterr().out
    assert code == 0
    assert "most-capable" in out
    assert "cheaper" in out
    # Hidden models are internal; offering them as choices would mislead.
    assert "internal-only" not in out
    # The user has to be able to see which one they get by default.
    assert "default" in out.lower()


def test_dry_run_shows_the_command_without_running_codex(capsys):
    code = main(
        ["--dry-run", "--effort", "max"],
        catalog_loader=lambda: CATALOG,
        prompt_reader=lambda: "implement the thing",
    )

    out = capsys.readouterr().out
    assert code == 0
    assert "-m most-capable" in out
    assert "model_reasoning_effort=max" in out
    assert "-s workspace-write" in out


def test_a_completed_run_exits_zero_and_leaves_its_artifacts(tmp_path, fake_codex):
    binary = fake_codex(
        [
            {"type": "thread.started", "thread_id": "th_cli"},
            {"type": "turn.completed", "usage": {"output_tokens": 5}},
        ]
    )
    run_dir = tmp_path / "run"

    code = main(
        ["--codex-bin", binary, "--run-dir", str(run_dir)],
        catalog_loader=lambda: CATALOG,
        prompt_reader=lambda: "do it",
    )

    assert code == 0
    assert (run_dir / "events.jsonl").exists()


def test_a_run_that_did_no_work_exits_non_zero(tmp_path, fake_codex, capsys):
    binary = fake_codex([{"type": "thread.started", "thread_id": "th_x"}], exit_code=0)

    code = main(
        ["--codex-bin", binary, "--run-dir", str(tmp_path / "run")],
        catalog_loader=lambda: CATALOG,
        prompt_reader=lambda: "do it",
    )

    assert code == 10
    # The thread id has to reach the caller, or an interrupted run cannot be resumed.
    assert "th_x" in capsys.readouterr().out
