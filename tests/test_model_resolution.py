"""Model resolution — picking which model codex runs on.

The trap this guards: the user's ~/.codex/config.toml can pin a model slug that
no longer exists (e.g. "gpt-5-codex"). Codex does not reject it, it silently
degrades to generic base instructions. So the wrapper always resolves a model
itself and passes -m explicitly.
"""

import pytest

from codex_run import UnknownModel, resolve_model


def test_picks_the_highest_priority_listed_model():
    # priority 1 is most capable; the catalog is deliberately out of order so
    # that returning the first entry would not pass.
    catalog = {
        "models": [
            {"slug": "middling", "priority": 7, "visibility": "list"},
            {"slug": "most-capable", "priority": 1, "visibility": "list"},
            {"slug": "weakest", "priority": 29, "visibility": "list"},
        ]
    }

    assert resolve_model(catalog).slug == "most-capable"


def test_explicit_slug_overrides_the_priority_pick():
    catalog = {
        "models": [
            {"slug": "most-capable", "priority": 1, "visibility": "list"},
            {"slug": "cheaper", "priority": 12, "visibility": "list"},
        ]
    }

    choice = resolve_model(catalog, explicit="cheaper")

    assert choice.slug == "cheaper"
    assert choice.source == "flag"


def test_unknown_explicit_slug_is_rejected_and_names_what_is_available():
    """The gpt-5-codex case: codex accepts a dead slug and silently degrades.

    Failing loudly here is the whole point — and the error has to say what the
    user can pick instead, or they are left guessing.
    """
    catalog = {"models": [{"slug": "real-model", "priority": 1, "visibility": "list"}]}

    with pytest.raises(UnknownModel) as excinfo:
        resolve_model(catalog, explicit="gpt-5-codex")

    message = str(excinfo.value)
    assert "gpt-5-codex" in message
    assert "real-model" in message


def test_env_var_is_used_when_no_slug_was_passed():
    catalog = {
        "models": [
            {"slug": "most-capable", "priority": 1, "visibility": "list"},
            {"slug": "cheaper", "priority": 12, "visibility": "list"},
        ]
    }

    choice = resolve_model(catalog, env={"CODEX_HEADLESS_MODEL": "cheaper"})

    assert choice.slug == "cheaper"
    assert choice.source == "env"


def test_explicit_slug_beats_the_env_var():
    catalog = {
        "models": [
            {"slug": "most-capable", "priority": 1, "visibility": "list"},
            {"slug": "cheaper", "priority": 12, "visibility": "list"},
        ]
    }

    choice = resolve_model(
        catalog, explicit="most-capable", env={"CODEX_HEADLESS_MODEL": "cheaper"}
    )

    assert choice.slug == "most-capable"
    assert choice.source == "flag"
