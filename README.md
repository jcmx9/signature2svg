# signature2svg

Convert a photograph of a handwritten signature into a clean, scalable SVG with color control via `currentColor`.

Also optimizes existing SVGs — pass an SVG file as input to clean, parametrize, and compress it.

## Prerequisites

- **Python** 3.12+
- **Potrace** — vectorization engine (image mode only)

```bash
# macOS
brew install potrace

# Debian/Ubuntu
sudo apt install potrace
```

## Installation

```bash
# From GitHub (recommended)
uv tool install git+https://github.com/jcmx9/signature2svg.git

# From source
git clone https://github.com/jcmx9/signature2svg.git
cd signature2svg
uv venv && source .venv/bin/activate
uv sync
```

## Usage

### Image to SVG

```bash
signature2svg photo.jpg signature.svg
```

Takes a photo of a signature on white paper and produces a clean SVG. Handles uneven lighting, shadows, and noise automatically.

### SVG optimization

```bash
signature2svg input.svg output.svg
```

Cleans an existing SVG: sets `fill="currentColor"` on all paths, removes backgrounds, strips editor metadata, and optimizes with scour.

### Options

```
signature2svg [OPTIONS] INPUT OUTPUT

Arguments:
  INPUT   Input image (.png/.jpg/.jpeg/.bmp/.tiff) or SVG (.svg)
  OUTPUT  Output SVG file

Options:
  --turdsize INT        Suppress speckles smaller than N px  [default: 2]
  --alphamax FLOAT      Corner smoothing 0.0–1.3  [default: 1.0]
  --opttolerance FLOAT  Curve optimization tolerance  [default: 0.2]
  --blur INT            Median blur kernel size, 0 = off  [default: 3]
  --morph INT           Morphological closing kernel, 0 = off  [default: 2]
  --debug / --no-debug  Write intermediate images to output dir  [default: no-debug]
```

Image-specific options (`--turdsize`, `--alphamax`, `--opttolerance`, `--blur`, `--morph`, `--debug`) are ignored in SVG mode.

## Output

The output SVG is designed for embedding with external color control:

- All paths use `fill="currentColor"` — color is inherited from the parent element
- No fixed `width`/`height` — SVG scales freely to any container size
- No background elements, no editor metadata, no namespace bloat
- Paths are losslessly optimized (shortened notation, compressed IDs)

### Typst

```typst
#text(fill: rgb("#0053A0"))[#image("signature.svg", width: 45mm)]
```

### HTML/CSS

```html
<div style="color: navy; width: 200px;">
  <img src="signature.svg" />
</div>
```

## Pipeline

### Image mode

```
Photo → Grayscale → Median Blur → CLAHE → Adaptive Threshold → Morph Open → Morph Close → Auto-Crop → Potrace → Clean → Parametrize → Optimize
```

1. **CLAHE** normalizes local brightness to eliminate shadows and lighting gradients
2. **Adaptive thresholding** separates ink from paper per-region (not globally)
3. **Morphological opening** removes isolated noise pixels
4. **Morphological closing** bridges small gaps in ink strokes
5. **Auto-crop** trims to the ink bounding box
6. **Potrace** traces the bitmap to vector paths
7. **Clean** removes background rects, metadata, editor attributes
8. **Parametrize** sets `fill="currentColor"` on all paths and adds a `<style>` fallback
9. **Optimize** runs scour for lossless SVG compression

### SVG mode

Steps 7–9 only.

## Development

```bash
git clone https://github.com/jcmx9/signature2svg.git
cd signature2svg
uv venv && source .venv/bin/activate
uv sync --all-extras

# Run tests
pytest -v

# Lint & format
ruff check --fix . && ruff format .

# Type check
mypy src/
```

## License

[MIT](LICENSE)
