#!/usr/bin/env python3
"""Check the report's surprising claims a second way.

The study's data comes from the adapters in adapters/. Each claim below is checked again by
calling the runtime directly (its command-line tool, or a few lines written independently of
the adapter), and also against the committed data. A claim passes only if both agree with the
expected value. Runtimes that are not installed are skipped.

Usage: python3 tools/verify_claims.py [CLAIM-ID ...]
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from big5matrix import store  # noqa: E402
from big5matrix.registry import Unavailable, _cargo, _java  # noqa: E402

JAVA = None
ICONV = "/usr/bin/iconv"


def sh(cmd: list[str], data: bytes = b"", cwd: Path | None = None) -> tuple[int, bytes]:
    r = subprocess.run(cmd, input=data, capture_output=True, cwd=cwd, timeout=600)
    return r.returncode, r.stdout


def utf32(b: bytes) -> str:
    return " ".join(f"{int.from_bytes(b[i:i + 4], 'big'):04X}" for i in range(0, len(b), 4)) or "-"


def text_cps(s: str) -> str:
    return " ".join(f"{ord(c):04X}" for c in s) or "-"


def data(impl: str, op: str, arg: str) -> str:
    return store.read_results(impl, op).get(arg, "?")


@dataclass
class Claim:
    id: str
    text: str
    needs: str  # executable that must exist
    expected: str
    direct: Callable[[], str]  # the runtime asked directly, without the adapter
    recorded: Callable[[], str] | None  # the committed data, in the same format (None: not in the data)


def _node(js: str) -> str:
    return subprocess.run(["node", "-e", js], capture_output=True, text=True, timeout=120).stdout.strip()


def _python(code: str) -> str:
    return subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=120).stdout.strip()


def _go(body: str) -> str:
    """Run a small independent Go program against the same x/text version as the adapter."""
    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp)
        shutil.copy(ROOT / "adapters" / "go" / "go.mod", t / "go.mod")
        shutil.copy(ROOT / "adapters" / "go" / "go.sum", t / "go.sum")
        (t / "main.go").write_text(body)
        r = subprocess.run(["go", "run", "."], cwd=t, capture_output=True, text=True, timeout=600)
        return (r.stdout or r.stderr).strip()


def _dotnet(body: str) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp)
        (t / "v.csproj").write_text(
            '<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType>'
            "<TargetFramework>net10.0</TargetFramework><ImplicitUsings>enable</ImplicitUsings>"
            "</PropertyGroup></Project>")
        (t / "Program.cs").write_text(body)
        r = subprocess.run(["dotnet", "run", "-v", "q"], cwd=t, capture_output=True, text=True, timeout=600)
        return (r.stdout or r.stderr).strip()


def _java_snippet(body: str) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / "V.java"
        f.write_text(body)
        r = subprocess.run([_java(), str(f)], capture_output=True, text=True, timeout=300)
        return (r.stdout or r.stderr).strip()


def _chromium(hexes: list[str]) -> str:
    """Decode with TextDecoder('big5') in headless Chromium (the browser adapter's playwright-core)."""
    script = (
        "import { chromium } from 'playwright-core';"
        "const b = await chromium.launch(); const p = await b.newPage();"
        f"const r = await p.evaluate((hs) => hs.map(h => {{ const s = new TextDecoder('big5').decode("
        "Uint8Array.from(h.match(/../g).map(x => parseInt(x, 16))));"
        "return Array.from({length: s.length}, (_, i) => s.charCodeAt(i).toString(16).toUpperCase()"
        f".padStart(4, '0')).join(' '); }}), {hexes!r});"
        "console.log(r.join(' | ')); await b.close();")
    r = subprocess.run(["node", "--input-type=module", "-e", script], cwd=ROOT / "adapters" / "browser",
                       capture_output=True, text=True, timeout=300)
    return (r.stdout or r.stderr).strip()


def chromium_available() -> bool:
    return (ROOT / "adapters" / "browser" / "node_modules" / "playwright-core").exists() and bool(shutil.which("node"))


def iconv_decode(charset: str, raw: bytes) -> str:
    rc, out = sh([ICONV, "-f", charset, "-t", "UTF-32BE"], raw)
    return utf32(out) + ("" if rc == 0 else " !")


def iconv_encode(charset: str, text: str) -> str:
    rc, out = sh([ICONV, "-f", "UTF-8", "-t", charset], text.encode())
    return (out.hex().upper() or "-") if rc == 0 else "!"


UCONV = next((p for p in ("/opt/homebrew/opt/icu4c/bin/uconv", shutil.which("uconv") or "") if p and os.path.exists(p)), "")


def err(r: str) -> str:
    return "error" if r in ("FFFD", "!") or r.startswith("!") else r


GO_DECODE = ('package main\nimport ("fmt";"golang.org/x/text/encoding/traditionalchinese";'
             '"golang.org/x/text/transform")\nfunc main(){s,_,_:=transform.String('
             'traditionalchinese.Big5.NewDecoder(),"%s");for _,r:=range s{fmt.Printf("%%04X ",r)}}')
DOTNET_PRE = "using System.Text;Encoding.RegisterProvider(CodePagesEncodingProvider.Instance);"

CLAIMS = [
    Claim("node-textdecoder-icu",
          "Node's TextDecoder('big5') decodes 0x83 0x5C to U+F00E (Private Use Area); the WHATWG decoder "
          "gives U+FFFD and keeps the backslash", "node", "F00E",
          lambda: _node("const d=new TextDecoder('big5');console.log([...d.decode(Buffer.from([0x83,0x5c]))]"
                        ".map(c=>c.codePointAt(0).toString(16).toUpperCase().padStart(4,'0')).join(' '))"),
          lambda: data("node.textdecoder", "d", "835C")),
    Claim("whatwg-keeps-backslash",
          "A WHATWG decoder (Chromium) turns 0x83 0x5C into U+FFFD U+005C, as the reference column does",
          "chromium", "FFFD 005C",
          lambda: _chromium(["835C"]),
          lambda: data("ref.whatwg", "d", "835C").replace("!", "FFFD")),
    Claim("chromium-8862",
          "Chromium decodes 0x8862 to U+0093 U+DF04 (a C1 control and a lone surrogate); WHATWG: U+00CA U+0304",
          "chromium", "0093 DF04",
          lambda: _chromium(["8862"]),
          lambda: data("browser.chromium", "d", "8862")),
    Claim("node-equals-icu-windows-950",
          "Node's TextDecoder('big5') agrees with ICU's windows-950-2000 (uconv) on 0x80, 0xFF, 0x8862, 0xA3E1",
          UCONV, "0080 | F8F8 | F325 | 20AC",
          lambda: " | ".join(utf32(sh([UCONV, "-f", "windows-950-2000", "-t", "UTF-32BE"], bytes.fromhex(h))[1])
                             for h in ("80", "FF", "8862", "A3E1")),
          lambda: " | ".join(data("node.textdecoder", "d", h) for h in ("80", "FF", "8862", "A3E1"))),
    Claim("go-swallows-ascii",
          "Go x/text decodes 0x81 0x40 to one U+FFFD (the '@' is consumed); WHATWG keeps the '@'",
          "go", "FFFD", lambda: _go(GO_DECODE % "\\x81\\x40"), lambda: data("go.big5", "d", "8140")),
    Claim("go-swallows-del", "Go x/text decodes 0xA1 0x7F to one U+FFFD (DEL consumed)",
          "go", "FFFD", lambda: _go(GO_DECODE % "\\xa1\\x7f"), lambda: data("go.big5", "d", "A17F")),
    Claim("iconv-hkscs-no-base",
          "macOS iconv BIG5-HKSCS cannot encode U+4E2D (中, Big5 0xA4A4)", ICONV, "!",
          lambda: iconv_encode("BIG5-HKSCS", "\u4e2d"), lambda: data("iconv.big5-hkscs", "e", "4E2D")),
    Claim("iconv-hkscs-plane-bits",
          "macOS iconv BIG5-HKSCS encodes U+0086 as 0x8BC5, which it decodes as U+20086", ICONV, "8BC5 -> 20086",
          lambda: iconv_encode("BIG5-HKSCS", "\u0086") + " -> " + iconv_decode("BIG5-HKSCS", bytes.fromhex("8BC5")),
          lambda: data("iconv.big5-hkscs", "e", "0086") + " -> " + data("iconv.big5-hkscs", "d", "8BC5")),
    Claim("iconv-hkscs-8862",
          "macOS iconv BIG5-HKSCS decodes 0x8862 to U+00CA alone (HKSCS-2004 and later: U+00CA U+0304)",
          ICONV, "00CA",
          lambda: iconv_decode("BIG5-HKSCS", bytes.fromhex("8862")), lambda: data("iconv.big5-hkscs", "d", "8862")),
    Claim("iconv-translit-ascii", "macOS iconv BIG5 turns 'a\u2039b' into 'a<b' and exits 0", ICONV, "613C62",
          lambda: iconv_encode("BIG5", "a\u2039b"), lambda: "61" + data("iconv.big5", "e", "2039") + "62"),
    Claim("iconv-big5-02b9", "macOS iconv BIG5 encodes U+02B9 as 0xACA1, which decodes to U+6D3B",
          ICONV, "ACA1 -> 6D3B",
          lambda: iconv_encode("BIG5", "\u02b9") + " -> " + iconv_decode("BIG5", bytes.fromhex("ACA1")),
          lambda: data("iconv.big5", "e", "02B9") + " -> " + data("iconv.big5", "d", "ACA1")),
    Claim("dotnet-950-a2a4", ".NET code page 950 rejects 0xA2A4 (CP950.TXT: U+2550)", "dotnet", "error",
          lambda: _dotnet(DOTNET_PRE + 'try{Encoding.GetEncoding(950,EncoderFallback.ExceptionFallback,'
                          'DecoderFallback.ExceptionFallback).GetString(new byte[]{0xA2,0xA4});Console.Write("ok");}'
                          'catch(DecoderFallbackException){Console.Write("error");}'),
          lambda: err(data("dotnet.950", "d", "A2A4"))),
    Claim("dotnet-bestfit-soft-hyphen",
          ".NET Encoding.GetEncoding(950).GetBytes(\"\\u00AD\") gives 0x2D ('-')", "dotnet", "2D",
          lambda: _dotnet(DOTNET_PRE + 'Console.Write(Convert.ToHexString(Encoding.GetEncoding(950).GetBytes("\\u00AD")));'),
          lambda: data("dotnet.950-default", "e", "00AD")),
    Claim("php-cp950-euro", "PHP mbstring CP950 rejects 0xA3E1 (Microsoft's Euro sign)", "php", "error",
          lambda: subprocess.run(["php", "-r", 'echo mb_check_encoding("\\xA3\\xE1", "CP950") ? "ok" : "error";'],
                                 capture_output=True, text=True).stdout.strip(),
          lambda: err(data("php.cp950", "d", "A3E1"))),
    Claim("perl-drops-lone-lead",
          "Perl's Encode::decode('big5-eten', \"\\xA4\") returns an empty string", "perl", "0",
          lambda: subprocess.run(["perl", "-MEncode", "-e", 'print length(decode("big5-eten", "\\xA4"))'],
                                 capture_output=True, text=True).stdout.strip(),
          lambda: "0" if data("perl.big5-eten", "d", "A4") == "-" else data("perl.big5-eten", "d", "A4")),
    Claim("icu-ibm950-rotation", "ICU's 'cp950' (ibm-950) decodes the byte 0x1A as U+001C", UCONV, "001C",
          lambda: utf32(sh([UCONV, "-f", "cp950", "-t", "UTF-32BE"], b"\x1a")[1]),
          lambda: data("icu.ibm-950", "d", "1A")),
    Claim("java-cp950-is-ibm", "Java's Charset.forName(\"cp950\") is x-IBM950, not x-windows-950", "java",
          "x-IBM950",
          lambda: _java_snippet('public class V{public static void main(String[] a){System.out.print('
                                'java.nio.charset.Charset.forName("cp950").name());}}'),
          None),
    Claim("java-hkscs-swallows-ascii",
          "Java's Big5-HKSCS decodes 0xA1 0x22 to one U+FFFD (the quote mark is consumed)", "java", "FFFD",
          lambda: _java_snippet('public class V{public static void main(String[] a)throws Exception{String s=new String('
                                'new byte[]{(byte)0xA1,0x22},"Big5-HKSCS");StringBuilder b=new StringBuilder();'
                                's.codePoints().forEach(c->b.append(String.format("%04X ",c)));'
                                'System.out.print(b.toString().trim());}}'),
          lambda: data("java.big5-hkscs", "d", "A122")),
    Claim("ruby-cp950-bestfit", "Ruby's CP950 encodes U+00AD (soft hyphen) as 0x2D without an error", "ruby", "2D",
          lambda: subprocess.run(["ruby", "-e", 'print "\\u00AD".encode("CP950").unpack1("H*")'],
                                 capture_output=True, text=True).stdout.strip().upper(),
          lambda: data("ruby.cp950", "e", "00AD")),
    Claim("icu-drops-soft-hyphen",
          "ICU (uconv) encodes 'a\\u00ADb' to 'ab': the soft hyphen disappears without an error", UCONV, "6162",
          lambda: sh([UCONV, "-f", "UTF-8", "-t", "windows-950-2000"], "a\u00adb".encode())[1].hex().upper(),
          lambda: "61" + data("icu.windows-950-2000", "e", "00AD").replace("-", "") + "62"),
    Claim("python-cp950-oneway", "Python's cp950 encodes U+00A2 as 0xA246, which it decodes as U+FFE0",
          sys.executable, "A246 FFE0",
          lambda: _python("print('\\u00a2'.encode('cp950').hex().upper(), "
                          "' '.join('%04X'%ord(c) for c in b'\\xa2\\x46'.decode('cp950')))"),
          lambda: data("python.cp950", "e", "00A2") + " " + data("python.cp950", "d", "A246")),
]


def norm(s: str) -> str:
    return " ".join(s.split()).upper()


def available(exe: str) -> bool:
    if not exe:
        return False
    if exe == "chromium":
        return chromium_available()
    if exe == "java":
        try:
            _java()
            return True
        except Unavailable:
            return False
    return bool(shutil.which(exe) or os.path.exists(exe))


def main(argv: list[str]) -> int:
    chosen = [c for c in CLAIMS if not argv or c.id in argv]
    failed = skipped = 0
    for c in chosen:
        if not available(c.needs):
            print(f"SKIP  {c.id}: {c.needs or 'tool'} not installed")
            skipped += 1
            continue
        direct = c.direct()
        recorded = c.recorded() if c.recorded else None
        ok = norm(direct) == norm(c.expected) and (recorded is None or norm(recorded) == norm(c.expected))
        failed += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {c.id}: {c.text}")
        print(f"      expected {c.expected!r}; direct {direct!r}; data {recorded!r}")
    print(f"{len(chosen) - failed - skipped} passed, {failed} failed, {skipped} skipped")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
