"""Tests for SVG cleaning."""

import pytest
from lxml import etree

from signature2svg.clean import clean_svg
from signature2svg.exceptions import NoPathsDetectedError

SAMPLE_SVG = """<?xml version="1.0" standalone="no"?>
<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 20010904//EN"
 "http://www.w3.org/TR/2001/REC-SVG-20010904/DTD/svg10.dtd">
<svg version="1.0" xmlns="http://www.w3.org/2000/svg"
 width="200" height="100" viewBox="0 0 200 100">
<!-- Created by potrace 1.16 -->
<rect width="100%" height="100%" fill="white"/>
<g transform="translate(10,90) scale(0.1,-0.1)" fill="#000000">
<path d="M 100 200 L 300 200 L 300 400 L 100 400 Z"/>
</g>
</svg>"""

SVG_NO_PATHS = """<?xml version="1.0"?>
<svg xmlns="http://www.w3.org/2000/svg" width="200" height="100" viewBox="0 0 200 100">
<rect width="100%" height="100%" fill="white"/>
</svg>"""


def test_removes_background_rect() -> None:
    result = clean_svg(SAMPLE_SVG)
    root = etree.fromstring(result.encode())
    ns = {"svg": "http://www.w3.org/2000/svg"}
    rects = root.findall(".//svg:rect", ns)
    assert len(rects) == 0


def test_preserves_viewbox() -> None:
    result = clean_svg(SAMPLE_SVG)
    root = etree.fromstring(result.encode())
    assert root.get("viewBox") == "0 0 200 100"


def test_strips_comments() -> None:
    result = clean_svg(SAMPLE_SVG)
    assert "potrace" not in result.lower()
    assert "<!--" not in result


def test_no_paths_raises() -> None:
    with pytest.raises(NoPathsDetectedError):
        clean_svg(SVG_NO_PATHS)


def test_no_width_height_on_root() -> None:
    result = clean_svg(SAMPLE_SVG)
    root = etree.fromstring(result.encode())
    assert root.get("width") is None
    assert root.get("height") is None
    assert root.get("viewBox") is not None


def test_removes_background_rect_no_namespace() -> None:
    svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 100">
<rect width="100%" height="100%" fill="white"/>
<path d="M 100 200 L 300 200 L 300 400 L 100 400 Z"/>
</svg>"""
    result = clean_svg(svg)
    root = etree.fromstring(result.encode())
    rects = root.findall(".//rect")
    assert len(rects) == 0


def test_strips_x_y_from_root() -> None:
    svg = """<svg xmlns="http://www.w3.org/2000/svg" x="10" y="20" viewBox="0 0 200 100">
<path d="M 10 10 L 100 10 L 100 80 L 10 80 Z"/>
</svg>"""
    result = clean_svg(svg)
    root = etree.fromstring(result.encode())
    assert root.get("x") is None
    assert root.get("y") is None


def test_removes_metadata() -> None:
    svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 100">
<metadata>Created by potrace</metadata>
<path d="M 10 10 L 100 10 L 100 80 L 10 80 Z"/>
</svg>"""
    result = clean_svg(svg)
    assert "metadata" not in result.lower()
    assert "potrace" not in result.lower()


def test_strips_fill_from_g() -> None:
    svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 100">
<g fill="#000000" stroke="none">
<path d="M 10 10 L 100 10 L 100 80 L 10 80 Z"/>
</g>
</svg>"""
    result = clean_svg(svg)
    root = etree.fromstring(result.encode())
    ns = {"svg": "http://www.w3.org/2000/svg"}
    for g in root.findall(".//svg:g", ns) + root.findall(".//g"):
        assert g.get("fill") is None
        assert g.get("stroke") is None


def test_strips_version() -> None:
    result = clean_svg(SAMPLE_SVG)
    root = etree.fromstring(result.encode())
    assert root.get("version") is None
