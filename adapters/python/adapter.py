"""Adapter for CPython's built-in codecs (big5, cp950, big5hkscs). See big5matrix/protocol.py."""

import codecs
import platform
import sys


def main() -> None:
    if sys.argv[1] == "--version":
        print(f"version=CPython {platform.python_version()} ({platform.python_implementation()})")
        print(f"key={platform.python_version()}")
        return
    codec = codecs.lookup(sys.argv[1]).name
    out = []
    for line in sys.stdin:
        op, arg = line.rstrip("\n").split("\t")
        if op == "d":
            text = bytes.fromhex(arg).decode(codec, "replace")
            res = " ".join(f"{ord(c):04X}" for c in text) or "-"
        else:
            text = "".join(chr(int(x, 16)) for x in arg.split())
            try:
                res = text.encode(codec, "strict").hex().upper() or "-"
            except UnicodeEncodeError:
                res = "!"
        out.append(f"{op}\t{arg}\t{res}\n")
    sys.stdout.write("".join(out))


if __name__ == "__main__":
    main()
