"""Reference columns computed from published tables, not from running a converter.

* ``whatwg``: the Big5 decoder and encoder algorithms of the WHATWG Encoding Standard, run over
  its index-big5.txt. The spec defines error handling, so this column has the replacement
  error model.
* ``unicode-big5``: Unicode's (obsolete) BIG5.TXT, decode only.
* ``ms-cp950``: Microsoft's CP950.TXT as published by Unicode, decode only.
* ``ms-bestfit950``: Microsoft's WindowsBestFit table for code page 950: its MBTABLE/DBCSTABLE
  for decoding and its WCTABLE, which includes the "best fit" mappings, for encoding.
* ``hkscs-2016``: the Hong Kong government's HKSCS-2016 data set (only the 5 005 characters that
  have a Big5 code, plus the four composed sequences), decode only and partial in scope.

A table says nothing about malformed input, so table columns use the strict model: the result
stops with ``!`` at the first byte sequence the table does not define.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from .protocol import EMPTY, ERROR, format_cps

REF_DIR = Path(__file__).resolve().parent.parent / "reference"


# ---------------------------------------------------------------------------------------------
# WHATWG Encoding Standard, section "Big5"


WHATWG_SPECIAL = {
    1133: (0x00CA, 0x0304),
    1135: (0x00CA, 0x030C),
    1164: (0x00EA, 0x0304),
    1166: (0x00EA, 0x030C),
}
WHATWG_LAST_POINTER = {0x2550, 0x255E, 0x2561, 0x256A, 0x5341, 0x5345}


def load_whatwg_index(path: Path | None = None) -> dict[int, int]:
    path = path or REF_DIR / "index-big5.txt"
    index: dict[int, int] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        pointer, cp = line.split("\t")[:2]
        index[int(pointer)] = int(cp, 16)
    return index


@dataclass
class Whatwg:
    """A direct transcription of the spec's Big5 decoder and encoder."""

    index: dict[int, int]
    _encode: dict[int, int] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        # Index Big5 pointer: exclude pointers below (0xA1 - 0x81) * 157 (the HKSCS rows), then
        # take the last pointer for six code points and the first pointer for all others.
        enc: dict[int, int] = {}
        for pointer in sorted(self.index):
            if pointer < (0xA1 - 0x81) * 157:
                continue
            cp = self.index[pointer]
            if cp in WHATWG_LAST_POINTER or cp not in enc:
                enc[cp] = pointer
        self._encode = enc

    def decode(self, data: bytes) -> list[int | str]:
        out: list[int | str] = []
        queue = list(data)
        lead = 0
        i = 0
        while True:
            if i == len(queue):
                if lead != 0:
                    out.append(ERROR)
                return out
            byte = queue[i]
            i += 1
            if lead != 0:
                pointer = None
                cur, lead = lead, 0
                offset = 0x40 if byte < 0x7F else 0x62
                if 0x40 <= byte <= 0x7E or 0xA1 <= byte <= 0xFE:
                    pointer = (cur - 0x81) * 157 + (byte - offset)
                if pointer in WHATWG_SPECIAL:
                    out.extend(WHATWG_SPECIAL[pointer])
                    continue
                cp = None if pointer is None else self.index.get(pointer)
                if cp is not None:
                    out.append(cp)
                    continue
                if byte < 0x80:
                    i -= 1  # restore the ASCII byte to the stream
                out.append(ERROR)
                continue
            if byte < 0x80:
                out.append(byte)
            elif 0x81 <= byte <= 0xFE:
                lead = byte
            else:
                out.append(ERROR)

    def encode(self, cps: tuple[int, ...]) -> bytes | None:
        out = bytearray()
        for cp in cps:
            if cp < 0x80:
                out.append(cp)
                continue
            pointer = self._encode.get(cp)
            if pointer is None:
                return None
            lead = pointer // 157 + 0x81
            trail = pointer % 157
            offset = 0x40 if trail < 0x3F else 0x62
            out += bytes([lead, trail + offset])
        return bytes(out)


