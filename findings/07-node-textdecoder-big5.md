# Node.js: `TextDecoder('big5')` is ICU's windows-950, not the WHATWG decoder (known)

**Component:** Node.js `TextDecoder` with the `big5` label (and its aliases `big5-hkscs`,
`cn-big5`, `csbig5`, `x-x-big5`). Tested with Node 25.5.0 (ICU 78.2).

**Severity:** medium. Node documents `TextDecoder` as the WHATWG Encoding API; code shared
between Node and browsers decodes the same bytes differently.

## What happens

Node passes the label to ICU, whose `big5` is `windows-950-2000`. Node's results equal ICU's on
every one of the 65,792 cases, and differ from the WHATWG decoder (and from Chromium and
encoding_rs) on 6,253 byte sequences:

- HKSCS characters decode to Private Use code points: `88 62` → U+F325 instead of U+00CA U+0304,
  `FE FE` → U+E310 instead of 秔 U+79D4.
- The user-defined rows decode to Private Use code points instead of errors: `83 5C` → U+F00E
  instead of U+FFFD followed by `\`.
- The single bytes 0x80 and 0xFF decode to U+0080 and U+F8F8 instead of errors.

With `{fatal: true}` these are not errors either.

## Reproduce

[`repro/07-node-textdecoder-big5.mjs`](repro/07-node-textdecoder-big5.mjs):

```
Node 25.5.0, ICU 78.2
80: node U+0080           WHATWG U+FFFD
8862: node U+F325           WHATWG U+00CA U+0304
835C: node U+F00E           WHATWG U+FFFD U+005C
FF: node U+F8F8           WHATWG U+FFFD
FEFE: node U+E310           WHATWG U+79D4
```

## Prior reports

Known: [nodejs/node#40091](https://github.com/nodejs/node/issues/40091) (2021, closed as not
planned), [#61041](https://github.com/nodejs/node/issues/61041) (open), and a fix in review,
[#65458](https://github.com/nodejs/node/pull/65458), which implements the WHATWG Big5 decoder
in JavaScript. This project adds only the measurement of how far the two are apart.
