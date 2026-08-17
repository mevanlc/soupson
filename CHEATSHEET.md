# SoupSON cheat sheet

The snippets below are option fragments. Run them as:

```sh
soupson OPTIONS example.html
```

Unless a snippet includes `-f`, it uses the default HTML-fragment (`ht`) format.
Quote CSS selectors, XPath expressions, globs translated to another syntax, and
regular expressions so the shell does not expand them.

## Example input

The examples refer to this `example.html`:

```html
<main data-page="docs">
  <!-- sponsored content -->
  <article data-track="utm_article" onclick="track()">
    <h2 data-track="tracking" data-link="javascript:heading()" onclick="track()">
      News
    </h2>
    <a href="javascript:openAd()" data-track="tracking" onclick="track()">
      Open <strong>offer</strong>
    </a>
    <x-note data-track="utm_note" data-link="javascript:note()" onclick="track()">
      Keep <em>this text</em>
    </x-note>
    <x-card data-track="tracking" onload="track()">
      <span>Card</span>
    </x-card>
    <script nonce="abc">alert("x")</script>
  </article>
</main>
```

The recurring match examples are:

- Exact tag, attribute name, and attribute value: `a`, `data-track`, and
  `tracking`.
- Tag-name, attribute-name, and attribute-value globs: `x-*`, `data-*`, and
  `utm_*`.
- Tag-name, attribute-name, and attribute-value regexes: `^h[1-6]$`,
  `^on[a-z]+$`, and `^javascript:`.

SoupSON has no native glob matcher. The glob examples below translate these
particular trailing-`*` globs to XPath `starts-with()` or to an equivalent
anchored regex. Translate other globs yourself; XPath 1.0 cannot express every
shell glob.

`-rx` and `-rs` unwrap selected elements, preserving their text and children.
`-rrx` and `-rrs` remove the selected elements and their entire subtrees. XPath
attribute results are removed with either XPath flag; this sheet uses `-rx` for
them. Python regex matching uses `re.search`, so anchors are required for exact
or whole-value matching. XPath and regex matching are case-sensitive unless the
expression says otherwise; HTML parsing normally lowercases tag and attribute
names, while XML preserves case.

A matched parse-root element cannot be unwrapped or deleted because it has no
parent. Its matching descendants are still processed.

SoupSON has no operation that clears all contents while retaining the matched
tag. Selecting `MATCH/*` can remove child elements, but it cannot remove direct
text. The “Removing just its children” entries call out that limitation.

## Remove tag by name

### Remove tag by exact tag name

These examples match `<script>`.

#### Preserving its children

```sh
-rs 'script'
```

#### Removing it and its children

```sh
-rrs 'script'
```

#### Removing just its children

Not exactly possible. This removes child elements of `<script>`, but not direct
text such as `alert("x")`:

```sh
-rrx '//script/*'
```

### Remove tag by glob-matched tag name

There is no native glob syntax. For the example glob `x-*`, use its equivalent
regex or XPath translation.

#### Preserving its children

```sh
-re e '^x-.*$'
```

#### Removing it and its children

```sh
-rre e '^x-.*$'
```

#### Removing just its children

Not exactly possible. This removes child elements of `x-*` tags, but not their
direct text:

```sh
-rrx '//*[starts-with(local-name(), "x-")]/*'
```

### Remove tag by regex-matched tag name

These examples match heading names with `^h[1-6]$`.

#### Preserving its children

```sh
-re e '^h[1-6]$'
```

#### Removing it and its children

```sh
-rre e '^h[1-6]$'
```

#### Removing just its children

Not exactly possible. Regex element-name matching acts on the matched element,
not its contents, and XPath 1.0 cannot generally select parents by regex.

## Remove attribute by name

### Remove attribute by exact attribute name

Remove every `data-track` attribute. `-ra` compares attribute names
case-insensitively and accepts a comma-separated list.

```sh
-ra 'data-track'
```

#### Constrained to tags with an exact name

Remove `data-track` only from `<a>`:

```sh
-rx '//a/@data-track'
```

#### Constrained to tags with a glob-matched name

Remove `data-track` only from tags matching `x-*`:

```sh
-rx '//*[starts-with(local-name(), "x-")]/@data-track'
```

#### Constrained to tags with a regex-matched name

Not exactly possible in general. Attribute XPath can constrain tag names, but
XPath 1.0 has no regex matching.

