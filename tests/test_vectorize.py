"""Tests for vectorization (Potrace wrapper)."""

import numpy as np
import pytest

from signature2svg.config import PipelineConfig
from signature2svg.vectorize import vectorize

pytestmark = pytest.mark.requires_potrace


def _make_binary_image(width: int = 200, height: int = 100) -> np.ndarray:
    """Create a binary image with a black rectangle on white background."""
    img = np.ones((height, width), dtype=np.uint8) * 255
    img[30:70, 50:150] = 0
    return img


def test_returns_svg_string() -> None:
    binary = _make_binary_image()
    result = vectorize(binary, PipelineConfig())
    assert isinstance(result, str)
    assert "<svg" in result
    assert "</svg>" in result


def test_svg_contains_path() -> None:
    binary = _make_binary_image()
    result = vectorize(binary, PipelineConfig())
    assert "<path" in result


def test_custom_turdsize() -> None:
    binary = _make_binary_image()
    result = vectorize(binary, PipelineConfig(turdsize=10))
    assert "<svg" in result


def test_all_white_produces_svg() -> None:
    binary = np.ones((100, 200), dtype=np.uint8) * 255
    result = vectorize(binary, PipelineConfig())
    assert "<svg" in result
