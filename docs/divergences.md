# Big5 in practice: what today's converters actually do

This document describes the data in [`data/`](../data). The prose is written by hand. The
numbers and tables are generated: each sits between HTML comment markers that name a value in
[`report/summary.json`](../report/summary.json), which `python3 -m big5matrix analyze` computes
from the data, and `python3 -m big5matrix report` refreshes them (view the Markdown source to
see which value each number is). A number that is not marked is a property of Big5 itself (157
trail bytes per lead byte, for example).

Data collected <!--n:collected.date-->2026-10-01<!--/n--> on <!--n:collected.platform-->Darwin 27.0 arm64<!--/n--> (an Apple M5 shared with
other work; nothing here is timing-sensitive). The site at
<https://useless-husband.github.io/big5-matrix/> shows every case.

## 1. Results in brief

- <!--n:impls.runs-->40<!--/n--> converters from <!--n:impls.runtimes-->12<!--/n--> runtimes and libraries, and <!--n:impls.tables-->5<!--/n--> published tables, were run
  over the whole one- and two-byte space (<!--n:decode.cases-->65,792<!--/n--> byte sequences) and over every
  BMP scalar value and every plane-2 code point (<!--n:encode.cases-->129,028<!--/n--> encode cases).
- All of them agree on the <!--n:decode.hanzi_cases-->13,053<!--/n--> hanzi of the Big5 core except
  <!--n:decode.hanzi_divergent-->1<!--/n-->. Outside the hanzi, they disagree on
  <!--n:decode.divergent_total-->19,467<!--/n--> of the <!--n:decode.nontrivial_cases-->33,024<!--/n--> byte sequences that do not start with an ASCII byte.
- By character map they fall into <!--n:families.multi-->6<!--/n--> families of two or more members plus a few one-off
  variants. Members of one family differ in at most <!--n:families.max_inside-->496<!--/n--> byte sequences; members
  of different families in at least <!--n:families.min_between-->655<!--/n-->.