### Remove attribute by glob-matched attribute name

There is no native glob syntax. Remove names matching `data-*` with the
equivalent regex:

```sh
-re a '^data-.*$'
```

#### Constrained to tags with an exact name

Remove `data-*` attributes only from `<a>`:

```sh
-rx '//a/@*[starts-with(local-name(), "data-")]'
```

#### Constrained to tags with a glob-matched name

Remove `data-*` attributes only from `x-*` tags:

```sh
-rx '//*[starts-with(local-name(), "x-")]/@*[starts-with(local-name(), "data-")]'
```

#### Constrained to tags with a regex-matched name

Not exactly possible in general. XPath 1.0 cannot apply a tag-name regex.

### Remove attribute by regex-matched attribute name

Remove every attribute whose name matches `^on[a-z]+$`:

```sh
-re a '^on[a-z]+$'
```

#### Constrained to tags with an exact name

Not exactly possible. `-re a` matches attribute names globally and cannot be
constrained to selected tags.

#### Constrained to tags with a glob-matched name

Not exactly possible. Regex attribute removal has no tag selector, and XPath
1.0 cannot express the attribute-name regex.

#### Constrained to tags with a regex-matched name

Not exactly possible. Regex removal accepts only one target at a time and does
not combine tag-name and attribute-name regexes.

## Remove attribute by value

### Remove attribute by exact attribute value

Remove every attribute whose complete value is `tracking`:

```sh
-rx '//@*[. = "tracking"]'
```

#### Constrained to tags with an exact name

Remove such attributes only from `<a>`:

```sh
-rx '//a/@*[. = "tracking"]'
```

#### Constrained to tags with a glob-matched name

Remove such attributes only from `x-*` tags:

```sh
-rx '//*[starts-with(local-name(), "x-")]/@*[. = "tracking"]'
```

#### Constrained to tags with a regex-matched name

Not exactly possible in general. XPath 1.0 cannot apply the tag-name regex.

### Remove attribute by glob-matched attribute value

There is no native glob syntax. For the value glob `utm_*`:

```sh
-rx '//@*[starts-with(., "utm_")]'
```

#### Constrained to tags with an exact name

Remove matching attributes only from `<a>`:

```sh
-rx '//a/@*[starts-with(., "utm_")]'
```

#### Constrained to tags with a glob-matched name

Remove matching attributes only from `x-*` tags:

```sh
-rx '//*[starts-with(local-name(), "x-")]/@*[starts-with(., "utm_")]'
```

#### Constrained to tags with a regex-matched name

Not exactly possible in general. XPath 1.0 cannot apply the tag-name regex.

### Remove attribute by regex-matched attribute value

Remove every attribute whose value matches `^javascript:`:

```sh
-re v '^javascript:'
```

#### Constrained to tags with an exact name

Not exactly possible in general. `-re v` matches values globally and has no tag
selector.

#### Constrained to tags with a glob-matched name

Not exactly possible in general. Regex value removal cannot be scoped to tags.

#### Constrained to tags with a regex-matched name

Not exactly possible. Regex removal accepts only one target at a time and
cannot combine tag-name and attribute-value regexes.

## Remove attribute by name AND value

### Remove attribute by exact attribute name and exact attribute value

Remove `data-track` only when its complete value is `tracking`:

```sh
-rx '//@data-track[. = "tracking"]'
```

#### Constrained to tags with an exact name

```sh
-rx '//a/@data-track[. = "tracking"]'
```

#### Constrained to tags with a glob-matched name

```sh
-rx '//*[starts-with(local-name(), "x-")]/@data-track[. = "tracking"]'
```

#### Constrained to tags with a regex-matched name

Not exactly possible in general. XPath 1.0 cannot apply the tag-name regex.

### Remove attribute by glob-matched attribute name and exact attribute value

For attribute-name glob `data-*` and exact value `tracking`:

```sh
-rx '//@*[starts-with(local-name(), "data-") and . = "tracking"]'
```

#### Constrained to tags with an exact name

```sh
-rx '//a/@*[starts-with(local-name(), "data-") and . = "tracking"]'
```

#### Constrained to tags with a glob-matched name

```sh
-rx '//*[starts-with(local-name(), "x-")]/@*[starts-with(local-name(), "data-") and . = "tracking"]'
```

#### Constrained to tags with a regex-matched name

Not exactly possible in general. XPath 1.0 cannot apply the tag-name regex.

