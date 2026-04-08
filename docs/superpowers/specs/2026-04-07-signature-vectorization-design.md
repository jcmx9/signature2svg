# Signature Vectorization Pipeline — Design Spec

## Goal

Convert a photograph of a handwritten signature on white paper into a clean, tight, color-parametrizable SVG. CLI tool, single PNG in → single SVG out.

## Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Project structure | `src/convert_png2svg/` package | Follows global conventions, installable via `uv` |
| CLI framework | typer | Consistent with other projects, less boilerplate |
| Package name | `convert_png2svg` | Matches repo name |
| Config/validation | Pydantic `PipelineConfig` | Validates parameter ranges, reusable when importing modules directly |
| Architecture | Sequential pipeline (plain functions) | 4 fixed steps, YAGNI for anything more complex |

## Project Structure

```
src/convert_png2svg/
├── __init__.py          # Version, package metadata
├── __main__.py          # python -m convert_png2svg
├── cli.py               # typer app, CLI entry point
├── config.py            # PipelineConfig (Pydantic BaseModel)
├── preprocess.py        # preprocess(path, config) → np.ndarray
├── vectorize.py         # vectorize(binary, config) → str
├── clean.py             # clean_svg(svg_string) → str
├── parametrize.py       # parametrize_svg(svg_string) → str
└── exceptions.py        # Custom exceptions
tests/
├── conftest.py          # Fixtures (generated test images, SVG strings)
├── test_preprocess.py
├── test_vectorize.py
├── test_clean.py
├── test_parametrize.py
└── test_cli.py
pyproject.toml
```

## Config Model

```python
class PipelineConfig(BaseModel):
    turdsize: int = Field(default=2, ge=0)
    alphamax: float = Field(default=1.0, ge=0.0, le=1.3)
    opttolerance: float = Field(default=0.2, ge=0.0)
    blur: int = Field(default=3, ge=0)           # 0 = off
    morph: int = Field(default=2, ge=0)           # 0 = off
    debug: bool = False
```

## Pipeline Data Flow

```python
def main(input_path: Path, output_path: Path, config: PipelineConfig) -> None:
    binary = preprocess(input_path, config)          # PNG → np.ndarray (uint8, binary)

    if config.debug:
        # write grayscale + binary intermediates next to output
        ...

    raw_svg = vectorize(binary, config)              # np.ndarray → raw SVG string
    cleaned = clean_svg(raw_svg)                     # raw SVG → tight viewBox, no background
    final = parametrize_svg(cleaned)                 # → fill="currentColor"

    output_path.write_text(final)
```

### Module Responsibilities

| Module | Input | Output | External Dependency |
|--------|-------|--------|---------------------|
| `preprocess` | `Path`, `PipelineConfig` | `np.ndarray` (binary uint8) | opencv-python, numpy |
| `vectorize` | `np.ndarray`, `PipelineConfig` | `str` (raw SVG) | potrace (subprocess) |
| `clean` | `str` (SVG) | `str` (SVG) | lxml, svgpathtools |
| `parametrize` | `str` (SVG) | `str` (SVG) | lxml |

- `clean` and `parametrize` do not need `PipelineConfig` — they operate purely on SVG strings.
- Temp files in `vectorize` via `tempfile.TemporaryDirectory` (PBM for Potrace).

## CLI Interface

```bash
python -m convert_png2svg input.png output.svg [options]
```

Options: `--turdsize`, `--alphamax`, `--opttolerance`, `--blur`, `--morph`, `--debug`

typer builds the `PipelineConfig` from CLI options and passes it to the pipeline.

## Error Handling

### Custom Exceptions (`exceptions.py`)

```python
class NoPathsDetectedError(ValueError):
    """No paths found after vectorization."""

class DegenerateBoundingBoxError(ValueError):
    """Bounding box is empty or degenerate."""

class PotraceError(RuntimeError):
    """Potrace subprocess failed."""
    def __init__(self, stderr: str):
        super().__init__(f"Potrace failed: {stderr}")
```

### Where They Raise

- `vectorize`: Potrace `subprocess.run` with `check=True` → `PotraceError` with stderr on failure
- `clean_svg`: No `<path>` elements found → `NoPathsDetectedError`
- `clean_svg`: Bounding box has zero width or height → `DegenerateBoundingBoxError`

### Debug Mode (`--debug`)

- Handled in `main()`, not in individual modules
- Writes `{output_dir}/{stem}_grayscale.png` and `{output_dir}/{stem}_binary.png` next to output file
- Modules remain side-effect-free (except `vectorize` with its temp dir)

## Output SVG Contract

- `viewBox` starts at `0 0` (paths translated so min = origin), no whitespace padding
- All paths use `fill="currentColor"` — no hardcoded colors
- No background `<rect>` elements, no `fill` on root `<svg>`
- No Inkscape/Illustrator namespace bloat, no external references
- Minimal valid SVG, single file

## Testing

### Fixtures (`conftest.py`)

- `sample_signature_png`: Programmatically generated test image (black strokes on white via numpy/OpenCV) — no real photos in repo
- `sample_binary_image`: Pre-binarized numpy array for `vectorize` tests
- `sample_raw_svg`: Potrace-like SVG string with background rect and hardcoded fills for `clean`/`parametrize` tests

### Test Coverage

| Test File | What Is Tested |
|-----------|---------------|
| `test_preprocess.py` | Output is binary (only 0/255), correct shape, blur/morph parameters take effect |
| `test_vectorize.py` | Returns valid SVG string, `PotraceError` on invalid input |
| `test_clean.py` | viewBox starts with `0 0`, no background rects, no metadata comments, `NoPathsDetectedError` and `DegenerateBoundingBoxError` |
| `test_parametrize.py` | All paths have `fill="currentColor"`, no `fill`/`color` on root `<svg>` |
| `test_cli.py` | End-to-end: CLI with sample PNG → output SVG satisfies output contract |

### System Dependency

`test_vectorize.py` and `test_cli.py` require Potrace installed. Use marker `@pytest.mark.requires_potrace` — tests skip if Potrace is not available.

## Dependencies

### Python (pyproject.toml)

```
opencv-python
numpy
Pillow
lxml
svgpathtools
typer
pydantic
```

### Dev Dependencies

```
pytest
pytest-cov
pytest-xdist
ruff
mypy
```

### System

- `potrace` — `brew install potrace` (macOS) / `apt install potrace` (Debian)

## Out of Scope

- Multi-color signatures
- Transparent background handling (input assumed white paper)
- Raster output (SVG only)
- GUI — CLI only
