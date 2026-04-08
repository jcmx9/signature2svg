"""SVG optimization: lossless size reduction via scour."""

import scour.scour as scour_mod


def optimize_svg(svg_string: str) -> str:
    """Optimize SVG losslessly using scour.

    Shortens path notation, removes unused IDs/defs, strips editor
    namespaces, collapses empty groups, normalizes numeric precision.

    Args:
        svg_string: SVG string to optimize.

    Returns:
        Optimized SVG string.
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

    # scour may move fill="currentColor" from path attributes into a <style> block
    # or remove redundant attributes — this is expected and lossless
    return str(scour_mod.scourString(svg_string, options))
