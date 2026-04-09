"""Image preprocessing: PNG/JPG → binary bitmap."""

from pathlib import Path

import cv2
import numpy as np
from numpy.typing import NDArray

from signature2svg.config import PipelineConfig


def _remove_dust(binary: NDArray[np.uint8], min_area_ratio: float = 0.005) -> NDArray[np.uint8]:
    """Remove small connected components (dust, speckles) from binary image.

    Keeps only components whose area is at least min_area_ratio of the
    largest component. The largest component is assumed to be the signature.
    """
    # Invert: connectedComponents expects white foreground
    inverted = cv2.bitwise_not(binary)
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(inverted)

    if num_labels <= 1:
        return binary

    # Component 0 is background, find the largest foreground component
    areas = stats[1:, cv2.CC_STAT_AREA]
    max_area = areas.max()
    min_area = int(max_area * min_area_ratio)

    # Zero out small components
    for label_id in range(1, num_labels):
        if stats[label_id, cv2.CC_STAT_AREA] < min_area:
            binary[labels == label_id] = 255  # set to white (background)

    return binary


def detect_stroke_width(binary: NDArray[np.uint8]) -> float:
    """Detect the typical stroke width in a binary image using distance transform.

    Args:
        binary: 2D array, 0 = ink, 255 = background.

    Returns:
        Estimated stroke width in pixels. Returns 2.0 as fallback if no ink found.
    """
    # Ink as foreground (white) for distance transform
    ink_mask = (binary == 0).astype(np.uint8) * 255

    if np.sum(ink_mask) == 0:
        return 2.0

    # Distance transform: each ink pixel gets the distance to nearest background pixel
    dist = cv2.distanceTransform(ink_mask, cv2.DIST_L2, 5)

    # Skeletonize: thin the ink to 1px lines, then read distances at skeleton points
    # The distance at skeleton points = half the local stroke width
    skeleton = cv2.ximgproc.thinning(ink_mask) if hasattr(cv2, "ximgproc") else None

    if skeleton is not None:
        skeleton_distances = dist[skeleton > 0]
        if len(skeleton_distances) > 0:
            return float(np.median(skeleton_distances)) * 2
    else:
        # Fallback without skeletonization: use median of all distance values on ink
        ink_distances = dist[dist > 0]
        if len(ink_distances) > 0:
            return float(np.median(ink_distances)) * 2

    return 2.0


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

    # Upscale small images for better vectorization quality
    min_width = 2000
    h, w = gray.shape[:2]
    if w < min_width:
        scale = min_width / w
        gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

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

    # Remove small connected components (dust, speckles far from signature)
    # Keep only components larger than min_component_ratio of the largest component
    binary = _remove_dust(binary, min_area_ratio=0.005)

    # Auto-crop to ink bounding box (remove white border)
    ink_pixels = np.where(binary == 0)
    if len(ink_pixels[0]) > 0:
        y_min, y_max = ink_pixels[0].min(), ink_pixels[0].max()
        x_min, x_max = ink_pixels[1].min(), ink_pixels[1].max()
        binary = binary[y_min : y_max + 1, x_min : x_max + 1]

    return binary  # type: ignore[return-value]
