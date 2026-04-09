"""Tests for PipelineConfig validation and custom exceptions."""

import pytest
from pydantic import ValidationError

from signature2svg.config import PipelineConfig
from signature2svg.exceptions import PotraceError


def test_default_config() -> None:
    config = PipelineConfig()
    assert config.turdsize == 0  # 0 = auto-detect from stroke width
    assert config.alphamax == 1.0
    assert config.opttolerance == 0.2
    assert config.blur == 3
    assert config.morph == 2
    assert config.debug is False


def test_custom_config() -> None:
    config = PipelineConfig(turdsize=5, alphamax=0.8, blur=0, debug=True)
    assert config.turdsize == 5
    assert config.alphamax == 0.8
    assert config.blur == 0
    assert config.debug is True


def test_alphamax_out_of_range() -> None:
    with pytest.raises(ValidationError):
        PipelineConfig(alphamax=2.0)


def test_negative_turdsize() -> None:
    with pytest.raises(ValidationError):
        PipelineConfig(turdsize=-1)


def test_negative_blur() -> None:
    with pytest.raises(ValidationError):
        PipelineConfig(blur=-1)


def test_potrace_error_message() -> None:
    err = PotraceError("some stderr")
    assert "Potrace failed" in str(err)
    assert "some stderr" in str(err)
    assert isinstance(err, RuntimeError)
