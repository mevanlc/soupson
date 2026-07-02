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
| -re  | TARGET PATTERN | Remove by regex (unwrap) |
| -rre | TARGET PATTERN | Remove by regex (recursive) |

Regex targets: `e`=element name, `a`=attr name, `v`=attr value

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
