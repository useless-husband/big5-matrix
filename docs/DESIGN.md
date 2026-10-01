# Design

big5-matrix answers one question for every Big5 byte sequence and every relevant character:
what does each converter really do? This document explains how the pieces fit, the problems
that made that hard, and the alternatives that were considered and rejected.

## Pieces

```
big5matrix/cases.py      the case list: 256 single bytes + 65,536 pairs; BMP + plane 2 + extras
big5matrix/protocol.py   the line protocol between the harness and the adapters
big5matrix/registry.py   every implementation: runtime, codec, how to build and find it
big5matrix/reference.py  the five reference columns computed from published tables
big5matrix/run.py        runs adapters (four at a time), validates answers, writes data/
big5matrix/store.py      the compact result files and the manifest
big5matrix/model.py      loads data/, normalises it, character maps, regions
big5matrix/analyze.py    error handling, families, divergence classes, one-way mappings, round trips
big5matrix/summary.py    named numbers and tables (report/summary.json)
big5matrix/report.py     refreshes the generated numbers in the Markdown documents
big5matrix/drift.py      the CI check: re-run what is installed, compare with data/
adapters/<runtime>/      one small program per runtime (Python, Go, Node, Rust, Java, .NET,
                         PHP, Ruby, Perl, C for ICU and iconv, Node + Chromium)
docs/                    the static site (reads data/ and report/summary.json directly)
tools/                   fetch_reference.py, verify_claims.py, serve.py
```

The harness is Python with no dependencies outside the standard library, so the whole study can
be re-analysed anywhere; each adapter uses its own runtime's ordinary package manager (Go
modules, Cargo, npm), with versions pinned by the lock files.

## Problem 1: one comparison across three error models

Converters fail in three ways. Most have a replacement mode: an error becomes U+FFFD and decoding
continues. macOS iconv only stops (EILSEQ). A published table has no error behaviour at all: a
byte sequence is either in it or not.

A single "result" per case would compare unlike things, so the protocol records what each one
actually does (code points, with `!` where a converter without a replacement mode stopped), and
the analysis compares two separate questions:

- **Mapping** ("is this byte sequence a character, and which?"): every implementation and every
  table takes part. The answer comes from the *character map*: the non-ASCII single bytes and
  two-byte sequences an implementation decodes, without error, as one character. A two-byte
  case counts only when its first byte does not decode on its own; otherwise `80 41` would be
  mistaken for one character in code page 950, where 0x80 is U+0080.