- The name tells you little. `cp950` is Microsoft's table in Python, Perl and Ruby but IBM's
  in Java and ICU. Node.js's `TextDecoder('big5')` is not the WHATWG decoder it is documented
  as (it is ICU's `windows-950`, <!--n:fact.node.vs_whatwg-->6,253<!--/n--> byte sequences different from WHATWG);
  Chromium's is.
- Writing text as "big5" in one runtime and reading it as "big5" in another loses or changes
  characters in all but <!--n:pair.big5.clean-->11<!--/n--> of the <!--n:pair.big5.total-->110<!--/n--> ordered pairs of
  runtimes tested. Example: Python writes Ё as `C7 B3`, which Go and browsers read as シ.
- Eight problems look like bugs rather than variant choices (section 9), among them: macOS
  iconv's BIG5-HKSCS cannot encode <!--n:fact.iconv.hkscs.hanzi_unencodable-->12,634<!--/n--> of the <!--n:fact.iconv.hkscs.hanzi_total-->13,053<!--/n--> ordinary hanzi, macOS iconv
  silently turns `‹` into `<` and `„` into `"`, Chromium decodes `88 62` to a lone surrogate,
  and Go's decoder swallows an ASCII byte where the WHATWG standard it follows keeps it.

## 2. What was tested

<!--t:implementations-->
| Column | What | Version tested | Ops |
| --- | --- | --- | --- |
| `python.big5` | Python codecs big5 | CPython 3.13.0 (CPython) | both |
| `python.cp950` | Python codecs cp950 | CPython 3.13.0 (CPython) | both |
| `python.big5hkscs` | Python codecs big5hkscs | CPython 3.13.0 (CPython) | both |
| `go.big5` | Go x/text traditionalchinese.Big5 | golang.org/x/text v0.42.0 (go1.27.1) | both |
| `node.textdecoder` | Node.js TextDecoder('big5') | Node 25.5.0 (ICU 78.2), iconv-lite 0.7.3 | decode |
| `node.iconv-lite-big5` | Node.js iconv-lite big5 | Node 25.5.0 (ICU 78.2), iconv-lite 0.7.3 | both |
| `node.iconv-lite-cp950` | Node.js iconv-lite cp950 | Node 25.5.0 (ICU 78.2), iconv-lite 0.7.3 | both |
| `rust.big5` | Rust encoding_rs BIG5 | encoding_rs 0.8.42 (rustc 1.98.1) | both |
| `browser.chromium` | Chromium TextDecoder('big5') | Chromium 153.0.8010.12 (headless, Playwright) | decode |
| `java.big5` | Java Big5 | OpenJDK 64-Bit Server VM 27 (Homebrew) | both |
| `java.x-windows-950` | Java x-windows-950 | OpenJDK 64-Bit Server VM 27 (Homebrew) | both |
| `java.x-ibm950` | Java x-IBM950 | OpenJDK 64-Bit Server VM 27 (Homebrew) | both |
| `java.x-big5-solaris` | Java x-Big5-Solaris | OpenJDK 64-Bit Server VM 27 (Homebrew) | both |
| `java.big5-hkscs` | Java Big5-HKSCS | OpenJDK 64-Bit Server VM 27 (Homebrew) | both |
| `java.x-big5-hkscs-2001` | Java x-Big5-HKSCS-2001 | OpenJDK 64-Bit Server VM 27 (Homebrew) | both |
| `java.x-ms950-hkscs` | Java x-MS950-HKSCS | OpenJDK 64-Bit Server VM 27 (Homebrew) | both |
| `java.x-ms950-hkscs-xp` | Java x-MS950-HKSCS-XP | OpenJDK 64-Bit Server VM 27 (Homebrew) | both |
| `dotnet.950` | .NET code page 950 (strict) | .NET 10.0.12 (System.Text.Encoding.CodePages 10.0.0.0) | both |
| `dotnet.950-default` | .NET code page 950 (default fallbacks) | .NET 10.0.12 (System.Text.Encoding.CodePages 10.0.0.0) | encode |
| `php.big-5` | PHP mbstring BIG-5 | PHP 8.5.11 mbstring 8.5.11 | both |
| `php.cp950` | PHP mbstring CP950 | PHP 8.5.11 mbstring 8.5.11 | both |
| `ruby.big5` | Ruby Big5 | Ruby 2.6.10p210 (universal.arm64e-darwin26) | both |
| `ruby.cp950` | Ruby CP950 | Ruby 2.6.10p210 (universal.arm64e-darwin26) | both |
| `ruby.cp951` | Ruby CP951 | Ruby 2.6.10p210 (universal.arm64e-darwin26) | both |
| `ruby.big5-hkscs` | Ruby Big5-HKSCS | Ruby 2.6.10p210 (universal.arm64e-darwin26) | both |
| `ruby.big5-uao` | Ruby Big5-UAO | Ruby 2.6.10p210 (universal.arm64e-darwin26) | both |
| `perl.big5-eten` | Perl Encode big5-eten | Perl 5.34.1, Encode 3.0801, Encode::TW 2.03 | both |
| `perl.cp950` | Perl Encode cp950 | Perl 5.34.1, Encode 3.0801, Encode::TW 2.03 | both |
| `perl.big5-hkscs` | Perl Encode big5-hkscs | Perl 5.34.1, Encode 3.0801, Encode::TW 2.03 | both |
| `icu.windows-950-2000` | ICU windows-950-2000 (Big5, windows-950) | ICU 78.3 (ucnv C API) | both |
| `icu.ibm-950` | ICU ibm-950_P110-1999 (cp950, x-IBM950) | ICU 78.3 (ucnv C API) | both |
| `icu.ibm-1373` | ICU ibm-1373_P100-2002 (ibm-1373) | ICU 78.3 (ucnv C API) | both |
| `icu.ibm-1375` | ICU ibm-1375_P100-2008 (Big5-HKSCS) | ICU 78.3 (ucnv C API) | both |
| `icu.ibm-5471` | ICU ibm-5471_P100-2006 (MS950_HKSCS, x-MS950-HKSCS) | ICU 78.3 (ucnv C API) | both |
| `iconv.big5` | macOS iconv BIG5 | macOS 27.0 (26A428) libiconv (Citrus) | both |
| `iconv.cp950` | macOS iconv CP950 | macOS 27.0 (26A428) libiconv (Citrus) | both |
| `iconv.big5-hkscs` | macOS iconv BIG5-HKSCS | macOS 27.0 (26A428) libiconv (Citrus) | both |
| `iconv.big5-2003` | macOS iconv BIG5-2003 | macOS 27.0 (26A428) libiconv (Citrus) | both |
| `iconv.big5-ibm` | macOS iconv BIG5-IBM | macOS 27.0 (26A428) libiconv (Citrus) | both |
| `iconv.big5-plus` | macOS iconv BIG5-PLUS | macOS 27.0 (26A428) libiconv (Citrus) | both |
| `ref.whatwg` | WHATWG Encoding Standard (algorithm + index-big5) | table | both |
| `ref.unicode-big5` | Unicode BIG5.TXT (table) | table | decode |
| `ref.ms-cp950` | Microsoft CP950.TXT (table) | table | decode |
| `ref.ms-bestfit950` | Microsoft bestfit950.txt (table, with best fit) | table | both |
| `ref.hkscs-2016` | HKSCS-2016 data set (table, HKSCS part only) | table | decode |
<!--/t-->

Each converter runs behind a small adapter ([`adapters/`](../adapters)) that reads cases on
standard input and writes results in one line format. Decoding uses the runtime's replacement
mode where it has one (what `new String(bytes, cs)`, `bytes.decode(enc, "replace")` and similar
calls do), so an error shows up as U+FFFD followed by whatever the converter does next; macOS
iconv has no such mode and records where it stops. Encoding is strict: an unmappable character
is reported, not replaced, except in the `.NET (default fallbacks)` column, which records what
`Encoding.GetEncoding(950).GetBytes()` does out of the box. Every case starts from a fresh
converter state, and the end of a case is the end of the input.

The five tables are not runs. The WHATWG column is the Encoding Standard's Big5 decoder and
encoder transcribed from the specification and run over its index; it agrees with
encoding_rs (Firefox's implementation) on every one of the <!--n:decode.cases-->65,792<!--/n--> decode cases
(<!--n:fact.rust.differs-->0<!--/n--> differences) and on every encode case (<!--n:fact.rust.encode_differs-->0<!--/n--> differences), and with
Chromium on all but <!--n:fact.chromium.differs-->4<!--/n--> decode cases (a Chromium bug, section 9). Microsoft's
bestfit950.txt stands in for Windows, which was not available; it is labelled as a table
throughout.

## 3. A short history of Big5

Big5 was defined in 1984 by Taiwan's Institute for Information Industry for a group of five
computer makers. It is a double-byte code: a lead byte 0x81–0xFE followed by a trail byte
0x40–0x7E or 0xA1–0xFE (157 values), with ASCII below 0x80. The 1984 set placed 408 symbols at
0xA140–0xA3BF, 5,401 frequent hanzi at 0xA440–0xC67E and 7,652 less frequent ones at
0xC940–0xF9D5, and left the rest unassigned. Two of the hanzi were encoded twice by mistake
(兀 and 嗀), and several symbols were never given an agreed Unicode equivalent, which is where
most of the symbol disputes below come from.

The unassigned space filled up differently in different places:

- **ETEN.** The ETEN Chinese system, widely used in the late 1980s, added kana, Cyrillic,
  circled numbers and other symbols at 0xC6A1–0xC8D3, and seven hanzi plus box-drawing
  characters at 0xF9D6–0xF9FE.
- **Microsoft code page 950** took ETEN's 0xF9D6–0xF9FE row, declared 0x8140–0xA0FE,
  0xC6A1–0xC8FE and 0xFA40–0xFEFE user-defined (Windows maps them to the Private Use Area,
  U+E000–U+F848), and later added the Euro sign at 0xA3E1. Its "best fit" table also maps
  characters it cannot represent to look-alikes when encoding.
- **Unicode's BIG5.TXT** (Unicode 1.1, kept as an obsolete mapping) has no user-defined area,
  no 0xF9D6–0xF9FE row, and its own layout of kana and Cyrillic at 0xC6A1–0xC7FC, which is not
  ETEN's.
- **Big5-2003**, a later Taiwanese standardisation, took in ETEN's extensions and the Euro
  sign.
- **HKSCS**, the Hong Kong Supplementary Character Set (1999, then 2001, 2004, 2008 and 2016),
  put about 5,000 characters used in Hong Kong into 0x8740–0xA0FE, 0xC6A1–0xC8FE and
  0xFA40–0xFEFE. Early editions mapped many of them to the Private Use Area because Unicode
  did not have them yet; later ones point to CJK Extension B and beyond, and four codes
  (0x8862, 0x8864, 0x88A3, 0x88A5) stand for a letter plus a combining mark.
- **Unicode-at-on (UAO)** is a community extension, popular with Taiwanese BBS software, that
  put many more Unicode characters (simplified Chinese and Japanese among them) into the same
  spare rows.
- **WHATWG.** Browsers needed one answer. From 2012 the WHATWG Encoding Standard defined a
  single "big5" (with "big5-hkscs" as another label for it): a decoder with HKSCS mappings at
  their Unicode code points plus code page 950's symbols and Euro sign, and an encoder that
  avoids writing the HKSCS rows. It also defines error handling exactly, including that an
  ASCII byte after a lead byte is never part of an invalid character.

So a byte sequence such as `C7 B3` is Ё in one table, シ in another and a Private Use code point
in a third, and each runtime picked one of these lineages, sometimes several under different
names.

## 4. Families: what each implementation really implements

The distance between two decoders is the number of byte sequences that are a character for at
least one of them and not the same character for both. Grouping decoders whose distance is at
most 400 (single linkage) gives these families:

<!--t:families-->
| # | Family | Members | Max. distance inside |
| ---: | --- | --- | ---: |
| 1 | Plain Big5: Unicode BIG5.TXT and Microsoft CP950.TXT, no user-defined areas | `python.big5`, `python.cp950`, `node.iconv-lite-cp950`, `java.big5`, `java.x-big5-solaris`, `php.big-5`, `ruby.big5`, `perl.big5-eten`, `iconv.cp950`, `iconv.big5-ibm`, `ref.unicode-big5`, `ref.ms-cp950` | 496 |
| 2 | Windows code page 950 (user-defined areas mapped to the Private Use Area) | `node.textdecoder`, `java.x-windows-950`, `dotnet.950`, `php.cp950`, `ruby.cp950`, `perl.cp950`, `icu.windows-950-2000`, `icu.ibm-1373`, `iconv.big5`, `iconv.big5-2003`, `ref.ms-bestfit950` | 419 |
| 3 | WHATWG Big5 (HKSCS characters at their Unicode code points) | `python.big5hkscs`, `go.big5`, `node.iconv-lite-big5`, `rust.big5`, `browser.chromium`, `java.big5-hkscs`, `java.x-big5-hkscs-2001`, `ruby.big5-hkscs`, `ref.whatwg` | 367 |
| 4 | IBM-950 | `java.x-ibm950`, `icu.ibm-950` | 0 |
| 5 | Microsoft's Big5-HKSCS (MS950_HKSCS) | `java.x-ms950-hkscs`, `iconv.big5-hkscs` | 56 |
| 6 | Code page 951: Microsoft's HKSCS-2001 table as on Windows XP | `java.x-ms950-hkscs-xp`, `ruby.cp951` | 79 |
| 7 | (single implementation) | `ruby.big5-uao` | 0 |
| 8 | (single implementation) | `perl.big5-hkscs` | 0 |
| 9 | (single implementation) | `icu.ibm-1375` | 0 |
| 10 | (single implementation) | `icu.ibm-5471` | 0 |
| 11 | (single implementation) | `iconv.big5-plus` | 0 |
<!--/t-->

The next table names what each column implements, region by region. "= X" means the column's
characters in that region are exactly those of table X (a partial table such as HKSCS-2016 is
compared only where it has entries); "≈ X (n)" means table X is the closest and n byte
sequences differ; "PUA" means every character there is a Private Use code point; "—" means it
decodes nothing there.

<!--t:variants-->
| Column | Family | Nearest table (differences) | 8140–A0FE | A140–A3BF | A3C0–A3FE | A440–C67E | C6A1–C8FE | C940–F9D5 | F9D6–F9FE | FA40–FEFE |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `python.big5` | 1 | BIG5.TXT (7) | — | ≈ BIG5.TXT (7) | — | = WHATWG, BIG5.TXT, CP950.TXT, bestfit950 | = BIG5.TXT | = WHATWG, BIG5.TXT, CP950.TXT, bestfit950 | — | — |
| `python.cp950` | 1 | BIG5.TXT (60) | — | = WHATWG, CP950.TXT, bestfit950 | = CP950.TXT, bestfit950 | = WHATWG, BIG5.TXT, CP950.TXT, bestfit950 | = BIG5.TXT | = WHATWG, BIG5.TXT, CP950.TXT, bestfit950 | = CP950.TXT, bestfit950 | — |
| `python.big5hkscs` | 3 | WHATWG (203) | ≈ HKSCS-2016 (71) | ≈ BIG5.TXT (7) | — | = WHATWG, BIG5.TXT, CP950.TXT, bestfit950 | = HKSCS-2016 | = WHATWG, BIG5.TXT, CP950.TXT, bestfit950 | = WHATWG, HKSCS-2016 | = HKSCS-2016 |
| `go.big5` | 3 | WHATWG (0) | = WHATWG | = WHATWG, CP950.TXT, bestfit950 | = WHATWG | = WHATWG, BIG5.TXT, CP950.TXT, bestfit950 | = WHATWG, HKSCS-2016 | = WHATWG, BIG5.TXT, CP950.TXT, bestfit950 | = WHATWG, HKSCS-2016 | = WHATWG, HKSCS-2016 |
| `node.textdecoder` | 2 | bestfit950 (0) | = bestfit950 | = WHATWG, CP950.TXT, bestfit950 | = CP950.TXT, bestfit950 | = WHATWG, BIG5.TXT, CP950.TXT, bestfit950 | = bestfit950 | = WHATWG, BIG5.TXT, CP950.TXT, bestfit950 | = CP950.TXT, bestfit950 | = bestfit950 |
| `node.iconv-lite-big5` | 3 | WHATWG (0) | = WHATWG | = WHATWG, CP950.TXT, bestfit950 | = WHATWG | = WHATWG, BIG5.TXT, CP950.TXT, bestfit950 | = WHATWG, HKSCS-2016 | = WHATWG, BIG5.TXT, CP950.TXT, bestfit950 | = WHATWG, HKSCS-2016 | = WHATWG, HKSCS-2016 |
| `node.iconv-lite-cp950` | 1 | CP950.TXT (0) | — | = WHATWG, CP950.TXT, bestfit950 | = CP950.TXT, bestfit950 | = WHATWG, BIG5.TXT, CP950.TXT, bestfit950 | — | = WHATWG, BIG5.TXT, CP950.TXT, bestfit950 | = CP950.TXT, bestfit950 | — |
| `rust.big5` | 3 | WHATWG (0) | = WHATWG | = WHATWG, CP950.TXT, bestfit950 | = WHATWG | = WHATWG, BIG5.TXT, CP950.TXT, bestfit950 | = WHATWG, HKSCS-2016 | = WHATWG, BIG5.TXT, CP950.TXT, bestfit950 | = WHATWG, HKSCS-2016 | = WHATWG, HKSCS-2016 |
| `browser.chromium` | 3 | WHATWG (4) | ≈ WHATWG (4) | = WHATWG, CP950.TXT, bestfit950 | = WHATWG | = WHATWG, BIG5.TXT, CP950.TXT, bestfit950 | = WHATWG, HKSCS-2016 | = WHATWG, BIG5.TXT, CP950.TXT, bestfit950 | = WHATWG, HKSCS-2016 | = WHATWG, HKSCS-2016 |
| `java.big5` | 1 | BIG5.TXT (5) | — | ≈ BIG5.TXT (5) | — | = WHATWG, BIG5.TXT, CP950.TXT, bestfit950 | = BIG5.TXT | = WHATWG, BIG5.TXT, CP950.TXT, bestfit950 | — | — |
| `java.x-windows-950` | 2 | bestfit950 (2) | = bestfit950 | = WHATWG, CP950.TXT, bestfit950 | = CP950.TXT, bestfit950 | = WHATWG, BIG5.TXT, CP950.TXT, bestfit950 | = bestfit950 | = WHATWG, BIG5.TXT, CP950.TXT, bestfit950 | = CP950.TXT, bestfit950 | = bestfit950 |
| `java.x-ibm950` | 4 | bestfit950 (1098) | = bestfit950 | ≈ WHATWG (7) | ≈ WHATWG (1) | ≈ WHATWG (1) | ≈ HKSCS-2016 (52), 1 PUA | = WHATWG, BIG5.TXT, CP950.TXT, bestfit950 | PUA | = bestfit950 |
| `java.x-big5-solaris` | 1 | BIG5.TXT (12) | — | ≈ BIG5.TXT (5) | — | = WHATWG, BIG5.TXT, CP950.TXT, bestfit950 | = BIG5.TXT | = WHATWG, BIG5.TXT, CP950.TXT, bestfit950 | ≈ BIG5.TXT (7) | — |
| `java.big5-hkscs` | 3 | WHATWG (144) | ≈ HKSCS-2016 (7) | ≈ BIG5.TXT (5) | — | = WHATWG, BIG5.TXT, CP950.TXT, bestfit950 | = HKSCS-2016 | = WHATWG, BIG5.TXT, CP950.TXT, bestfit950 | = WHATWG, HKSCS-2016 | = HKSCS-2016 |
| `java.x-big5-hkscs-2001` | 3 | WHATWG (367) | ≈ HKSCS-2016 (226), 31 PUA | ≈ BIG5.TXT (5) | — | = WHATWG, BIG5.TXT, CP950.TXT, bestfit950 | ≈ HKSCS-2016 (4), 4 PUA | = WHATWG, BIG5.TXT, CP950.TXT, bestfit950 | = WHATWG, HKSCS-2016 | = HKSCS-2016 |
| `java.x-ms950-hkscs` | 5 | WHATWG (1286) | ≈ HKSCS-2016 (7), 1182 PUA | = WHATWG, CP950.TXT, bestfit950 | = CP950.TXT, bestfit950 | = WHATWG, BIG5.TXT, CP950.TXT, bestfit950 | = HKSCS-2016 | = WHATWG, BIG5.TXT, CP950.TXT, bestfit950 | = WHATWG, HKSCS-2016 | = HKSCS-2016 |
| `java.x-ms950-hkscs-xp` | 6 | bestfit950 (3016) | ≈ HKSCS-2016 (1664), 2838 PUA | = WHATWG, CP950.TXT, bestfit950 | = CP950.TXT, bestfit950 | = WHATWG, BIG5.TXT, CP950.TXT, bestfit950 | ≈ HKSCS-2016 (7), 56 PUA | = WHATWG, BIG5.TXT, CP950.TXT, bestfit950 | = WHATWG, HKSCS-2016 | ≈ HKSCS-2016 (288), 310 PUA |
| `dotnet.950` | 2 | bestfit950 (10) | = bestfit950 | ≈ WHATWG (6) | = CP950.TXT, bestfit950 | = WHATWG, BIG5.TXT, CP950.TXT, bestfit950 | = bestfit950 | = WHATWG, BIG5.TXT, CP950.TXT, bestfit950 | ≈ CP950.TXT (4) | = bestfit950 |
| `php.big-5` | 1 | BIG5.TXT (42) | — | ≈ BIG5.TXT (1) | — | = WHATWG, BIG5.TXT, CP950.TXT, bestfit950 | = BIG5.TXT | = WHATWG, BIG5.TXT, CP950.TXT, bestfit950 | = CP950.TXT, bestfit950 | — |
| `php.cp950` | 2 | bestfit950 (3) | = bestfit950 | = WHATWG, CP950.TXT, bestfit950 | — | = WHATWG, BIG5.TXT, CP950.TXT, bestfit950 | = bestfit950 | = WHATWG, BIG5.TXT, CP950.TXT, bestfit950 | = CP950.TXT, bestfit950 | = bestfit950 |
| `ruby.big5` | 1 | CP950.TXT (408) | — | = WHATWG, CP950.TXT, bestfit950 | = CP950.TXT, bestfit950 | = WHATWG, BIG5.TXT, CP950.TXT, bestfit950 | = bestfit950 | = WHATWG, BIG5.TXT, CP950.TXT, bestfit950 | = CP950.TXT, bestfit950 | — |
| `ruby.cp950` | 2 | bestfit950 (2) | = bestfit950 | = WHATWG, CP950.TXT, bestfit950 | = CP950.TXT, bestfit950 | = WHATWG, BIG5.TXT, CP950.TXT, bestfit950 | = bestfit950 | = WHATWG, BIG5.TXT, CP950.TXT, bestfit950 | = CP950.TXT, bestfit950 | = bestfit950 |
| `ruby.cp951` | 6 | bestfit950 (3094) | ≈ HKSCS-2016 (1585), 2760 PUA | = WHATWG, CP950.TXT, bestfit950 | = CP950.TXT, bestfit950 | = WHATWG, BIG5.TXT, CP950.TXT, bestfit950 | ≈ HKSCS-2016 (7), 56 PUA | = WHATWG, BIG5.TXT, CP950.TXT, bestfit950 | = WHATWG, HKSCS-2016 | ≈ HKSCS-2016 (288), 310 PUA |
| `ruby.big5-hkscs` | 3 | WHATWG (222) | ≈ HKSCS-2016 (75) | = BIG5.TXT | — | = WHATWG, BIG5.TXT, CP950.TXT, bestfit950 | = HKSCS-2016 | = WHATWG, BIG5.TXT, CP950.TXT, bestfit950 | ≈ WHATWG (8) | = HKSCS-2016 |
| `ruby.big5-uao` | 7 | WHATWG (5926) | ≈ HKSCS-2016 (3846), 133 PUA | = WHATWG, CP950.TXT, bestfit950 | ≈ WHATWG (29), 29 PUA | = WHATWG, BIG5.TXT, CP950.TXT, bestfit950 | ≈ HKSCS-2016 (44), 15 PUA | = WHATWG, BIG5.TXT, CP950.TXT, bestfit950 | = CP950.TXT, bestfit950 | ≈ bestfit950 (672), 113 PUA |
| `perl.big5-eten` | 1 | CP950.TXT (409) | — | ≈ WHATWG (3) | = CP950.TXT, bestfit950 | ≈ WHATWG (1) | ≈ HKSCS-2016 (24), 46 PUA | = WHATWG, BIG5.TXT, CP950.TXT, bestfit950 | = CP950.TXT, bestfit950 | — |
| `perl.cp950` | 2 | bestfit950 (0) | = bestfit950 | = WHATWG, CP950.TXT, bestfit950 | = CP950.TXT, bestfit950 | = WHATWG, BIG5.TXT, CP950.TXT, bestfit950 | = bestfit950 | = WHATWG, BIG5.TXT, CP950.TXT, bestfit950 | = CP950.TXT, bestfit950 | = bestfit950 |
| `perl.big5-hkscs` | 8 | WHATWG (2005) | ≈ HKSCS-2016 (1585), 1413 PUA | ≈ WHATWG (3) | = CP950.TXT, bestfit950 | ≈ WHATWG (1) | ≈ HKSCS-2016 (7), 49 PUA | = WHATWG, BIG5.TXT, CP950.TXT, bestfit950 | = WHATWG, HKSCS-2016 | ≈ HKSCS-2016 (288), 288 PUA |
| `icu.windows-950-2000` | 2 | bestfit950 (0) | = bestfit950 | = WHATWG, CP950.TXT, bestfit950 | = CP950.TXT, bestfit950 | = WHATWG, BIG5.TXT, CP950.TXT, bestfit950 | = bestfit950 | = WHATWG, BIG5.TXT, CP950.TXT, bestfit950 | = CP950.TXT, bestfit950 | = bestfit950 |
| `icu.ibm-950` | 4 | bestfit950 (1098) | = bestfit950 | ≈ WHATWG (7) | ≈ WHATWG (1) | ≈ WHATWG (1) | ≈ HKSCS-2016 (52), 1 PUA | = WHATWG, BIG5.TXT, CP950.TXT, bestfit950 | PUA | = bestfit950 |
| `icu.ibm-1373` | 2 | bestfit950 (3) | = bestfit950 | = WHATWG, CP950.TXT, bestfit950 | = CP950.TXT, bestfit950 | ≈ WHATWG (1) | = bestfit950 | = WHATWG, BIG5.TXT, CP950.TXT, bestfit950 | = CP950.TXT, bestfit950 | = bestfit950 |
| `icu.ibm-1375` | 9 | WHATWG (789) | ≈ HKSCS-2016 (38), 661 PUA | = WHATWG, CP950.TXT, bestfit950 | = CP950.TXT, bestfit950 | = WHATWG, BIG5.TXT, CP950.TXT, bestfit950 | ≈ HKSCS-2016 (3), 3 PUA | = WHATWG, BIG5.TXT, CP950.TXT, bestfit950 | = WHATWG, HKSCS-2016 | = HKSCS-2016 |
| `icu.ibm-5471` | 10 | WHATWG (2629) | ≈ HKSCS-2016 (1585), 2019 PUA | = WHATWG, CP950.TXT, bestfit950 | = CP950.TXT, bestfit950 | = WHATWG, BIG5.TXT, CP950.TXT, bestfit950 | ≈ HKSCS-2016 (7), 7 PUA | = WHATWG, BIG5.TXT, CP950.TXT, bestfit950 | = WHATWG, HKSCS-2016 | ≈ HKSCS-2016 (288), 288 PUA |
| `iconv.big5` | 2 | bestfit950 (382) | = bestfit950 | ≈ BIG5.TXT (7) | — | = WHATWG, BIG5.TXT, CP950.TXT, bestfit950 | ≈ BIG5.TXT (116), 42 PUA | = WHATWG, BIG5.TXT, CP950.TXT, bestfit950 | = CP950.TXT, bestfit950 | = bestfit950 |
| `iconv.cp950` | 1 | CP950.TXT (0) | — | = WHATWG, CP950.TXT, bestfit950 | = CP950.TXT, bestfit950 | = WHATWG, BIG5.TXT, CP950.TXT, bestfit950 | — | = WHATWG, BIG5.TXT, CP950.TXT, bestfit950 | = CP950.TXT, bestfit950 | — |
| `iconv.big5-hkscs` | 5 | WHATWG (1267) | ≈ HKSCS-2016 (7), 1178 PUA | ≈ BIG5.TXT (7) | ≈ WHATWG (1) | = WHATWG, BIG5.TXT, CP950.TXT, bestfit950 | = HKSCS-2016 | = WHATWG, BIG5.TXT, CP950.TXT, bestfit950 | = WHATWG, HKSCS-2016 | = HKSCS-2016 |
| `iconv.big5-2003` | 2 | bestfit950 (411) | = bestfit950 | ≈ BIG5.TXT (7) | ≈ WHATWG (1) | = WHATWG, BIG5.TXT, CP950.TXT, bestfit950 | ≈ BIG5.TXT (159), 45 PUA | = WHATWG, BIG5.TXT, CP950.TXT, bestfit950 | = CP950.TXT, bestfit950 | = bestfit950 |
| `iconv.big5-ibm` | 1 | BIG5.TXT (396) | — | ≈ BIG5.TXT (7) | ≈ WHATWG (2) | = WHATWG, BIG5.TXT, CP950.TXT, bestfit950 | ≈ HKSCS-2016 (52), 1 PUA | = WHATWG, BIG5.TXT, CP950.TXT, bestfit950 | PUA | — |
| `iconv.big5-plus` | 11 | bestfit950 (8103) | ≈ bestfit950 (3454), 1570 PUA | ≈ BIG5.TXT (7) | ≈ WHATWG (30) | = WHATWG, BIG5.TXT, CP950.TXT, bestfit950 | ≈ HKSCS-2016 (131) | = WHATWG, BIG5.TXT, CP950.TXT, bestfit950 | ≈ WHATWG (5) | = bestfit950 |
| `ref.whatwg` | 3 | CP950.TXT (5092) | = WHATWG | = WHATWG, CP950.TXT, bestfit950 | = WHATWG | = WHATWG, BIG5.TXT, CP950.TXT, bestfit950 | = WHATWG, HKSCS-2016 | = WHATWG, BIG5.TXT, CP950.TXT, bestfit950 | = WHATWG, HKSCS-2016 | = WHATWG, HKSCS-2016 |
| `ref.unicode-big5` | 1 | CP950.TXT (309) | — | = BIG5.TXT | — | = WHATWG, BIG5.TXT, CP950.TXT, bestfit950 | = BIG5.TXT | = WHATWG, BIG5.TXT, CP950.TXT, bestfit950 | — | — |
| `ref.ms-cp950` | 1 | BIG5.TXT (309) | — | = WHATWG, CP950.TXT, bestfit950 | = CP950.TXT, bestfit950 | = WHATWG, BIG5.TXT, CP950.TXT, bestfit950 | — | = WHATWG, BIG5.TXT, CP950.TXT, bestfit950 | = CP950.TXT, bestfit950 | — |
| `ref.ms-bestfit950` | 2 | CP950.TXT (6219) | = bestfit950 | = WHATWG, CP950.TXT, bestfit950 | = CP950.TXT, bestfit950 | = WHATWG, BIG5.TXT, CP950.TXT, bestfit950 | = bestfit950 | = WHATWG, BIG5.TXT, CP950.TXT, bestfit950 | = CP950.TXT, bestfit950 | = bestfit950 |
<!--/t-->

What stands out:

- **Plain Big5 is still the default in several runtimes.** Python's `big5`, Java's `Big5` and
  PHP's `BIG-5` are within a few dozen byte sequences of BIG5.TXT, including its layout of
  0xC6A1–0xC7FC, and reject the user-defined rows. Perl's `big5` (an alias of `big5-eten`) is
  CP950.TXT plus ETEN's row 0xC6A1–0xC8FE, also without the user-defined rows.
- **`cp950` means two different things.** Python's `cp950`, Perl's `cp950`, Ruby's `CP950` and
  PHP's `CP950` are Microsoft's table (Python's without the user-defined areas). In Java and
  ICU the name `cp950` resolves to IBM-950 (`x-IBM950`, `ibm-950_P110-1999`), which differs
  from Microsoft's in more than a thousand byte sequences, uses trail bytes 0x80–0xA0 for IBM
  extensions and, in ICU, maps the control bytes 0x1A, 0x1C and 0x7F to other control
  characters. Microsoft's table is `ms950` or `x-windows-950` in Java and `windows-950` in ICU.
- **Node.js is not the browser.** Node's `TextDecoder('big5')` gives the same result as ICU's
  `windows-950-2000` on every case, so it decodes HKSCS bytes to Private Use code points and
  0x80 and 0xFF as characters. Chromium and encoding_rs implement the WHATWG decoder.
- **Hong Kong data has no single answer.** The HKSCS columns spread over several families
  depending on the edition they follow and on whether they use Private Use code points:
  Python's `big5hkscs`, Java's `Big5-HKSCS` and Ruby's `Big5-HKSCS` map every HKSCS character
  in 0x8140–0xA0FE to a Unicode character, while Java's and macOS's MS950-style converters,
  Ruby's `CP951`, Perl's `big5-hkscs` and ICU's `ibm-1375` and `ibm-5471` map hundreds to
  thousands of them to Private Use code points instead (the 0x8140–0xA0FE column above gives
  the count for each).

## 5. Malformed input

Real Big5 data contains errors: truncated files, text cut in the middle of a character,
mislabelled data. The decoders disagree on what an error costs.

<!--t:error-handling-->
| Decoder | Error marker | Lead + ASCII 00–3F/7F | Lead + unmapped ASCII 40–7E | Lead + 80–A0/FF | Lead at end | Bytes 80 / FF |
| --- | --- | --- | --- | --- | --- | --- |
| `python.big5` | U+FFFD | kept | kept | two errors | error | error / error |
| `python.cp950` | U+FFFD | kept | kept | two errors | error | error / error |
| `python.big5hkscs` | U+FFFD | kept | kept | two errors | error | error / error |
| `go.big5` | U+FFFD | kept 8,064, swallowed 126 | swallowed | swallowed | error | error / error |
| `node.textdecoder` | U+FFFD | kept | none (all are characters) | kept 126, swallowed 4,158 | error | U+0080 / U+F8F8 |
| `node.iconv-lite-big5` | U+FFFD | kept | kept | two errors | error | error / error |
| `node.iconv-lite-cp950` | U+FFFD | kept | kept | two errors | error | error / error |
| `rust.big5` | U+FFFD | kept | kept | swallowed | error | error / error |
| `browser.chromium` | U+FFFD | kept | kept | swallowed | error | error / error |
| `java.big5` | U+FFFD | kept | kept | swallowed 2,992, two errors 1,292 | error | error / error |
| `java.x-windows-950` | U+FFFD | kept | none (all are characters) | swallowed 252, two errors 4,032 | error | error / error |
| `java.x-ibm950` | U+FFFD | kept | kept | swallowed 252, two errors 3,427, character 605 | error | error / error |
| `java.x-big5-solaris` | U+FFFD | kept | kept | swallowed 2,992, two errors 1,292 | error | error / error |
| `java.big5-hkscs` | U+FFFD | swallowed | swallowed | swallowed | error | error / error |
| `java.x-big5-hkscs-2001` | U+FFFD | swallowed | swallowed | swallowed | error | error / error |
| `java.x-ms950-hkscs` | U+FFFD | swallowed | none (all are characters) | swallowed | error | error / error |
| `java.x-ms950-hkscs-xp` | U+FFFD | swallowed | none (all are characters) | swallowed | error | error / error |
| `dotnet.950` | U+FFFD | swallowed | none (all are characters) | swallowed | error | U+0080 / U+F8F8 |
| `php.big-5` | U+FFFD | kept 2,405, swallowed 5,785 | kept 2,394, swallowed 2 | swallowed 3,026, two errors 1,258 | error | error / error |
| `php.cp950` | U+FFFD | swallowed | none (all are characters) | swallowed | error | error / error |
| `ruby.big5` | U+FFFD | kept | swallowed | two errors | error | error / error |
| `ruby.cp950` | U+FFFD | kept | none (all are characters) | two errors | error | error / error |
| `ruby.cp951` | U+FFFD | kept | none (all are characters) | two errors | error | error / error |
| `ruby.big5-hkscs` | U+FFFD | kept | swallowed | two errors | error | error / error |
| `ruby.big5-uao` | U+FFFD | kept | none (all are characters) | two errors | error | error / error |
| `perl.big5-eten` | U+FFFD | kept | kept | two errors | dropped 89, error 37 | error / error |
| `perl.cp950` | U+FFFD | kept | none (all are characters) | kept 252, swallowed 4,032 | dropped | U+0080 / U+F8F8 |
| `perl.big5-hkscs` | U+FFFD | kept | kept | swallowed 3,150, two errors 1,134 | dropped 119, error 7 | error / error |
| `icu.windows-950-2000` | U+FFFD | kept | none (all are characters) | kept 126, swallowed 4,158 | error | U+0080 / U+F8F8 |
| `icu.ibm-950` | U+001A (marked), U+FFFD for some errors | kept | swallowed | swallowed 3,553, two errors 126, character 605 | error | error / error |
| `icu.ibm-1373` | U+001A (marked), U+FFFD for some errors | kept | none (all are characters) | swallowed 4,158, two errors 126 | error | error / error |
| `icu.ibm-1375` | U+FFFD | kept | swallowed | swallowed 252, two errors 4,032 | error | error / error |
| `icu.ibm-5471` | U+FFFD | kept | swallowed | swallowed | error | error / error |
| `iconv.big5` | none (stops) | stops | none (all are characters) | stops | stops | error / error |
| `iconv.cp950` | none (stops) | stops | stops | stops | stops | error / error |
| `iconv.big5-hkscs` | none (stops) | stops | none (all are characters) | stops | stops | error / error |
| `iconv.big5-2003` | none (stops) | stops | none (all are characters) | stops | stops | error / error |
| `iconv.big5-ibm` | none (stops) | stops | stops | stops | stops | error / error |
| `iconv.big5-plus` | none (stops) | stops | none (all are characters) | stops 126, character 4,158 | stops | error / error |
| `ref.whatwg` | U+FFFD | kept | kept | swallowed | error | error / error |
<!--/t-->

"kept" means the decoder reports one error for the lead byte and then decodes the next byte on
its own; "swallowed" means one error consumes both bytes; "stops" is macOS iconv, which has no
replacement mode and returns an error at that point.

- **A lead byte followed by ASCII.** <!--n:error.keep_all-->25<!--/n--> decoders keep the ASCII byte, as the WHATWG
  decoder requires; <!--n:error.swallow_all-->6<!--/n--> swallow it in every case
  (<!--n:error.swallow_list-->`java.big5-hkscs`, `java.x-big5-hkscs-2001`, `java.x-ms950-hkscs`, `java.x-ms950-hkscs-xp`, `dotnet.950`, `php.cp950`<!--/n-->), so that `A1 22` (a stray
  lead byte before a quote mark) comes out as one replacement character with the quote mark
  gone. Others keep bytes 0x00–0x3F but swallow 0x40–0x7E when the pair is not mapped: Ruby,
  ICU's IBM converters, and Go, which also swallows 0x7F, in <!--n:error.go_swallowed-->522<!--/n--> cases in all
  although it follows WHATWG (section 9).
- **Why it matters.** When two systems disagree on whether the byte after a stray lead byte is
  part of a character, a filter on one side and a parser on the other see different text. The
  WHATWG rule protects quote marks and angle brackets, but WHATWG's own issue
  [#171](https://github.com/whatwg/encoding/issues/171) points out the reverse case: a
  backslash kept after an invalid lead byte can escape a string delimiter for a reader that
  treats the pair as one character. The safe position is that both ends of a pipeline use the
  same decoder, or that malformed input is rejected rather than repaired.
- **A truncated character at the end.** Every decoder reports it except Perl's Encode, which
  silently drops it (<!--n:error.lone_dropped_impls-->`perl.big5-eten` (89), `perl.cp950` (126), `perl.big5-hkscs` (119)<!--/n--> of the 126 lead bytes), even
  when told to die on errors (section 9).
- **Error markers that are not U+FFFD.** ICU's IBM converters write U+001A (SUBSTITUTE) for
  most errors, so code that looks for U+FFFD to detect bad input will not see them. .NET's
  default decoder writes `?`, which cannot be told apart from a real question mark.

## 6. Where the mappings disagree

One divergence class per region of the code space (each links to the page that lists every
case):

<!--t:classes-->
| Class | Cases | Cases with disagreement | Distinct ways to disagree |
| --- | ---: | ---: | ---: |
| [ASCII bytes](https://useless-husband.github.io/big5-matrix/docs/class.html?id=ascii) | 128 | 3 | 1 |
| [Bytes 0x80 and 0xFF](https://useless-husband.github.io/big5-matrix/docs/class.html?id=byte-80-ff) | 514 | 514 | 6 |
| [A lead byte at the end of the input](https://useless-husband.github.io/big5-matrix/docs/class.html?id=lone-lead) | 126 | 126 | 3 |
| [A lead byte followed by an ASCII byte](https://useless-husband.github.io/big5-matrix/docs/class.html?id=ascii-after-lead) | 16,128 | 10,649 | 17 |
| [A lead byte followed by a non-ASCII byte that is not a trail byte](https://useless-husband.github.io/big5-matrix/docs/class.html?id=bad-trail) | 4,284 | 4,284 | 16 |
| [0x8140-0xA0FE](https://useless-husband.github.io/big5-matrix/docs/class.html?id=eudc-8140) | 5,024 | 5,024 | 29 |
| [0xA140-0xA3BF](https://useless-husband.github.io/big5-matrix/docs/class.html?id=symbols) | 408 | 28 | 9 |
| [0xA3C0-0xA3FE](https://useless-husband.github.io/big5-matrix/docs/class.html?id=a3c0) | 63 | 63 | 4 |
| [0xA440-0xC67E](https://useless-husband.github.io/big5-matrix/docs/class.html?id=hanzi1) | 5,401 | 1 | 1 |
| [0xC6A1-0xC8FE](https://useless-husband.github.io/big5-matrix/docs/class.html?id=c6a1) | 408 | 408 | 17 |
| [0xC940-0xF9D5](https://useless-husband.github.io/big5-matrix/docs/class.html?id=hanzi2) | 7,652 | 0 | 0 |
| [0xF9D6-0xF9FE](https://useless-husband.github.io/big5-matrix/docs/class.html?id=f9d6) | 41 | 41 | 5 |
| [0xFA40-0xFEFE](https://useless-husband.github.io/big5-matrix/docs/class.html?id=eudc-fa40) | 785 | 785 | 6 |
<!--/t-->

Pairs whose first byte is ASCII are left out: in all <!--n:decode.ascii_first_decoders-->43<!--/n--> whole-space decoder columns,
such a pair decodes exactly as the ASCII byte followed by the second byte on its own
(<!--n:decode.ascii_first_exceptions-->0<!--/n--> exceptions), so they add nothing to the single-byte cases.

### Symbols, and the one hanzi in dispute

Of the 408 symbol positions, <!--n:symbols.disputed-->28<!--/n--> are decoded differently by some column:

<!--t:symbol-disputes-->
| Bytes | Decoded as (number of columns) |
| --- | --- |
| `A145` | U+2027 (29); U+2022 (14) |
| `A14E` | U+FE51 (29); U+FF64 (14) |
| `A155` | U+FF5C (41); U+FE31 (2) |
| `A156` | U+2013 (41); U+2014 (2) |
| `A157` | U+FE31 (41); U+FE32 (2) |
| `A158` | U+2014 (41); U+FE58 (2) |
| `A15A` | U+2574 (36); U+FF3F (4); error (3) |
| `A1C2` | U+00AF (27); U+203E (16) |
| `A1C3` | U+FFE3 (36); error (7) |
| `A1C5` | U+02CD (36); error (7) |
| `A1E3` | U+FF5E (27); U+223C (16) |
| `A1F2` | U+2295 (29); U+2641 (14) |
| `A1F3` | U+2299 (29); U+2609 (14) |
| `A1FD` | U+2223 (41); U+FF5C (2) |
| `A1FE` | U+FF0F (36); U+2571 (4); error (3) |
| `A240` | U+FF3C (36); U+2572 (4); error (3) |
| `A241` | U+2215 (29); U+FF0F (14) |
| `A242` | U+FE68 (29); U+FF3C (14) |
| `A244` | U+FFE5 (30); U+00A5 (13) |
| `A246` | U+FFE0 (29); U+00A2 (14) |
| `A247` | U+FFE1 (29); U+00A3 (14) |
| `A2A4` | U+2550 (42); error (1) |
| `A2A5` | U+255E (42); error (1) |
| `A2A6` | U+256A (42); error (1) |
| `A2A7` | U+2561 (42); error (1) |
| `A2CC` | U+5341 (32); U+3038 (7); error (4) |
| `A2CD` | U+5344 (41); U+3039 (2) |
| `A2CE` | U+5345 (32); U+303A (7); error (4) |
| `C255` | U+5F5D (38); U+5F5E (5) |
<!--/t-->

These are the classic disputes. 0xA145 is HYPHENATION POINT (U+2027) in Microsoft's table and
BULLET (U+2022) in BIG5.TXT; 0xA14E, 0xA1C2, 0xA1E3, 0xA1F2, 0xA1F3, 0xA241, 0xA242 and the
three currency signs at 0xA244–0xA247 split the same way, between Microsoft's choice and
BIG5.TXT's (for the currency signs: fullwidth ￠ ￡ ￥ or plain ¢ £ ¥). BIG5.TXT leaves
0xA15A, 0xA1C3, 0xA1C5, 0xA1FE, 0xA240, 0xA2CC and 0xA2CE unmapped because they duplicate
other codes or had no Unicode equivalent; Java fills three of them instead (0xA15A with
U+FF3F, 0xA1FE and 0xA240 with box-drawing diagonals). 0xA2CC and 0xA2CE are the Hangzhou numerals ten and thirty in some tables
(U+3038, U+303A) and the hanzi 十 and 卅 (U+5341, U+5345, which also sit at 0xA451 and 0xA4CA) in
others. IBM-950 differs on five more dashes and bars (0xA155–0xA158, 0xA1FD). The only hanzi in dispute is 0xC255: 彝
(U+5F5D) in most tables, 彞 (U+5F5E) in IBM's and Perl's.

The duplicated hanzi 兀 (0xA461 and 0xC94A) and 嗀 (0xDCD1 and 0xDDFC) decode the same in every
column.

### Row A3: the Euro sign

0xA3E1 is € in code page 950, Big5-2003, HKSCS and WHATWG; WHATWG also maps 0xA3C0–0xA3E0 to the
control pictures. BIG5.TXT, Python's `big5`, PHP's `BIG-5`, Java's `Big5` and macOS iconv's
`BIG5` reject it. PHP's `CP950` rejects it too: PHP's own test data for that converter is
Microsoft's 1998 table, from before the Euro sign was added.

### Rows C6A1–C8FE and F9D6–F9FE: ETEN

Row 0xC6A1–0xC8FE is where the families diverge most visibly. BIG5.TXT has kana, Cyrillic and
circled numbers at 0xC6A1–0xC7FC in a different order from ETEN's, which HKSCS and WHATWG
adopted; code page 950 treats the whole row as user-defined. So the same bytes are Ё, シ or a
Private Use code point depending on the reader. 0xF9D6–0xF9FE (ETEN's seven hanzi and box
drawing) is absent from BIG5.TXT and present almost everywhere else; its last code, 0xF9FE, is
▓ (U+2593) for Microsoft and ￭ (U+FFED) for HKSCS and WHATWG.

### User-defined rows 0x8140–0xA0FE and 0xFA40–0xFEFE

These rows show the widest spread: code page 950 maps every position to the Private Use Area,
HKSCS-based columns map the HKSCS characters to their Unicode code points (or, following older
editions, to Private Use code points of their own), UAO and Big5+ put other characters there,
and plain Big5 rejects them. Every one of the <!--n:class.eudc-8140.cases-->5,024<!--/n--> positions in 0x8140–0xA0FE is
decoded differently by at least one column.

## 7. Encoding

<!--t:encode-repertoire-->
| Encoder | Non-ASCII code points encoded | of which PUA | of which plane 2 | Dropped silently | Written as '?' |
| --- | ---: | ---: | ---: | ---: | ---: |
| `python.big5` | 13,706 | 0 | 0 | 0 | 0 |
| `python.cp950` | 13,751 | 0 | 0 | 0 | 0 |
| `python.big5hkscs` | 18,386 | 0 | 1,693 | 0 | 0 |
| `go.big5` | 18,490 | 0 | 1,713 | 0 | 0 |
| `node.iconv-lite-big5` | 18,490 | 0 | 1,713 | 0 | 0 |
| `node.iconv-lite-cp950` | 13,493 | 0 | 0 | 0 | 0 |
| `rust.big5` | 14,653 | 0 | 291 | 0 | 0 |
| `java.big5` | 13,703 | 0 | 0 | 0 | 0 |
| `java.x-windows-950` | 19,710 | 6,217 | 0 | 0 | 0 |
| `java.x-ibm950` | 20,075 | 6,209 | 0 | 0 | 0 |
| `java.x-big5-solaris` | 13,710 | 0 | 0 | 0 | 0 |
| `java.big5-hkscs` | 23,419 | 4,968 | 1,713 | 0 | 0 |
| `java.x-big5-hkscs-2001` | 20,443 | 2,186 | 1,651 | 0 | 0 |
| `java.x-ms950-hkscs` | 24,675 | 6,217 | 1,713 | 0 | 0 |
| `java.x-ms950-hkscs-xp` | 22,723 | 6,217 | 0 | 0 | 0 |
| `dotnet.950` | 19,712 | 6,218 | 0 | 0 | 0 |
| `dotnet.950-default` | 20,192 | 6,218 | 0 | 0 | 108,704 |
| `php.big-5` | 13,736 | 0 | 0 | 0 | 0 |
| `php.cp950` | 19,709 | 6,217 | 0 | 0 | 0 |
| `ruby.big5` | 13,901 | 408 | 0 | 0 | 0 |
| `ruby.cp950` | 20,190 | 6,217 | 0 | 0 | 0 |
| `ruby.cp951` | 23,255 | 6,217 | 0 | 0 | 0 |
| `ruby.big5-hkscs` | 18,457 | 0 | 1,713 | 0 | 0 |
| `ruby.big5-uao` | 19,316 | 290 | 0 | 0 | 0 |
| `perl.big5-eten` | 13,900 | 46 | 3 | 0 | 0 |
| `perl.cp950` | 20,192 | 6,218 | 0 | 0 | 0 |
| `perl.big5-hkscs` | 19,991 | 1,750 | 1,651 | 0 | 0 |
| `icu.windows-950-2000` | 19,712 | 6,218 | 0 | 66 | 0 |
| `icu.ibm-950` | 20,075 | 6,209 | 0 | 66 | 0 |
| `icu.ibm-1373` | 19,710 | 6,217 | 0 | 66 | 0 |
| `icu.ibm-1375` | 21,371 | 2,948 | 1,713 | 66 | 0 |
| `icu.ibm-5471` | 19,438 | 2,854 | 0 | 66 | 0 |
| `iconv.big5` | 20,576 | 6,174 | 0 | 0 | 0 |
| `iconv.cp950` | 13,493 | 0 | 0 | 0 | 0 |
| `iconv.big5-hkscs` | 16,024 | 6,299 | 2,961 | 0 | 0 |
| `iconv.big5-2003` | 20,677 | 6,217 | 0 | 0 | 0 |
| `iconv.big5-ibm` | 13,860 | 42 | 0 | 0 | 0 |
| `iconv.big5-plus` | 23,937 | 2,355 | 0 | 0 | 0 |
| `ref.whatwg` | 14,653 | 0 | 291 | 0 | 0 |
| `ref.ms-bestfit950` | 20,192 | 6,218 | 0 | 0 | 1 |
<!--/t-->

**Duplicates.** Where Big5 has two codes for one character, encoders must pick one, and they do
not all pick the same: <!--n:encode.choice-->6,651<!--/n--> code points are encoded by at least two encoders to
different bytes. Most are HKSCS characters and Private Use code points. Among the classic
duplicates, ═ ╞ ╪ ╡ (U+2550, U+255E, U+256A, U+2561) go to row 0xF9 in some encoders and to
0xA2A4–0xA2A7 in others; 十 and 卅 go to 0xA451 and 0xA4CA almost everywhere. (For exactly these
six characters the WHATWG encoder specifies the last of the duplicate codes rather than the
first.)

**One-way mappings** are characters that an encoder writes as bytes its own decoder reads as
something else:

<!--t:oneway-->
| Encoder | To ASCII | From PUA | Undecodable | Other | As '?' | ASCII characters produced |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `python.cp950` | 0 | 0 | 0 | 9 | 0 |  |
| `java.big5-hkscs` | 0 | 4,964 | 4 | 0 | 0 |  |
| `java.x-big5-hkscs-2001` | 0 | 2,151 | 0 | 28 | 0 |  |
| `java.x-ms950-hkscs` | 0 | 4,964 | 0 | 1 | 0 |  |
| `java.x-ms950-hkscs-xp` | 0 | 3,013 | 0 | 1 | 0 |  |
| `dotnet.950-default` | 72 | 0 | 0 | 412 | 108,704 | `!-123ACDEINORTUYaceinostuy\|` |
| `ruby.cp950` | 72 | 0 | 0 | 408 | 0 | `!-123ACDEINORTUYaceinostuy\|` |
| `ruby.cp951` | 52 | 3,091 | 0 | 402 | 0 | `!-123ACDEINORTUYaceinostuy\|` |
| `ruby.big5-hkscs` | 0 | 0 | 82 | 11 | 0 |  |
| `perl.cp950` | 72 | 0 | 0 | 408 | 0 | `!-123ACDEINORTUYaceinostuy\|` |
| `perl.big5-hkscs` | 0 | 0 | 0 | 1,651 | 0 |  |
| `icu.ibm-1375` | 0 | 2,284 | 0 | 0 | 0 |  |
| `icu.ibm-5471` | 0 | 540 | 0 | 0 | 0 |  |
| `iconv.big5` | 199 | 323 | 2 | 437 | 0 | ` !"'*+,-./:<>ABCDEFGHIKLMNOPQRSTUZ\ˋabcdefghijklmnoprstuvxz\|~` |
| `iconv.big5-hkscs` | 186 | 5,056 | 19 | 6,256 | 0 | ` !"'*+,-./:<>ABCDEFGHIKLMNOPQRSTUZ\_ˋabcdefghijklmnoprstuz\|~` |
| `iconv.big5-2003` | 199 | 363 | 3 | 438 | 0 | ` !"'*+,-./:<>ABCDEFGHIKLMNOPQRSTUZ\ˋabcdefghijklmnoprstuvxz\|~` |
| `iconv.big5-ibm` | 0 | 0 | 0 | 12 | 0 |  |
| `iconv.big5-plus` | 0 | 0 | 0 | 12 | 0 |  |
| `ref.ms-bestfit950` | 72 | 0 | 0 | 408 | 1 | `!-123ACDEINORTUYaceinostuy\|` |
<!--/t-->

- **Best fit.** Microsoft's table maps 72 characters to ASCII look-alikes (© → c, ¡ → !, the soft
  hyphen U+00AD → `-`) and 408 more to other Big5 characters. .NET's default encoder applies it,
  and so do the encoders of Ruby's `CP950` and Perl's `cp950`, whose tables contain the
  best-fit entries. The soft hyphen
  to `-` mapping is the one behind CVE-2024-4577 (PHP-CGI argument injection on Windows) and
  is part of the WorstFit research
  ([DEVCORE, 2025](https://devco.re/blog/2025/01/09/worstfit-unveiling-hidden-transformers-in-windows-ansi/)):
  input that contains no `-` gains one after conversion.
- **macOS iconv goes much further.** Its `BIG5`, `BIG5-2003` and `BIG5-HKSCS` encoders map
  <!--n:oneway.iconv.big5.to-ascii-->199<!--/n-->, <!--n:oneway.iconv.big5-2003.to-ascii-->199<!--/n--> and <!--n:oneway.iconv.big5-hkscs.to-ascii-->186<!--/n--> non-ASCII characters to ASCII, including ‹ → `<`, › → `>`,
  „ and ˝ → `"`, ´ → `'`, ∖ → `\` and ⁄ → `/`, and report each one as an exact conversion
  (section 9).
- **Private Use input.** The HKSCS encoders accept the Private Use code points that older HKSCS
  editions used and write the current Big5 code, whose decode is the proper Unicode character.
  That is deliberate compatibility.
- **ICU drops some characters.** ICU's converters encode <!--n:fact.icu.dropped-->66<!--/n--> code points, all of them
  default-ignorable (U+00AD SOFT HYPHEN, U+034F, U+180B–U+180F, U+FFF0–U+FFF8 and others), to
  nothing, without an error, under the default settings `uconv` also uses.

## 8. Round trips

### Inside one implementation

Bytes → text → bytes covers every byte sequence the implementation decodes to a character;
text → bytes → text covers every code point it encodes.

<!--t:within-->
| Implementation | bytes→text→bytes: same | changed | lost | text→bytes→text: same | changed | changed (PUA input) | error |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `python.big5` | 13,706 | 4 | 0 | 13,834 | 0 | 0 | 0 |
| `python.cp950` | 13,742 | 10 | 0 | 13,870 | 9 | 0 | 0 |
| `python.big5hkscs` | 18,390 | 12 | 0 | 18,518 | 0 | 0 | 0 |
| `go.big5` | 18,490 | 100 | 4 | 18,618 | 0 | 0 | 0 |
| `node.iconv-lite-big5` | 18,494 | 100 | 0 | 18,622 | 0 | 0 | 0 |
| `node.iconv-lite-cp950` | 13,493 | 10 | 0 | 13,621 | 0 | 0 | 0 |
| `rust.big5` | 14,653 | 90 | 3,851 | 14,781 | 0 | 0 | 0 |
| `java.big5` | 13,703 | 5 | 0 | 13,831 | 0 | 0 | 0 |
| `java.x-windows-950` | 19,710 | 10 | 0 | 19,838 | 0 | 0 | 0 |
| `java.x-ibm950` | 20,075 | 189 | 0 | 20,203 | 0 | 0 | 0 |
| `java.x-big5-solaris` | 13,710 | 5 | 0 | 13,838 | 0 | 0 | 0 |
| `java.big5-hkscs` | 18,451 | 19 | 0 | 18,579 | 0 | 4,964 | 4 |
| `java.x-big5-hkscs-2001` | 18,264 | 19 | 0 | 18,392 | 28 | 2,151 | 0 |
| `java.x-ms950-hkscs` | 19,710 | 10 | 0 | 19,838 | 1 | 4,964 | 0 |
| `java.x-ms950-hkscs-xp` | 19,709 | 11 | 0 | 19,837 | 1 | 3,013 | 0 |
| `dotnet.950` | 19,712 | 0 | 0 | 19,840 | 0 | 0 | 0 |
| `dotnet.950-default` | 19,712 | 0 | 0 | 19,840 | 484 | 0 | 0 |
| `php.big-5` | 13,736 | 8 | 0 | 13,864 | 0 | 0 | 0 |
| `php.cp950` | 19,709 | 10 | 0 | 19,837 | 0 | 0 | 0 |
| `ruby.big5` | 13,901 | 10 | 0 | 14,029 | 0 | 0 | 0 |
| `ruby.cp950` | 19,710 | 10 | 0 | 19,838 | 480 | 0 | 0 |
| `ruby.cp951` | 19,710 | 10 | 0 | 19,838 | 454 | 3,091 | 0 |
| `ruby.big5-hkscs` | 18,364 | 10 | 9 | 18,492 | 11 | 0 | 82 |
| `ruby.big5-uao` | 19,316 | 466 | 0 | 19,444 | 0 | 0 | 0 |
| `perl.big5-eten` | 13,900 | 8 | 0 | 14,028 | 0 | 0 | 0 |
| `perl.cp950` | 19,712 | 10 | 0 | 19,840 | 480 | 0 | 0 |
| `perl.big5-hkscs` | 18,340 | 70 | 0 | 18,468 | 1,651 | 0 | 0 |
| `icu.windows-950-2000` | 19,712 | 10 | 0 | 19,840 | 0 | 0 | 0 |
| `icu.ibm-950` | 20,075 | 189 | 0 | 20,203 | 0 | 0 | 0 |
| `icu.ibm-1373` | 19,710 | 10 | 0 | 19,838 | 0 | 0 | 0 |
| `icu.ibm-1375` | 19,087 | 10 | 0 | 19,215 | 0 | 2,284 | 0 |
| `icu.ibm-5471` | 18,898 | 10 | 0 | 19,026 | 0 | 540 | 0 |
| `iconv.big5` | 19,615 | 58 | 3 | 19,743 | 636 | 323 | 2 |
| `iconv.cp950` | 13,493 | 10 | 0 | 13,621 | 0 | 0 | 0 |
| `iconv.big5-hkscs` | 4,507 | 451 | 14,795 | 4,635 | 6,442 | 5,056 | 19 |
| `iconv.big5-2003` | 19,674 | 59 | 20 | 19,802 | 637 | 363 | 3 |
| `iconv.big5-ibm` | 13,848 | 2 | 0 | 13,976 | 12 | 0 | 0 |
| `iconv.big5-plus` | 23,925 | 13 | 0 | 24,053 | 12 | 0 | 0 |
| `ref.whatwg` | 14,653 | 90 | 3,851 | 14,781 | 0 | 0 | 0 |
| `ref.ms-bestfit950` | 19,712 | 10 | 0 | 19,840 | 480 | 0 | 0 |
<!--/t-->

Most "changed" counts in the first half are the duplicate codes (0xA2CC decodes to 十, which
encodes back as 0xA451). WHATWG and encoding_rs lose the HKSCS rows by design: the standard's
encoder does not write them. macOS iconv's `BIG5-HKSCS` cannot encode most of what it decodes
(section 9).

### Between runtimes, by the name "big5"

The question most people actually face: one program writes text as "big5" and another reads it
as "big5". Each cell counts the code points the writer encodes that the reader does not give
back, as "changed silently / reported as an error"; "0" means every character survives.

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

<!--t:by-name-big5-legend-->
| Runtime | Name used | Writer column | Reader column |
| --- | --- | --- | --- |
| Python | codecs 'big5' | `python.big5` | `python.big5` |
| Go | x/text Big5 | `go.big5` | `go.big5` |
| Node.js | iconv-lite 'big5' / TextDecoder('big5') | `node.iconv-lite-big5` | `node.textdecoder` |
| Rust | encoding_rs BIG5 | `rust.big5` | `rust.big5` |
| Java | Charset 'Big5' | `java.big5` | `java.big5` |
| .NET | GetEncoding('big5') = 950 | `dotnet.950-default` | `dotnet.950` |
| PHP | mbstring 'BIG5' | `php.big-5` | `php.big-5` |
| Ruby | 'Big5' | `ruby.big5` | `ruby.big5` |
| Perl | Encode 'big5' = big5-eten | `perl.big5-eten` | `perl.big5-eten` |
| ICU | ucnv 'Big5' = windows-950-2000 | `icu.windows-950-2000` | `icu.windows-950-2000` |
| macOS iconv | 'BIG5' | `iconv.big5` | `iconv.big5` |
<!--/t-->

The diagonal is the round trip inside one runtime. Off the diagonal only <!--n:pair.big5.clean-->11<!--/n--> of
<!--n:pair.big5.total-->110<!--/n--> pairs lose nothing. Writers that know HKSCS (Go, Node.js's iconv-lite, and Rust to
a smaller extent) produce thousands of byte sequences that plain-Big5 readers reject; writers
with Windows tables produce bytes for Private Use code points that other readers reject; and
between a BIG5.TXT-style runtime and an ETEN-style one about 260 symbols, Cyrillic letters and
kana silently become other characters.

### By the name "cp950"

<!--t:by-name-cp950-->
| writer ↓ / reader → | Python | Node.js | Java | .NET | PHP | Ruby | Perl | ICU | macOS iconv |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **Python** | 9 / 0 | 9 / 249 | 297 / 1 | 258 / 4 | 258 / 1 | 258 / 0 | 258 / 0 | 300 / 1 | 9 / 249 |
| **Node.js** | 0 | 0 | 41 / 1 | 0 / 6 | 0 / 1 | 0 | 0 | 44 / 1 | 0 |
| **Java** | 298 / 6,326 | 49 / 6,575 | 0 | 360 / 459 | 364 / 451 | 364 / 451 | 364 / 451 | 3 / 0 | 49 / 6,575 |
| **.NET** | 733 / 5,970 | 484 / 6,219 | 844 / 96 | 484 / 0 | 484 / 3 | 484 / 2 | 484 / 0 | 847 / 96 | 484 / 6,219 |
| **PHP** | 249 / 5,968 | 0 / 6,217 | 356 / 93 | 0 / 4 | 0 | 0 | 0 | 359 / 93 | 0 / 6,217 |
| **Ruby** | 729 / 5,968 | 480 / 6,217 | 840 / 94 | 480 / 0 | 480 / 1 | 480 / 0 | 480 / 0 | 843 / 94 | 480 / 6,217 |
| **Perl** | 729 / 5,970 | 480 / 6,219 | 840 / 96 | 480 / 0 | 480 / 3 | 480 / 2 | 480 / 0 | 843 / 96 | 480 / 6,219 |
| **ICU** | 301 / 6,326 | 52 / 6,575 | 3 / 0 | 363 / 459 | 367 / 451 | 367 / 451 | 367 / 451 | 0 | 52 / 6,575 |
| **macOS iconv** | 0 | 0 | 49 / 1 | 0 / 4 | 0 / 1 | 0 | 0 | 52 / 1 | 0 |
<!--/t-->

<!--t:by-name-cp950-legend-->
| Runtime | Name used | Writer column | Reader column |
| --- | --- | --- | --- |
| Python | codecs 'cp950' | `python.cp950` | `python.cp950` |
| Node.js | iconv-lite 'cp950' | `node.iconv-lite-cp950` | `node.iconv-lite-cp950` |
| Java | Charset 'cp950' = x-IBM950 | `java.x-ibm950` | `java.x-ibm950` |
| .NET | GetEncoding(950) | `dotnet.950-default` | `dotnet.950` |
| PHP | mbstring 'CP950' | `php.cp950` | `php.cp950` |
| Ruby | 'CP950' | `ruby.cp950` | `ruby.cp950` |
| Perl | Encode 'cp950' | `perl.cp950` | `perl.cp950` |
| ICU | ucnv 'cp950' = ibm-950_P110-1999 | `icu.ibm-950` | `icu.ibm-950` |
| macOS iconv | 'CP950' | `iconv.cp950` | `iconv.cp950` |
<!--/t-->

### What actually changes

Selected pairs, grouped by where the bytes fall and what the reader does:

<!--t:pair-examples-->
| Writer → reader | Bytes / outcome | Characters | Examples |
| --- | --- | ---: | --- |
| Python → Go (`big5`) | C6A1–C8FE: silently different text | 249 | Ё U+0401 → `C7B3` → シ U+30B7; Д U+0414 → `C7B1` → サ U+30B5; Е U+0415 → `C7B2` → ザ U+30B6 |
|  | A140–A3BF: silently different text | 11 | ¢ U+00A2 → `A246` → ￠ U+FFE0; £ U+00A3 → `A247` → ￡ U+FFE1; ¥ U+00A5 → `A244` → ￥ U+FFE5 |
| Java → Node.js (`big5`) | C6A1–C8FE: silently different text | 249 | Ё U+0401 → `C7B3` → U+F760; Д U+0414 → `C7B1` → U+F75E; Е U+0415 → `C7B2` → U+F75F |
|  | A140–A3BF: silently different text | 11 | ¢ U+00A2 → `A246` → ￠ U+FFE0; £ U+00A3 → `A247` → ￡ U+FFE1; ¥ U+00A5 → `A244` → ￥ U+FFE5 |
| PHP → .NET (`big5`) | C6A1–C8FE: silently different text | 249 | Ё U+0401 → `C7B3` → U+F760; Д U+0414 → `C7B1` → U+F75E; Е U+0415 → `C7B2` → U+F75F |
|  | A140–A3BF: silently different text | 10 | ¢ U+00A2 → `A246` → ￠ U+FFE0; £ U+00A3 → `A247` → ￡ U+FFE1; • U+2022 → `A145` → ‧ U+2027 |
|  | A140–A3BF: reader reports an error | 4 | ═ U+2550 → `A2A4` → error; ╞ U+255E → `A2A5` → error; ╡ U+2561 → `A2A7` → error |
| Go → Python (`big5`) | 8140–A0FE: reader reports an error | 3,837 | À U+00C0 → `8859` → error + Y U+0059; Á U+00C1 → `8857` → error + W U+0057; È U+00C8 → `885D` → error + ] U+005D |
|  | FA40–FEFE: reader reports an error | 785 | 㑺 U+347A → `FA68` → error + h U+0068; 㕡 U+3561 → `FB70` → error + p U+0070; 㖡 U+35A1 → `FB7A` → error + z U+007A |
|  | C6A1–C8FE: silently different text | 245 | ¨ U+00A8 → `C6D8` → ぴ U+3074; ˆ U+02C6 → `C6D9` → ふ U+3075; Ё U+0401 → `C7F9` → ⑺ U+247A |
|  | C6A1–C8FE: reader reports an error | 116 | ø U+00F8 → `C8FB` → error; ŋ U+014B → `C8FC` → error; œ U+0153 → `C8FA` → error |
|  | F9D6–F9FE: reader reports an error | 41 | ═ U+2550 → `F9F9` → error; ║ U+2551 → `F9F8` → error; ╒ U+2552 → `F9E6` → error |
|  | A3C0–A3FE: reader reports an error | 34 | € U+20AC → `A3E1` → error; ␀ U+2400 → `A3C0` → error; ␁ U+2401 → `A3C1` → error |
|  | A140–A3BF: silently different text | 11 | ¯ U+00AF → `A1C2` → ‾ U+203E; ‧ U+2027 → `A145` → • U+2022; ∕ U+2215 → `A241` → ／ U+FF0F |
| .NET → PHP (`big5`) | 8140–A0FE: reader reports an error | 5,024 | U+E311 → `8E40` → error + @ U+0040; U+E312 → `8E41` → error + A U+0041; U+E313 → `8E42` → error + B U+0042 |
|  | FA40–FEFE: reader reports an error | 785 | U+E000 → `FA40` → error + @ U+0040; U+E001 → `FA41` → error + A U+0041; U+E002 → `FA42` → error + B U+0042 |
|  | A440–C67E: silently different text | 369 | ㆒ U+3192 → `A440` → 一 U+4E00; ㆓ U+3193 → `A447` → 二 U+4E8C; ㆔ U+3194 → `A454` → 三 U+4E09 |
|  | C6A1–C8FE: silently different text | 249 | U+F6B1 → `C6A1` → ヾ U+30FE; U+F6B2 → `C6A2` → ゝ U+309D; U+F6B3 → `C6A3` → ゞ U+309E |
|  | C6A1–C8FE: reader reports an error | 159 | U+F7AA → `C7FD` → error; U+F7AB → `C7FE` → error; U+F7AC → `C840` → error + @ U+0040 |
|  | ASCII byte: silently different text | 72 | ¡ U+00A1 → `21` → ! U+0021; ¦ U+00A6 → `7C` → \| U+007C; © U+00A9 → `63` → c U+0063 |
|  | A140–A3BF: silently different text | 32 | ¥ U+00A5 → `A244` → ￥ U+FFE5; ¨ U+00A8 → `A14C` → ‥ U+2025; ¯ U+00AF → `A1C2` → ‾ U+203E |
|  | C940–F9D5: silently different text | 10 | 菉 U+F93E → `DB77` → 菉 U+83C9; 拏 U+F95B → `CED4` → 拏 U+62CF; 磻 U+F964 → `EDA8` → 磻 U+78FB |
|  | A140–A3BF: reader reports an error | 6 | ˍ U+02CD → `A1C5` → error; ‾ U+203E → `A1C3` → error; ╴ U+2574 → `A15A` → error |
|  | two ASCII bytes: silently different text | 4 | Ê̄ U+00CA U+0304 → `453F` → E? U+0045 U+003F; Ê̌ U+00CA U+030C → `453F` → E? U+0045 U+003F; ê̄ U+00EA U+0304 → `653F` → e? U+0065 U+003F |
|  | single byte: reader reports an error | 2 | U+0080 → `80` → error; U+F8F8 → `FF` → error |
|  | A3C0–A3FE: reader reports an error | 1 | € U+20AC → `A3E1` → error |
| Java → .NET (`cp950`) | lead + 80–A0 (IBM's extra trail bytes): reader reports an error | 418 | ´ U+00B4 → `F28C` → error; ¶ U+00B6 → `F38A` → error; ‐ U+2010 → `F28B` → error |
|  | C6A1–C8FE: silently different text | 315 | ¨ U+00A8 → `C6D8` → U+F6E8; ʺ U+02BA → `C6DE` → U+F6EE; Ё U+0401 → `C7F9` → U+F7A6 |
|  | F9D6–F9FE: silently different text | 37 | U+F813 → `F9D6` → 碁 U+7881; U+F814 → `F9D7` → 銹 U+92B9; U+F815 → `F9D8` → 裏 U+88CF |
|  | A3C0–A3FE: reader reports an error | 33 | ␀ U+2400 → `A3C0` → error; ␁ U+2401 → `A3C1` → error; ␂ U+2402 → `A3C2` → error |
|  | A140–A3BF: silently different text | 7 | — U+2014 → `A156` → – U+2013; ‾ U+203E → `A1C2` → ¯ U+00AF; ∼ U+223C → `A1E3` → ～ U+FF5E |
|  | A140–A3BF: reader reports an error | 4 | ═ U+2550 → `A2A4` → error; ╞ U+255E → `A2A5` → error; ╡ U+2561 → `A2A7` → error |
|  | F9D6–F9FE: reader reports an error | 4 | U+F837 → `F9FA` → error; U+F838 → `F9FB` → error; U+F839 → `F9FC` → error |
|  | A440–C67E: silently different text | 1 | 彞 U+5F5E → `C255` → 彝 U+5F5D |
<!--/t-->

## 9. Problems that look like bugs

Each has a reproducer in [`findings/`](../findings). This project has not reported any of
them upstream; two were already known.

1. [macOS iconv BIG5-HKSCS](../findings/01-macos-iconv-big5-hkscs.md) cannot encode
   <!--n:fact.iconv.hkscs.hanzi_unencodable-->12,634<!--/n--> of the <!--n:fact.iconv.hkscs.hanzi_total-->13,053<!--/n--> ordinary hanzi, encodes <!--n:fact.iconv.hkscs.plane_bits-->1,554<!--/n--> BMP code points as the bytes of the
   plane-2 character with the same low 16 bits (U+0086 → `8B C5`, which it decodes as U+20086),
   cannot encode <!--n:fact.iconv.hkscs.plane2_unencodable-->1,708<!--/n--> of the <!--n:fact.iconv.hkscs.plane2_decoded-->1,713<!--/n--> plane-2 characters it decodes, and
   decodes 0x8862 without its combining mark.
2. [macOS iconv transliterates to ASCII](../findings/02-macos-iconv-silent-ascii.md) without
   being asked to, and reports the result as an exact conversion.
3. [Chromium](../findings/03-chromium-big5-composed.md) decodes 0x8862, 0x8864, 0x88A3 and
   0x88A5 to a C1 control character and a lone surrogate.
4. [Go x/text](../findings/04-go-xtext-big5-ascii.md) consumes the ASCII byte after a lead byte
   in <!--n:error.go_swallowed-->522<!--/n--> cases where the WHATWG decoder keeps it. (Its encoder's choice of HKSCS
   codes for <!--n:fact.go.encode_other_choice-->27<!--/n--> common characters such as 港 and 包 is already
   [golang/go#43581](https://github.com/golang/go/issues/43581).)
5. [Perl Encode](../findings/05-perl-encode-truncated.md) drops a truncated final character
   silently, even with `FB_CROAK`, in every table-driven multibyte encoding tried.
6. [.NET code page 950](../findings/06-dotnet-cp950-duplicates.md) rejects <!--n:fact.dotnet.rejects_cp950-->10<!--/n--> byte sequences
   that Microsoft's own tables map.
7. [Node.js `TextDecoder('big5')`](../findings/07-node-textdecoder-big5.md) is ICU's
   windows-950 and differs from the WHATWG decoder in <!--n:fact.node.vs_whatwg-->6,253<!--/n--> byte sequences. This is
   known ([nodejs/node#40091](https://github.com/nodejs/node/issues/40091),
   [#61041](https://github.com/nodejs/node/issues/61041)), and a fix is open
   ([#65458](https://github.com/nodejs/node/pull/65458)).
8. [Ruby 2.6's Big5-HKSCS](../findings/08-ruby-big5-hkscs-87.md) encodes HKSCS-2008 characters
   to row 0x87 but cannot decode that row. Ruby 2.6 is the end-of-life system Ruby on macOS;
   the current Ruby source has the decoding entries, so this needs a re-test on a current
   Ruby before anyone reports it.

## 10. Recommendations

- **Decide which Big5 you mean, and name the converter, not the label.** For text from the web
  or from browsers, use a WHATWG implementation (encoding_rs, a browser, or Go's x/text, which
  decodes the same characters but see finding 4). For data written by Windows programs, use
  Microsoft's table (`ms950` or `x-windows-950` in Java, `windows-950` in ICU, `cp950` in Python, Perl and Ruby; never
  `cp950` in Java or ICU). For Hong Kong data, use an HKSCS converter that maps to Unicode code
  points (Python's `big5hkscs`, Java's `Big5-HKSCS`, WHATWG).
- **Read and write with the same implementation**, or check the pair against the tables above.
  Moving data from a BIG5.TXT-style writer to an ETEN-style reader changes Cyrillic, kana and
  about a dozen symbols without any error.
- **Reject malformed input instead of repairing it** wherever the decoded text feeds a parser,
  a filter or a security check, and do not rely on U+FFFD to detect errors (ICU's IBM
  converters write U+001A, .NET's default writes `?`, Perl drops truncated characters).
- **Turn best fit off.** Encode with an exception fallback in .NET; do not use Ruby's `CP950`,
  Perl's `cp950` or macOS iconv's Big5 converters to produce data for something that parses it.
- **Do not use macOS iconv for Big5-HKSCS output** (finding 1).
- **Before moving data between two systems, run it through both** (decode with the reader,
  encode with the writer) and compare, or look up the characters you care about on the site.

## 11. Method and limits

- Cases: every single byte and every two-byte sequence (one decoder call each); every BMP
  scalar value, every plane-2 code point and the multi-code-point sequences any decoder
  produced (one encoder call each). Longer inputs were not tested, except that the
  concatenation check in section 6 shows a leading ASCII byte never changes the result.
- Error handling is compared only among real converters and the WHATWG algorithm; tables say
  nothing about malformed input.
- Windows was not run. The bestfit950 column is Microsoft's published table, and .NET's code
  page 950 (which differs from it in <!--n:fact.dotnet.rejects_cp950-->10<!--/n--> byte sequences) is the closest real
  Microsoft converter here.
- glibc iconv and GNU libiconv, the converters most Linux programs use, were not available on
  the machine that produced the data. The macOS iconv tested is the FreeBSD-derived "Citrus"
  implementation (its manual page says so), which Apple adopted in macOS 14 according to the
  reports linked in finding 1.
- Ruby and Perl are the system versions on macOS (Ruby 2.6.10, Perl 5.34.1 with Encode 3.08),
  both old.
- Every surprising claim here is checked a second way by
  [`tools/verify_claims.py`](../tools/verify_claims.py), which asks each runtime directly
  (command-line tools or a few independent lines of code) and compares with the data.
