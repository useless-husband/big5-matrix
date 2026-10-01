# Changelog

## 0.1.0 (2026-10-01)

First complete study.

- Harness (Python, standard library only): case generation for the whole one- and two-byte
  space and the BMP and plane 2, a line protocol for adapters, a runner that validates every
  answer, compact deterministic result files bound to their case list, and `show`, `dump`,
  `build`, `run`, `analyze`, `report` and `check` commands.
- Adapters for Python codecs, Go x/text, Node.js (`TextDecoder` and iconv-lite), Rust
  encoding_rs, Chromium (through playwright-core), Java, .NET code pages, PHP mbstring, Ruby,
  Perl Encode, ICU4C and the system iconv(3): 40 converters in all.
- Reference columns: the WHATWG Big5 algorithm and index, Unicode BIG5.TXT, Microsoft CP950.TXT
  and bestfit950.txt, and the HKSCS-2016 data set, pinned by SHA-256.
- Data collected on macOS 27.0 (Apple M5).
- Analysis: error handling, families, per-region comparison with the tables, divergence classes,
  one-way encodings, and round trips within and between implementations; the report
  (`docs/divergences.md`) and the READMEs take every number from it.
- Eight findings with reproducers (`findings/`), checked a second way by
  `tools/verify_claims.py`.
- A static site in `docs/` that reads the committed data directly.
- CI on macOS and Linux: tests, the drift check, documents against data, lint for every
  language; a Pages workflow.