### Remove attribute by regex-matched attribute name and exact attribute value

Not exactly possible. `-re a` cannot add a value predicate, and XPath 1.0 cannot
express a general attribute-name regex.

#### Constrained to tags with an exact name

Not exactly possible for the same reason.

#### Constrained to tags with a glob-matched name

Not exactly possible for the same reason.

#### Constrained to tags with a regex-matched name

Not exactly possible. No removal mode combines all three conditions.

### Remove attribute by exact attribute name and glob-matched attribute value

For exact name `data-track` and value glob `utm_*`:

```sh
-rx '//@data-track[starts-with(., "utm_")]'
```

#### Constrained to tags with an exact name

```sh
-rx '//a/@data-track[starts-with(., "utm_")]'
```

#### Constrained to tags with a glob-matched name

```sh
-rx '//*[starts-with(local-name(), "x-")]/@data-track[starts-with(., "utm_")]'
```

#### Constrained to tags with a regex-matched name

Not exactly possible in general. XPath 1.0 cannot apply the tag-name regex.

### Remove attribute by exact attribute name and regex-matched attribute value

Not exactly possible in general. `-re v` cannot add an attribute-name
condition, and XPath 1.0 has no regex matching.

#### Constrained to tags with an exact name

Not exactly possible for the same reason.

#### Constrained to tags with a glob-matched name

Not exactly possible for the same reason.

#### Constrained to tags with a regex-matched name

Not exactly possible. No removal mode combines all three conditions.

### Remove attribute by glob-matched attribute name and glob-matched attribute value

For attribute-name glob `data-*` and value glob `utm_*`:

```sh
-rx '//@*[starts-with(local-name(), "data-") and starts-with(., "utm_")]'
```

#### Constrained to tags with an exact name

```sh
-rx '//a/@*[starts-with(local-name(), "data-") and starts-with(., "utm_")]'
```

#### Constrained to tags with a glob-matched name

```sh
-rx '//*[starts-with(local-name(), "x-")]/@*[starts-with(local-name(), "data-") and starts-with(., "utm_")]'
```

#### Constrained to tags with a regex-matched name

Not exactly possible in general. XPath 1.0 cannot apply the tag-name regex.

### Remove attribute by glob-matched attribute name and regex-matched attribute value

Not exactly possible in general. XPath can express the example name glob, but
not the value regex; `-re v` cannot add a name condition.

#### Constrained to tags with an exact name

Not exactly possible for the same reason.

#### Constrained to tags with a glob-matched name

Not exactly possible for the same reason.

#### Constrained to tags with a regex-matched name

Not exactly possible. No removal mode combines all three conditions.

### Remove attribute by regex-matched attribute name and glob-matched attribute value

Not exactly possible in general. `-re a` cannot add a value condition, and
XPath 1.0 cannot express the name regex.

#### Constrained to tags with an exact name

Not exactly possible for the same reason.

#### Constrained to tags with a glob-matched name

Not exactly possible for the same reason.

#### Constrained to tags with a regex-matched name

Not exactly possible. No removal mode combines all three conditions.

### Remove attribute by regex-matched attribute name and regex-matched attribute value

Not exactly possible. Separate `-re a` and `-re v` operations produce OR-like
removal, not an AND predicate on the same attribute.

#### Constrained to tags with an exact name

Not exactly possible.

#### Constrained to tags with a glob-matched name

Not exactly possible.

#### Constrained to tags with a regex-matched name

Not exactly possible. No removal mode combines all three regex conditions.

## Remove attribute by name OR value

### Remove attribute by exact attribute name or exact attribute value

Remove attributes named `onclick` or having the complete value `tracking`:

```sh
-rx '//@*[local-name() = "onclick" or . = "tracking"]'
```

### Remove attribute by glob-matched attribute name or glob-matched attribute value

For name glob `data-*` or value glob `utm_*`:

```sh
-rx '//@*[starts-with(local-name(), "data-") or starts-with(., "utm_")]'
```

### Remove attribute by regex-matched attribute name or regex-matched attribute value

Run the two global regex removals in sequence. The combined result is OR-like:

```sh
-re a '^on[a-z]+$' -re v '^javascript:'
```

## Remove tag by attribute name

### Remove tag by exact attribute name

These examples select tags that have an `onclick` attribute.

#### Preserving its children

```sh
-rs '[onclick]'
```

