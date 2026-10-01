# Go x/text: the Big5 decoder consumes ASCII bytes that the WHATWG decoder keeps

**Component:** `golang.org/x/text/encoding/traditionalchinese`, `Big5` decoder. Tested with
x/text v0.42.0 and Go 1.27.1.

**Severity:** medium. Printable ASCII disappears from malformed input, and Go's result
disagrees with browsers and other WHATWG implementations on the same bytes, which is the kind
of disagreement that lets text pass a filter on one side and mean something else on the other.

## What happens

The package follows the WHATWG Encoding Standard (its decoder cites
<https://encoding.spec.whatwg.org/#big5> for the composed characters, and its mappings are the
standard's). The standard's decoder says, for a lead byte followed by a byte that does not
complete a character: "If byte is an ASCII byte, restore byte to ioQueue." Go does this for
bytes 0x00–0x3F, but not for:

- **0x40–0x7E** when the pair is not in the index (all of rows 0x81–0x86, and gaps in later
  rows): the decoder writes U+FFFD for both bytes;
- **0x7F** after any lead byte: the same.

That is 522 two-byte cases, all listed by
`python3 -m big5matrix dump go.big5 decode` against `ref.whatwg`. The bytes lost include
`@`, letters, `[`, `\`, `]`, `^`, `` ` ``, `{`, `|`, `}`, `~` and DEL. The cause is visible in
[`big5.go`](https://github.com/golang/text/blob/master/encoding/traditionalchinese/big5.go):
for a trail byte in 0x40–0x7E the size is set to 2 before the index lookup, and when the lookup
fails the decoder writes U+FFFD without going back to size 1; 0x7F takes the `default` branch
with size 2.

## Reproduce

[`repro/04-go-xtext-big5-ascii.go`](repro/04-go-xtext-big5-ascii.go):

```
$ go run .
81 40 -> "�"
81 5C -> "�"
A1 7F -> "�"
A1 30 -> "�0"
```

encoding_rs, Chromium and the standard give `"�@"`, `"�\\"`, `"�\x7f"` and
`"�0"`.

## Note on the opposite risk

WHATWG issue [#171](https://github.com/whatwg/encoding/issues/171) argues that keeping the
backslash in `83 5C` is itself risky, because a reader that treats `83 5C` as one character
(Windows code page 950 does) sees no backslash. That is an argument about the standard. Go's
decoder otherwise matches the standard exactly (the same character for every byte sequence)
and cites it, so this difference is most likely unintended.

## Related, already reported

Go's encoder writes 27 common characters (港, 包, 煮 and others) to their HKSCS duplicate codes in
rows 0xFA–0xFE instead of their standard Big5 codes, so plain-Big5 readers cannot read them,
and it still writes the 3,837 HKSCS-row characters that the current standard's encoder
excludes. The first part is [golang/go#43581](https://github.com/golang/go/issues/43581) (open
since 2021; [#21910](https://github.com/golang/go/issues/21910) was closed in its favour).

## Prior reports

None found for the decoder in the Go issue tracker (searched for "big5" and
"traditionalchinese"). Not reported by this project.
