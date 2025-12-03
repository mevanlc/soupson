# soupson

A command-line utility for stewing html-like content using BeautifulSoup.

## Usage

```bash
soupson [options] [infile] [outfile]
```

### Options

- infile: Input file (default: stdin)
- outfile: Output file (default: stdout)

| Short | Long           | Value    | Description                                                    |
|-------|----------------|----------|----------------------------------------------------------------|
| -i    | --indent       | N        | Number of spaces to use for indentation                        |
| -f    | --format       | xml│html | Output tag format                                              |
| -e    | --encoding     | name     | Interpret input using this character encoding (default: guess) |
| -E    | --out-encoding | name     | Output using this character encoding (default: UTF-8)          |
| -r    | --remove       | selector | Remove nodes matching the CSS selector (children are kept)     |
| -p    | --parser       | name     | Force a specific BeautifulSoup backend (default: auto)         |

### Parsers

BeautifulSoup can sit on top of several well-known backends:

- `html.parser` (stdlib, always available)
- `lxml` (fast HTML & XML)
- `html5lib` (HTML5, most forgiving)
- `lxml-xml` / `xml` (XML mode; requires `lxml`)

Auto-selection follows BeautifulSoup’s default order: `lxml`, then `html5lib`, then `html.parser` for HTML; for XML we try `lxml-xml`, then `xml`. Use `-p/--parser` to pin a backend; the command errors if it isn’t installed.


## Tech

- Python 3.14
- argparse
- BeautifulSoup4

Optional:
- lxml

## Installation

```bash
cd soupson
uv tool install [-e] .
```

To include optional parser dependencies when installing:

- `uv tool install . --extra lxml` (fast HTML/XML)
- `uv tool install . --extra html5lib` (HTML5, forgiving)
- `uv tool install . --all-extras` (install both extras)

## Dev notes

I recommend installing soupson using `uv tool install -e`. This will put soupson on your path in a way where it can find its dependencies and your edits will be reflected immediately upon new invocations of the command.