# ---------------------------------------------------------------------------------------------
# Plain mapping tables


@dataclass
class Table:
    """A byte-sequence -> code points table, decoded with the strict model."""

    singles: dict[int, tuple[int, ...]]
    pairs: dict[bytes, tuple[int, ...]]
    encode_map: dict[tuple[int, ...], bytes] | None = None
    scope: set[bytes] | None = None  # None: the table covers the whole code space

    def __post_init__(self) -> None:
        self.leads = {p[0] for p in self.pairs}

    def in_scope(self, data: bytes) -> bool:
        if self.scope is None:
            return True
        return data in self.scope

    def decode(self, data: bytes) -> list[int | str]:
        out: list[int | str] = []
        i = 0
        while i < len(data):
            b = data[i]
            if b in self.singles:
                out.extend(self.singles[b])
                i += 1
                continue
            pair = data[i : i + 2]
            if len(pair) == 2 and pair in self.pairs:
                out.extend(self.pairs[pair])
                i += 2
                continue
            out.append(ERROR)
            return out
        return out

    def encode(self, cps: tuple[int, ...]) -> bytes | None:
        if self.encode_map is None:
            raise ValueError("this table is decode-only")
        whole = self.encode_map.get(cps)
        if whole is not None:
            return whole
        out = bytearray()
        for cp in cps:
            b = self.encode_map.get((cp,))
            if b is None:
                return None
            out += b
        return bytes(out)


ASCII = {b: (b,) for b in range(0x80)}


def _hexpairs(path: Path, encoding: str = "latin-1"):
    """Yield (code, unicode) pairs from a 'Format A' style mapping file."""
    pat = re.compile(r"^\s*0x([0-9A-Fa-f]+)\s+0x([0-9A-Fa-f]+)")
    for line in path.read_text(encoding=encoding).splitlines():
        m = pat.match(line)
        if m:
            yield int(m.group(1), 16), int(m.group(2), 16)


def load_unicode_big5(path: Path | None = None) -> Table:
    path = path or REF_DIR / "BIG5.TXT"
    pairs = {}
    for code, cp in _hexpairs(path):
        if cp == 0xFFFD:  # BIG5.TXT's way of saying "not mapped"
            continue
        pairs[code.to_bytes(2, "big")] = (cp,)
    # BIG5.TXT lists only the double-byte part; ASCII is implied.
    return Table(dict(ASCII), pairs)


def load_ms_cp950(path: Path | None = None) -> Table:
    path = path or REF_DIR / "CP950.TXT"
    singles, pairs = {}, {}
    for code, cp in _hexpairs(path):
        if code < 0x100:
            singles[code] = (cp,)
        else:
            pairs[code.to_bytes(2, "big")] = (cp,)
    return Table(singles, pairs)


def load_ms_bestfit950(path: Path | None = None) -> Table:
    """Parse the WindowsBestFit format. Every section header carries its record count, which is
    what tells a lead-byte range record apart from a mapping record (both are two hex fields)."""
    path = path or REF_DIR / "bestfit950.txt"
    lines = []
    for raw in path.read_text(encoding="latin-1").splitlines():
        line = raw.split(";", 1)[0].strip()
        if line:
            lines.append(line.split())
    singles: dict[int, tuple[int, ...]] = {}
    pairs: dict[bytes, tuple[int, ...]] = {}
    enc: dict[tuple[int, ...], bytes] = {}
    i = 0

    def records(n: int):
        nonlocal i
        recs = [(int(f[0], 16), int(f[1], 16)) for f in lines[i : i + n]]
        if len(recs) != n:
            raise ValueError("truncated section in bestfit table")
        i += n
        return recs

    while i < len(lines):
        tag, *rest = lines[i]
        i += 1
        tag = tag.upper()
        if tag == "MBTABLE":
            for a, b in records(int(rest[0])):
                singles[a] = (b,)
        elif tag == "DBCSRANGE":
            for _ in range(int(rest[0])):
                (first, last), = records(1)
                for lead in range(first, last + 1):
                    head, count = lines[i]
                    if head.upper() != "DBCSTABLE":
                        raise ValueError(f"expected DBCSTABLE for lead 0x{lead:02X}, got {head}")
                    i += 1
                    for trail, cp in records(int(count)):
                        pairs[bytes([lead, trail])] = (cp,)
        elif tag == "WCTABLE":
            for a, b in records(int(rest[0])):
                enc[(a,)] = bytes([b]) if b < 0x100 else b.to_bytes(2, "big")
        elif tag == "ENDCODEPAGE":
            break
        elif tag in ("CODEPAGE", "CPINFO"):
            continue
        else:
            raise ValueError(f"unexpected record {lines[i - 1]} in bestfit table")
    return Table(singles, pairs, encode_map=enc)