#### Removing it and its children

```sh
-rrs '[onclick]'
```

#### Removing just its children

Not exactly possible. This removes child elements, but direct text remains:

```sh
-rrs '[onclick] > *'
```

### Remove tag by glob-matched attribute name

There is no native glob syntax. These XPath examples select tags having an
attribute whose name matches `data-*`.

#### Preserving its children

```sh
-rx '//*[@*[starts-with(local-name(), "data-")]]'
```

#### Removing it and its children

```sh
-rrx '//*[@*[starts-with(local-name(), "data-")]]'
```

#### Removing just its children

Not exactly possible. This removes child elements, but direct text remains:

```sh
-rrx '//*[@*[starts-with(local-name(), "data-")]]/*'
```

### Remove tag by regex-matched attribute name

SoupSON can regex-match attribute names only to remove those attributes, not
their owning tags.

#### Preserving its children

Not exactly possible in general.

#### Removing it and its children

Not exactly possible in general.

#### Removing just its children

Not exactly possible. Neither owner-tag selection by attribute-name regex nor a
full content-clearing operation is available.

## Remove tag by attribute value

### Remove tag by exact attribute value

These examples select tags having any attribute whose complete value is
`tracking`.

#### Preserving its children

```sh
-rx '//*[@*[. = "tracking"]]'
```

#### Removing it and its children

```sh
-rrx '//*[@*[. = "tracking"]]'
```

#### Removing just its children

Not exactly possible. This removes child elements, but direct text remains:

```sh
-rrx '//*[@*[. = "tracking"]]/*'
```

### Remove tag by glob-matched attribute value

There is no native glob syntax. These examples translate value glob `utm_*`.

#### Preserving its children

```sh
-rx '//*[@*[starts-with(., "utm_")]]'
```

#### Removing it and its children

```sh
-rrx '//*[@*[starts-with(., "utm_")]]'
```

#### Removing just its children

Not exactly possible. This removes child elements, but direct text remains:

```sh
-rrx '//*[@*[starts-with(., "utm_")]]/*'
```

### Remove tag by regex-matched attribute value

SoupSON can regex-match attribute values only to remove those attributes, not
their owning tags.

#### Preserving its children

Not exactly possible in general.

#### Removing it and its children

Not exactly possible in general.

#### Removing just its children

Not exactly possible. Neither owner-tag selection by attribute-value regex nor
a full content-clearing operation is available.

## Remove tag by attribute name AND value

### Remove tag by exact attribute name and exact attribute value

These examples select tags having `data-track="tracking"`.

#### Preserving its children

```sh
-rx '//*[@data-track = "tracking"]'
```

#### Removing it and its children

```sh
-rrx '//*[@data-track = "tracking"]'
```

#### Removing just its children

Not exactly possible. This removes child elements, but direct text remains:

```sh
-rrx '//*[@data-track = "tracking"]/*'
```

### Remove tag by glob-matched attribute name and exact attribute value

These examples select tags having a `data-*` attribute equal to `tracking`.

#### Preserving its children

```sh
-rx '//*[@*[starts-with(local-name(), "data-") and . = "tracking"]]'
```

#### Removing it and its children

```sh
-rrx '//*[@*[starts-with(local-name(), "data-") and . = "tracking"]]'
```

#### Removing just its children

Not exactly possible. This removes child elements, but direct text remains:

```sh
-rrx '//*[@*[starts-with(local-name(), "data-") and . = "tracking"]]/*'
```

### Remove tag by regex-matched attribute name and exact attribute value

SoupSON cannot combine an attribute-name regex with an exact value predicate.

#### Preserving its children

Not exactly possible.

#### Removing it and its children

Not exactly possible.

#### Removing just its children

Not exactly possible.

### Remove tag by exact attribute name and glob-matched attribute value

These examples select tags whose `data-track` value matches `utm_*`.

#### Preserving its children

```sh
-rx '//*[@data-track[starts-with(., "utm_")]]'
```

#### Removing it and its children

```sh
-rrx '//*[@data-track[starts-with(., "utm_")]]'
```

#### Removing just its children

Not exactly possible. This removes child elements, but direct text remains:

```sh
-rrx '//*[@data-track[starts-with(., "utm_")]]/*'
```

### Remove tag by exact attribute name and regex-matched attribute value

SoupSON cannot use a value regex as an XPath predicate selecting owner tags.

#### Preserving its children

