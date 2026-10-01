// Adapter for golang.org/x/text/encoding/traditionalchinese. See big5matrix/protocol.py.
package main

import (
	"bufio"
	"fmt"
	"os"
	"runtime"
	"runtime/debug"
	"strconv"
	"strings"

	"golang.org/x/text/encoding"
	"golang.org/x/text/encoding/traditionalchinese"
)

func xtextVersion() string {
	if bi, ok := debug.ReadBuildInfo(); ok {
		for _, d := range bi.Deps {
			if d.Path == "golang.org/x/text" {
				return d.Version
			}
		}
	}
	return "unknown"
}

func main() {
	if len(os.Args) != 2 {
		fmt.Fprintln(os.Stderr, "usage: adapter --version | adapter big5")
		os.Exit(2)
	}
	if os.Args[1] == "--version" {
		fmt.Printf("version=golang.org/x/text %s (%s)\n", xtextVersion(), runtime.Version())
		fmt.Printf("key=%s\n", xtextVersion())
		return
	}
	var enc encoding.Encoding
	switch os.Args[1] {
	case "big5":
		enc = traditionalchinese.Big5
	default:
		fmt.Fprintf(os.Stderr, "unknown codec %q\n", os.Args[1])
		os.Exit(2)
	}
	in := bufio.NewScanner(os.Stdin)
	out := bufio.NewWriterSize(os.Stdout, 1<<16)
	defer out.Flush()
	for in.Scan() {
		op, arg, _ := strings.Cut(in.Text(), "\t")
		var res string
		switch op {
		case "d":
			b, err := parseHexBytes(arg)
			if err != nil {
				fatal(err)
			}
			// The decoder replaces malformed input with U+FFFD; it never returns an error for it.
			s, err := enc.NewDecoder().Bytes(b)
			if err != nil {
				fatal(err)
			}
			res = codePoints(string(s))
		case "e":
			s, err := parseCodePoints(arg)
			if err != nil {
				fatal(err)
			}
			b, err := enc.NewEncoder().Bytes([]byte(s))
			if err != nil {
				res = "!"
			} else {
				res = hexOrDash(b)
			}
		default:
			fatal(fmt.Errorf("bad op %q", op))
		}
		fmt.Fprintf(out, "%s\t%s\t%s\n", op, arg, res)
	}
	if err := in.Err(); err != nil {
		fatal(err)
	}
}

func parseHexBytes(s string) ([]byte, error) {
	b := make([]byte, len(s)/2)
	for i := range b {
		v, err := strconv.ParseUint(s[2*i:2*i+2], 16, 8)
		if err != nil {
			return nil, err
		}
		b[i] = byte(v)
	}
	return b, nil
}

func parseCodePoints(s string) (string, error) {
	var sb strings.Builder
	for _, f := range strings.Fields(s) {
		v, err := strconv.ParseUint(f, 16, 32)
		if err != nil {
			return "", err
		}
		sb.WriteRune(rune(v))
	}
	return sb.String(), nil
}

func codePoints(s string) string {
	if s == "" {
		return "-"
	}
	parts := make([]string, 0, 2)
	for _, r := range s {
		parts = append(parts, fmt.Sprintf("%04X", r))
	}
	return strings.Join(parts, " ")
}

func hexOrDash(b []byte) string {
	if len(b) == 0 {
		return "-"
	}
	return strings.ToUpper(fmt.Sprintf("%x", b))
}

func fatal(err error) {
	fmt.Fprintln(os.Stderr, "adapter:", err)
	os.Exit(1)
}
