"""CLI entry point and pipeline orchestration."""

from pathlib import Path
from typing import Annotated

import cv2
import typer

from signature2svg import __version__
from signature2svg.clean import clean_svg
from signature2svg.config import PipelineConfig
from signature2svg.optimize import optimize_svg
from signature2svg.parametrize import parametrize_svg
from signature2svg.preprocess import preprocess
from signature2svg.vectorize import vectorize


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"signature2svg {__version__}")
        raise typer.Exit()


app = typer.Typer(
    help=f"signature2svg {__version__} — Convert images or SVGs to clean, color-parametrizable SVGs."
)

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff"}


@app.command()
def main(
    input_path: Annotated[Path, typer.Argument(help="Input image or SVG file", exists=True)],
    version: Annotated[
        bool, typer.Option("--version", callback=_version_callback, is_eager=True)
    ] = False,
    turdsize: Annotated[int, typer.Option(help="Suppress speckles smaller than N px")] = 2,
    alphamax: Annotated[float, typer.Option(help="Corner smoothing (0.0–1.3)")] = 1.0,
    opttolerance: Annotated[float, typer.Option(help="Curve optimization tolerance")] = 0.2,
    blur: Annotated[int, typer.Option(help="Median blur kernel size (0 = off)")] = 3,
    morph: Annotated[int, typer.Option(help="Morphological closing kernel size (0 = off)")] = 2,
    debug: Annotated[bool, typer.Option(help="Write intermediate images to output dir")] = False,
) -> None:
    """Convert an image or SVG to a clean, color-parametrizable SVG.

    Output files are written next to the input with '_cc' suffix:
      input.jpg → input_cc.svg + input_cc.png (cleaned binary for manual editing)
      input.svg → input_cc.svg
    """
    ext = input_path.suffix.lower()
    stem = input_path.stem
    output_dir = input_path.parent
    output_svg = output_dir / f"{stem}_cc.svg"

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

        # Save cleaned binary as PNG (black ink on white background) for manual editing
        output_png = output_dir / f"{stem}_cc.png"
        cv2.imwrite(str(output_png), binary)
        typer.echo(f"Written: {output_png}")

        if config.debug:
            gray = cv2.imread(str(input_path), cv2.IMREAD_GRAYSCALE)
            if gray is not None:
                cv2.imwrite(str(output_dir / f"{stem}_grayscale.png"), gray)

        svg_string = vectorize(binary, config)
    else:
        raise typer.BadParameter(f"Unsupported file format: {ext}")

    cleaned = clean_svg(svg_string)
    final = parametrize_svg(cleaned)
    optimized = optimize_svg(final)

    output_svg.write_text(optimized, encoding="utf-8")
    typer.echo(f"Written: {output_svg}")
