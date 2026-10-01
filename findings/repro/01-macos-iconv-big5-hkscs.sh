#!/bin/sh
# macOS iconv: the BIG5-HKSCS encoder cannot encode ordinary Big5 characters, and encodes some
# BMP code points as the bytes of plane-2 characters. Run on macOS 14 or later.
set -u
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
conv() { # conv FROM TO BYTES: print the output as hex and iconv's exit status
    printf "$3" > "$tmp/in"
    /usr/bin/iconv -f "$1" -t "$2" "$tmp/in" > "$tmp/out" 2> "$tmp/err"
    status=$?
    printf '   %s -> %s: %s (exit %s) %s\n' "$1" "$2" "$(xxd -p "$tmp/out")" "$status" "$(cat "$tmp/err")"
}
echo "1. 中 (U+4E2D, Big5 A4 A4):"
conv UTF-8 BIG5-HKSCS '\344\270\255'
conv UTF-8 BIG5 '\344\270\255'
echo "2. U+0086 (a C1 control), the bytes it becomes, and U+20086 itself:"
conv UTF-8 BIG5-HKSCS '\302\206'
conv BIG5-HKSCS UTF-32BE '\213\305'
conv UTF-8 BIG5-HKSCS '\360\240\202\206'
echo "3. 0x8862 (HKSCS-2004 and later: U+00CA U+0304):"
conv BIG5-HKSCS UTF-32BE '\210\142'
