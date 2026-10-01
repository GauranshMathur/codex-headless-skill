"""The command line the skill and the subagent actually call."""

import json
import textwrap

import pytest

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


@pytest.mark.parametrize("explicit_run_dir", [False, True])
def test_dry_run_shows_the_command_without_running_codex(
    capsys, tmp_path, monkeypatch, explicit_run_dir
):
    monkeypatch.setenv("HOME", str(tmp_path))
    args = ["--dry-run", "--effort", "max"]
    if explicit_run_dir:
        args += ["--run-dir", str(tmp_path / "nested" / "run")]
    code = main(
        args,
        catalog_loader=lambda: CATALOG,
        prompt_reader=lambda: "implement the thing",
    )

    out = capsys.readouterr().out
    assert code == 0
    assert "-m most-capable" in out
    assert "model_reasoning_effort=max" in out
    assert "-s workspace-write" in out
    assert "-o " in out
    assert "last-message.md" in out
    assert list(tmp_path.iterdir()) == []


def test_a_completed_run_writes_its_last_message(tmp_path, fake_codex):
    binary = fake_codex([{"type": "turn.completed", "usage": {"output_tokens": 5}}])
    run_dir = tmp_path / "nested" / "run"

    code = main(
        ["--codex-bin", binary, "--run-dir", str(run_dir)],
        catalog_loader=lambda: CATALOG,
        prompt_reader=lambda: "do it",
    )

    assert code == 0
    assert (run_dir / "last-message.md").read_text() == "Final message from fake codex\n"


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


def _manifest(run_dir):
    return json.loads((run_dir / "manifest.json").read_text())


def test_a_run_keeps_its_prompt_and_a_finished_manifest(tmp_path, fake_codex):
    binary = fake_codex(
        [
            {"type": "thread.started", "thread_id": "th_m"},
            {"type": "turn.completed", "usage": {"output_tokens": 5}},
        ]
    )
    run_dir = tmp_path / "run"

    code = main(
        ["--codex-bin", binary, "--run-dir", str(run_dir), "--cwd", str(tmp_path)],
        catalog_loader=lambda: CATALOG,
        prompt_reader=lambda: "add the retry",
    )

    manifest = _manifest(run_dir)
    assert code == 0
    assert (run_dir / "prompt.md").read_text() == "add the retry"
    assert manifest["outcome"] == "success"
    assert manifest["exit_code"] == 0
    assert manifest["thread_id"] == "th_m"
    assert manifest["model"] == "most-capable"
    # ADR 0001: where the model came from has to be visible after the fact.
    assert manifest["model_source"] == "catalog"
    assert manifest["effort"] == "high"
    assert manifest["cwd"] == str(tmp_path.resolve())
    assert manifest["finished_at"] is not None
    # prompt.md holds the prompt; the manifest should not hold a second copy.
    assert "add the retry" not in manifest["argv"]
    assert not (run_dir / "manifest.json.tmp").exists()


def test_the_manifest_records_an_explicit_model_and_a_stepped_down_effort(
    tmp_path, fake_codex
):
    binary = fake_codex([{"type": "turn.completed", "usage": {"output_tokens": 5}}])
    run_dir = tmp_path / "run"

    main(
        ["--codex-bin", binary, "--run-dir", str(run_dir)]
        + ["--model", "cheaper", "--effort", "ultra"],
        catalog_loader=lambda: CATALOG,
        prompt_reader=lambda: "do it",
    )

    manifest = _manifest(run_dir)
    assert manifest["model"] == "cheaper"
    assert manifest["model_source"] == "flag"
    assert manifest["effort"] == "xhigh"
    assert manifest["effort_requested"] == "ultra"
    assert "ultra" in manifest["effort_warning"]


def test_the_manifest_exists_before_codex_starts(tmp_path):
    """A run killed from outside never gets its final write, so the first one
    has to land before codex is spawned."""
    binary = tmp_path / "peeking_codex"
    binary.write_text(
        textwrap.dedent(
            """\
            #!/usr/bin/env python3
            import json, shutil, sys
            from pathlib import Path
            run_dir = Path(sys.argv[sys.argv.index("-o") + 1]).parent
            shutil.copy(run_dir / "manifest.json", run_dir / "seen-by-codex.json")
            print(json.dumps({"type": "turn.completed"}), flush=True)
            """
        )
    )
    binary.chmod(0o755)
    run_dir = tmp_path / "run"

    main(
        ["--codex-bin", str(binary), "--run-dir", str(run_dir)],
        catalog_loader=lambda: CATALOG,
        prompt_reader=lambda: "do it",
    )

    seen = json.loads((run_dir / "seen-by-codex.json").read_text())
    assert seen["outcome"] == "running"
    assert seen["finished_at"] is None
    assert _manifest(run_dir)["outcome"] == "success"


def test_a_timed_out_run_is_recorded_as_one(tmp_path, fake_codex):
    binary = fake_codex([{"type": "thread.started", "thread_id": "th_t"}], then_sleep=30)
    run_dir = tmp_path / "run"

    code = main(
        ["--codex-bin", binary, "--run-dir", str(run_dir), "--idle-timeout", "1"],
        catalog_loader=lambda: CATALOG,
        prompt_reader=lambda: "do it",
    )

    manifest = _manifest(run_dir)
    assert code == 13
    assert manifest["outcome"] == "timeout"
    assert manifest["exit_code"] == 13
    # The thread id is what makes a stopped run resumable.
    assert manifest["thread_id"] == "th_t"


def test_a_wrapper_failure_is_recorded_before_it_propagates(tmp_path):
    run_dir = tmp_path / "run"

    with pytest.raises(FileNotFoundError):
        main(
            ["--codex-bin", str(tmp_path / "no-such-codex"), "--run-dir", str(run_dir)],
            catalog_loader=lambda: CATALOG,
            prompt_reader=lambda: "do it",
        )

    manifest = _manifest(run_dir)
    assert manifest["outcome"] == "wrapper_error"
    assert "FileNotFoundError" in manifest["detail"]
