# big5-matrix

**What today's runtimes actually do with Big5, the legacy encoding of Traditional Chinese, measured
on every byte sequence and every relevant character.**

Big5 is still how a great deal of text from Taiwan and Hong Kong is stored and exchanged, and it
comes in many variants: Microsoft's code page 950, Unicode's BIG5.TXT, ETEN, Big5-2003, HKSCS,
UAO, the WHATWG standard browsers use. Runtimes picked different ones, often under the same
name, so text written as "big5" by one program can come back as different characters from
another, with no error. This project runs <!--n:impls.runs-->40<!--/n--> converters from <!--n:impls.runtimes-->12<!--/n--> runtimes and libraries
(Python, Go, Node.js, Rust, Java, .NET, PHP, Ruby, Perl, ICU, macOS iconv, Chromium) over the
whole one- and two-byte space and over every BMP and plane-2 character, compares them with
<!--n:impls.tables-->5<!--/n--> published tables, and publishes every place they disagree.

- **[Site](https://useless-husband.github.io/big5-matrix/docs/)**: look up any byte sequence or
  character, browse each class of disagreement, compare any writer with any reader.
- **[Report](docs/divergences.md)**: families, error handling, mapping disputes, round trips,
  history and recommendations.
- **[Findings](findings/)**: eight problems that look like bugs, each with a reproducer.
- [繁體中文說明](README.zh-TW.md) · [Design](docs/DESIGN.md) · [Data](data/)

## What it shows

- All implementations agree on the <!--n:decode.hanzi_cases-->13,053<!--/n--> hanzi of the Big5 core except <!--n:decode.hanzi_divergent-->1<!--/n-->; everywhere
  else they disagree on <!--n:decode.divergent_total-->19,467<!--/n--> of <!--n:decode.nontrivial_cases-->33,024<!--/n--> byte sequences.
- Writing with one runtime's "big5" and reading with another's changes or loses characters in
  all but <!--n:pair.big5.clean-->11<!--/n--> of <!--n:pair.big5.total-->110<!--/n--> pairs. Python writes Ё as `C7 B3`; Go and browsers read シ.
- `cp950` is Microsoft's table in Python, Perl and Ruby and IBM's in Java and ICU. Node.js's
  `TextDecoder('big5')` is ICU's windows-950, <!--n:fact.node.vs_whatwg-->6,253<!--/n--> byte sequences away from the WHATWG decoder
  that browsers implement.
- After a stray lead byte, <!--n:error.keep_all-->25<!--/n--> decoders keep the next ASCII byte (as WHATWG requires) and
  <!--n:error.swallow_all-->6<!--/n--> swallow it, quote marks included. Perl drops a truncated final character silently.
- macOS iconv's Big5 encoders turn <!--n:oneway.iconv.big5.to-ascii-->199<!--/n--> non-ASCII characters into ASCII without an error
  (`‹` → `<`, `„` → `"`, `∖` → `\`), and its BIG5-HKSCS encoder cannot encode
  <!--n:fact.iconv.hkscs.hanzi_unencodable-->12,634<!--/n--> of the <!--n:fact.iconv.hkscs.hanzi_total-->13,053<!--/n--> ordinary hanzi.

Write with the runtime on the left, read with the one on the top, both asking for "big5"
(characters changed silently / reported as errors; 0 means nothing is lost):

<!--t:by-name-big5-->
| writer ↓ / reader → | Python | Go | Node.js | Rust | Java | .NET | PHP | Ruby | Perl | ICU | macOS iconv |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **Python** | 0 | 260 / 0 | 260 / 0 | 260 / 0 | 1 / 2 | 260 / 4 | 1 / 3 | 260 / 0 | 262 / 0 | 260 / 0 | 0 |
| **Go** | 256 / 4,813 | 0 | 4,984 / 33 | 0 | 259 / 4,815 | 4,984 / 37 | 256 / 4,777 | 362 / 4,655 | 28 / 4,655 | 4,984 / 33 | 4,884 / 74 |
| **Node.js** | 259 / 4,792 | 0 | 4,970 / 33 | 0 | 262 / 4,794 | 4,970 / 33 | 259 / 4,760 | 365 / 4,638 | 32 / 4,638 | 4,970 / 33 | 4,870 / 74 |
| **Rust** | 259 / 951 | 0 | 1,129 / 33 | 0 | 262 / 953 | 1,129 / 33 | 259 / 919 | 365 / 797 | 32 / 797 | 1,129 / 33 | 1,029 / 74 |
| **Java** | 0 | 260 / 0 | 260 / 0 | 260 / 0 | 0 | 260 / 4 | 1 / 0 | 260 / 0 | 262 / 0 | 260 / 0 | 0 |
| **.NET** | 737 / 6,008 | 5,543 / 1,161 | 484 / 0 | 5,543 / 1,161 | 739 / 6,011 | 484 / 0 | 736 / 5,977 | 484 / 5,811 | 845 / 5,814 | 484 / 0 | 811 / 46 |
| **PHP** | 1 / 33 | 260 / 0 | 259 / 0 | 260 / 0 | 1 / 33 | 259 / 4 | 0 | 259 / 0 | 261 / 0 | 259 / 0 | 1 / 0 |
| **Ruby** | 260 / 193 | 366 / 43 | 0 | 366 / 43 | 263 / 195 | 0 / 4 | 259 / 165 | 0 | 361 / 3 | 0 | 334 / 44 |
| **Perl** | 264 / 194 | 35 / 40 | 363 / 0 | 35 / 40 | 267 / 196 | 361 / 2 | 261 / 164 | 363 / 0 | 0 | 363 / 0 | 271 / 41 |
| **ICU** | 260 / 6,008 | 5,059 / 1,161 | 0 | 5,059 / 1,161 | 263 / 6,010 | 0 | 259 / 5,976 | 0 / 5,811 | 361 / 5,814 | 0 | 334 / 46 |
| **macOS iconv** | 864 / 6,006 | 5,892 / 1,161 | 911 / 2 | 5,892 / 1,161 | 865 / 6,008 | 909 / 8 | 863 / 5,977 | 892 / 5,830 | 1,154 / 5,830 | 911 / 2 | 959 / 2 |
<!--/t-->

The [report](docs/divergences.md) explains each number; every number in this README and the
report is generated from the committed data (`python3 -m big5matrix report`).

## Try it

```
$ python3 -m big5matrix show C7 B3
decode C7 B3
  U+30B7 シ  (23)
      python.big5hkscs, go.big5, node.iconv-lite-big5, rust.big5, browser.chromium,
      java.x-ibm950, java.big5-hkscs, java.x-big5-hkscs-2001, java.x-ms950-hkscs,
      java.x-ms950-hkscs-xp, ruby.cp951, ruby.big5-hkscs, ruby.big5-uao, perl.big5-eten,
      perl.big5-hkscs, icu.ibm-950, icu.ibm-1375, icu.ibm-5471, iconv.big5-hkscs,
      iconv.big5-ibm, iconv.big5-plus, ref.whatwg, ref.hkscs-2016
  U+F760  (10)
      node.textdecoder, java.x-windows-950, dotnet.950, php.cp950, ruby.big5, ruby.cp950,
      perl.cp950, icu.windows-950-2000, icu.ibm-1373, ref.ms-bestfit950
  U+0401 Ё  (8)
      python.big5, python.cp950, java.big5, java.x-big5-solaris, php.big-5, iconv.big5,
      iconv.big5-2003, ref.unicode-big5
  error  (2)
      iconv.cp950, ref.ms-cp950
  error error  (1)
      node.iconv-lite-cp950
```

`show` takes bytes (`A145`), a character (`兀`) or a code point (`U+2027`). The data is in
the repository, so this needs only Python 3.9 or later and no other runtime.

## How it works

```
 cases.py: every 1- and 2-byte sequence (65,792), every BMP and plane-2 code point (129,028)
      │
      ├──► adapters/<runtime>/   one small program per runtime; reads cases on stdin, writes
      │                          results in one line format; built and run by the harness
      │
      ├──► reference.py          WHATWG algorithm + index, BIG5.TXT, CP950.TXT, bestfit950,
      │                          HKSCS-2016 (published tables, pinned by SHA-256)
      ▼
 data/decode/<impl>.txt.gz, data/encode/<impl>.txt.gz, data/manifest.json (versions, digests)
      │
      ├──► analyze.py ──► report/summary.json ──► docs/divergences.md, README (generated numbers)
      ├──► docs/ site (reads data/ and the summary directly, no copy)
      └──► check: re-run what is installed and compare (CI)
```

- **One protocol for every runtime.** An adapter receives `d<TAB>A140` or `e<TAB>00CA 0304`
  and answers with the code points or bytes it produced. Decoding uses the runtime's
  replacement mode, so the data shows how many bytes an error swallows; encoding is strict, so
  it shows the real mapping. Every case starts from a fresh converter. See
  [`adapters/README.md`](adapters/README.md) for how each runtime is called.
- **Version keys.** Each adapter reports the version that decides its behaviour (the x/text
  module for Go, the crate for Rust, ICU's version for ICU). The CI drift check re-runs every
  adapter the runner has: with the same key the results must be identical; with a newer key the
  differences are reported, not failed.
- **Compact, checkable data.** One result per line, in a fixed case order, gzip'd
  deterministically: <!--n:impls.runs-->40<!--/n--> converters and <!--n:impls.tables-->5<!--/n--> tables in 5.6 MB, every file under 100 KB. Each
  file names the case list it belongs to, and the manifest holds its SHA-256.
- **Second opinions.** The WHATWG column is the specification transcribed; it matches
  encoding_rs on all <!--n:decode.cases-->65,792<!--/n--> decode cases and Chromium on all but <!--n:fact.chromium.differs-->4<!--/n--> (a Chromium bug).
  `tools/verify_claims.py` re-checks each surprising claim by asking the runtime directly
  (its command-line tool or a few independent lines of code).

## Running it

Requirements: Python 3.9 or later (standard library only). Each runtime is optional; adapters
whose runtime is missing are skipped with a notice.

```sh
make build     # build the adapters whose runtime is installed, print their versions
make run       # run them over every case and update data/      (12.9 s on the machine below)
make analyze   # compute report/summary.json                     (43.9 s)
make report    # refresh the generated numbers in the documents
make check     # drift check: re-run and compare with the committed data
make test      # unit and integration tests
make verify    # check the report's claims a second way
make lint      # every language in the repository
make serve     # the site on 127.0.0.1 (prints the URL)
```

The data was collected on macOS 27.0 on an Apple M5 (10 cores, 16 GB), shared with other
work; `make run` ran four adapters at a time and re-running it reproduced the committed files
byte for byte. Runtimes tested: CPython 3.13.0, Go 1.27.1 with x/text v0.42.0, Node 25.5.0 with
iconv-lite 0.7.3, Rust 1.98.1 with encoding_rs 0.8.42, Chromium 153 (via playwright-core),
OpenJDK 27, .NET 10.0.12, PHP 8.5.11, Ruby 2.6.10 and Perl 5.34.1 (the macOS system versions),
ICU 78.3, and the macOS iconv. The [report](docs/divergences.md#2-what-was-tested) lists every
converter.

## Limitations

- Windows itself was not run; Microsoft's published bestfit950 table stands in for it and is
  labelled as a table. .NET's code page 950 is the only Microsoft converter run.
- glibc iconv and GNU libiconv (what most Linux programs use) were not available on the machine
  that produced the data. On Linux the iconv adapter is skipped rather than compared with
  macOS's data.
- Ruby and Perl are the old versions macOS ships. Firefox and Safari were not run (encoding_rs is
  Firefox's library).
- Cases are one or two bytes long; longer inputs are covered only by the check that a leading
  ASCII byte never changes the result.
- .NET's code page 20002 ("x-Chinese-Eten") is not a Big5 layout and is left out; PHP's
  `iconv()` is the system iconv and is not listed separately.

## Related work

Big5 tables have been compared before, and this project builds on that work:

- Bruno Haible's [conversion table comparison](https://www.haible.de/bruno/charsets/conversion-tables/Big5.html)
  (last modified January 2020) describes how the Big5 tables of libiconv, glibc, several JDKs,
  ICU, Windows and others differ from each other.
- HarJIT's [CNS and Big5 charts](https://harjit.moe/cns-conc.html) and the
  [ecma35lib](https://github.com/harjitmoe/ecma35lib) project compare mapping tables of Big5
  variants in detail; they compare tables, not running converters.
- MozTW's [Big5 page](https://moztw.org/docs/big5/) documents the variants (Big5-2003, UAO,
  HKSCS, the WHATWG standard) as tables.
- ICU's [icu-data](https://github.com/unicode-org/icu-data) repository keeps vendor mapping
  files collected from many systems, mostly from around 2000.
- The WHATWG Encoding Standard's Big5 definition came out of browser testing; see Anne van
  Kesteren's [2012 notes](https://annevankesteren.nl/2012/04/big5) and
  [whatwg/encoding#75](https://github.com/whatwg/encoding/issues/75).
- On security: WHATWG [issue #171](https://github.com/whatwg/encoding/issues/171) on ASCII after
  an invalid lead byte, and DEVCORE's
  [WorstFit](https://devco.re/blog/2025/01/09/worstfit-unveiling-hidden-transformers-in-windows-ansi/)
  research on Windows best-fit conversion.

What this project adds, to my knowledge, is running the current converters themselves rather
than comparing tables: every byte sequence and every relevant character through each runtime's
decoder and encoder, their error handling, and round trips within and between runtimes, with a
check that tracks how the results change as runtimes are updated.

## License

[MIT](LICENSE). The tables in [`reference/`](reference/) are third-party data under their own
terms; see [`reference/SOURCES.md`](reference/SOURCES.md).
