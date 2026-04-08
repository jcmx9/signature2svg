# Signature Vectorization Pipeline — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a CLI tool that converts a signature photo (PNG) into a clean, color-parametrizable SVG using Potrace.

**Architecture:** Sequential pipeline of 4 pure functions (preprocess → vectorize → clean → parametrize), orchestrated by a typer CLI. Config validated via Pydantic. Each module has no knowledge of the others.

**Tech Stack:** Python 3.14+, OpenCV, numpy, Pillow, lxml, svgpathtools, Potrace (system binary), typer, Pydantic, uv

---

## File Map

| File | Responsibility |
|------|----------------|
| `pyproject.toml` | Package metadata, dependencies, entry point |
| `src/convert_png2svg/__init__.py` | `__version__` |
| `src/convert_png2svg/__main__.py` | `python -m convert_png2svg` entry |
| `src/convert_png2svg/config.py` | `PipelineConfig` Pydantic model |
| `src/convert_png2svg/exceptions.py` | `NoPathsDetectedError`, `DegenerateBoundingBoxError`, `PotraceError` |
| `src/convert_png2svg/preprocess.py` | `preprocess(path, config) → np.ndarray` |
| `src/convert_png2svg/vectorize.py` | `vectorize(binary, config) → str` |
| `src/convert_png2svg/clean.py` | `clean_svg(svg_string) → str` |
| `src/convert_png2svg/parametrize.py` | `parametrize_svg(svg_string) → str` |
| `src/convert_png2svg/cli.py` | typer app, `main()` pipeline orchestration |
| `tests/conftest.py` | Shared fixtures |
| `tests/test_preprocess.py` | Preprocessing tests |
| `tests/test_vectorize.py` | Vectorization tests (requires potrace) |
| `tests/test_clean.py` | SVG cleaning tests |
| `tests/test_parametrize.py` | SVG parametrization tests |
| `tests/test_cli.py` | End-to-end CLI tests (requires potrace) |

---

### Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `src/convert_png2svg/__init__.py`
- Create: `src/convert_png2svg/__main__.py`

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[project]
name = "convert-png2svg"
version = "0.1.0"
description = "Convert signature photos to clean, color-parametrizable SVGs"
requires-python = ">=3.12"
dependencies = [
    "opencv-python>=4.10",
    "numpy>=2.0",
    "Pillow>=11.0",
    "lxml>=5.0",
    "svgpathtools>=1.6",
    "typer>=0.15",
    "pydantic>=2.0",
]

[project.scripts]
convert-png2svg = "convert_png2svg.cli:app"

[dependency-groups]
dev = [
    "pytest>=8.0",
    "pytest-cov>=6.0",
    "pytest-xdist>=3.0",
    "ruff>=0.11",
    "mypy>=1.15",
    "lxml-stubs>=0.5",
]

[tool.ruff]
line-length = 100

[tool.mypy]
strict = true

[tool.pytest.ini_options]
markers = [
    "requires_potrace: test requires potrace binary installed",
]
```

- [ ] **Step 2: Create `src/convert_png2svg/__init__.py`**

```python
"""Convert signature photos to clean, color-parametrizable SVGs."""

__version__ = "0.1.0"
```

- [ ] **Step 3: Create `src/convert_png2svg/__main__.py`**

```python
"""Allow running as `python -m convert_png2svg`."""

from convert_png2svg.cli import app

app()
```

- [ ] **Step 4: Install the project**

Run: `cd /Users/rolandkreus/GitHub/convertPng2Svg && uv venv && source .venv/bin/activate && uv sync --all-extras`
Expected: Dependencies install successfully, package is importable.

- [ ] **Step 5: Verify import works**

Run: `python -c "import convert_png2svg; print(convert_png2svg.__version__)"`
Expected: `0.1.0`

- [ ] **Step 6: Commit**

```bash
git init
git add pyproject.toml src/convert_png2svg/__init__.py src/convert_png2svg/__main__.py uv.lock
git commit -m "chore: scaffold project with pyproject.toml and package structure"
```

---

### Task 2: Config & Exceptions

**Files:**
- Create: `src/convert_png2svg/config.py`
- Create: `src/convert_png2svg/exceptions.py`
- Create: `tests/conftest.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Create `src/convert_png2svg/exceptions.py`**

