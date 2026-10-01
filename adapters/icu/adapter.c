/*
 * Adapter for ICU4C converters (ucnv), the library behind the uconv tool. See
 * big5matrix/protocol.py.
 *
 * Converters are used with ICU's default settings, which are also uconv's: on decoding the
 * substitute callback, and no "fallback" mappings except those ICU always applies. ICU's
 * substitute is U+FFFD or, for some converters and errors, U+001A; to tell a U+001A written
 * for an error from a real U+001A, decoding goes through a callback that calls ICU's own
 * substitute callback and notes what it wrote, and the adapter prints such a substitute as
 * "!001A". On encoding the stop callback reports an unmappable character instead of writing
 * the substitution byte.
 *
 * Build: cc -O2 adapter.c $(pkg-config --cflags --libs icu-uc) -o icu-adapter
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <unicode/ucnv.h>
#include <unicode/ucnv_err.h>
#include <unicode/uclean.h>
#include <unicode/uversion.h>
#include <unicode/utf16.h>

#define UCAP 1024

/* Output positions [start, end) that ICU's substitute callback wrote during one conversion. */
typedef struct {
    const UChar *base;
    int n;
    int32_t start[64], end[64];
} SubMarks;

static void U_CALLCONV mark_substitute(const void *context, UConverterToUnicodeArgs *args,
                                       const char *codeUnits, int32_t length,
                                       UConverterCallbackReason reason, UErrorCode *err) {
    SubMarks *m = (SubMarks *)context;
    const UChar *before = args->target;
    UCNV_TO_U_CALLBACK_SUBSTITUTE(NULL, args, codeUnits, length, reason, err);
    if (reason <= UCNV_IRREGULAR && m->n < 64) {
        m->start[m->n] = (int32_t)(before - m->base);
        m->end[m->n] = (int32_t)(args->target - m->base);
        m->n++;
    }
}

static int substituted(const SubMarks *m, int32_t pos) {
    for (int i = 0; i < m->n; i++)
        if (pos >= m->start[i] && pos < m->end[i]) return 1;
    return 0;
}

static void die(const char *msg, UErrorCode err) {
    fprintf(stderr, "icu adapter: %s: %s\n", msg, u_errorName(err));
    exit(1);
}

static int hexval(int c) {
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    return -1;
}

int main(int argc, char **argv) {
    if (argc != 2) {
        fprintf(stderr, "usage: icu-adapter --version | icu-adapter <converter>\n");
        return 2;
    }
    if (strcmp(argv[1], "--version") == 0) {
        UVersionInfo v;
        char s[U_MAX_VERSION_STRING_LENGTH];
        u_getVersion(v);
        u_versionToString(v, s);
        printf("version=ICU %s (ucnv C API)\n", s);
        printf("key=%s\n", s);
        return 0;
    }
    UErrorCode err = U_ZERO_ERROR;
    UConverter *cnv = ucnv_open(argv[1], &err);
    if (U_FAILURE(err)) die("ucnv_open", err);
    if (err == U_AMBIGUOUS_ALIAS_WARNING) {
        fprintf(stderr, "icu adapter: %s is an ambiguous alias; use a converter name\n", argv[1]);
        return 2;
    }
    static UChar ubuf[UCAP];
    static SubMarks marks;
    marks.base = ubuf;
    err = U_ZERO_ERROR;
    ucnv_setToUCallBack(cnv, mark_substitute, &marks, NULL, NULL, &err);
    if (U_FAILURE(err)) die("ucnv_setToUCallBack", err);
    err = U_ZERO_ERROR;
    ucnv_setFromUCallBack(cnv, UCNV_FROM_U_CALLBACK_STOP, NULL, NULL, NULL, &err);
    if (U_FAILURE(err)) die("ucnv_setFromUCallBack", err);

    static char line[4096];
    static char bbuf[1024];
    static uint8_t bytes[1024];
    while (fgets(line, sizeof line, stdin)) {
        size_t n = strlen(line);
        if (n && line[n - 1] == '\n') line[--n] = 0;
        char *tab = strchr(line, '\t');
        if (!tab) { fprintf(stderr, "bad line\n"); return 1; }
        *tab = 0;
        const char *op = line, *arg = tab + 1;
        printf("%s\t%s\t", op, arg);
        if (strcmp(op, "d") == 0) {
            size_t len = strlen(arg) / 2;
            for (size_t i = 0; i < len; i++) bytes[i] = (uint8_t)(hexval(arg[2 * i]) << 4 | hexval(arg[2 * i + 1]));
            ucnv_reset(cnv);
            marks.n = 0;
            err = U_ZERO_ERROR;
            UChar *target = ubuf;
            const char *source = (const char *)bytes;
            /* One call with flush=TRUE converts the whole input and ends it, like ucnv_toUChars. */
            ucnv_toUnicode(cnv, &target, ubuf + UCAP, &source, source + len, NULL, 1, &err);
            if (U_FAILURE(err)) die("ucnv_toUnicode", err);
            int32_t ulen = (int32_t)(target - ubuf);
            if (ulen == 0) printf("-");
            for (int32_t i = 0; i < ulen;) {
                UChar32 c;
                int32_t at = i;
                U16_NEXT(ubuf, i, ulen, c);
                if (at > 0) printf(" ");
                if (substituted(&marks, at) && c != 0xFFFD) printf("!%04X", (unsigned)c);
                else printf("%04X", (unsigned)c);
            }
        } else if (strcmp(op, "e") == 0) {
            int32_t ulen = 0;
            const char *p = arg;
            while (*p) {
                char *end;
                unsigned long cp = strtoul(p, &end, 16);
                U16_APPEND_UNSAFE(ubuf, ulen, (UChar32)cp);
                p = *end ? end + 1 : end;
            }
            ucnv_reset(cnv);
            err = U_ZERO_ERROR;
            int32_t blen = ucnv_fromUChars(cnv, bbuf, sizeof bbuf, ubuf, ulen, &err);
            if (err == U_INVALID_CHAR_FOUND || err == U_ILLEGAL_CHAR_FOUND) {
                printf("!");
            } else if (U_FAILURE(err)) {
                die("ucnv_fromUChars", err);
            } else if (blen == 0) {
                printf("-");
            } else {
                for (int32_t i = 0; i < blen; i++) printf("%02X", (uint8_t)bbuf[i]);
            }
        } else {
            fprintf(stderr, "bad op %s\n", op);
            return 1;
        }
        printf("\n");
    }
    ucnv_close(cnv);
    u_cleanup();
    return 0;
}
