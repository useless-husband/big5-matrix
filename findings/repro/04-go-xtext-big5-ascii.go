// Go x/text Big5 decoder: an ASCII byte 0x40-0x7E after a lead byte is consumed when the pair
// is not mapped, and 0x7F always is. The WHATWG Big5 decoder (which the package's comments
// cite) restores any ASCII byte to the stream. Run with: go run 04-go-xtext-big5-ascii.go
// (in a module that requires golang.org/x/text).
package main

import (
	"fmt"

	"golang.org/x/text/encoding/traditionalchinese"
	"golang.org/x/text/transform"
)

func main() {
	for _, in := range []string{"\x81\x40", "\x81\x5c", "\xa1\x7f", "\xa1\x30"} {
		s, _, _ := transform.String(traditionalchinese.Big5.NewDecoder(), in)
		fmt.Printf("% X -> %+q\n", in, s)
	}
	// WHATWG (encoding_rs, browsers): 81 40 -> "\ufffd@", 81 5C -> "\ufffd\\", A1 7F -> "\ufffd\x7f", A1 30 -> "\ufffd0"
}
