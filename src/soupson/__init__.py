"""soupson: pretty-print HTML/XML from the command line."""

from __future__ import annotations

import argparse
import sys
from enum import Enum
from html import escape as html_escape
from pathlib import Path
from typing import Collection

from bs4 import UnicodeDammit
from lxml import etree
from lxml.html import fromstring as html_fromstring, tostring as html_tostring
from lxml.cssselect import CSSSelector


class SelectorType(Enum):
    """Type of selector expression."""

    CSS = "css"
    XPATH = "xpath"


def _parse_selector(expr: str) -> tuple[SelectorType, str]:
    """Detect selector type and normalize expression.

    - Starts with `/` or `!` → XPath (strip leading `!`)
    - Otherwise → CSS selector
    """
    expr = expr.strip()
    if expr.startswith(("!", "/")):
        return SelectorType.XPATH, expr.lstrip("!")
    return SelectorType.CSS, expr


# A configurable set of HTML inline elements. You can override this from
# your own code by importing and mutating HTML_INLINE_TAGS.
HTML_INLINE_TAGS: set[str] = {
    "a",
    "abbr",
    "acronym",
    "b",
    "bdi",
    "bdo",
    "big",
    "br",
    "button",
    "cite",
    "code",
    "data",
    "del",
    "dfn",
    "em",
    "i",
    "img",
    "input",
    "ins",
    "kbd",
    "label",
    "map",
    "mark",
    "object",
    "output",
    "q",
    "ruby",
    "s",
    "samp",
    "script",
    "select",
    "small",
    "span",
    "strong",
    "sub",
    "sup",
    "textarea",
    "time",
    "u",
    "var",
    "wbr",
}

# Tags that should preserve internal whitespace
PRESERVE_WHITESPACE_TAGS: set[str] = {"pre", "script", "style", "textarea"}


def _detect_base_indent(lines: list[str]) -> int:
    """Find the smallest non-zero leading space count."""

    indents = [
        len(line) - len(line.lstrip())
        for line in lines
        if line.strip()
    ]
    positives = [i for i in indents if i > 0]
    return min(positives) if positives else 0


def _reindent(text: str, indent_width: int) -> str:
    """Re-indent a prettified string to the requested width."""

    lines = text.splitlines()
    if indent_width < 0:
        indent_width = 0

    base = _detect_base_indent(lines)
    if base == 0 or indent_width == base:
        return text

    adjusted: list[str] = []
    for line in lines:
        stripped = line.lstrip()
        if stripped:
            depth = (len(line) - len(stripped)) // base
            adjusted.append(" " * (depth * indent_width) + stripped)
        else:
            adjusted.append("" if line else line)

    return "\n".join(adjusted)


def _read_input(path: str | None, encoding: str | None) -> str:
    """Read input from a file or stdin, decoding with a given or guessed encoding."""

    raw: bytes
    if path:
        raw = Path(path).read_bytes()
    else:
        # stdin may already be text, but .buffer ensures bytes either way.
        raw = sys.stdin.buffer.read()

    if encoding:
        return raw.decode(encoding, errors="replace")

    dammit = UnicodeDammit(raw)
    if dammit.unicode_markup:
        return dammit.unicode_markup

    # Fallback if detection fails.
    return raw.decode("utf-8", errors="replace")


def _write_output(path: str | None, content: str, encoding: str) -> None:
    data = content.encode(encoding, errors="replace")
    if path:
        Path(path).write_bytes(data)
    else:
        sys.stdout.buffer.write(data)


def _lxml_unwrap(element) -> None:
    """Remove an lxml element while preserving its children and text.

    Equivalent to BeautifulSoup's Tag.unwrap().
    """
    parent = element.getparent()
    if parent is None:
        return  # Cannot unwrap root element

    index = list(parent).index(element)

    # Handle element's text (goes before first child or to parent/prev sibling)
    if element.text:
        if index > 0:
            prev_sibling = parent[index - 1]
            prev_sibling.tail = (prev_sibling.tail or "") + element.text
        else:
            parent.text = (parent.text or "") + element.text

    # Move all children to parent at element's position
    children = list(element)
    for i, child in enumerate(children):
        parent.insert(index + i, child)

    # Handle element's tail text
    if element.tail:
        if children:
            children[-1].tail = (children[-1].tail or "") + element.tail
        elif index > 0:
            prev_sibling = parent[index - 1]
            prev_sibling.tail = (prev_sibling.tail or "") + element.tail
        else:
            parent.text = (parent.text or "") + element.tail

    parent.remove(element)


def _apply_css_removal(tree, selector: str, recursive: bool) -> None:
    """Apply CSS selector removal to lxml tree."""
    try:
        css = CSSSelector(selector)
    except Exception as e:
        raise ValueError(f"Invalid CSS selector '{selector}': {e}") from e

    for elem in reversed(css(tree)):
        if recursive:
            parent = elem.getparent()
            if parent is not None:
                parent.remove(elem)
        else:
            _lxml_unwrap(elem)


