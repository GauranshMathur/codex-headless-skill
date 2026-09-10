"""Model resolution — picking which model codex runs on.

The trap this guards: the user's ~/.codex/config.toml can pin a model slug that
no longer exists (e.g. "gpt-5-codex"). Codex does not reject it, it silently
degrades to generic base instructions. So the wrapper always resolves a model
itself and passes -m explicitly.
"""

from codex_run import resolve_model


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
