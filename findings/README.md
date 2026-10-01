# Findings

Divergences that look like bugs (an implementation disagreeing with its own documented
standard or with itself), as opposed to variant choices. Each file states the version tested,
what happens, a minimal reproducer in [`repro/`](repro) with its real output, and whether it was
already known. None has been reported upstream by this project; that is for the repository
owner to decide.

| # | Component | Summary | Known before? |
|---|---|---|---|
| [01](01-macos-iconv-big5-hkscs.md) | macOS iconv `BIG5-HKSCS` | cannot encode most ordinary hanzi; BMP code points encoded as plane-2 characters; 0x8862 loses its combining mark | not found |
| [02](02-macos-iconv-silent-ascii.md) | macOS iconv `BIG5`, `BIG5-2003`, `BIG5-HKSCS` | non-ASCII characters silently become `< > " ' \ /` and others; `iconv()` reports an exact conversion | not found |
| [03](03-chromium-big5-composed.md) | Chromium 153 | 0x8862, 0x8864, 0x88A3, 0x88A5 decode to a C1 control and a lone surrogate | not found |
| [04](04-go-xtext-big5-ascii.md) | Go x/text v0.42.0 | decoder consumes ASCII 0x40–0x7F after a lead byte where WHATWG keeps it | decoder: not found; encoder: golang/go#43581 |
| [05](05-perl-encode-truncated.md) | Perl Encode 3.08 | truncated final character dropped, no U+FFFD and no error even with `FB_CROAK` | not found |
| [06](06-dotnet-cp950-duplicates.md) | .NET 10 code page 950 | rejects ten byte sequences Microsoft's tables map | not found |
| [07](07-node-textdecoder-big5.md) | Node.js 25 `TextDecoder('big5')` | ICU's windows-950, not the WHATWG decoder | yes: nodejs/node#40091, #61041, PR #65458 |
| [08](08-ruby-big5-hkscs-87.md) | Ruby 2.6 `Big5-HKSCS` | encodes row 0x87 that it cannot decode (re-test on a current Ruby) | not searched |

`python3 tools/verify_claims.py` re-checks the key claim of each finding directly against the
runtime and against the committed data.
