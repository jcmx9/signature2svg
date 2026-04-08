"""Vectorization: binary bitmap → SVG via Potrace."""

import subprocess
import tempfile
from pathlib import Path

import cv2
import numpy as np
from numpy.typing import NDArray

from signature2svg.config import PipelineConfig
from signature2svg.exceptions import PotraceError


def vectorize(binary: NDArray[np.uint8], config: PipelineConfig) -> str:
    """Convert a binary image to SVG using Potrace.

    Args:
        binary: 2D numpy array, dtype uint8, values 0 (ink) and 255 (background).
        config: Pipeline configuration with Potrace settings.

    Returns:
        Raw SVG string from Potrace.

    Raises:
        PotraceError: If Potrace subprocess fails.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        pbm_path = Path(tmp_dir) / "input.pbm"

        # Potrace expects PBM: 1 = black, 0 = white. OpenCV binary: 0 = black, 255 = white.
        # Invert so ink pixels become 1 (foreground for Potrace).
        inverted = cv2.bitwise_not(binary)
        cv2.imwrite(str(pbm_path), inverted)

        cmd = [
            "potrace",
            "--svg",
            "--output",
            "-",
            "--turdsize",
            str(config.turdsize),
            "--alphamax",
            str(config.alphamax),
            "--opttolerance",
            str(config.opttolerance),
            str(pbm_path),
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError as e:
            raise PotraceError(e.stderr) from e

    return result.stdout