Not exactly possible in general.

#### Removing it and its children

Not exactly possible in general.

#### Removing just its children

Not exactly possible.

### Remove tag by glob-matched attribute name and glob-matched attribute value

These examples select tags having a `data-*` attribute matching `utm_*`.

#### Preserving its children

```sh
-rx '//*[@*[starts-with(local-name(), "data-") and starts-with(., "utm_")]]'
```

#### Removing it and its children

```sh
-rrx '//*[@*[starts-with(local-name(), "data-") and starts-with(., "utm_")]]'
```

#### Removing just its children

Not exactly possible. This removes child elements, but direct text remains:

```sh
-rrx '//*[@*[starts-with(local-name(), "data-") and starts-with(., "utm_")]]/*'
```

### Remove tag by glob-matched attribute name and regex-matched attribute value

SoupSON cannot combine the translated name glob with a value regex when
selecting owner tags.

#### Preserving its children

Not exactly possible in general.

#### Removing it and its children

Not exactly possible in general.

#### Removing just its children

Not exactly possible.

### Remove tag by regex-matched attribute name and glob-matched attribute value

SoupSON cannot combine an attribute-name regex with the translated value glob
when selecting owner tags.

#### Preserving its children

Not exactly possible in general.

#### Removing it and its children

Not exactly possible in general.

#### Removing just its children

Not exactly possible.

### Remove tag by regex-matched attribute name and regex-matched attribute value

SoupSON cannot combine attribute-name and attribute-value regexes to select
owner tags.

#### Preserving its children

Not exactly possible.

#### Removing it and its children

Not exactly possible.

#### Removing just its children

Not exactly possible.

## Remove comments

Remove all comments while preserving text after each comment:

```sh
-rco
```

## Substituting values

Patterns and replacements use Python `re.sub` syntax. Replacements may contain
backreferences such as `\1`.

### Substitute in attribute values matched by XPath

Change `javascript:` to `https:` in every `href` value:

```sh
-sx '//@href' '^javascript:' 'https:'
```

XPath must return attribute nodes; element and text results are ignored.

### Substitute in attribute values of elements matched by CSS selector

Apply the substitution only to the `href` attribute of matching `<a>` tags:

```sh
-sc 'a[onclick]' href '^javascript:' 'https:'
```

Matching elements without that attribute are left unchanged.

### Substitute by regex. TARGET: e=element name

Rename `x-note` to `aside`:

```sh
-se e '^x-note$' 'aside'
```

### Substitute by regex. TARGET: a=attr name

Rename `data-track` to `data-source`:

```sh
-se a '^data-track$' 'data-source'
```

### Substitute by regex. TARGET: v=attr value

Change `javascript:` to `https:` in every attribute value:

```sh
-se v '^javascript:' 'https:'
```

## Controlling indentation

Use `-i N`, where `N` is the number of spaces per indentation level. The
default is 2. Zero disables indentation, and negative values are treated as 0.

```sh
-i 4
```

## Controlling newline behavior for inline-kind tags

Inline-aware formatting is enabled by default for `html`, `ht`, and
`htmlpart`. It keeps recognized inline elements and their text together on one
line:

```sh
--inl
```

Disable it and use lxml's ordinary pretty-printer instead:

```sh
--no-inl
```

The inline-kind tag set is fixed by `HTML_INLINE_TAGS` in the Python API; there
is no CLI option for changing the set. `--inl` has no effect on XML output.

## Controlling input text encoding

Use `-c NAME` to decode the input as a specific character set:

```sh
-c windows-1252
```

Without `-c`, SoupSON guesses using `charset-normalizer`. Invalid byte
sequences are replaced rather than rejected.

## Controlling output text encoding

Use `-C NAME` to encode the output as a specific character set:

```sh
-C iso-8859-1
```

The default is UTF-8. Characters unavailable in the chosen encoding are
replaced rather than rejected.

## Controlling output format

### html

Parse and emit a full HTML document. Fragment input is given `<html>` and
`<body>` structure:

```sh
-f html
```

### ht (or htmlpart)

Parse and emit an HTML fragment without deliberately adding full-document
structure. `ht` is the default; `htmlpart` is an alias.

```sh
-f ht
```

```sh
-f htmlpart
```

### xml

Parse as XML and emit XML. Input must be well-formed XML with a single root
element, and names remain case-sensitive.

```sh
-f xml
```
