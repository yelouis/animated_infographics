"""Basic package import tests."""

import animated_infographics
import animated_infographics.config


def test_import_and_version() -> None:
    assert animated_infographics.__version__ == "0.1.0"
