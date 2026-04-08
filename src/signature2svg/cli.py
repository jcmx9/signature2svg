"""CLI entry point and pipeline orchestration."""

from pathlib import Path
from typing import Annotated

import cv2
import typer

from signature2svg.clean import clean_svg
from signature2svg.config import PipelineConfig
from signature2svg.optimize import optimize_svg
from signature2svg.parametrize import parametrize_svg
from signature2svg.preprocess import preprocess
from signature2svg.vectorize import vectorize

app = typer.Typer(help="Convert images or SVGs to clean, color-parametrizable SVGs.")

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff"}


@app.command()
def main(
    input_path: Annotated[Path, typer.Argument(help="Input image or SVG file")],
    output_path: Annotated[Path, typer.Argument(help="Output SVG file")],
    turdsize: Annotated[int, typer.Option(help="Suppress speckles smaller than N px")] = 2,
    alphamax: Annotated[float, typer.Option(help="Corner smoothing (0.0–1.3)")] = 1.0,
    opttolerance: Annotated[float, typer.Option(help="Curve optimization tolerance")] = 0.2,
    blur: Annotated[int, typer.Option(help="Median blur kernel size (0 = off)")] = 3,
    morph: Annotated[int, typer.Option(help="Morphological closing kernel size (0 = off)")] = 2,
    debug: Annotated[bool, typer.Option(help="Write intermediate images to output dir")] = False,
) -> None:
    """Convert an image or SVG to a clean, color-parametrizable SVG."""
    ext = input_path.suffix.lower()

    if ext == ".svg":
        svg_string = input_path.read_text(encoding="utf-8")
    elif ext in IMAGE_EXTENSIONS:
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
            if gray is not None:
                cv2.imwrite(str(output_dir / f"{stem}_grayscale.png"), gray)
            cv2.imwrite(str(output_dir / f"{stem}_binary.png"), binary)

        svg_string = vectorize(binary, config)
    else:
        raise typer.BadParameter(f"Unsupported file format: {ext}")

    cleaned = clean_svg(svg_string)
    final = parametrize_svg(cleaned)
    optimized = optimize_svg(final)

    output_path.write_text(optimized, encoding="utf-8")
    typer.echo(f"Written: {output_path}")