```python
"""Custom exceptions for the vectorization pipeline."""


class NoPathsDetectedError(ValueError):
    """No paths found after vectorization."""

    def __init__(self) -> None:
        super().__init__("No paths detected — check threshold settings")


class DegenerateBoundingBoxError(ValueError):
    """Bounding box is empty or degenerate."""

    def __init__(self) -> None:
        super().__init__("Degenerate bounding box — width or height is zero")


class PotraceError(RuntimeError):
    """Potrace subprocess failed."""

    def __init__(self, stderr: str) -> None:
        super().__init__(f"Potrace failed: {stderr}")
```

- [ ] **Step 2: Create `src/convert_png2svg/config.py`**

```python
"""Pipeline configuration with Pydantic validation."""

from pydantic import BaseModel, Field


class PipelineConfig(BaseModel):
    """Configuration for the signature vectorization pipeline."""

    turdsize: int = Field(default=2, ge=0, description="Suppress speckles smaller than N px")
    alphamax: float = Field(
        default=1.0, ge=0.0, le=1.3, description="Corner smoothing (0.0–1.3)"
    )
    opttolerance: float = Field(
        default=0.2, ge=0.0, description="Curve optimization tolerance"
    )
    blur: int = Field(default=3, ge=0, description="Median blur kernel size (0 = off)")
    morph: int = Field(default=2, ge=0, description="Morphological closing kernel size (0 = off)")
    debug: bool = Field(default=False, description="Write intermediate images to output dir")
```

- [ ] **Step 3: Write failing test for config validation**

Create `tests/conftest.py`:

```python
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
```

Create `tests/test_config.py`:

```python
"""Tests for PipelineConfig validation."""

import pytest
from pydantic import ValidationError

from convert_png2svg.config import PipelineConfig


def test_default_config() -> None:
    config = PipelineConfig()
    assert config.turdsize == 2
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
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_config.py -v`
Expected: All 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/convert_png2svg/config.py src/convert_png2svg/exceptions.py tests/conftest.py tests/test_config.py
git commit -m "feat: add PipelineConfig model and custom exceptions"
```

---

### Task 3: Preprocess Module

**Files:**
- Create: `src/convert_png2svg/preprocess.py`
- Create: `tests/test_preprocess.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_preprocess.py`:

```python
"""Tests for image preprocessing."""

from pathlib import Path

import cv2
import numpy as np

from convert_png2svg.config import PipelineConfig
from convert_png2svg.preprocess import preprocess


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


# Need the import for test_file_not_found
import pytest  # noqa: E402
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_preprocess.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'convert_png2svg.preprocess'`

- [ ] **Step 3: Implement `preprocess.py`**

Create `src/convert_png2svg/preprocess.py`:

```python
"""Image preprocessing: PNG → binary bitmap."""

from pathlib import Path

import cv2
import numpy as np
from numpy.typing import NDArray

from convert_png2svg.config import PipelineConfig


def preprocess(png_path: Path, config: PipelineConfig) -> NDArray[np.uint8]:
    """Convert a signature photo to a binary image (black ink on white).

    Args:
        png_path: Path to input PNG file.
        config: Pipeline configuration with blur/morph settings.

    Returns:
        2D numpy array, dtype uint8, values 0 (ink) and 255 (background).

    Raises:
        FileNotFoundError: If png_path does not exist.
    """
    if not png_path.exists():
        raise FileNotFoundError(f"Input file not found: {png_path}")

    img = cv2.imread(str(png_path))
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    if config.blur > 0:
        kernel = config.blur if config.blur % 2 == 1 else config.blur + 1
        gray = cv2.medianBlur(gray, kernel)

    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    if config.morph > 0:
        kernel = np.ones((config.morph, config.morph), np.uint8)
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

    return binary  # type: ignore[return-value]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_preprocess.py -v`
Expected: All 7 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/convert_png2svg/preprocess.py tests/test_preprocess.py
git commit -m "feat: add preprocess module (grayscale, threshold, morphology)"
```

---

### Task 4: Vectorize Module

**Files:**
- Create: `src/convert_png2svg/vectorize.py`
- Create: `tests/test_vectorize.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_vectorize.py`:

```python
"""Tests for vectorization (Potrace wrapper)."""

