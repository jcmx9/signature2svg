# signature2svg — Design Spec

## Goal

Rename `svgsign` to `signature2svg`. Add dual-mode CLI: image input runs full pipeline, SVG input runs only SVG optimization. Improve preprocessing to handle photo artifacts (shadows, uneven lighting).

## Rename

| From | To |
|------|-----|
| Package `svgsign` | `signature2svg` |
| CLI `svgsign` | `signature2svg` |
| GitHub repo `convertPng2Svg` | `signature2svg` |
| All imports `from svgsign.` | `from signature2svg.` |

## Versioning

CalVer `YY.M.x` — current: `26.4.0`. x resets to 0 each new month.

## Dual Mode (auto-detected via file extension)

| Input Extension | Mode | Pipeline |
|----------------|------|----------|
| `.png`, `.jpg`, `.jpeg`, `.bmp`, `.tiff` | Image | preprocess → vectorize → clean → parametrize → optimize |
| `.svg` | SVG-only | clean → parametrize → optimize |
| anything else | Error | `ValueError("Unsupported file format: .xyz")` |

Potrace/preprocessing CLI options (`--turdsize`, `--blur`, `--morph`, `--debug`) are silently ignored in SVG mode.

## New Module: `optimize.py`

```python
def optimize_svg(svg_string: str) -> str
```

Wraps `scour` for lossless SVG optimization:
- Shorten path `d` notation (`0.500` → `.5`, absolute → relative)
- Remove unused IDs and `defs`
- Strip editor namespaces (Inkscape, Illustrator)
- Collapse empty `<g>` elements
- Normalize numeric precision

Uses `scour.scour.scourString()` with these options:
- `strip_xml_prolog = True`
- `remove_metadata = True`
- `strip_comments = True`
- `shorten_ids = True`
- `indent = none`

## Preprocessing Improvement

Current problem: Otsu thresholding is global — photos with shadows/gradients produce large black areas that get vectorized.

New pipeline:
```
Image → Grayscale → Median Blur → CLAHE → Adaptive Threshold → Morph Open (noise) → Morph Close (gaps) → Auto-Crop
```

### CLAHE (new step)
Contrast Limited Adaptive Histogram Equalization before thresholding. Normalizes local brightness so shadows on white paper don't appear as dark regions.

Parameters: `clip_limit=2.0`, `tile_grid_size=(8, 8)` — sensible defaults for document photos.

### Adaptive Threshold (replaces Otsu)
`cv2.adaptiveThreshold(gray, 255, ADAPTIVE_THRESH_GAUSSIAN_C, THRESH_BINARY, block_size=51, C=10)`

Computes threshold per local region — handles uneven lighting.

### Morphological Opening (new step)
`cv2.morphologyEx(binary, MORPH_OPEN, kernel)` with small kernel (2x2) BEFORE closing.

Removes isolated noise pixels and small speckles that aren't part of ink strokes. Opening = erode then dilate: thin noise disappears, thick strokes survive.

### Full preprocess flow
1. Read image, convert to grayscale
2. Median blur (if `config.blur > 0`)
3. CLAHE normalization
4. Adaptive threshold → binary
5. Morphological opening (noise removal, small kernel)
6. Morphological closing (bridge gaps in strokes, if `config.morph > 0`)
7. Auto-crop to ink bounding box

## CLI Changes

```python
@app.command()
def main(input_path, output_path, ...):
    ext = input_path.suffix.lower()

    if ext == ".svg":
        svg_string = input_path.read_text()
    elif ext in (".png", ".jpg", ".jpeg", ".bmp", ".tiff"):
        binary = preprocess(input_path, config)
        if config.debug:
            # write intermediates
            ...
        svg_string = vectorize(binary, config)
    else:
        raise ValueError(f"Unsupported file format: {ext}")

    cleaned = clean_svg(svg_string)
    final = parametrize_svg(cleaned)
    optimized = optimize_svg(final)

    output_path.write_text(optimized)
```

## Project Structure

```
src/signature2svg/
├── __init__.py
├── __main__.py
├── cli.py              # dual-mode dispatch
├── config.py           # PipelineConfig
├── exceptions.py
├── preprocess.py       # CLAHE + adaptive threshold
├── vectorize.py        # Potrace wrapper
├── clean.py            # strip backgrounds, metadata
├── parametrize.py      # currentColor + style block
└── optimize.py         # scour wrapper (NEW)
tests/
├── conftest.py
├── test_preprocess.py
├── test_vectorize.py
├── test_clean.py
├── test_parametrize.py
├── test_optimize.py    # NEW
└── test_cli.py
```

## New Dependency

`scour` added to `[project.dependencies]` in `pyproject.toml`.

## Output Contract (unchanged)

- No `width`/`height` on root `<svg>` — scales freely
- All paths `fill="currentColor"`
- `<style>path { fill: currentColor; }</style>` block present
- No background rects, no metadata, no editor namespaces
- viewBox present, losslessly optimized paths