HKSCS_COMPOSED = {
    # HKSCS-2004 and later: four Big5 codes stand for a base letter plus a combining mark.
    bytes.fromhex("8862"): (0x00CA, 0x0304),
    bytes.fromhex("8864"): (0x00CA, 0x030C),
    bytes.fromhex("88A3"): (0x00EA, 0x0304),
    bytes.fromhex("88A5"): (0x00EA, 0x030C),
}


def load_hkscs_2016(path: Path | None = None) -> Table:
    path = path or REF_DIR / "HKSCS2016.json"
    rows = json.loads(path.read_text(encoding="utf-8-sig"))
    pairs: dict[bytes, tuple[int, ...]] = {}
    for row in rows:
        m = re.fullmatch(r"H-([0-9A-F]{4})", row["H-Source"])
        if not m:
            continue  # characters added in 2016 without a Big5 code
        code = bytes.fromhex(m.group(1))
        if code in pairs:
            raise ValueError(f"duplicate HKSCS Big5 code {m.group(1)}")
        pairs[code] = (int(row["codepoint"], 16),)
    pairs.update(HKSCS_COMPOSED)
    return Table(dict(ASCII), pairs, scope=set(pairs))


# ---------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class RefSpec:
    id: str
    label: str
    ops: str
    error_model: str
    source: str


REFERENCES = [
    RefSpec("ref.whatwg", "WHATWG Encoding Standard (algorithm + index-big5)", "de", "replace",
            "reference/index-big5.txt"),
    RefSpec("ref.unicode-big5", "Unicode BIG5.TXT (table)", "d", "strict", "reference/BIG5.TXT"),
    RefSpec("ref.ms-cp950", "Microsoft CP950.TXT (table)", "d", "strict", "reference/CP950.TXT"),
    RefSpec("ref.ms-bestfit950", "Microsoft bestfit950.txt (table, with best fit)", "de", "strict",
            "reference/bestfit950.txt"),
    RefSpec("ref.hkscs-2016", "HKSCS-2016 data set (table, HKSCS part only)", "d", "strict",
            "reference/HKSCS2016.json"),
]


def load(ref_id: str):
    return {
        "ref.whatwg": lambda: Whatwg(load_whatwg_index()),
        "ref.unicode-big5": load_unicode_big5,
        "ref.ms-cp950": load_ms_cp950,
        "ref.ms-bestfit950": load_ms_bestfit950,
        "ref.hkscs-2016": load_hkscs_2016,
    }[ref_id]()


def run_reference(ref_id: str, op: str, args: list[str]) -> dict[str, str]:
    """Compute results for a reference column, in the same format adapters produce."""
    model = load(ref_id)
    out: dict[str, str] = {}
    for arg in args:
        if op == "d":
            data = bytes.fromhex(arg)
            if isinstance(model, Table) and not model.in_scope(data):
                continue
            toks = model.decode(data)
            out[arg] = " ".join(t if t == ERROR else f"{t:04X}" for t in toks) or EMPTY
        else:
            cps = tuple(int(x, 16) for x in arg.split())
            b = model.encode(cps)
            out[arg] = ERROR if b is None else (b.hex().upper() or EMPTY)
    return out


__all__ = ["Whatwg", "Table", "REFERENCES", "run_reference", "load", "format_cps"]
