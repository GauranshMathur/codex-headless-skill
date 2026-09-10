"""Assembling the `codex exec` command line.

Two of these are behaviours we verified against the installed CLI rather than
inferred: `-c mcp_servers={}` is silently a no-op (config tables deep-merge, so
an empty table merges nothing), and arrays replace, which is what makes
`-c notify=[]` able to suppress the per-turn notify hook.
"""

from codex_run import build_argv


def test_always_passes_the_model_explicitly():
    """Omitting -m lets ~/.codex/config.toml decide, which is the whole trap."""
    argv = build_argv(model="gpt-6-astra", effort="high", prompt="do the thing")

    assert "-m" in argv
    assert argv[argv.index("-m") + 1] == "gpt-6-astra"
