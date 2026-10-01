/*
 * Adapter for the system iconv(3): on macOS the FreeBSD-derived "Citrus" iconv in libSystem
 * (the library behind /usr/bin/iconv), on Linux glibc's. See big5matrix/protocol.py.
 *
 * iconv has no replacement mode: a conversion stops at the first malformed or incomplete
 * sequence (EILSEQ / EINVAL), which the adapter writes as "!" after the text converted so far.
 * POSIX also lets iconv() convert a valid but unmappable character to an implementation-
 * defined substitute and count it in its return value; such a count is also written as "!".
 *
 * Build: cc -O2 adapter.c -o iconv-adapter   (add -liconv on macOS)
 */
#include <errno.h>
#include <iconv.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifdef __APPLE__
#include <sys/sysctl.h>
#else
#include <gnu/libc-version.h>
#endif

static int hexval(int c) {
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    return -1;
}

static void print_version(void) {
#ifdef __APPLE__
    char product[64] = "?", build[64] = "?";
    size_t n = sizeof product;
    sysctlbyname("kern.osproductversion", product, &n, NULL, 0);
    n = sizeof build;
    sysctlbyname("kern.osversion", build, &n, NULL, 0);
    printf("version=macOS %s (%s) libiconv (Citrus)\n", product, build);
    printf("key=macos-%s-%s\n", product, build);
#else
    printf("version=glibc %s iconv\n", gnu_get_libc_version());
    printf("key=glibc-%s\n", gnu_get_libc_version());
#endif
}

int main(int argc, char **argv) {
    if (argc != 2) {
        fprintf(stderr, "usage: iconv-adapter --version | iconv-adapter <charset>\n");
        return 2;
    }
    if (strcmp(argv[1], "--version") == 0) {
        print_version();
        return 0;
    }
    iconv_t dec = iconv_open("UTF-32BE", argv[1]);
    iconv_t enc = iconv_open(argv[1], "UTF-32BE");
    if (dec == (iconv_t)-1 || enc == (iconv_t)-1) {
        perror("iconv_open");
        return 2;
    }
    static char line[4096];
    static unsigned char in[1024], out[4096];
    while (fgets(line, sizeof line, stdin)) {
        size_t n = strlen(line);
        if (n && line[n - 1] == '\n') line[--n] = 0;
        char *tab = strchr(line, '\t');
        if (!tab) { fprintf(stderr, "bad line\n"); return 1; }
        *tab = 0;
        const char *op = line, *arg = tab + 1;
        int decoding = strcmp(op, "d") == 0;
        if (!decoding && strcmp(op, "e") != 0) { fprintf(stderr, "bad op %s\n", op); return 1; }

        size_t inlen = 0;
        if (decoding) {
            for (const char *p = arg; p[0] && p[1]; p += 2) in[inlen++] = (unsigned char)(hexval(p[0]) << 4 | hexval(p[1]));
        } else {
            const char *p = arg;
            while (*p) {
                char *end;
                unsigned long cp = strtoul(p, &end, 16);
                in[inlen++] = (unsigned char)(cp >> 24);
                in[inlen++] = (unsigned char)(cp >> 16);
                in[inlen++] = (unsigned char)(cp >> 8);
                in[inlen++] = (unsigned char)cp;
                p = *end ? end + 1 : end;
            }
        }
        iconv_t cd = decoding ? dec : enc;
        iconv(cd, NULL, NULL, NULL, NULL); /* reset the conversion state */
        char *ip = (char *)in, *op_ = (char *)out;
        size_t ileft = inlen, oleft = sizeof out;
        int failed = 0;
        size_t r = iconv(cd, &ip, &ileft, &op_, &oleft);
        if (r == (size_t)-1) {
            if (errno != EILSEQ && errno != EINVAL) { perror("iconv"); return 1; }
            failed = 1;
        } else {
            if (r > 0) failed = 1; /* non-identical (substituted) conversions */
            if (iconv(cd, NULL, NULL, &op_, &oleft) == (size_t)-1) failed = 1; /* flush */
        }
        size_t olen = sizeof out - oleft;
        printf("%s\t%s\t", op, arg);
        if (decoding) {
            int first = 1;
            for (size_t i = 0; i + 3 < olen; i += 4) {
                uint32_t cp = (uint32_t)out[i] << 24 | (uint32_t)out[i + 1] << 16 | (uint32_t)out[i + 2] << 8 | out[i + 3];
                printf(first ? "%04X" : " %04X", cp);
                first = 0;
            }
            if (failed) printf(first ? "!" : " !");
            else if (first) printf("-");
        } else if (failed) {
            printf("!");
        } else if (olen == 0) {
            printf("-");
        } else {
            for (size_t i = 0; i < olen; i++) printf("%02X", out[i]);
        }
        printf("\n");
    }
    iconv_close(dec);
    iconv_close(enc);
    return 0;
}
