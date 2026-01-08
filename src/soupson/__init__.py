"""soupson: pretty-print HTML/XML from the command line."""

from __future__ import annotations

import argparse
import sys
from enum import Enum
from pathlib import Path
from typing import Iterable, Collection

from bs4 import BeautifulSoup, UnicodeDammit

# Optional lxml import for XPath support
try:
    from lxml import etree as lxml_etree
    from lxml.html import document_fromstring as lxml_html_fromstring
    from lxml.html import tostring as lxml_html_tostring

    LXML_AVAILABLE = True
except ImportError:
    lxml_etree = None  # type: ignore[assignment]
    lxml_html_fromstring = None  # type: ignore[assignment]
    lxml_html_tostring = None  # type: ignore[assignment]
    LXML_AVAILABLE = False
from bs4.element import Tag, NavigableString
from bs4.formatter import Formatter


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


def _select_parser(prefer_xml: bool) -> str:
    """Pick the best available BeautifulSoup parser for the requested format."""

    candidates: Iterable[str]
    if prefer_xml:
        candidates = ("lxml-xml", "xml")
    else:
        candidates = ("lxml", "html.parser")

    for parser in candidates:
        try:
            # Instantiation with an empty doc is cheap; parser availability is the
            # important part here.
            BeautifulSoup("", parser)
        except Exception:
            continue
        return parser

    raise RuntimeError("No suitable parser available. Install 'lxml' to continue.")


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


def _apply_css_removal(soup: BeautifulSoup, selector: str, recursive: bool) -> None:
    """Apply CSS selector removal to BeautifulSoup tree."""
    for tag in list(soup.select(selector)):
        if recursive:
            tag.decompose()
        else:
            tag.unwrap()


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


def _parser_available(name: str) -> bool:
    try:
        BeautifulSoup("", name)
    except Exception:
        return False
    return True