import numpy as np
import pytest

from convert_png2svg.config import PipelineConfig
from convert_png2svg.exceptions import PotraceError
from convert_png2svg.vectorize import vectorize

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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_vectorize.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'convert_png2svg.vectorize'`

- [ ] **Step 3: Implement `vectorize.py`**

Create `src/convert_png2svg/vectorize.py`:

```python
"""Vectorization: binary bitmap → SVG via Potrace."""

import subprocess
import tempfile
from pathlib import Path

import cv2
import numpy as np
from numpy.typing import NDArray

from convert_png2svg.config import PipelineConfig
from convert_png2svg.exceptions import PotraceError


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
            "--output", "-",
            "--turdsize", str(config.turdsize),
            "--alphamax", str(config.alphamax),
            "--opttolerance", str(config.opttolerance),
            str(pbm_path),
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError as e:
            raise PotraceError(e.stderr) from e

    return result.stdout
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_vectorize.py -v`
Expected: All 4 tests PASS (or skipped if potrace not installed).

- [ ] **Step 5: Commit**

```bash
git add src/convert_png2svg/vectorize.py tests/test_vectorize.py
git commit -m "feat: add vectorize module (Potrace subprocess wrapper)"
```

---

### Task 5: Clean SVG Module

**Files:**
- Create: `src/convert_png2svg/clean.py`
- Create: `tests/test_clean.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_clean.py`:

```python
"""Tests for SVG cleaning."""

import pytest
from lxml import etree

from convert_png2svg.clean import clean_svg
from convert_png2svg.exceptions import DegenerateBoundingBoxError, NoPathsDetectedError

SAMPLE_SVG = """<?xml version="1.0" standalone="no"?>
<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 20010904//EN"
 "http://www.w3.org/TR/2001/REC-SVG-20010904/DTD/svg10.dtd">
<svg version="1.0" xmlns="http://www.w3.org/2000/svg"
 width="200" height="100" viewBox="0 0 200 100">
<!-- Created by potrace 1.16 -->
<rect width="100%" height="100%" fill="white"/>
<g transform="translate(10,90) scale(0.1,-0.1)" fill="#000000">
<path d="M 100 200 L 300 200 L 300 400 L 100 400 Z"/>
</g>
</svg>"""

SVG_NO_PATHS = """<?xml version="1.0"?>
<svg xmlns="http://www.w3.org/2000/svg" width="200" height="100" viewBox="0 0 200 100">
<rect width="100%" height="100%" fill="white"/>
</svg>"""


def test_removes_background_rect() -> None:
    result = clean_svg(SAMPLE_SVG)
    root = etree.fromstring(result.encode())
    ns = {"svg": "http://www.w3.org/2000/svg"}
    rects = root.findall(".//svg:rect", ns)
    assert len(rects) == 0


def test_viewbox_starts_at_zero() -> None:
    result = clean_svg(SAMPLE_SVG)
    root = etree.fromstring(result.encode())
    viewbox = root.get("viewBox", "")
    parts = viewbox.split()
    assert parts[0] == "0"
    assert parts[1] == "0"


def test_strips_comments() -> None:
    result = clean_svg(SAMPLE_SVG)
    assert "potrace" not in result.lower()
    assert "<!--" not in result


def test_no_paths_raises() -> None:
    with pytest.raises(NoPathsDetectedError):
        clean_svg(SVG_NO_PATHS)


def test_width_height_match_viewbox() -> None:
    result = clean_svg(SAMPLE_SVG)
    root = etree.fromstring(result.encode())
    viewbox = root.get("viewBox", "")
    parts = viewbox.split()
    assert root.get("width") == parts[2]
    assert root.get("height") == parts[3]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_clean.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'convert_png2svg.clean'`

- [ ] **Step 3: Implement `clean.py`**

Create `src/convert_png2svg/clean.py`:

```python
"""SVG cleaning: remove backgrounds, compute tight viewBox, strip metadata."""

from lxml import etree
from svgpathtools import parse_path

from convert_png2svg.exceptions import DegenerateBoundingBoxError, NoPathsDetectedError

SVG_NS = "http://www.w3.org/2000/svg"
NSMAP = {"svg": SVG_NS}


