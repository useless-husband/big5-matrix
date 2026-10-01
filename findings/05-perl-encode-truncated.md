# Perl Encode: a truncated multibyte character at the end of the input vanishes without an error

**Component:** Perl's `Encode` module, table-driven multibyte encodings (`Encode::TW`'s
`big5-eten`, `cp950`, `big5-hkscs`; also `shiftjis`, `euc-kr`, `euc-jp`, `gb2312`). Tested with
Perl 5.34.1 and Encode 3.08 (the macOS system Perl); a current Encode was not tested.

**Severity:** medium. Data is lost silently, even by code that asked to die on errors.

## What happens

`decode('big5-eten', "a\xA4")` returns `"a"`: the lead byte 0xA4, a truncated character, is
dropped. The documentation of `CHECK` says:

> If CHECK is 0, encoding and decoding replace any malformed character with a substitution
> character. ... When you decode, the Unicode REPLACEMENT CHARACTER, code point U+FFFD, is used.

> If CHECK is 1, methods immediately die with an error message.

Neither happens: with `FB_DEFAULT` there is no U+FFFD and with `FB_CROAK` there is no error.
In the data, `cp950` drops all 126 lead bytes when they end the input, `big5-eten` 89 and
`big5-hkscs` 119 (the others are not lead bytes in those tables and do produce U+FFFD).

This looks like the partial-character handling meant for `FB_QUIET` and `STOP_AT_PARTIAL`
(where the caller keeps the unprocessed bytes for the next call) being applied in every mode.

## Reproduce

[`repro/05-perl-encode-truncated.pl`](repro/05-perl-encode-truncated.pl):

```
$ perl findings/repro/05-perl-encode-truncated.pl
Encode 3.0801
big5-eten  check=0: U+0061
big5-eten  check=1: U+0061
cp950      check=0: U+0061
cp950      check=1: U+0061
big5-hkscs check=0: U+0061
big5-hkscs check=1: U+0061
shiftjis   check=0: U+0061
shiftjis   check=1: U+0061
euc-kr     check=0: U+0061
euc-kr     check=1: U+0061
```

Expected: `U+0061 U+FFFD` for check=0 and an error for check=1.

## Prior reports

None found in the Encode issue tracker (dankogai/p5-encode; searched for "partial" and
"big5"). Not reported by this project; it should be re-tested with the current Encode from
CPAN first.
