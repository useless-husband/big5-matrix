# Reference tables

These files are copies of published data, kept here so every run is reproducible offline.
`python3 tools/fetch_reference.py` downloads them again and checks each against the SHA-256
below (all five matched the live sources on 2026-10-01).

| File | Source | SHA-256 | Terms |
|---|---|---|---|
| `index-big5.txt` | WHATWG Encoding Standard, <https://encoding.spec.whatwg.org/index-big5.txt> (Identifier `8dfc7710…`, dated 2024-09-18 in its header) | `08e24270c8e95d998c994c03f907e972480dc01f58743e078654cc466203c8ff` | CC BY 4.0, © WHATWG (Apple, Google, Mozilla, Microsoft) |
| `BIG5.TXT` | Unicode, obsolete East Asian mappings, <https://www.unicode.org/Public/MAPPINGS/OBSOLETE/EASTASIA/OTHER/BIG5.TXT> (table version 2.0, 2011, header 2015) | `d1b60c58a1d327918f1616a620162c60ad2079a229ee42a73488f186e11f3aac` | Unicode License (data files), © Unicode, Inc. |
| `CP950.TXT` | Microsoft, published by Unicode, <https://www.unicode.org/Public/MAPPINGS/VENDORS/MICSFT/WINDOWS/CP950.TXT> (table version 2.01, 2000-01-07) | `ed403857b05e07ecd5667c7eff6b25898cb1fefe2d06cfe718d82d631e6058b6` | Unicode License (data files) |
| `bestfit950.txt` | Microsoft WindowsBestFit tables, published by Unicode, <https://www.unicode.org/Public/MAPPINGS/VENDORS/MICSFT/WindowsBestFit/bestfit950.txt> | `cf8c23389a42a226ea707f7ec32c665556d1fc3364db25bd765ce64d54eaee2a` | Unicode License (data files) |
| `HKSCS2016.json` | Hong Kong Digital Policy Office, "Hong Kong Supplementary Character Set related information", <https://www.digitalpolicy.gov.hk/open_data/ccli/HKSCS2016.json> (via DATA.GOV.HK) | `a28a3b74e469726c7df2174346e9a3992760f5842c02ac07b834529bc5b931e5` | DATA.GOV.HK terms of use (free reuse with attribution) |

## How each table is used

- **WHATWG**: the decoder and encoder algorithms of the Encoding Standard's Big5 section are
  transcribed in `big5matrix/reference.py` and run over this index, including the four
  pointers that decode to two code points and the "index Big5 pointer" rules for encoding.
- **BIG5.TXT**: decode only. Its seven entries mapped to U+FFFD are documented in the file as
  "not mapped" and are treated as unmapped. It lists only the double-byte part; bytes
  0x00-0x7F are taken as ASCII.
- **CP950.TXT**: decode only, as published (it lists ASCII, and lead bytes without mappings).
- **bestfit950.txt**: decoding from its MBTABLE and DBCSTABLE records, encoding from its
  WCTABLE, which contains Windows' round-trip mappings plus its "best fit" mappings. This is
  what `WideCharToMultiByte(950, ...)` does by default. It is a table, not a Windows run.
- **HKSCS2016.json**: decode only, and only for the 5,005 characters whose `H-Source` field
  gives a Big5 code (`H-8840` and so on). It has no entries for the base Big5 set, so this
  column says nothing outside the HKSCS area. The four composed sequences HKSCS assigns to
  0x8862, 0x8864, 0x88A3 and 0x88A5 (Ê̄, Ê̌, ê̄, ê̌) are not single code points and are not in
  the data set; they are added from the HKSCS-2008 and later documents (and agree with
  WHATWG).

A table defines no behaviour for malformed input, so table columns use the strict model: a
result ends with `!` at the first sequence the table does not define.
