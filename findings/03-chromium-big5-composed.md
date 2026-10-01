# Chromium: Big5 0x8862, 0x8864, 0x88A3, 0x88A5 decode to a control character and a lone surrogate

**Component:** Chromium's Big5 decoder (used by `TextDecoder('big5')` and when parsing a Big5
page). Tested with Chromium 153.0.8010.12 on macOS, both the full browser and the headless shell
that Playwright 1.63 installs.

**Severity:** low to medium. The four codes are rare (Ê̄, Ê̌, ê̄, ê̌ in Cantonese romanisation),
but the output is not valid text: a lone surrogate cannot be encoded as UTF-8, and APIs that
validate strings may throw or substitute.

## What happens

| Bytes | Chromium | WHATWG Encoding Standard |
|---|---|---|
| `88 62` | U+0093 U+DF04 | U+00CA U+0304 (Ê̄) |
| `88 64` | U+0093 U+DF0C | U+00CA U+030C (Ê̌) |
| `88 A3` | U+00B3 U+DF04 | U+00EA U+0304 (ê̄) |
| `88 A5` | U+00B3 U+DF0C | U+00EA U+030C (ê̌) |

The second code unit is the low surrogate with the combining mark's low ten bits
(0xDC00 | 0x304); the first is not a high surrogate. Every other one of the 65,792 one- and
two-byte cases matches the standard, and encoding_rs (Firefox) matches it on all of them.

## Reproduce

Open [`repro/03-chromium-big5-composed.html`](repro/03-chromium-big5-composed.html) in the
browser. Output with Chromium 153:

```
8862: U+0093 U+DF04
8864: U+0093 U+DF0C
88A3: U+00B3 U+DF04
88A5: U+00B3 U+DF0C
expected: U+00CA U+0304, U+00CA U+030C, U+00EA U+0304, U+00EA U+030C
```

The same happens when a page is served as `text/html; charset=big5`: its text content for the
bytes `88 62 41` is U+0093 U+DF04 U+0041. `python3 tools/verify_claims.py chromium-8862`
checks it.

## Why this is a bug and not a variant

The WHATWG Encoding Standard, which Chromium implements, gives these four pointers (1133, 1135,
1164, 1166) two code points each. A lone surrogate is not a possible result of any decoder in the
standard.

## Prior reports

None found in a web search; the Chromium tracker was not searched exhaustively. Not reported by
this project.
