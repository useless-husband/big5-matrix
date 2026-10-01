"""`python3 -m big5matrix show A145` / `show U+2027` / `show 兀`: one case across all implementations.

Implementations that give the same result are listed together; `--all` lists them one per line.
"""

from __future__ import annotations

import re
import textwrap

from . import protocol, store
from .registry import IMPLS


def parse_input(text: str) -> tuple[str, str]:
    """Return (op, arg) for a user-supplied byte sequence or character."""
    t = text.strip()
    m = re.fullmatch(r"(?:U\+|u\+)([0-9A-Fa-f]{4,6})", t)
    if m:
        return "e", f"{int(m.group(1), 16):04X}"
    h = re.sub(r"[\s,]+", "", re.sub(r"^0x", "", t, flags=re.I))
    if re.fullmatch(r"[0-9A-Fa-f]{2}|[0-9A-Fa-f]{4}", h):
        return "d", h.upper()
    if len(t) == 1:
        return "e", f"{ord(t):04X}"
    raise ValueError(f"not a one- or two-byte hex sequence or a character: {text!r}")


def describe(op: str, res: str) -> str:
    if res is None:
        return "(outside this table)"
    if op == "e":
        return {"!": "error (not encodable)", "-": "nothing (no bytes, no error)"}.get(res, " ".join(
            res[i:i + 2] for i in range(0, len(res), 2)))
    toks = protocol.decode_tokens(res)
    if not toks:
        return "nothing"
    parts = []
    for t in toks:
        if t == protocol.ERROR:
            parts.append("error")
            continue
        c = int(t, 16)
        printable = c >= 0x20 and not (0x7F <= c < 0xA0) and not (0xD800 <= c <= 0xF8FF)
        parts.append(f"U+{t}" + (f" {chr(c)}" if printable else ""))
    return " ".join(parts)


def show(text: str, every: bool = False) -> int:
    op, arg = parse_input(text)
    args = store.case_args(op)
    if arg not in args:
        print(f"{arg} is not one of the {store.OPS[op]} cases")
        return 1
    print(f"{store.OPS[op]} {' '.join(arg[i:i + 2] for i in range(0, len(arg), 2)) if op == 'd' else 'U+' + arg}")
    groups: dict[str, list[str]] = {}
    for impl in IMPLS:
        if op not in impl.ops or not store.has_results(impl.id, op):
            continue
        res = store.read_results(impl.id, op, args=args).get(arg)
        groups.setdefault(describe(op, res), []).append(impl.id)
    if every:
        for value, ids in groups.items():
            for i in ids:
                print(f"  {i:28s} {value}")
        return 0
    for value, ids in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        print(f"  {value}  ({len(ids)})")
        print(textwrap.fill(", ".join(ids), width=96, initial_indent="      ", subsequent_indent="      ",
                            break_on_hyphens=False, break_long_words=False))
    return 0