def clean_svg(svg_string: str) -> str:
    """Clean a raw Potrace SVG: remove backgrounds, set tight viewBox, strip metadata.

    Args:
        svg_string: Raw SVG string from Potrace.

    Returns:
        Cleaned SVG string with tight viewBox starting at 0,0.

    Raises:
        NoPathsDetectedError: If no path elements are found.
        DegenerateBoundingBoxError: If bounding box has zero width or height.
    """
    parser = etree.XMLParser(remove_comments=True)
    root = etree.fromstring(svg_string.encode(), parser)

    # Remove background rects
    for rect in root.findall(".//{%s}rect" % SVG_NS):
        fill = rect.get("fill", "").lower()
        if fill in ("white", "#fff", "#ffffff"):
            parent = rect.getparent()
            if parent is not None:
                parent.remove(rect)

    # Remove rects without namespace too (Potrace sometimes omits ns)
    for rect in root.findall(".//rect"):
        fill = rect.get("fill", "").lower()
        if fill in ("white", "#fff", "#ffffff"):
            parent = rect.getparent()
            if parent is not None:
                parent.remove(rect)

    # Collect all path elements
    paths_els = root.findall(".//{%s}path" % SVG_NS) + root.findall(".//path")
    if not paths_els:
        raise NoPathsDetectedError()

    # Compute bounding box from path geometry
    min_x = float("inf")
    min_y = float("inf")
    max_x = float("-inf")
    max_y = float("-inf")

    for path_el in paths_els:
        d = path_el.get("d", "")
        if not d:
            continue
        try:
            path = parse_path(d)
            bbox = path.bbox()
            min_x = min(min_x, bbox[0])
            max_x = max(max_x, bbox[1])
            min_y = min(min_y, bbox[2])
            max_y = max(max_y, bbox[3])
        except Exception:
            continue

    width = max_x - min_x
    height = max_y - min_y

    if width <= 0 or height <= 0:
        raise DegenerateBoundingBoxError()

    # Translate all paths so bounding box starts at 0,0
    # We do this by wrapping content in a <g> with a translate transform
    # First, remove any existing transform on the root or top-level g
    svg_children = list(root)
    wrapper = etree.SubElement(root, "g")
    wrapper.set("transform", f"translate({-min_x},{-min_y})")
    for child in svg_children:
        root.remove(child)
        wrapper.append(child)

    # Set viewBox and dimensions
    root.set("viewBox", f"0 0 {width} {height}")
    root.set("width", str(width))
    root.set("height", str(height))

    # Remove x, y offsets on root
    for attr in ("x", "y"):
        if attr in root.attrib:
            del root.attrib[attr]

    # Strip DOCTYPE and XML declaration, output clean SVG
    result = etree.tostring(root, pretty_print=True, xml_declaration=False).decode()
    return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_clean.py -v`
Expected: All 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/convert_png2svg/clean.py tests/test_clean.py
git commit -m "feat: add clean_svg module (tight viewBox, strip backgrounds/metadata)"
```

---

### Task 6: Parametrize SVG Module

**Files:**
- Create: `src/convert_png2svg/parametrize.py`
- Create: `tests/test_parametrize.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_parametrize.py`:

```python
"""Tests for SVG parametrization."""

from lxml import etree

from convert_png2svg.parametrize import parametrize_svg

SVG_NS = "http://www.w3.org/2000/svg"

SAMPLE_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 50" width="100" height="50">
<path d="M 0 0 L 100 0 L 100 50 Z" fill="#000000"/>
<path d="M 10 10 L 90 10" fill="black" style="fill:rgb(0,0,0)"/>
</svg>"""


def test_paths_use_current_color() -> None:
    result = parametrize_svg(SAMPLE_SVG)
    root = etree.fromstring(result.encode())
    paths = root.findall(".//{%s}path" % SVG_NS) + root.findall(".//path")
    for path in paths:
        assert path.get("fill") == "currentColor"


def test_no_fill_in_style() -> None:
    result = parametrize_svg(SAMPLE_SVG)
    root = etree.fromstring(result.encode())
    paths = root.findall(".//{%s}path" % SVG_NS) + root.findall(".//path")
    for path in paths:
        style = path.get("style", "")
        assert "fill" not in style


def test_root_has_no_fill() -> None:
    svg_with_fill = '<svg xmlns="http://www.w3.org/2000/svg" fill="black"><path d="M 0 0 L 1 1" fill="black"/></svg>'
    result = parametrize_svg(svg_with_fill)
    root = etree.fromstring(result.encode())
    assert root.get("fill") is None
    assert root.get("color") is None


def test_preserves_viewbox() -> None:
    result = parametrize_svg(SAMPLE_SVG)
    root = etree.fromstring(result.encode())
    assert root.get("viewBox") == "0 0 100 50"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_parametrize.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'convert_png2svg.parametrize'`

