"""Tests for SVG optimization via scour."""

from lxml import etree

from signature2svg.optimize import optimize_svg

SVG_NS = "http://www.w3.org/2000/svg"

SAMPLE_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 50">
<path d="M 0.000 0.000 L 100.000 0.000 L 100.000 50.000 Z" fill="currentColor"/>
</svg>"""

SVG_WITH_NAMESPACE = """<svg xmlns="http://www.w3.org/2000/svg"
  xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
  inkscape:version="1.0" viewBox="0 0 100 50">
<path d="M 0 0 L 100 0 L 100 50 Z" fill="currentColor"/>
</svg>"""


def test_returns_valid_svg() -> None:
    result = optimize_svg(SAMPLE_SVG)
    assert "<svg" in result
    assert "</svg>" in result


def test_shortens_path_notation() -> None:
    result = optimize_svg(SAMPLE_SVG)
    assert "0.000" not in result


def test_strips_editor_namespaces() -> None:
    result = optimize_svg(SVG_WITH_NAMESPACE)
    assert "inkscape" not in result


def test_preserves_viewbox() -> None:
    result = optimize_svg(SAMPLE_SVG)
    root = etree.fromstring(result.encode())
    assert root.get("viewBox") is not None


def test_preserves_path_content() -> None:
    result = optimize_svg(SAMPLE_SVG)
    root = etree.fromstring(result.encode())
    paths = root.findall(".//{%s}path" % SVG_NS) + root.findall(".//path")
    assert len(paths) >= 1


def test_fill_color_on_path_attributes() -> None:
    """Fill color must remain as path attribute, not in a style block."""
    result = optimize_svg(SAMPLE_SVG, color="#FF0000")
    root = etree.fromstring(result.encode())
    paths = root.findall(".//{%s}path" % SVG_NS) + root.findall(".//path")
    for path in paths:
        assert path.get("fill") == "#FF0000"


def test_default_fill_color() -> None:
    """Default fill color should be #2C3F6B."""
    result = optimize_svg(SAMPLE_SVG)
    root = etree.fromstring(result.encode())
    paths = root.findall(".//{%s}path" % SVG_NS) + root.findall(".//path")
    for path in paths:
        assert path.get("fill") == "#2C3F6B"


def test_no_style_block_in_output() -> None:
    """Scour might create style blocks — post-fixup must remove them."""
    svg_with_style = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 50">
<style>path { fill: currentColor; }</style>
<path d="M 0 0 L 100 0 L 100 50 Z" fill="currentColor"/>
</svg>"""
    result = optimize_svg(svg_with_style)
    root = etree.fromstring(result.encode())
    styles = root.findall(".//{%s}style" % SVG_NS) + root.findall(".//style")
    assert len(styles) == 0
