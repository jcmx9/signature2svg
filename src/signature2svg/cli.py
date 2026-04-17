"""CLI entry point and pipeline orchestration."""

from pathlib import Path
from typing import Annotated

import cv2
import typer

from lxml import etree

from signature2svg import __version__
from signature2svg.clean import clean_svg
from signature2svg.config import PipelineConfig
from signature2svg.optimize import optimize_svg
from signature2svg.parametrize import parametrize_svg
from signature2svg.preprocess import detect_stroke_width, preprocess
from signature2svg.vectorize import vectorize

SVG_NS = "http://www.w3.org/2000/svg"


def _set_svg_height(svg_string: str, height_pt: int) -> str:
    """Set height attribute on SVG root element. Width scales from viewBox."""
    root = etree.fromstring(svg_string.encode())
    root.set("height", f"{height_pt}pt")
    return etree.tostring(root, pretty_print=False, xml_declaration=False).decode()


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"signature2svg {__version__}")
        raise typer.Exit()


app = typer.Typer(
    help=f"signature2svg {__version__} — Convert images or SVGs to clean, color-parametrizable SVGs.",
    context_settings={"help_option_names": ["-h", "--help"]},
)

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}


@app.command()
def main(
    input_path: Annotated[Path | None, typer.Argument(help="Input image or SVG file")] = None,
    version: Annotated[
        bool, typer.Option("--version", "-V", callback=_version_callback, is_eager=True)
    ] = False,
    turdsize: Annotated[
        int, typer.Option(help="Suppress speckles smaller than N px (0 = auto from stroke width)")
    ] = 0,
    alphamax: Annotated[float, typer.Option(help="Corner smoothing (0.0–1.3)")] = 1.0,
    opttolerance: Annotated[float, typer.Option(help="Curve optimization tolerance")] = 0.2,
    blur: Annotated[int, typer.Option(help="Median blur kernel size (0 = off)")] = 3,
    morph: Annotated[int, typer.Option(help="Morphological closing kernel size (0 = off)")] = 2,
    debug: Annotated[bool, typer.Option(help="Write intermediate images to output dir")] = False,
    height: Annotated[
        int | None, typer.Option(help="Set SVG height in pt (width scales proportionally)")
    ] = None,
    hexcode: Annotated[
        str, typer.Option(help="Fill color for signature paths (hex code or 'currentColor')")
    ] = "#2C3F6B",
) -> None:
    """Convert an image or SVG to a clean, color-parametrizable SVG.

    Output files are written next to the input with '_cc' suffix:
      input.jpg → input_cc.svg + input_cc.png (cleaned binary for manual editing)
      input.svg → input_cc.svg
    """
    if input_path is None:
        typer.echo(typer.main.get_command(app).get_help(typer.Context(typer.main.get_command(app))))
        raise typer.Exit()

    if not input_path.exists():
        raise typer.BadParameter(f"File not found: {input_path}")

    ext = input_path.suffix.lower()
    stem = input_path.stem
    output_dir = input_path.parent
    output_svg = output_dir / f"{stem}_cc.svg"

    if ext == ".svg":
        typer.echo(f"[1/3] Reading SVG: {input_path.name}")
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

        typer.echo(f"[1/5] Preprocessing: {input_path.name}")
        binary = preprocess(input_path, config)

        # Auto-detect turdsize from stroke width if not set explicitly
        if config.turdsize == 0:
            stroke_w = detect_stroke_width(binary)
            config = config.model_copy(update={"turdsize": max(2, int(stroke_w * 0.7))})
            typer.echo(f"      Stroke width: {stroke_w:.1f}px → turdsize: {config.turdsize}")

        # Save cleaned binary as PNG (black ink on white background) for manual editing
        output_png = output_dir / f"{stem}_cc.png"
        cv2.imwrite(str(output_png), binary)
        typer.echo(f"      Saved: {output_png.name}")

        if config.debug:
            gray = cv2.imread(str(input_path), cv2.IMREAD_GRAYSCALE)
            if gray is not None:
                cv2.imwrite(str(output_dir / f"{stem}_grayscale.png"), gray)

        typer.echo("[2/5] Vectorizing (potrace)")
        svg_string = vectorize(binary, config)

        typer.echo("[3/5] Cleaning SVG")
        cleaned = clean_svg(svg_string)
        typer.echo(f"[4/5] Setting fill: {hexcode}")
        final = parametrize_svg(cleaned, color=hexcode)
        typer.echo("[5/5] Optimizing (scour)")
        optimized = optimize_svg(final)
    else:
        raise typer.BadParameter(f"Unsupported file format: {ext}")

    if ext == ".svg":
        typer.echo(f"[2/3] Cleaning + parametrizing (fill: {hexcode})")
        cleaned = clean_svg(svg_string)
        final = parametrize_svg(cleaned, color=hexcode)
        typer.echo("[3/3] Optimizing (scour)")
        optimized = optimize_svg(final)

    if height is not None:
        optimized = _set_svg_height(optimized, height)

    output_svg.write_text(optimized, encoding="utf-8")
    typer.echo(f"Done: {output_svg.name}")
