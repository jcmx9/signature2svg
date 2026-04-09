"""SVG optimization: lossless size reduction via scour."""

import re

from lxml import etree

import scour.scour as scour_mod

SVG_NS = "http://www.w3.org/2000/svg"


def optimize_svg(svg_string: str) -> str:
    """Optimize SVG losslessly using scour, then restore currentColor on paths.

    Scour may consolidate fill="currentColor" from path attributes into a
    <style> block. This function re-applies fill="currentColor" as path
    attributes and removes any <style> blocks to keep the output minimal
    and compatible with Typst/HTML embedding.
    """
    options = scour_mod.generateDefaultOptions()
    options.strip_xml_prolog = True
    options.remove_metadata = True
    options.strip_comments = True
    options.shorten_ids = True
    options.indent_type = "none"
    options.newlines = False
    options.strip_xml_space_attribute = True
    options.remove_descriptive_elements = True
    options.enable_viewboxing = True

    optimized = str(scour_mod.scourString(svg_string, options))

    # Post-scour fixup: ensure fill="currentColor" stays on path attributes
    root = etree.fromstring(optimized.encode())

    for path in root.findall(".//{%s}path" % SVG_NS) + root.findall(".//path"):
        path.set("fill", "currentColor")
        # Remove fill from inline style if scour moved it there
        style = path.get("style", "")
        if style:
            cleaned = re.sub(r"fill\s*:[^;]+;?\s*", "", style).strip()
            if cleaned:
                path.set("style", cleaned)
            else:
                del path.attrib["style"]

    # Remove <style> blocks that scour may have created
    for style_el in root.findall(".//{%s}style" % SVG_NS) + root.findall(".//style"):
        parent = style_el.getparent()
        if parent is not None:
            parent.remove(style_el)

    return etree.tostring(root, pretty_print=False, xml_declaration=False).decode()