- [ ] **Step 3: Implement `parametrize.py`**

Create `src/convert_png2svg/parametrize.py`:

```python
"""SVG parametrization: replace fills with currentColor."""

import re

from lxml import etree

SVG_NS = "http://www.w3.org/2000/svg"


def parametrize_svg(svg_string: str) -> str:
    """Replace all path fills with currentColor for external color control.

    Args:
        svg_string: Cleaned SVG string.

    Returns:
        SVG string with all paths using fill="currentColor".
    """
    root = etree.fromstring(svg_string.encode())

    # Process all path elements
    paths = root.findall(".//{%s}path" % SVG_NS) + root.findall(".//path")
    for path in paths:
        path.set("fill", "currentColor")

        # Remove fill from inline style
        style = path.get("style", "")
        if style:
            cleaned = re.sub(r"fill\s*:[^;]+;?\s*", "", style).strip()
            if cleaned:
                path.set("style", cleaned)
            else:
                del path.attrib["style"]

    # Remove fill and color from root <svg>
    for attr in ("fill", "color"):
        if attr in root.attrib:
            del root.attrib[attr]

    return etree.tostring(root, pretty_print=True, xml_declaration=False).decode()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_parametrize.py -v`
Expected: All 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/convert_png2svg/parametrize.py tests/test_parametrize.py
git commit -m "feat: add parametrize_svg module (currentColor replacement)"
```

---

### Task 7: CLI & Pipeline Orchestration

**Files:**
- Create: `src/convert_png2svg/cli.py`
- Create: `tests/test_cli.py`

- [ ] **Step 1: Implement `cli.py`**

Create `src/convert_png2svg/cli.py`:

```python
"""CLI entry point and pipeline orchestration."""

from pathlib import Path
from typing import Annotated

import cv2
import typer

from convert_png2svg.clean import clean_svg
from convert_png2svg.config import PipelineConfig
from convert_png2svg.parametrize import parametrize_svg
from convert_png2svg.preprocess import preprocess
from convert_png2svg.vectorize import vectorize

app = typer.Typer(help="Convert signature photos to clean, color-parametrizable SVGs.")


@app.command()
def main(
    input_path: Annotated[Path, typer.Argument(help="Input PNG file")],
    output_path: Annotated[Path, typer.Argument(help="Output SVG file")],
    turdsize: Annotated[int, typer.Option(help="Suppress speckles smaller than N px")] = 2,
    alphamax: Annotated[float, typer.Option(help="Corner smoothing (0.0–1.3)")] = 1.0,
    opttolerance: Annotated[float, typer.Option(help="Curve optimization tolerance")] = 0.2,
    blur: Annotated[int, typer.Option(help="Median blur kernel size (0 = off)")] = 3,
    morph: Annotated[int, typer.Option(help="Morphological closing kernel size (0 = off)")] = 2,
    debug: Annotated[bool, typer.Option(help="Write intermediate images to output dir")] = False,
) -> None:
    """Convert a signature photograph to a clean SVG."""
    config = PipelineConfig(
        turdsize=turdsize,
        alphamax=alphamax,
        opttolerance=opttolerance,
        blur=blur,
        morph=morph,
        debug=debug,
    )

    binary = preprocess(input_path, config)

    if config.debug:
        output_dir = output_path.parent
        stem = input_path.stem
        gray = cv2.imread(str(input_path), cv2.IMREAD_GRAYSCALE)
        cv2.imwrite(str(output_dir / f"{stem}_grayscale.png"), gray)
        cv2.imwrite(str(output_dir / f"{stem}_binary.png"), binary)

    raw_svg = vectorize(binary, config)
    cleaned = clean_svg(raw_svg)
    final = parametrize_svg(cleaned)

    output_path.write_text(final)
    typer.echo(f"Written: {output_path}")
