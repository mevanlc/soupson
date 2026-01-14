"""soupson: pretty-print HTML/XML from the command line."""

from __future__ import annotations

import argparse
import re
import sys
from html import escape as html_escape
from pathlib import Path
from typing import Collection

from charset_normalizer import from_bytes as detect_encoding
from lxml import etree
from lxml.html import (
    document_fromstring as html_document_fromstring,
    fromstring as html_fromstring,
    tostring as html_tostring,
)
from lxml.cssselect import CSSSelector


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


def _read_input(path: str | None, charset: str | None) -> str:
    """Read input from a file or stdin, decoding with a given or guessed charset."""

    raw: bytes
    if path:
        raw = Path(path).read_bytes()
    else:
        # stdin may already be text, but .buffer ensures bytes either way.
        raw = sys.stdin.buffer.read()

    if charset:
        return raw.decode(charset, errors="replace")

    # Use charset-normalizer for encoding detection
    result = detect_encoding(raw).best()
    if result is not None:
        return str(result)

    # Fallback if detection fails.
    return raw.decode("utf-8", errors="replace")


def _write_output(path: str | None, content: str, charset: str) -> None:
    data = content.encode(charset, errors="replace")
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


def _remove_element(elem, recursive: bool) -> None:
    """Remove an element, either recursively or by unwrapping."""
    if recursive:
        parent = elem.getparent()
        if parent is not None:
            parent.remove(elem)
    else:
        _lxml_unwrap(elem)


def _apply_css_removal(tree, selector: str, recursive: bool) -> None:
    """Apply CSS selector removal to lxml tree."""
    try:
        css = CSSSelector(selector)
    except Exception as e:
        raise ValueError(f"Invalid CSS selector '{selector}': {e}") from e

    for elem in reversed(css(tree)):
        _remove_element(elem, recursive)


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
            _remove_element(result, recursive)


def _apply_regex_removal(tree, target: str, pattern: str, recursive: bool) -> None:
    """Apply regex-based removal to lxml tree.

    Args:
        tree: lxml tree to modify
        target: 'e' for element names, 'a' for attr names, 'v' for attr values
        pattern: regex pattern to match
        recursive: for elements, whether to remove children too
    """
    try:
        regex = re.compile(pattern)
    except re.error as e:
        raise ValueError(f"Invalid regex pattern '{pattern}': {e}") from e

    if target == "e":
        # Match element names
        for elem in reversed(list(tree.iter())):
            if isinstance(elem.tag, str) and regex.search(elem.tag):
                _remove_element(elem, recursive)
    elif target == "a":
        # Match attribute names
        for elem in tree.iter():
            if not isinstance(elem.tag, str):
                continue
            to_remove = [name for name in elem.attrib if regex.search(name)]
            for name in to_remove:
                del elem.attrib[name]
    elif target == "v":
        # Match attribute values
        for elem in tree.iter():
            if not isinstance(elem.tag, str):
                continue
            to_remove = [
                name for name, value in elem.attrib.items()
                if regex.search(value)
            ]
            for name in to_remove:
                del elem.attrib[name]
    else:
        raise ValueError(f"Invalid regex target '{target}': must be 'e', 'a', or 'v'")


def _apply_xpath_substitution(tree, xpath: str, pattern: str, replacement: str) -> None:
    """Apply substitution to attribute values matched by XPath.

    Args:
        tree: lxml tree to modify
        xpath: XPath expression selecting attributes (e.g., //@href)
        pattern: regex pattern to find
        replacement: replacement string (supports backreferences)
    """
    try:
        regex = re.compile(pattern)
    except re.error as e:
        raise ValueError(f"Invalid regex pattern '{pattern}': {e}") from e

    try:
        results = tree.xpath(xpath)
    except Exception as e:
        raise ValueError(f"Invalid XPath expression '{xpath}': {e}") from e

    for result in results:
        # Attribute result (lxml returns smart strings with metadata)
        if hasattr(result, "is_attribute") and result.is_attribute:
            parent = result.getparent()
            attrname = result.attrname
            if parent is not None and attrname in parent.attrib:
                old_value = parent.attrib[attrname]
                new_value = regex.sub(replacement, old_value)
                parent.attrib[attrname] = new_value


def _apply_css_substitution(
    tree, selector: str, attr: str, pattern: str, replacement: str
) -> None:
    """Apply substitution to attribute values on elements matched by CSS selector.

    Args:
        tree: lxml tree to modify
        selector: CSS selector to match elements
        attr: attribute name to modify on matched elements
        pattern: regex pattern to find
        replacement: replacement string (supports backreferences)
    """
    try:
        regex = re.compile(pattern)
    except re.error as e:
        raise ValueError(f"Invalid regex pattern '{pattern}': {e}") from e

    try:
        css = CSSSelector(selector)
    except Exception as e:
        raise ValueError(f"Invalid CSS selector '{selector}': {e}") from e

    for elem in css(tree):
        if attr in elem.attrib:
            old_value = elem.attrib[attr]
            new_value = regex.sub(replacement, old_value)
            elem.attrib[attr] = new_value


