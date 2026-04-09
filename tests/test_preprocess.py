"""Tests for image preprocessing."""

from pathlib import Path

import cv2
import numpy as np
import pytest

from signature2svg.config import PipelineConfig
from signature2svg.preprocess import preprocess


def _create_test_png(path: Path, width: int = 200, height: int = 100) -> None:
    """Create a white image with black strokes for testing."""
    img = np.ones((height, width, 3), dtype=np.uint8) * 255
    cv2.line(img, (20, 50), (180, 50), (0, 0, 0), 3)
    cv2.line(img, (50, 20), (150, 80), (0, 0, 0), 2)
    cv2.imwrite(str(path), img)


def test_output_is_binary(tmp_path: Path) -> None:
    png = tmp_path / "sig.png"
    _create_test_png(png)
    result = preprocess(png, PipelineConfig())
    unique_values = set(np.unique(result))
    assert unique_values <= {0, 255}


def test_output_is_2d(tmp_path: Path) -> None:
    png = tmp_path / "sig.png"
    _create_test_png(png)
    result = preprocess(png, PipelineConfig())
    assert result.ndim == 2


def test_output_dtype_uint8(tmp_path: Path) -> None:
    png = tmp_path / "sig.png"
    _create_test_png(png)
    result = preprocess(png, PipelineConfig())
    assert result.dtype == np.uint8


def test_blur_off(tmp_path: Path) -> None:
    png = tmp_path / "sig.png"
    _create_test_png(png)
    config = PipelineConfig(blur=0)
    result = preprocess(png, config)
    assert result.ndim == 2


def test_morph_off(tmp_path: Path) -> None:
    png = tmp_path / "sig.png"
    _create_test_png(png)
    config = PipelineConfig(morph=0)
    result = preprocess(png, config)
    assert result.ndim == 2


def test_contains_black_pixels(tmp_path: Path) -> None:
    png = tmp_path / "sig.png"
    _create_test_png(png)
    result = preprocess(png, PipelineConfig())
    assert 0 in result


def test_file_not_found() -> None:
    with pytest.raises(FileNotFoundError):
        preprocess(Path("/nonexistent.png"), PipelineConfig())


def test_cv2_imread_none_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Cover the cv2.imread returns None branch."""
    import cv2 as _cv2

    png = tmp_path / "sig.png"
    _create_test_png(png)

    monkeypatch.setattr(_cv2, "imread", lambda *_args, **_kwargs: None)
    with pytest.raises(FileNotFoundError, match="cv2 could not read image"):
        preprocess(png, PipelineConfig())


def test_handles_uneven_lighting(tmp_path: Path) -> None:
    """Simulate a photo with shadow gradient — should not produce large black areas."""
    img = np.ones((200, 400, 3), dtype=np.uint8) * 255
    cv2.line(img, (50, 80), (350, 80), (30, 30, 30), 2)
    cv2.line(img, (100, 40), (300, 120), (30, 30, 30), 2)
    for y in range(100, 200):
        darkness = int((y - 100) * 2.5)
        img[y, :] = np.maximum(img[y, :].astype(int) - darkness, 0).astype(np.uint8)
    cv2.imwrite(str(tmp_path / "shadow.png"), img)

    result = preprocess(tmp_path / "shadow.png", PipelineConfig())
    black_ratio = np.sum(result == 0) / result.size
    assert black_ratio < 0.15, f"Too many black pixels ({black_ratio:.1%}) — shadow not removed"


def test_noise_removal(tmp_path: Path) -> None:
    """Small isolated noise pixels should be removed by morph open."""
    img = np.ones((100, 200, 3), dtype=np.uint8) * 255
    cv2.line(img, (20, 50), (180, 50), (0, 0, 0), 4)
    rng = np.random.default_rng(42)
    noise_coords = rng.integers(0, [100, 200], size=(50, 2))
    for y, x in noise_coords:
        img[y, x] = [40, 40, 40]
    cv2.imwrite(str(tmp_path / "noisy.png"), img)

    result = preprocess(tmp_path / "noisy.png", PipelineConfig())
    num_labels, _ = cv2.connectedComponents(cv2.bitwise_not(result))
    assert num_labels <= 5, f"Too many components ({num_labels}) — noise not removed"


def test_dust_removal(tmp_path: Path) -> None:
    """Isolated small dots far from the signature should be removed."""
    img = np.ones((300, 600, 3), dtype=np.uint8) * 255
    # Draw signature strokes (large connected component)
    cv2.line(img, (50, 150), (550, 150), (0, 0, 0), 3)
    cv2.line(img, (100, 100), (400, 200), (0, 0, 0), 3)
    # Add dust specks in corners (small isolated components)
    cv2.circle(img, (10, 10), 2, (0, 0, 0), -1)
    cv2.circle(img, (590, 10), 2, (0, 0, 0), -1)
    cv2.circle(img, (10, 290), 2, (0, 0, 0), -1)
    cv2.circle(img, (590, 290), 2, (0, 0, 0), -1)
    cv2.imwrite(str(tmp_path / "dusty.png"), img)

    result = preprocess(tmp_path / "dusty.png", PipelineConfig())

    # Dust should be removed — only signature strokes remain
    inverted = cv2.bitwise_not(result)
    num_labels, _, stats, _ = cv2.connectedComponentsWithStats(inverted)
    # Only signature components should remain (background + 1-2 stroke components)
    assert num_labels <= 4, f"Too many components ({num_labels}) — dust not removed"

    # The image should be cropped tightly to the signature, not include dust corners
    # (upscaling may increase dimensions, so check ratio instead of absolute size)
    aspect = result.shape[1] / result.shape[0]
    assert aspect > 2.0, f"Aspect ratio {aspect:.1f} — dust expanded bounding box vertically"