def _inline_aware_prettify(
    soup: BeautifulSoup,
    formatter: str | Formatter,
    inline_tag_set: Collection[str] | None = None,
) -> str:
    """Pretty-print HTML while keeping inline elements on a single line.

    This reuses BeautifulSoup's tag and attribute formatting but changes
    how indentation and newlines are applied so that inline tags (and
    their text) are rendered together instead of being split across
    multiple lines.
    """

    # Resolve formatter name to a Formatter instance, like Tag.decode does.
    if not isinstance(formatter, Formatter):
        # BeautifulSoup/Tag exposes formatter_for_name; type ignore because
        # the stubs don't declare it on BeautifulSoup.
        formatter = soup.formatter_for_name(formatter)  # type: ignore[attr-defined]

    # Normalize the inline tag set.
    if inline_tag_set is None:
        inline_tag_names: set[str] = {name.lower() for name in HTML_INLINE_TAGS}
    else:
        inline_tag_names = {name.lower() for name in inline_tag_set}

    # Tags like <pre>, <script>, <style> should preserve their internal
    # whitespace; BS tracks them on the Tag class.
    preserve_whitespace = getattr(soup, "preserve_whitespace_tags", set()) or set()

    lines: list[str] = []
    indent_unit = formatter.indent

    def is_inline_tag(node: object) -> bool:
        return isinstance(node, Tag) and (node.name or "").lower() in inline_tag_names

    def is_literal_tag(node: object) -> bool:
        return isinstance(node, Tag) and node.name in preserve_whitespace

    def indent(depth: int) -> str:
        if depth <= 0:
            return ""
        return indent_unit * depth

    # Inline rendering -----------------------------------------------------

    def render_inline(node: object) -> str:
        # Render a node and its descendants without introducing line breaks.
        if isinstance(node, NavigableString):
            text = node.output_ready(formatter)
            # Collapse runs of whitespace but preserve whether whitespace
            # exists at the ends.
            # Using split / join here would drop leading/trailing spaces, so
            # do a manual pass.
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

        if not isinstance(node, Tag):
            return str(node)

        # Literal tags (e.g. <pre>) keep their contents as-is.
        if is_literal_tag(node):
            return str(node)

        # Treat everything else as inline here, even if it's structurally
        # block-ish – HTML disallows blocks inside inline contexts anyway.
        # We intentionally flatten nested inline tags.
        # BeautifulSoup's internal helpers give us consistent tag markup.
        from bs4.element import Tag as _Tag  # Local import to satisfy type checkers

        tag = node
        # `_format_tag` uses an eventual encoding mainly for charset
        # substitution; utf-8 is fine for CLI output before re-encoding.
        piece_open = tag._format_tag("utf-8", formatter, opening=True)  # type: ignore[attr-defined]
        children_parts: list[str] = []
        for child in tag.children:
            children_parts.append(render_inline(child))
        piece_close = tag._format_tag("utf-8", formatter, opening=False)  # type: ignore[attr-defined]
        return piece_open + "".join(children_parts) + piece_close

    # Block rendering ------------------------------------------------------

    def render_block(tag: Tag, depth: int) -> None:
        # Literal tags: don't reflow internal whitespace.
        if is_literal_tag(tag):
            open_piece = tag._format_tag("utf-8", formatter, opening=True)  # type: ignore[attr-defined]
            lines.append(indent(depth) + open_piece)
            inner = "".join(str(c) for c in tag.contents)
            if inner:
                for raw_line in inner.splitlines():
                    lines.append(indent(depth + 1) + raw_line)
            close_piece = tag._format_tag("utf-8", formatter, opening=False)  # type: ignore[attr-defined]
            lines.append(indent(depth) + close_piece)
            return

        open_piece = tag._format_tag("utf-8", formatter, opening=True)  # type: ignore[attr-defined]
        lines.append(indent(depth) + open_piece)

        inline_buffer_parts: list[str] = []

        for child in tag.children:
            # Ignore pure-whitespace nodes between blocks; they don't carry
            # semantic information and just clutter output.
            if isinstance(child, NavigableString) and not child.strip():
                continue

            if isinstance(child, Tag) and not is_inline_tag(child):
                # Child is a (non-literal) block — flush any accumulated
                # inline content as its own line, then recurse.
                inline_line = "".join(inline_buffer_parts).strip()
                if inline_line:
                    lines.append(indent(depth + 1) + inline_line)
                    inline_buffer_parts.clear()
                render_block(child, depth + 1)
            else:
                # Inline or text node — keep appending to the current line.
                inline_buffer_parts.append(render_inline(child))

        inline_line = "".join(inline_buffer_parts).strip()
        if inline_line:
            lines.append(indent(depth + 1) + inline_line)

        close_piece = tag._format_tag("utf-8", formatter, opening=False)  # type: ignore[attr-defined]
        lines.append(indent(depth) + close_piece)

    # Root traversal -------------------------------------------------------

    # Top-level: interleave block tags and inline/text segments.
    pending_inline: list[str] = []
    for node in soup.contents:
        if isinstance(node, Tag) and not is_inline_tag(node):
            inline_line = "".join(pending_inline).strip()
            if inline_line:
                lines.append(inline_line)
                pending_inline.clear()
            render_block(node, depth=0)
        else:
            pending_inline.append(render_inline(node))

    inline_line = "".join(pending_inline).strip()
    if inline_line:
        lines.append(inline_line)

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
        "-p",
        "--parser",
        choices=[
            "auto",
            "html.parser",
            "lxml",
            "html5lib",
            "xml",
            "lxml-xml",
        ],
        default="auto",
        help="Force a specific BeautifulSoup backend; default picks automatically",
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

    # Get all removals (list of (expr, recursive) tuples)
    all_removals: list[tuple[str, bool]] = getattr(args, "all_removals", None) or []

    # Check if any removals use XPath
    has_xpath = any(
        _parse_selector(expr)[0] == SelectorType.XPATH for expr, _ in all_removals
    )

    # Validate XPath requirements
    if has_xpath:
        if not LXML_AVAILABLE:
            parser.error(
                "XPath expressions require lxml. Install it with: pip install lxml"
            )
        lxml_parsers = {"lxml", "lxml-xml", "xml"}
        if args.parser != "auto" and args.parser not in lxml_parsers:
            parser.error(
                f"XPath expressions require an lxml-based parser "
                f"(lxml, lxml-xml, or xml), not '{args.parser}'."
            )

    if args.parser != "auto":
        if not _parser_available(args.parser):
            parser.error(
                f"Parser '{args.parser}' is not available. Install its dependency "
                "(e.g., 'lxml' or 'html5lib') and try again."
            )
        parser_name = args.parser
    else:
        # Force lxml if XPath is used
        if has_xpath:
            parser_name = "lxml-xml" if args.format == "xml" else "lxml"
        else:
            parser_name = _select_parser(args.format == "xml")

    soup = BeautifulSoup(source_text, parser_name)

    # Apply removals in command-line order
    lxml_tree = None
    for expr, recursive in all_removals:
        selector_type, selector = _parse_selector(expr)
        if selector_type == SelectorType.CSS:
            _apply_css_removal(soup, selector, recursive)
        else:
            # XPath: need to work with lxml tree
            if lxml_tree is None:
                # Convert soup to lxml tree
                if args.format == "xml":
                    lxml_tree = lxml_etree.fromstring(str(soup).encode("utf-8"))
                else:
                    lxml_tree = lxml_html_fromstring(str(soup))
            _apply_xpath_removal(lxml_tree, selector, recursive)

    # If we used XPath, convert lxml tree back to BeautifulSoup
    if lxml_tree is not None:
        if args.format == "xml":
            modified_markup = lxml_etree.tostring(lxml_tree, encoding="unicode")
        else:
            modified_markup = lxml_html_tostring(lxml_tree, encoding="unicode")
        soup = BeautifulSoup(modified_markup, parser_name)

    formatter = "html" if args.format == "html" else "minimal"
    if args.pretty_inline and args.format == "html":
        pretty_raw = _inline_aware_prettify(soup, formatter=formatter)
    else:
        pretty_raw = soup.prettify(formatter=formatter)
    pretty = _reindent(pretty_raw, args.indent)

    _write_output(args.outfile, pretty, args.out_encoding)


if __name__ == "__main__":
    main()
