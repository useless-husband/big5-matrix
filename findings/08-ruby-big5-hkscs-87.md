# Ruby 2.6: Big5-HKSCS encodes HKSCS-2008 characters to row 0x87 and cannot decode them

**Component:** Ruby's `Big5-HKSCS` transcoder. Tested with Ruby 2.6.10, the system Ruby of
macOS, which is end-of-life. **Not checked on a current Ruby**: the current source
([`enc/trans/big5-hkscs-tbl.rb`](https://github.com/ruby/ruby/blob/master/enc/trans/big5-hkscs-tbl.rb))
contains decoding entries for row 0x87, so this may be fixed.

**Severity:** low on current systems; on Ruby 2.6 text written by Ruby cannot be read back.

## What happens

The encoder writes the HKSCS-2008 additions in row 0x87 for characters such as U+34E6, but the
decoder rejects those bytes. The same is true of fourteen symbol codes (0xA15A, 0xA1C3, 0xA1C5,
0xA1FE, 0xA240, 0xA3E1 (€), 0xF9E9–0xF9EB and 0xF9F9–0xF9FD). In all, 82 code points encode
to bytes that Ruby 2.6's own decoder rejects: 68 in row 0x87 and those 14.

## Reproduce

[`repro/08-ruby-big5-hkscs-87.rb`](repro/08-ruby-big5-hkscs-87.rb):

```
2.6.10: U+34E6 -> 87be
back: Encoding::UndefinedConversionError: "\x87\xBE" from Big5-HKSCS to UTF-8
```

## Prior reports

Not searched; re-test on a current Ruby first. Not reported by this project.