- **Recovery** ("what does an error cost?"): only converters and the WHATWG algorithm take part.
  Each case is classified as *kept* (one error, then the second byte decoded on its own,
  compared with that implementation's own single-byte result), *swallowed*, *two errors*,
  *stops*, *dropped* or *character*.

Replacement mode is used for decoding because it is what most programs get by default
(`new String(bytes, cs)`, `bytes.decode(enc, "replace")`, `TextDecoder`), and because it is the
only way to observe how many bytes an error consumes. Strict mode would hide exactly the
differences that matter for security. Encoding is strict because a substitute byte would hide
the mapping; the one exception is a separate `.NET 950 (default fallbacks)` column, since what
.NET does by default (best fit) is itself the finding.

## Problem 2: substitutes that look like data

Some converters do not use U+FFFD. ICU's IBM converters write U+001A for most errors, but
ibm-950 also maps the byte 0x7F to U+001A, so `A1 7F` → `U+001A U+001A` is ambiguous. .NET's
default decoder writes `?`. iconv-lite and PHP's mbstring have no strict encoder.

- **ICU:** the adapter installs a to-Unicode callback that calls ICU's own substitute callback
  (so the output is exactly what `uconv` would write) and records which output positions it
  wrote; the protocol marks those as `!001A`. A re-run confirmed that the only change from
  plain decoding was the marker, on 25,340 cases.
- **iconv-lite:** it writes `?` for an unmappable character; 0x3F is never a Big5 trail byte, so
  a 0x3F in the output for input without `?` is exactly such a substitution.
- **PHP:** encoding uses the `long` substitute mode, which writes `U+XXXX` in ASCII; no single
  character legitimately encodes to text containing `U+`.
- **.NET default decoder:** left out (its decoder differs from the strict column only in
  writing `?`); the default column is encode-only.

## Problem 3: making each case independent and the space finite

Big5 is stateless and its characters are at most two bytes long, so every one- and two-byte
sequence (65,792 cases) covers every character and every way a single character can go wrong.
Each case is decoded with a fresh converter and the end of the case is the end of the input, so
a lead byte at the end of a case is a truncated character, as at the end of a file.

Longer inputs could still interact (an error could swallow the start of the next character). The
analysis checks the one interaction that could make most pairs redundant: for every whole-space
decoder, a pair whose first byte is ASCII decodes exactly as that byte followed by the second
byte alone (<!--n:decode.ascii_first_exceptions-->0<!--/n--> exceptions in <!--n:decode.ascii_first_decoders-->43<!--/n--> columns), so those 32,768 cases are summarised rather than listed.

For encoding, the cases are the BMP scalar values, plane 2 (CJK Extensions B–F, where HKSCS
lives) and any other sequence a decoder produced: the four HKSCS composed characters
(Ê̄ = U+00CA U+0304 and so on). That list depends on the decoders, so it is committed
(`data/encode-extra.txt`) and every result file records the digest of the case list it was made
for; reading a file made for a different list fails instead of misaligning silently. Chromium
produced lone surrogates for those composed characters (finding 3); a lone surrogate is not a
Unicode scalar value, so it is never made into an encode case.

## Problem 4: data small enough to commit, exact enough to trust

The first layout repeated the input on every line and came to 22 MB. Since the case order is
fixed, each file now holds one result per line after a header naming its case list: 40
converters and 5 tables in 5.6 MB, no file over 100 KB. Files are gzip'd with a zero timestamp
and no name, so the bytes are reproducible, and the manifest stores the SHA-256 of the
*uncompressed* content so that a different zlib can never look like drift. Re-running the full
collection reproduced the committed files byte for byte.

## Problem 5: versions change, and CI is not this machine

Each adapter reports a *behaviour key*: the part of its version that decides results (the x/text
module for Go, encoding_rs's crate version, the ICU version, the macOS build for iconv, the Node
version for `TextDecoder` and the iconv-lite version for iconv-lite, which is plain JavaScript).
The drift check re-runs every adapter available on the CI runner against the committed case
list:

- same key, same results: pass;
- same key, different results: fail (the data or an adapter changed without a version change);
- different key: report the differences with examples as a notice, not a failure;
- an adapter that fails: a failure with the committed key, a notice with another (an older
  Ruby may lack a codec);
- runtime missing: skipped with a notice.

The CI workflow pins the versions the data depends on (CPython 3.13.0, Node 25.5.0, Java 27;
x/text, encoding_rs and iconv-lite through their lock files), so those comparisons are exact,
while the macOS iconv, .NET and the Linux runner's ICU, Perl, PHP and Ruby are expected to
differ and are reported.

## Problem 6: every number traceable

The report and the READMEs quote dozens of numbers. They are not typed by hand: each sits
between a pair of HTML comments that name a value `analyze` computes (an `n:` comment for a
number, a `t:` comment for a table; view the Markdown source to see them), and `report`
refreshes them in place. An unknown key is an error, and CI
regenerates everything and fails on any difference, so a document cannot drift from the data.
The marker pattern refuses to span lines, after an early version matched a literal example in
the prose and would have swallowed a paragraph.

## Problem 7: a site that cannot disagree with the data

The site has no data of its own. The pages load `data/*.txt.gz`, decompress them with the
browser's `DecompressionStream`, and recompute lookups, divergence classes and any writer/reader
comparison; structured summaries come from `report/summary.json`. That required porting the
normalisation, the character map and the round-trip rules to JavaScript, so
`tests/test_site_js.py` runs the site's modules under Node and checks that they reproduce
Python's numbers for every divergence class, every by-name pair, every round trip and every
character map.

## Problem 8: trusting the reference columns

The WHATWG column is the specification transcribed in about 60 lines of Python. It is checked
three ways: against the specification's examples in unit tests, against encoding_rs (identical
on every decode and encode case), and against Chromium (identical except for the four cases
that turned out to be a Chromium bug). The four other tables are pinned by SHA-256 and can be
re-downloaded and compared (`tools/fetch_reference.py`). Microsoft's bestfit950.txt has two
record kinds with the same shape (a lead-byte range and a mapping), so the parser follows the
record counts in the section headers instead of guessing.

## Families

The distance between two decoders is the number of byte sequences that are a character for at
least one of them and not the same character for both (a partial table counts only where it has
entries). Single-linkage clustering at 400 gives <!--n:families.multi-->6<!--/n--> families of two or more; the largest
distance inside a family is <!--n:families.max_inside-->496<!--/n--> and the smallest between families is <!--n:families.min_between-->655<!--/n-->, so the grouping is
not sensitive to the exact threshold. Which variant each implementation "really" implements is
then read off a per-region comparison with each table rather than asserted.

## Rejected alternatives

- **Running `uconv` once per case.** 65,792 processes per converter would take many minutes;
  the adapter calls the same ICU library with the same defaults, and `tools/verify_claims.py`
  cross-checks results with the real `uconv` and `iconv` command-line tools.
- **Emulating recovery for iconv** (skip a byte after EILSEQ and continue): that would record
  the harness's behaviour, not iconv's.
- **Storing each implementation as a difference from a baseline:** smaller, but every file would
  depend on the baseline, and changing one implementation would rewrite others.
- **Precomputed JSON for the site:** several megabytes of duplicated data that could drift from
  `data/`; computing in the browser costs about 3.6 MB of downloads on the heaviest page (all
  decode results, for a divergence class).
- **Strict decoding everywhere:** simpler, but it would erase the difference between a decoder
  that keeps a quote mark after an error and one that eats it.
- **A Linux container for glibc iconv:** not available on the shared machine; listed as a
  limitation instead.
