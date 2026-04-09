"""SVG cleaning: remove backgrounds, strip metadata, clean up Potrace output."""

import re

from lxml import etree

from signature2svg.exceptions import NoPathsDetectedError

SVG_NS = "http://www.w3.org/2000/svg"


def clean_svg(svg_string: str) -> str:
    """Clean a raw Potrace SVG: remove backgrounds, strip metadata, tidy attributes.

    The viewBox from Potrace is preserved — it matches the input image dimensions,
    which are already tight-cropped in the preprocessing step.

    Args:
        svg_string: Raw SVG string from Potrace.

    Returns:
        Cleaned SVG string.

    Raises:
        NoPathsDetectedError: If no path elements are found.
    """
    parser = etree.XMLParser(remove_comments=True)
    root = etree.fromstring(svg_string.encode(), parser)

    # Remove <metadata> elements
    for meta in root.findall(".//{%s}metadata" % SVG_NS) + root.findall(".//metadata"):
        parent = meta.getparent()
        if parent is not None:
            parent.remove(meta)

    # Remove background rects
    for rect in root.findall(".//{%s}rect" % SVG_NS) + root.findall(".//rect"):
        fill = rect.get("fill", "").lower()
        if fill in ("white", "#fff", "#ffffff"):
            parent = rect.getparent()
            if parent is not None:
                parent.remove(rect)

    # Strip fill/stroke from <g> elements (Potrace sets fill="#000000" stroke="none" on groups)
    for g in root.findall(".//{%s}g" % SVG_NS) + root.findall(".//g"):
        for attr in ("fill", "stroke"):
            if attr in g.attrib:
                del g.attrib[attr]

    # Check that paths exist
    paths_els = root.findall(".//{%s}path" % SVG_NS) + root.findall(".//path")
    if not paths_els:
        raise NoPathsDetectedError()

    # Remove width/height so SVG scales freely; keep viewBox from Potrace
    for attr in ("width", "height", "x", "y", "version"):
        if attr in root.attrib:
            del root.attrib[attr]

    # Clean up floating-point noise in transform attributes
    for g in root.findall(".//{%s}g" % SVG_NS) + root.findall(".//g"):
        transform = g.get("transform", "")
        if transform:
            cleaned = re.sub(r"-0\.0\b", "0", transform)
            cleaned = re.sub(r"(\d+)\.0+(?=[\s,)])", r"\1", cleaned)
            g.set("transform", cleaned)

    result = etree.tostring(root, pretty_print=True, xml_declaration=False).decode()
    return result