def _apply_xpath_removal(tree, xpath: str, recursive: bool) -> None:
    """Apply XPath removal to lxml tree.

    Handles elements and attributes via lxml's smart string results.
    """
    try:
        results = tree.xpath(xpath)
    except Exception as e:
        raise ValueError(f"Invalid XPath expression '{xpath}': {e}") from e

    for result in reversed(list(results)):
        # Attribute result (lxml returns smart strings with metadata)
        if hasattr(result, "is_attribute") and result.is_attribute:
            parent = result.getparent()
            if parent is not None and result.attrname in parent.attrib:
                del parent.attrib[result.attrname]
        # Element result
        elif hasattr(result, "getparent") and hasattr(result, "tag"):
            if recursive:
                parent = result.getparent()
                if parent is not None:
                    parent.remove(result)
            else:
                _lxml_unwrap(result)


def _format_open_tag(elem, html_format: bool = True) -> str:
    """Format an opening tag with attributes."""
    tag_name = elem.tag if isinstance(elem.tag, str) else "unknown"

    attrs = []
    for key, value in elem.attrib.items():
        if value is None:
            attrs.append(key)
        else:
            escaped = html_escape(value, quote=True)
            attrs.append(f'{key}="{escaped}"')

    if attrs:
        return f"<{tag_name} {' '.join(attrs)}>"
    return f"<{tag_name}>"


def _format_close_tag(elem) -> str:
    """Format a closing tag."""
    tag_name = elem.tag if isinstance(elem.tag, str) else "unknown"
    return f"</{tag_name}>"


def _is_void_element(tag_name: str) -> bool:
    """Check if an HTML tag is a void element (self-closing)."""
    return tag_name.lower() in {
        "area", "base", "br", "col", "embed", "hr", "img", "input",
        "link", "meta", "param", "source", "track", "wbr"
    }


def _inline_aware_prettify(
    tree,
    indent_str: str = "  ",
    inline_tag_set: Collection[str] | None = None,
    html_format: bool = True,
) -> str:
    """Pretty-print HTML/XML while keeping inline elements on a single line.

    Works directly with lxml elements.
    """
    # Normalize the inline tag set.
    if inline_tag_set is None:
        inline_tag_names: set[str] = {name.lower() for name in HTML_INLINE_TAGS}
    else:
        inline_tag_names = {name.lower() for name in inline_tag_set}

    lines: list[str] = []

    def get_tag_name(elem) -> str:
        return elem.tag.lower() if isinstance(elem.tag, str) else ""

    def is_inline_tag(elem) -> bool:
        return get_tag_name(elem) in inline_tag_names

    def is_literal_tag(elem) -> bool:
        return get_tag_name(elem) in PRESERVE_WHITESPACE_TAGS

    def indent(depth: int) -> str:
        if depth <= 0:
            return ""
        return indent_str * depth

    def collapse_whitespace(text: str) -> str:
        """Collapse runs of whitespace to single spaces."""
        result_chars: list[str] = []
        saw_space = False
        for ch in text:
            if ch.isspace():
                if not saw_space:
                    result_chars.append(" ")
                    saw_space = True
            else:
                result_chars.append(ch)
                saw_space = False
        return "".join(result_chars)

    # Inline rendering -----------------------------------------------------

    def render_inline(elem) -> str:
        """Render an element and its descendants without line breaks."""
        tag_name = get_tag_name(elem)

        # Literal tags keep contents as-is
        if is_literal_tag(elem):
            return html_tostring(elem, encoding="unicode")

        parts: list[str] = []

        # Opening tag
        if html_format and _is_void_element(tag_name):
            parts.append(_format_open_tag(elem, html_format))
        else:
            parts.append(_format_open_tag(elem, html_format))

            # Text content
            if elem.text:
                parts.append(html_escape(collapse_whitespace(elem.text)))

            # Children
            for child in elem:
                parts.append(render_inline(child))
                if child.tail:
                    parts.append(html_escape(collapse_whitespace(child.tail)))

            # Closing tag
            if not (html_format and _is_void_element(tag_name)):
                parts.append(_format_close_tag(elem))

        return "".join(parts)

    # Block rendering ------------------------------------------------------

    def render_block(elem, depth: int) -> None:
        """Render a block element with proper indentation."""
        tag_name = get_tag_name(elem)

        # Literal tags: don't reflow internal whitespace
        if is_literal_tag(elem):
            lines.append(indent(depth) + _format_open_tag(elem, html_format))
            inner = (elem.text or "") + "".join(
                html_tostring(child, encoding="unicode") + (child.tail or "")
                for child in elem
            )
            if inner:
                for raw_line in inner.splitlines():
                    lines.append(indent(depth + 1) + raw_line)
            lines.append(indent(depth) + _format_close_tag(elem))
            return

        # Void elements
        if html_format and _is_void_element(tag_name):
            lines.append(indent(depth) + _format_open_tag(elem, html_format))
            return

        lines.append(indent(depth) + _format_open_tag(elem, html_format))

        inline_buffer: list[str] = []

        # Handle text before first child
        if elem.text and elem.text.strip():
            inline_buffer.append(html_escape(collapse_whitespace(elem.text)))

        for child in elem:
            if not is_inline_tag(child):
                # Flush inline buffer
                inline_line = "".join(inline_buffer).strip()
                if inline_line:
                    lines.append(indent(depth + 1) + inline_line)
                    inline_buffer.clear()
                render_block(child, depth + 1)
                # Handle tail text after block child
                if child.tail and child.tail.strip():
                    inline_buffer.append(html_escape(collapse_whitespace(child.tail)))
            else:
                # Inline element
                inline_buffer.append(render_inline(child))
                if child.tail:
                    inline_buffer.append(html_escape(collapse_whitespace(child.tail)))

        # Flush remaining inline content
        inline_line = "".join(inline_buffer).strip()
        if inline_line:
            lines.append(indent(depth + 1) + inline_line)

        lines.append(indent(depth) + _format_close_tag(elem))

    # Root handling --------------------------------------------------------

    # Handle the root element
    render_block(tree, depth=0)

    return "\n".join(lines)


