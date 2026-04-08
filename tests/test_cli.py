"""End-to-end CLI tests."""

from pathlib import Path

import cv2
import numpy as np
import pytest
from lxml import etree
from typer.testing import CliRunner

from signature2svg.cli import app

runner = CliRunner()

SVG_NS = "http://www.w3.org/2000/svg"


def _create_test_png(path: Path) -> None:
    """Create a white image with black strokes for testing."""
    img = np.ones((200, 400, 3), dtype=np.uint8) * 255
    cv2.line(img, (40, 100), (360, 100), (0, 0, 0), 4)
    cv2.line(img, (100, 40), (300, 160), (0, 0, 0), 3)
    cv2.ellipse(img, (200, 100), (80, 40), 0, 0, 360, (0, 0, 0), 2)
    cv2.imwrite(str(path), img)


@pytest.mark.requires_potrace
def test_cli_produces_svg_and_png(tmp_path: Path) -> None:
    png = tmp_path / "sig.png"
    _create_test_png(png)

    result = runner.invoke(app, [str(png)])
    assert result.exit_code == 0
    assert (tmp_path / "sig_cc.svg").exists()
    assert (tmp_path / "sig_cc.png").exists()


@pytest.mark.requires_potrace
def test_cc_png_is_black_on_white(tmp_path: Path) -> None:
    png = tmp_path / "sig.png"
    _create_test_png(png)

    runner.invoke(app, [str(png)])
    cc_png = cv2.imread(str(tmp_path / "sig_cc.png"), cv2.IMREAD_GRAYSCALE)
    assert cc_png is not None
    unique = set(np.unique(cc_png))
    assert unique <= {0, 255}
    # More white than black (background > ink)
    assert np.sum(cc_png == 255) > np.sum(cc_png == 0)


@pytest.mark.requires_potrace
def test_output_contract(tmp_path: Path) -> None:
    png = tmp_path / "sig.png"
    _create_test_png(png)

    runner.invoke(app, [str(png)])
    svg = tmp_path / "sig_cc.svg"
    content = svg.read_text()
    root = etree.fromstring(content.encode())

    viewbox = root.get("viewBox", "")
    parts = viewbox.split()
    assert len(parts) == 4

    paths = root.findall(".//{%s}path" % SVG_NS) + root.findall(".//path")
    assert len(paths) > 0
    assert "currentColor" in content

    rects = root.findall(".//{%s}rect" % SVG_NS) + root.findall(".//rect")
    assert len(rects) == 0

    assert root.get("fill") is None
    assert root.get("color") is None


@pytest.mark.requires_potrace
def test_debug_writes_grayscale(tmp_path: Path) -> None:
    png = tmp_path / "sig.png"
    _create_test_png(png)

    runner.invoke(app, [str(png), "--debug"])
    assert (tmp_path / "sig_grayscale.png").exists()


def test_svg_mode_produces_output(tmp_path: Path) -> None:
    svg_in = tmp_path / "input.svg"
    svg_in.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 50">'
        '<path d="M 0 0 L 100 0 L 100 50 Z" fill="#000000"/>'
        "</svg>"
    )

    result = runner.invoke(app, [str(svg_in)])
    assert result.exit_code == 0
    assert (tmp_path / "input_cc.svg").exists()


def test_svg_mode_sets_current_color(tmp_path: Path) -> None:
    svg_in = tmp_path / "input.svg"
    svg_in.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 50">'
        '<path d="M 0 0 L 100 0 L 100 50 Z" fill="black"/>'
        "</svg>"
    )

    runner.invoke(app, [str(svg_in)])
    content = (tmp_path / "input_cc.svg").read_text()
    assert "currentColor" in content


def test_svg_mode_no_png_output(tmp_path: Path) -> None:
    svg_in = tmp_path / "input.svg"
    svg_in.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 50">'
        '<path d="M 0 0 L 100 0 L 100 50 Z" fill="black"/>'
        "</svg>"
    )

    runner.invoke(app, [str(svg_in)])
    assert not (tmp_path / "input_cc.png").exists()


def test_unsupported_format(tmp_path: Path) -> None:
    txt = tmp_path / "input.txt"
    txt.write_text("not an image")

    result = runner.invoke(app, [str(txt)])
    assert result.exit_code != 0
