# macOS iconv: the BIG5-HKSCS encoder is broken

**Component:** the system `iconv` on macOS (libiconv in libSystem, the FreeBSD "Citrus"
implementation Apple has shipped since macOS 14), charset `BIG5-HKSCS` (aliases
`BIG5-HKSCS:2004`, `BIG5HKSCS`). Tested on macOS 27.0 (26A428).

**Severity:** high for anyone producing Big5-HKSCS on macOS: ordinary text cannot be encoded,
and some input is encoded to the wrong characters without an error.

## What happens

1. **Ordinary Big5 characters cannot be encoded.** Of the 13,053 hanzi in the Big5 core
   (0xA440–0xC67E and 0xC940–0xF9D5), the encoder rejects 12,634, including 中 and 一. The decoder
   reads all of them. `BIG5` (without HKSCS) encodes them.
2. **BMP code points are encoded as plane-2 characters.** 1,554 BMP code points are encoded to
   the Big5 code of the plane-2 character whose low 16 bits are the same: U+0086 becomes
   `8B C5`, which the same converter decodes as U+20086 𠂆. The plane-2 characters themselves
   cannot be encoded: of the 1,713 plane-2 characters the decoder produces, the encoder rejects
   1,708.
3. **Other one-way output.** Some code points produce a single non-ASCII byte that is not a
   character at all (U+A1B1 → `A7`), and 186 non-ASCII characters are written as ASCII (see
   [finding 2](02-macos-iconv-silent-ascii.md)).
4. **Composed characters lose their mark.** 0x8862, 0x8864, 0x88A3 and 0x88A5 decode to U+00CA or
   U+00EA alone. HKSCS-2004 and later (and the WHATWG Encoding Standard) map them to a base
   letter plus U+0304 or U+030C, as Python's `big5hkscs`, encoding_rs and Go do.

Item 2 suggests the Unicode-to-Big5 table for this charset was built with code points truncated
to 16 bits. Item 1 suggests the HKSCS table is used without the Big5 base table in the
encoding direction.

## Reproduce

[`repro/01-macos-iconv-big5-hkscs.sh`](repro/01-macos-iconv-big5-hkscs.sh) uses only
`/usr/bin/iconv`:

```
$ sh findings/repro/01-macos-iconv-big5-hkscs.sh
1. 中 (U+4E2D, Big5 A4 A4):
   UTF-8 -> BIG5-HKSCS:  (exit 1) iconv: iconv(): Illegal byte sequence
   UTF-8 -> BIG5: a4a4 (exit 0)
2. U+0086 (a C1 control), the bytes it becomes, and U+20086 itself:
   UTF-8 -> BIG5-HKSCS: 8bc5 (exit 0)
   BIG5-HKSCS -> UTF-32BE: 00020086 (exit 0)
   UTF-8 -> BIG5-HKSCS:  (exit 1) iconv: iconv(): Illegal byte sequence
3. 0x8862 (HKSCS-2004 and later: U+00CA U+0304):
   BIG5-HKSCS -> UTF-32BE: 000000ca (exit 0)
```

The full lists: `python3 -m big5matrix dump iconv.big5-hkscs encode`, or the site's lookup
page. The counts above are `fact.iconv.hkscs.*` in [`report/summary.json`](../report/summary.json).

## Why this is a bug and not a variant

The converter is named after HKSCS-2004 and rejects or mis-encodes characters that every edition
of HKSCS, and Big5 itself, define; its own decoder disagrees with its encoder. No other Big5-HKSCS
implementation tested (Python, Java, ICU, Ruby, Perl, WHATWG) behaves like this.

## Prior reports

None found. Apple's switch to this iconv in macOS 14 is known to have caused other
incompatibilities ([Homebrew discussion #4884](https://github.com/orgs/Homebrew/discussions/4884)).
Not reported by this project.
