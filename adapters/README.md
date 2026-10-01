# Adapters

Each directory holds one small program that drives one runtime's converters and speaks the line
protocol described in [`big5matrix/protocol.py`](../big5matrix/protocol.py):

```
$ printf 'd\tA130\ne\t20AC\n' | python3 adapters/python/adapter.py cp950
d	A130	FFFD 0030
e	20AC	A3E1
```

The harness builds what needs building into `build/` (`python3 -m big5matrix run` does it), so
nothing compiled is committed. How each adapter calls its library, and why:

| Adapter | Decoding | Encoding | Version key |
|---|---|---|---|
| `python/adapter.py` | `bytes.decode(codec, "replace")` | `str.encode(codec, "strict")` | Python version |
| `go/main.go` | x/text `Decoder.Bytes` (always replaces with U+FFFD) | `Encoder.Bytes`, error = unmappable | x/text module version |
| `node/adapter.mjs` | `new TextDecoder('big5')` (non-fatal); `iconv.decode` | iconv-lite only; it writes `?` for an unmappable character, which the adapter detects (0x3F is never a Big5 trail byte) | Node version; iconv-lite version |
| `rust/` | `BIG5.decode_without_bom_handling` | `encode_from_utf8_without_replacement` (no HTML character references) | encoding_rs version from `Cargo.lock` |
| `java/Adapter.java` | `CharsetDecoder` with `REPLACE` (what `new String(bytes, cs)` does) | `CharsetEncoder` with `REPORT` | `java.version` |
| `dotnet/` | `DecoderReplacementFallback("�")`; `950/default` keeps the default fallbacks | `EncoderFallback.ExceptionFallback`; `950/default` keeps the default best-fit fallback and reports the bytes produced | .NET runtime version |
| `php/adapter.php` | `mb_convert_encoding` with `mb_substitute_character(0xFFFD)` | `mb_convert_encoding` with the `long` substitute mode, which the adapter detects | PHP version |
| `ruby/adapter.rb` | `String#encode(invalid: :replace, undef: :replace, replace: "�")` | `String#encode`, error = unmappable | Ruby version |
| `perl/adapter.pl` | `Encode::decode($enc, $bytes, FB_DEFAULT)` | `Encode::encode($enc, $text, FB_CROAK)` | Encode version |
| `icu/adapter.c` | `ucnv_toUChars` with ICU's default substitute callback (U+FFFD, or U+001A where ICU picks it) and default fallback setting, as `uconv` uses them | `ucnv_fromUChars` with the stop callback | ICU version |
| `iconv/adapter.c` | `iconv(3)`; stops at the first error (writes `!`) | `iconv(3)`; an error or a non-zero "non-identical conversions" count is `!` | macOS version and build |

Every decode call starts from a fresh decoder state and flushes it at the end of the input, so
a lead byte at the end of a case is treated as truncated input, exactly as when a whole file
ends there.

Two choices that shape the data:

- **Replacement mode for decoding.** Where a runtime offers it, decoding replaces errors with
  U+FFFD and continues. This is what most programs do by default, and it shows how many bytes an
  error swallows (does `A1 30` give `U+FFFD 0` or a lone `U+FFFD`?). macOS iconv has no
  replacement mode, so its column records where it stops.
- **Strict mode for encoding.** Encoding reports an unmappable character instead of writing a
  substitute, so the data records the real mapping. The `.NET 950 (default fallbacks)` column is
  the exception: it records what `Encoding.GetEncoding(950)` does out of the box, best fit
  included.

Not included: .NET's code page 20002 ("x-Chinese-Eten") is not a Big5 layout (it encodes 一
U+4E00 as `92 A0`, where every Big5 variant uses `A4 40`). glibc iconv and GNU libiconv were
not available on the machine that produced the data.