```

- [ ] **Step 2: Verify CLI help works**

Run: `python -m convert_png2svg --help`
Expected: Shows usage with all options listed.

- [ ] **Step 3: Write end-to-end CLI test**

Create `tests/test_cli.py`:

```python
"""End-to-end CLI tests."""

from pathlib import Path

import cv2
import numpy as np
import pytest
from lxml import etree
from typer.testing import CliRunner

from convert_png2svg.cli import app

pytestmark = pytest.mark.requires_potrace

runner = CliRunner()

SVG_NS = "http://www.w3.org/2000/svg"


def _create_test_png(path: Path) -> None:
    """Create a white image with black strokes for testing."""
    img = np.ones((200, 400, 3), dtype=np.uint8) * 255
    cv2.line(img, (40, 100), (360, 100), (0, 0, 0), 4)
    cv2.line(img, (100, 40), (300, 160), (0, 0, 0), 3)
    cv2.ellipse(img, (200, 100), (80, 40), 0, 0, 360, (0, 0, 0), 2)
    cv2.imwrite(str(path), img)


def test_cli_produces_svg(tmp_path: Path) -> None:
    png = tmp_path / "sig.png"
    svg = tmp_path / "sig.svg"
    _create_test_png(png)

    result = runner.invoke(app, [str(png), str(svg)])
    assert result.exit_code == 0
    assert svg.exists()


def test_output_contract(tmp_path: Path) -> None:
    png = tmp_path / "sig.png"
    svg = tmp_path / "sig.svg"
    _create_test_png(png)

    runner.invoke(app, [str(png), str(svg)])
    content = svg.read_text()
    root = etree.fromstring(content.encode())

    # viewBox starts at 0 0
    viewbox = root.get("viewBox", "")
    parts = viewbox.split()
    assert len(parts) == 4
    assert parts[0] == "0"
    assert parts[1] == "0"

    # All paths use currentColor
    paths = root.findall(".//{%s}path" % SVG_NS) + root.findall(".//path")
    assert len(paths) > 0
    for path in paths:
        assert path.get("fill") == "currentColor"

    # No background rects
    rects = root.findall(".//{%s}rect" % SVG_NS) + root.findall(".//rect")
    assert len(rects) == 0

    # No fill/color on root
    assert root.get("fill") is None
    assert root.get("color") is None


def test_debug_writes_intermediates(tmp_path: Path) -> None:
    png = tmp_path / "sig.png"
    svg = tmp_path / "sig.svg"
    _create_test_png(png)

    runner.invoke(app, [str(png), str(svg), "--debug"])
    assert (tmp_path / "sig_grayscale.png").exists()
    assert (tmp_path / "sig_binary.png").exists()
```

- [ ] **Step 4: Run all tests**

Run: `pytest -v`
Expected: All tests PASS (vectorize/cli tests skipped if potrace not installed).

- [ ] **Step 5: Commit**

```bash
git add src/convert_png2svg/cli.py tests/test_cli.py
git commit -m "feat: add CLI with typer and end-to-end pipeline"
```

---

### Task 8: Lint, Type Check & Final Verification

**Files:**
- Modify: any files with lint/type issues

- [ ] **Step 1: Run ruff**

Run: `ruff check --fix . && ruff format .`
Expected: No errors (or auto-fixed).

- [ ] **Step 2: Run mypy**

Run: `mypy src/`
Expected: No errors (may need type stubs or `# type: ignore` for OpenCV).

- [ ] **Step 3: Fix any issues found**

Address any lint or type errors. Common: `cv2` has incomplete type stubs — add `# type: ignore[import-untyped]` for the `cv2` import if needed.

- [ ] **Step 4: Run full test suite with coverage**

Run: `pytest --cov=src -v`
Expected: All tests pass, coverage ≥80%.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "chore: fix lint and type errors"
```

---

### Task 9: Update CLAUDE.md

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Update CLAUDE.md to reflect actual implementation**

Review the implemented code and update CLAUDE.md if any details changed during implementation (e.g., actual function signatures, additional dependencies, changed defaults).

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md to match implementation"
```
