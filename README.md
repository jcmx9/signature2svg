# signature2svg

Convert a photograph of a handwritten signature into a clean, scalable SVG with configurable fill color.

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
# Install (requires uv)
uv tool install git+https://github.com/jcmx9/signature2svg.git

# Update
uv tool install --force git+https://github.com/jcmx9/signature2svg.git

# From source
git clone https://github.com/jcmx9/signature2svg.git
cd signature2svg
uv venv && source .venv/bin/activate
uv sync
```

## Usage

### Image to SVG

```bash
signature2svg photo.jpg
```

Produces `photo_cc.svg` and `photo_cc.png`. The PNG is the cleaned binary image (black ink on white) — useful for manual touch-up in a photo editor before re-running.

### SVG optimization

```bash
signature2svg input.svg
```

Produces `input_cc.svg`. Cleans the SVG: sets fill color (default `#2C3F6B`), removes backgrounds, strips editor metadata, optimizes with scour.

### Iterative workflow

1. `signature2svg photo.jpg` → produces `photo_cc.png` + `photo_cc.svg`
2. Open `photo_cc.png` in a photo editor, remove stray dots or artifacts
3. `signature2svg photo_cc.png` → produces `photo_cc_cc.png` + `photo_cc_cc.svg` (or rename first)

### Options

```
signature2svg [OPTIONS] INPUT

Arguments:
  INPUT   Input image (.png/.jpg/.jpeg/.bmp/.tiff) or SVG (.svg)

Output:
  {name}_cc.svg   Clean, parametrized SVG
  {name}_cc.png   Cleaned binary image (image mode only)

Options:
  --turdsize INT        Suppress speckles smaller than N px (0 = auto)  [default: 0]
  --alphamax FLOAT      Corner smoothing 0.0–1.3  [default: 1.0]
  --opttolerance FLOAT  Curve optimization tolerance  [default: 0.2]
  --blur INT            Median blur kernel size, 0 = off  [default: 3]
  --morph INT           Morphological closing kernel, 0 = off  [default: 2]
  --hexcode TEXT         Fill color for signature paths  [default: #2C3F6B]
  --height INT          Set SVG height in pt (width scales proportionally)
  --debug / --no-debug  Write intermediate images to output dir  [default: no-debug]
```

`--hexcode` accepts any CSS color value, e.g. `#000000` or `currentColor`. Image-specific options are ignored in SVG mode.

## Output

The output SVG is designed for embedding with external color control:

- All paths use the configured fill color (default `#2C3F6B`, override with `--hexcode`)
- No fixed `width`/`height` by default — SVG scales freely (`--height` sets fixed height in pt)
- No background elements, no editor metadata, no namespace bloat
- Paths are losslessly optimized (shortened notation, compressed IDs)

### Typst

```typst
// Default color (#2C3F6B) is baked in — just embed:
#image("signature.svg", width: 45mm)

// Or use currentColor mode for external control:
// signature2svg input.jpg --hexcode currentColor
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
8. **Parametrize** sets fill color on all paths (default `#2C3F6B`), removes `<style>` blocks
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
