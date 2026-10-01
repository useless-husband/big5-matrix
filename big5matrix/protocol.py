"""The line protocol spoken between the harness and every adapter.

An adapter is started as ``<adapter> <codec>`` and reads requests on stdin, one per line:

    d<TAB>A140            decode these bytes (uppercase hex, no separators)
    e<TAB>00CA 0304       encode this sequence of code points (hex, space separated)

and writes exactly one response line per request, in the same order:

    d<TAB>A140<TAB>3000
    e<TAB>00CA 0304<TAB>8862

Decode result: the decoded text as space-separated code points (uppercase hex, at least four
digits), produced in the implementation's replacement mode, so an error shows up as FFFD
followed by whatever the implementation does next. An implementation that substitutes something
other than U+FFFD for an error, and lets the adapter tell, writes ``!XXXX`` for that substitute
(ICU's IBM converters write U+001A, for example). An implementation that has no replacement mode
(it can only stop) writes ``!`` where it stopped. ``-`` means the output was empty.

Encode result: the bytes in uppercase hex, ``!`` if the implementation reported the input as
not encodable, ``-`` if the output was empty.

``<adapter> --version`` prints ``version=<description>`` and ``key=<behaviour key>`` lines. The
key is the part of the version that determines behaviour (for example the x/text module version
for Go); the drift check compares data only when the key is unchanged. An adapter whose codecs
depend on different components may add ``key.<codec>=...`` lines that override ``key``.
"""

from __future__ import annotations

from dataclasses import dataclass

ERROR = "!"
EMPTY = "-"
REPLACEMENT = "FFFD"


class ProtocolError(ValueError):
    """An adapter wrote something that does not follow the protocol."""


@dataclass(frozen=True)
class Response:
    op: str
    arg: str
    result: str


def format_request(op: str, arg: str) -> str:
    if op not in ("d", "e"):
        raise ValueError(f"unknown op {op!r}")
    return f"{op}\t{arg}\n"


def bytes_arg(data: bytes) -> str:
    return data.hex().upper()


def cps_arg(cps: tuple[int, ...]) -> str:
    return " ".join(f"{c:04X}" for c in cps)


def parse_cps_arg(arg: str) -> tuple[int, ...]:
    return tuple(int(x, 16) for x in arg.split())


def format_cps(cps) -> str:
    """Format decoded code points as a decode result."""
    out = " ".join(f"{c:04X}" for c in cps)
    return out or EMPTY


def format_bytes(data: bytes) -> str:
    return data.hex().upper() or EMPTY


def _is_hex(tok: str, min_len: int) -> bool:
    return len(tok) >= min_len and all(c in "0123456789ABCDEF" for c in tok)


def validate_result(op: str, result: str) -> None:
    """Raise ProtocolError unless result is well formed for op."""
    if result in (ERROR, EMPTY):
        return
    if op == "e":
        if len(result) % 2 or not _is_hex(result, 2):
            raise ProtocolError(f"bad encode result {result!r}")
        return
    toks = result.split(" ")
    for i, t in enumerate(toks):
        if t == ERROR:
            if i != len(toks) - 1:
                raise ProtocolError(f"'!' must end a decode result: {result!r}")
            continue
        if t.startswith(ERROR):
            t = t[1:]
        if not _is_hex(t, 4) or len(t) > 6 or int(t, 16) > 0x10FFFF:
            raise ProtocolError(f"bad code point {t!r} in {result!r}")


def parse_response(line: str) -> Response:
    parts = line.rstrip("\n").split("\t")
    if len(parts) != 3:
        raise ProtocolError(f"expected 3 tab-separated fields, got {line!r}")
    op, arg, result = parts
    if op not in ("d", "e"):
        raise ProtocolError(f"unknown op in {line!r}")
    validate_result(op, result)
    return Response(op, arg, result)


def parse_version(text: str) -> dict[str, str]:
    info: dict[str, str] = {}
    for line in text.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            info[k.strip()] = v.strip()
    if "version" not in info or "key" not in info:
        raise ProtocolError(f"--version must print version= and key= lines, got {text!r}")
    return info


def decode_tokens(result: str) -> list[str]:
    """Normalise a decode result into tokens: hex code points and '!' for every error.

    U+FFFD is the replacement character every replacement-mode implementation emits, so it is
    read as an error. (No implementation or table in this study maps a valid sequence to
    U+FFFD on purpose; BIG5.TXT uses it to mean "unmapped", which is also an error.) A marked
    substitute ``!XXXX`` is an error too.
    """
    if result == EMPTY:
        return []
    return [ERROR if t == REPLACEMENT or t.startswith(ERROR) else t for t in result.split(" ")]


def is_clean_decode(result: str) -> bool:
    """True when the decode produced text without any error."""
    return ERROR not in decode_tokens(result)
