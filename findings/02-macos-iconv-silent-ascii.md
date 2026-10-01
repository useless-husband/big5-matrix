# macOS iconv: Big5 encoders turn non-ASCII characters into ASCII and report an exact conversion

**Component:** the system `iconv` on macOS (FreeBSD-derived Citrus iconv), charsets `BIG5`
(and its aliases such as `BIG5-E` and `BIG5-ETEN`), `BIG5-2003` and `BIG5-HKSCS`.
Tested on macOS 27.0 (26A428).

**Severity:** medium to high where converted text is parsed afterwards: input that contains no
`<`, `"` or `\` can contain them after conversion, without any error.

## What happens

Converting to `BIG5`, `BIG5-2003` or `BIG5-HKSCS` maps 199, 199 and 186 non-ASCII characters to
ASCII bytes, and `iconv()` returns 0, which means "no non-identical conversions". Among them:

| Input | Output |
|---|---|
| ‹ U+2039, › U+203A | `<`, `>` |
| „ U+201E, ‟ U+201F, ˝ U+02DD | `"` |
| ´ U+00B4, ‛ U+201B, ʽ U+02BD, ˈ U+02C8 | `'` |
| ∖ U+2216 (and ﹨ U+FE68 in BIG5-HKSCS) | `\` |
| ⁄ U+2044 (and ∕ U+2215 in BIG5-HKSCS) | `/` |
| soft hyphen U+00AD, ‐ ‑ ‒ ― (U+2010, U+2011, U+2012, U+2015), − U+2212 | `-` |
| ｀ U+FF40 | `` ` `` |

That is the complete list of inputs that become one of ``< > " ' \ / - ` ``. The same encoders
also write some characters as Big5 codes that their decoder reads as other characters (for `BIG5`: U+02B9 → `AC A1`, which decodes as U+6D3B; Cyrillic А U+0410 → `C7 F3`,
which decodes as ⑴ U+2474).

## Reproduce

[`repro/02-macos-iconv-silent-ascii.c`](repro/02-macos-iconv-silent-ascii.c) calls `iconv(3)`
and prints its return value:

```
$ cc findings/repro/02-macos-iconv-silent-ascii.c -liconv -o /tmp/r && /tmp/r
a U+2039 b  (a‹b)          -> "a<b"  iconv() returned 0
a U+201E b  (a„b)          -> "a"b"  iconv() returned 0
a U+2216 b  (a∖b)          -> "a\b"  iconv() returned 0
a U+00B4 b  (a´b)           -> "a'b"  iconv() returned 0
```

or with the command-line tool: `printf 'a‹b' | iconv -f UTF-8 -t BIG5` prints `a<b` and exits
with status 0. The full list: `python3 -m big5matrix dump iconv.big5 encode` (rows whose bytes
are a single ASCII byte for a non-ASCII input).

## Why this is a bug and not a variant

POSIX specifies that `iconv()` "shall return the number of non-identical conversions performed";
a caller has no other way to learn that ‹ became `<`. GNU libiconv and glibc transliterate only
when asked to (`//TRANSLIT`). Microsoft's own best-fit table for code page 950, which is meant
to approximate, has 72 such mappings, and the only syntax characters among them are `!`, `|`
and `-`.

The risk is the one described by the WorstFit research
([DEVCORE, 2025](https://devco.re/blog/2025/01/09/worstfit-unveiling-hidden-transformers-in-windows-ansi/)):
text validated in Unicode is converted to a legacy encoding and then parsed, and the
conversion introduces delimiters the validation never saw.

## Prior reports

None found. Not reported by this project.