def _apply_regex_substitution(tree, target: str, pattern: str, replacement: str) -> None:
    """Apply regex-based substitution to lxml tree.

    Args:
        tree: lxml tree to modify
        target: 'e' for element names, 'a' for attr names, 'v' for attr values
        pattern: regex pattern to find
        replacement: replacement string (supports backreferences)
    """
    try:
        regex = re.compile(pattern)
    except re.error as e:
        raise ValueError(f"Invalid regex pattern '{pattern}': {e}") from e

    if target == "e":
        # Substitute in element names (rename tags)
        for elem in tree.iter():
            if isinstance(elem.tag, str) and regex.search(elem.tag):
                elem.tag = regex.sub(replacement, elem.tag)
    elif target == "a":
        # Substitute in attribute names (rename attributes)
        for elem in tree.iter():
            if not isinstance(elem.tag, str):
                continue
            # Build new attrib dict with renamed keys
            new_attrib = {}
            for name, value in list(elem.attrib.items()):
                new_name = regex.sub(replacement, name)
                new_attrib[new_name] = value
            elem.attrib.clear()
            elem.attrib.update(new_attrib)
    elif target == "v":
        # Substitute in attribute values
        for elem in tree.iter():
            if not isinstance(elem.tag, str):
                continue
            for name, value in elem.attrib.items():
                if regex.search(value):
                    elem.attrib[name] = regex.sub(replacement, value)
    else:
        raise ValueError(f"Invalid regex target '{target}': must be 'e', 'a', or 'v'")


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
    """Custom action to collect removals in command-line order."""

    def __call__(self, parser, namespace, values, option_string=None):
        if not hasattr(namespace, "all_removals") or namespace.all_removals is None:
            namespace.all_removals = []

        # Determine removal type and recursive flag from option string
        # -rx/-rrx = xpath, -rs/-rrs = css, -re/-rre = regex
        if option_string.startswith("-rr"):
            recursive = True
            suffix = option_string[3:]  # after "-rr"
        else:
            recursive = False
            suffix = option_string[2:]  # after "-r"

        if suffix == "x":
            removal = ("xpath", values, recursive)
        elif suffix == "s":
            removal = ("css", values, recursive)
        elif suffix == "e":
            # values is a list: [target, pattern]
            removal = ("regex", (values[0], values[1]), recursive)
        else:
            raise ValueError(f"Unknown removal option: {option_string}")

        namespace.all_removals.append(removal)


class _AppendSubstitution(argparse.Action):
    """Custom action to collect substitutions in command-line order."""

    def __call__(self, parser, namespace, values, option_string=None):
        if not hasattr(namespace, "all_substitutions") or namespace.all_substitutions is None:
            namespace.all_substitutions = []

        # -sx = xpath, -sc = css, -se = regex
        suffix = option_string[2:]  # after "-s"

        if suffix == "x":
            # values: [xpath, pattern, replacement]
            sub = ("xpath", values[0], values[1], values[2])
        elif suffix == "c":
            # values: [selector, attr, pattern, replacement]
            sub = ("css", values[0], values[1], values[2], values[3])
        elif suffix == "e":
            # values: [target, pattern, replacement]
            sub = ("regex", values[0], values[1], values[2])
        else:
            raise ValueError(f"Unknown substitution option: {option_string}")

        namespace.all_substitutions.append(sub)


def _trace(*args, **kwargs):
    """Print trace info if SOUPSON_TRACE is set."""
    import os
    if os.environ.get("SOUPSON_TRACE"):
        print("[TRACE]", *args, **kwargs, file=sys.stderr)


