# soupson CLI Surface Philosophy

## Brevity is justified

This tool speaks XPath and CSS — languages where `//div[@class='foo']` *is* the readable version. A CLI surface of `-rrx` is practically chatty by comparison.

## The removal matrix

Two axes:
- **What**: xpath (`x`), css selector (`s`), regex (`e`)
- **How**: unwrap (`-r*`), recursive (`-rr*`)

## Removal zen

If you request recursive removal of something that can't be recursed into (e.g., an attribute), just do the subset that's possible. No warning, no error. You asked for "at least this much removal" — you got it.

## Let the tools do their job

Don't parse XPath with regex. Don't track html/body wrappers manually. If lxml has a `fromstring` that auto-detects fragments, use it. If lxml returns smart strings with `.attrname`, use them.

The tooling is smarter than our hacks.