class _AppendRemoval(argparse.Action):
    """Custom action to collect -r and -R removals in order."""

    def __call__(self, parser, namespace, values, option_string=None):
        if not hasattr(namespace, "all_removals") or namespace.all_removals is None:
            namespace.all_removals = []
        # Track whether this is recursive (-R) or unwrap (-r)
        recursive = option_string in ("-R", "--re-remove")
        namespace.all_removals.append((values, recursive))


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="soupson",
        description="Stew HTML/XML and serve it back neatly indented.",
    )
    parser.add_argument("infile", nargs="?", help="Input file (default: stdin)")
    parser.add_argument("outfile", nargs="?", help="Output file (default: stdout)")
    parser.add_argument(
        "-i",
        "--indent",
        type=int,
        default=2,
        help="Number of spaces to use for indentation (default: 2)",
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=["xml", "html"],
        default="html",
        help="Output tag format (default: html)",
    )
    parser.add_argument(
        "-e",
        "--encoding",
        dest="encoding",
        help="Interpret input using this character encoding (default: guess)",
    )
    parser.add_argument(
        "-E",
        "--out-encoding",
        dest="out_encoding",
        default="utf-8",
        help="Output using this character encoding (default: UTF-8)",
    )
    parser.add_argument(
        "-r",
        "--remove",
        action=_AppendRemoval,
        metavar="EXPR",
        help="Remove matching elements but keep children (unwrap). "
        "CSS by default; XPath if starts with / or !",
    )
    parser.add_argument(
        "-R",
        "--re-remove",
        action=_AppendRemoval,
        metavar="EXPR",
        help="Remove matching elements and all descendants (recursive). "
        "CSS by default; XPath if starts with / or !",
    )
    parser.add_argument(
        "--pretty-inline",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "Keep inline elements and their text on a single line "
            "(default: enabled; disable with --no-pretty-inline)"
        ),
    )

    args = parser.parse_args()

    source_text = _read_input(args.infile, args.encoding)

    # Parse with lxml
    if args.format == "xml":
        tree = etree.fromstring(source_text.encode("utf-8"))
    else:
        tree = html_fromstring(source_text)

    # Get all removals (list of (expr, recursive) tuples)
    all_removals: list[tuple[str, bool]] = getattr(args, "all_removals", None) or []

    # Apply removals in command-line order
    for expr, recursive in all_removals:
        selector_type, selector = _parse_selector(expr)
        if selector_type == SelectorType.CSS:
            _apply_css_removal(tree, selector, recursive)
        else:
            _apply_xpath_removal(tree, selector, recursive)

    # Pretty print
    if args.pretty_inline and args.format == "html":
        pretty_raw = _inline_aware_prettify(
            tree,
            indent_str="  ",
            html_format=True,
        )
    else:
        # Use lxml's built-in pretty print
        etree.indent(tree, space="  ")
        if args.format == "xml":
            pretty_raw = etree.tostring(tree, encoding="unicode")
        else:
            pretty_raw = html_tostring(tree, encoding="unicode")

    pretty = _reindent(pretty_raw, args.indent)

    _write_output(args.outfile, pretty, args.out_encoding)


if __name__ == "__main__":
    main()
