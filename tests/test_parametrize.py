"""Tests for SVG parametrization."""

from lxml import etree

from signature2svg.parametrize import parametrize_svg

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


def test_style_with_other_attrs_preserved() -> None:
    """Cover: style has fill + other attrs — fill removed, other kept."""
    svg = '<svg xmlns="http://www.w3.org/2000/svg"><path d="M 0 0 L 1 1" style="fill:black;stroke:red"/></svg>'
    result = parametrize_svg(svg)
    root = etree.fromstring(result.encode())
    paths = root.findall(".//{%s}path" % SVG_NS) + root.findall(".//path")
    assert paths[0].get("fill") == "currentColor"
    # stroke should remain in style
    style = paths[0].get("style", "")
    assert "stroke:red" in style
    assert "fill" not in style


def test_no_style_block_in_output() -> None:
    """Per spec: Do NOT add a <style> block — keep it minimal."""
    result = parametrize_svg(SAMPLE_SVG)
    root = etree.fromstring(result.encode())
    style_els = root.findall(".//{%s}style" % SVG_NS) + root.findall(".//style")
    assert len(style_els) == 0


def test_existing_style_block_removed() -> None:
    """Existing <style> blocks are stripped to keep output minimal."""
    svg = """<svg xmlns="http://www.w3.org/2000/svg">
<style>path { fill: #000; }</style>
<path d="M 0 0 L 1 1" fill="black"/>
</svg>"""
    result = parametrize_svg(svg)
    root = etree.fromstring(result.encode())
    style_els = root.findall(".//{%s}style" % SVG_NS) + root.findall(".//style")
    assert len(style_els) == 0
    # path fill should still be set via attribute
    paths = root.findall(".//{%s}path" % SVG_NS) + root.findall(".//path")
    assert paths[0].get("fill") == "currentColor"
