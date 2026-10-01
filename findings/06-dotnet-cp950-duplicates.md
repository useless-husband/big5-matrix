# .NET: code page 950 rejects ten byte sequences that Microsoft's tables map

**Component:** `System.Text.Encoding.CodePages` (`CodePagesEncodingProvider`), code page 950.
Tested with .NET 10.0.12 on macOS.

**Severity:** low. Ten box-drawing characters and two hanzi that have a second code decode as
errors (or `?` with the default fallback).

## What happens

| Bytes | CP950.TXT and bestfit950.txt | .NET 950 |
|---|---|---|
| `A2 A4` `A2 A5` `A2 A6` `A2 A7` | ═ ╞ ╪ ╡ (U+2550, U+255E, U+256A, U+2561) | error |
| `A2 CC` `A2 CE` | 十 卅 (U+5341, U+5345) | error |
| `F9 FA` `F9 FB` `F9 FC` `F9 FD` | ╭ ╮ ╰ ╯ (U+256D, U+256E, U+2570, U+256F) | error |

Each of these characters has a second code (`F9 F9`, `A4 51` and so on) that .NET decodes and
encodes. Microsoft's published table for code page 950 (CP950.TXT) and its "best fit" table for
Windows (bestfit950.txt, the MBTABLE/DBCSTABLE part, which describes `MultiByteToWideChar`) map
all ten. Every other Windows-950 implementation tested (Java `x-windows-950`, ICU
`windows-950-2000`, Ruby `CP950`, Perl `cp950`, PHP `CP950`, Node.js's `TextDecoder`) decodes
them. It looks as if .NET's decoding table was built from the round-trip mappings only.

## Reproduce

[`repro/06-dotnet-cp950-duplicates.cs`](repro/06-dotnet-cp950-duplicates.cs):

```
A2A4 -> error
A2A5 -> error
A2A6 -> error
A2A7 -> error
A2CC -> error
A2CE -> error
F9FA -> error
F9FB -> error
F9FC -> error
F9FD -> error
F9F9 -> U+2550
A451 -> U+5341
```

## Caveat

Windows itself was not run. The claim is that .NET differs from Microsoft's published tables,
not that it differs from Windows.

## Prior reports

None found. Not reported by this project.