def main() -> None:
    _trace("argv:", sys.argv)

    parser = argparse.ArgumentParser(
        prog="soupson",
        description="Stew HTML/XML and serve it back cooked to order.",
    )
    parser.add_argument("infile", nargs="?", help="Input file (default: stdin)")
    parser.add_argument("outfile", nargs="?", help="Output file (default: stdout)")
    parser.add_argument(
        "-i",
        dest="indent",
        type=int,
        default=2,
        help="Number of spaces to use for indentation (default: 2)",
    )
    parser.add_argument(
        "-f",
        choices=["xml", "html", "ht"],
        default="ht",
        dest="format",
        help="Output format: html (full document), ht (fragment), xml (default: ht)",
    )
    parser.add_argument(
        "-c",
        metavar="NAME",
        dest="charset",
        help="Interpret input using this character set (default: guess)",
    )
    parser.add_argument(
        "-C",
        dest="out_charset",
        metavar="NAME",
        default="utf-8",
        help="Output using this character set (default: UTF-8)",
    )

    # XPath removals
    parser.add_argument(
        "-rx",
        action=_AppendRemoval,
        metavar=" XPATH",
        help="Remove elements matching XPath (unwrap, keep children)",
    )
    parser.add_argument(
        "-rrx",
        action=_AppendRemoval,
        metavar="XPATH",
        help="Remove elements matching XPath (recursive, remove children too)",
    )

    # CSS selector removals
    parser.add_argument(
        "-rs",
        action=_AppendRemoval,
        metavar=" SELECTOR",
        help="Remove elements matching CSS selector (unwrap, keep children)",
    )
    parser.add_argument(
        "-rrs",
        action=_AppendRemoval,
        metavar="SELECTOR",
        help="Remove elements matching CSS selector (recursive, remove children too)",
    )

    # Regex removals
    parser.add_argument(
        "-re",
        action=_AppendRemoval,
        nargs=2,
        metavar=(" TARGET", "PATTERN"),
        help="Remove by regex (unwrap). TARGET: e=element name, a=attr name, v=attr value",
    )
    parser.add_argument(
        "-rre",
        action=_AppendRemoval,
        nargs=2,
        metavar=("TARGET", "PATTERN"),
        help="Remove by regex (recursive). TARGET: e=element name, a=attr name, v=attr value",
    )

    # XPath substitutions
    parser.add_argument(
        "-sx",
        action=_AppendSubstitution,
        nargs=3,
        metavar=("XPATH", "PATT", "REPL"),
        help="Substitute in attribute values matched by XPath",
    )

    # CSS selector substitutions
    parser.add_argument(
        "-sc",
        action=_AppendSubstitution,
        nargs=4,
        metavar=("SEL", "ATTR", "PAT", "REP"),
        help="Substitute in attribute values of elements matched by CSS selector",
    )

    # Regex substitutions
    parser.add_argument(
        "-se",
        action=_AppendSubstitution,
        nargs=3,
        metavar=("TARGET", "PATT", "REPL"),
        help="Substitute by regex. TARGET: e=element name, a=attr name, v=attr value",
    )

    parser.add_argument(
        "--inl",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "Keep inline elements and their text on a single line "
            "(default: enabled; disable with --no-inl)"
        ),
    )

    args = parser.parse_args()
    _trace("parsed args:", args)
    _trace("all_removals:", getattr(args, "all_removals", None))
    _trace("all_substitutions:", getattr(args, "all_substitutions", None))

    source_text = _read_input(args.infile, args.charset)

    # Parse with lxml
    if args.format == "xml":
        tree = etree.fromstring(source_text.encode("utf-8"))
    elif args.format == "html":
        # Full document mode - ensure <html><body> structure
        tree = html_document_fromstring(source_text)
    else:  # ht
        # Fragment mode - preserve input structure
        tree = html_fromstring(source_text)

    # Get all removals (list of (type, value(s), recursive) tuples)
    all_removals = getattr(args, "all_removals", None) or []

    # Apply removals in command-line order
    for removal_type, value, recursive in all_removals:
        if removal_type == "xpath":
            _apply_xpath_removal(tree, value, recursive)
        elif removal_type == "css":
            _apply_css_removal(tree, value, recursive)
        elif removal_type == "regex":
            target, pattern = value
            _apply_regex_removal(tree, target, pattern, recursive)

    # Get all substitutions
    all_substitutions = getattr(args, "all_substitutions", None) or []

    # Apply substitutions in command-line order
    _trace("applying substitutions:", all_substitutions)
    for sub in all_substitutions:
        sub_type = sub[0]
        _trace("  applying sub:", sub)
        if sub_type == "xpath":
            _, xpath, pattern, replacement = sub
            _apply_xpath_substitution(tree, xpath, pattern, replacement)
        elif sub_type == "css":
            _, selector, attr, pattern, replacement = sub
            _apply_css_substitution(tree, selector, attr, pattern, replacement)
        elif sub_type == "regex":
            _, target, pattern, replacement = sub
            _apply_regex_substitution(tree, target, pattern, replacement)

    # Pretty print
    if args.inl and args.format in ("html", "ht"):
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
        else:  # html or ht
            pretty_raw = html_tostring(tree, encoding="unicode")

    pretty = _reindent(pretty_raw, args.indent)

    _write_output(args.outfile, pretty, args.out_charset)


if __name__ == "__main__":
    main()
