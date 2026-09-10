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


def config_overrides(argv):
    """Every value passed via -c, in order."""
    return [argv[i + 1] for i, arg in enumerate(argv) if arg == "-c"]


def test_disables_each_configured_mcp_server_by_name():
    """`-c mcp_servers={}` looks right and does nothing: config tables
    deep-merge, so an empty table merges no change and every server stays on.
    Disabling them one by one is what actually works."""
    argv = build_argv(
        model="m", effort="high", prompt="p", mcp_servers=["serena", "context7"]
    )

    overrides = config_overrides(argv)
    assert "mcp_servers.serena.enabled=false" in overrides
    assert "mcp_servers.context7.enabled=false" in overrides
    assert "mcp_servers={}" not in overrides


def test_suppresses_the_notify_hook():
    """A configured `notify` command runs on every turn end — on this machine it
    launches a GUI helper. Arrays replace rather than merge, so [] clears it."""
    argv = build_argv(model="m", effort="high", prompt="p")

    assert "notify=[]" in config_overrides(argv)


def test_the_prompt_is_the_final_argument():
    argv = build_argv(model="m", effort="high", prompt="the brief")

    assert argv[-1] == "the brief"
