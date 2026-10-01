"""`python3 -m big5matrix show A145` / `show U+2027` / `show 兀`: one case across all implementations."""

from __future__ import annotations

import re

from . import protocol, store
from .registry import IMPLS


def parse_input(text: str) -> tuple[str, str]:
    """Return (op, arg) for a user-supplied byte sequence or character."""
    t = text.strip()
    m = re.fullmatch(r"(?:U\+|u\+)([0-9A-Fa-f]{4,6})", t)
    if m:
        return "e", f"{int(m.group(1), 16):04X}"
    m = re.fullmatch(r"(?:0x)?([0-9A-Fa-f]{2}|[0-9A-Fa-f]{4})", t)
    if m:
        return "d", m.group(1).upper()
    if len(t) == 1:
        return "e", f"{ord(t):04X}"
    raise ValueError(f"not a one- or two-byte hex sequence or a character: {text!r}")


def show(text: str) -> int:
    op, arg = parse_input(text)
    args = store.case_args(op)
    if arg not in args:
        print(f"{arg} is not one of the {store.OPS[op]} cases")
        return 1
    print(f"{store.OPS[op]} {arg}")
    for impl in IMPLS:
        if op not in impl.ops or not store.has_results(impl.id, op):
            continue
        res = store.read_results(impl.id, op, args=args).get(arg, "(outside this table)")
        if op == "d" and res not in ("(outside this table)",):
            res = " ".join(protocol.decode_tokens(res)) or "(nothing)"
        print(f"  {impl.id:28s} {res}")
    return 0
