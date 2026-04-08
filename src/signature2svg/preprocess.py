"""Image preprocessing: PNG/JPG → binary bitmap."""

from pathlib import Path

import cv2
import numpy as np
from numpy.typing import NDArray

from signature2svg.config import PipelineConfig


def preprocess(png_path: Path, config: PipelineConfig) -> NDArray[np.uint8]:
    """Convert a signature photo to a binary image (black ink on white).

    Pipeline: grayscale → blur → CLAHE → adaptive threshold → morph open → morph close → crop.

    Args:
        png_path: Path to input image file (PNG, JPG, etc.).
        config: Pipeline configuration with blur/morph settings.

    Returns:
        2D numpy array, dtype uint8, values 0 (ink) and 255 (background).

    Raises:
        FileNotFoundError: If png_path does not exist.
    """
    if not png_path.exists():
        raise FileNotFoundError(f"Input file not found: {png_path}")

    img = cv2.imread(str(png_path))
    if img is None:
        raise FileNotFoundError(f"cv2 could not read image: {png_path}")
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Median blur to reduce photo noise
    if config.blur > 0:
        blur_kernel = config.blur if config.blur % 2 == 1 else config.blur + 1
        gray = cv2.medianBlur(gray, blur_kernel)

    # CLAHE: normalize local brightness to handle shadows and uneven lighting
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)

    # Adaptive thresholding: per-region threshold handles remaining gradients
    binary = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 51, 10
    )

    # Morphological opening: remove isolated noise pixels (erode then dilate)
    open_kernel: NDArray[np.uint8] = np.ones((2, 2), np.uint8)
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, open_kernel)

    # Morphological closing: bridge small gaps in ink strokes
    if config.morph > 0:
        close_kernel: NDArray[np.uint8] = np.ones((config.morph, config.morph), np.uint8)
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, close_kernel)

    # Auto-crop to ink bounding box (remove white border)
    ink_pixels = np.where(binary == 0)
    if len(ink_pixels[0]) > 0:
        y_min, y_max = ink_pixels[0].min(), ink_pixels[0].max()
        x_min, x_max = ink_pixels[1].min(), ink_pixels[1].max()
        binary = binary[y_min : y_max + 1, x_min : x_max + 1]

    return binary  # type: ignore[return-value]
