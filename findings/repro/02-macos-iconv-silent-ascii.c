/* macOS iconv: converting to BIG5 turns some non-ASCII characters into ASCII ones and returns 0
 * (no non-identical conversions). POSIX: iconv() "shall return the number of non-identical
 * conversions performed".
 * Build and run on macOS: cc 02-macos-iconv-silent-ascii.c -liconv -o /tmp/r && /tmp/r */
#include <iconv.h>
#include <stdio.h>
#include <string.h>

static void convert(const char *label, const char *utf8) {
    iconv_t cd = iconv_open("BIG5", "UTF-8");
    char in[64], out[64];
    strcpy(in, utf8);
    char *ip = in, *op = out;
    size_t il = strlen(in), ol = sizeof out;
    size_t r = iconv(cd, &ip, &il, &op, &ol);
    printf("%-28s -> \"%.*s\"  iconv() returned %zd\n", label, (int)(sizeof out - ol), out, (ssize_t)r);
    iconv_close(cd);
}

int main(void) {
    convert("a U+2039 b  (a‹b)", "a\xe2\x80\xb9" "b");
    convert("a U+201E b  (a„b)", "a\xe2\x80\x9e" "b");
    convert("a U+2216 b  (a∖b)", "a\xe2\x88\x96" "b");
    convert("a U+00B4 b  (a´b)", "a\xc2\xb4" "b");
    return 0;
}
