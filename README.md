# soupson

A command-line utility for pretty-printing and sanitizing HTML/XML.

## Usage

```bash
soupson [options] [infile] [outfile]
```

### Options

- infile: Input file (default: stdin)
- outfile: Output file (default: stdout)

| Flag | Args | Description |
|------|------|-------------|
| -i   | N | Indent width (default: 2) |
| -f   | html\|xml | Output format (default: html) |
| -c   | CHARSET | Input charset (default: guess) |
| -C   | CHARSET | Output charset (default: utf-8) |
| -rx  | XPATH | Remove by XPath (unwrap) |
| -rrx | XPATH | Remove by XPath (recursive) |
| -rs  | SELECTOR | Remove by CSS (unwrap) |
| -rrs | SELECTOR | Remove by CSS (recursive) |
| -ra  | NAME[,NAME...] | Remove attributes by exact name (case-insensitive) |
| -rco | | Remove comments |
| -re  | TARGET PATTERN | Remove by regex (unwrap) |
| -rre | TARGET PATTERN | Remove by regex (recursive) |
| -rb  | | Remove blank elements (unwrap) |
| -rrb | | Remove blank elements (recursive) |
| -rbs | SELECTOR | Remove blank elements matching CSS selector (unwrap) |
| -rrbs | SELECTOR | Remove blank elements matching CSS selector (recursive) |
| -rbe | PATTERN | Remove blank elements whose name matches regex (unwrap) |
| -rrbe | PATTERN | Remove blank elements whose name matches regex (recursive) |

Regex targets: `e`=element name, `a`=attr name, `v`=attr value

### Blank elements

An element is *blank* when it has no child nodes and no meaningful text:
whitespace-only text for ordinary tags, exactly empty text for
whitespace-preserving tags (`pre`, `script`, `style`, `textarea`).

- Attributes are ignored — `<span class="x"></span>` is blank.
- Any child node counts as content, including a comment. Run `-rco` first to
  expose comment-only elements.
- Void elements (`br`, `img`, `input`, ...) are never blank in HTML mode; in
  XML mode every empty tag is a candidate.
- Removal cascades bottom-up in a single pass: a parent left blank by the
  removal of its blank children is removed too.
- Unwrap keeps the element's whitespace text, recursive drops it. Tail text
  following the element is preserved either way.

## Tech

- Python 3.14+
- lxml
- cssselect

## Installation

```bash
uv tool install .
```

For development:
```bash
uv tool install -e .
```
