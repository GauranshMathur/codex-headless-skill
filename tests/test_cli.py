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
