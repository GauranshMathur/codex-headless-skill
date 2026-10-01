"""Reading the model catalog from the codex binary the caller named.

When codex is not on PATH, `--codex-bin` and `CODEX_BIN` are the documented
fix. The catalog has to come from that same binary, or the run fails before
codex is ever started.
"""

import json
import sys
import textwrap

import pytest

from codex_run import CatalogUnavailable, load_catalog, main

CATALOG = {
    "models": [
        {
            "slug": "only-model",
            "priority": 1,
            "visibility": "list",
            "supported_reasoning_levels": [{"effort": "high"}],
        }
    ]
}


@pytest.fixture
def off_path_codex(tmp_path, monkeypatch):
    """A stand-in codex that is reachable only by its path.

    PATH is emptied so a real codex installed on the machine cannot answer in
    its place. The shebang names this interpreter directly for the same reason.
    """
    binary = tmp_path / "bin" / "codex"
    binary.parent.mkdir()
    binary.write_text(
        textwrap.dedent(
            f"""\
            #!{sys.executable}
            import json, sys
            if sys.argv[1:3] == ["debug", "models"]:
                print({json.dumps(CATALOG)!r})
                sys.exit(0)
            print(json.dumps({{"type": "turn.completed"}}), flush=True)
            """
        )
    )
    binary.chmod(0o755)
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))
    return str(binary)


def test_the_catalog_is_read_from_the_named_binary(off_path_codex):
    assert load_catalog(off_path_codex) == CATALOG


def test_a_run_with_codex_bin_works_when_codex_is_not_on_path(off_path_codex, tmp_path):
    run_dir = tmp_path / "run"

    code = main(
        ["--codex-bin", off_path_codex, "--run-dir", str(run_dir)],
        prompt_reader=lambda: "do it",
    )

    assert code == 0
    assert json.loads((run_dir / "manifest.json").read_text())["model"] == "only-model"


def test_an_unreadable_catalog_names_the_binary_and_the_fix(tmp_path):
    missing = str(tmp_path / "no-such-codex")

    with pytest.raises(CatalogUnavailable) as raised:
        load_catalog(missing)

    assert missing in str(raised.value)
    assert "--codex-bin" in str(raised.value)
