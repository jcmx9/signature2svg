"""SVG parametrization: replace fills with currentColor."""

import re

from lxml import etree

SVG_NS = "http://www.w3.org/2000/svg"


def parametrize_svg(svg_string: str) -> str:
    """Replace all path fills with currentColor for external color control.

    Args:
        svg_string: Cleaned SVG string.

    Returns:
        SVG string with all paths using fill="currentColor".
    """
    root = etree.fromstring(svg_string.encode())

    # Process all path elements — set fill="currentColor" on each
    paths = root.findall(".//{%s}path" % SVG_NS) + root.findall(".//path")
    for path in paths:
        path.set("fill", "currentColor")

        # Remove fill from inline style
        style = path.get("style", "")
        if style:
            cleaned = re.sub(r"fill\s*:[^;]+;?\s*", "", style).strip()
            if cleaned:
                path.set("style", cleaned)
            else:
                del path.attrib["style"]

    # Remove existing <style> blocks — keep output minimal per spec
    for style_el in root.findall(".//{%s}style" % SVG_NS) + root.findall(".//style"):
        parent = style_el.getparent()
        if parent is not None:
            parent.remove(style_el)

    # Remove fill and color from root <svg>
    for attr in ("fill", "color"):
        if attr in root.attrib:
            del root.attrib[attr]

    return etree.tostring(root, pretty_print=True, xml_declaration=False).decode()
