"""Shared test fixtures."""

import shutil

import pytest


requires_potrace = pytest.mark.requires_potrace


def pytest_configure(config: pytest.Config) -> None:
    """Skip tests marked requires_potrace if potrace is not installed."""
    potrace_available = shutil.which("potrace") is not None
    if not potrace_available:
        setattr(config, "_potrace_skip", True)


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Auto-skip requires_potrace tests when potrace is missing."""
    if getattr(config, "_potrace_skip", False):
        skip = pytest.mark.skip(reason="potrace not installed")
        for item in items:
            if "requires_potrace" in item.keywords:
                item.add_marker(skip)
