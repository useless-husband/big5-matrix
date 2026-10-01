"""The committed data, loaded and normalised for analysis.

Normalised decode result: a string of space-separated tokens, each a code point in hex or ``!``
for an error (U+FFFD, a marked substitute, or the point where a strict converter stopped);
``-`` for empty output. Encode results are kept as written (hex bytes, ``!`` or ``-``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path

from . import protocol, store
from .registry import IMPLS, Impl

ERR = protocol.ERROR
EMPTY = protocol.EMPTY


def norm_decode(result: str) -> str:
    toks = protocol.decode_tokens(result)
    return " ".join(toks) if toks else EMPTY


def is_clean(nresult: str) -> bool:
    """A normalised decode result that is non-empty text without errors."""
    return nresult != EMPTY and ERR not in nresult.split(" ")


# ---------------------------------------------------------------------------------------------
# Regions of the code space


DECODE_REGIONS = [
    # (id, title, description)
    ("ascii", "ASCII bytes", "Single bytes 0x00-0x7F."),
    ("byte-80-ff", "Bytes 0x80 and 0xFF", "The two non-ASCII bytes that are never Big5 lead bytes, alone or "
     "followed by another byte. Windows code page 950 maps them to U+0080 and U+F8F8."),
    ("lone-lead", "A lead byte at the end of the input",
     "A lead byte 0x81-0xFE with nothing after it: a truncated character."),
    ("ascii-after-lead", "A lead byte followed by an ASCII byte",
     "A lead byte followed by a byte 0x00-0x7F where the pair is not a character (for that "
     "implementation). Does the ASCII byte survive? The WHATWG decoder always gives it back."),
    ("bad-trail", "A lead byte followed by a non-ASCII byte that is not a trail byte",
     "A lead byte followed by 0x80-0xA0 or 0xFF: one error, two errors, or a new character?"),
    ("eudc-8140", "0x8140-0xA0FE", "User-defined area 1 of code page 950 (mapped to the Private Use "
     "Area), where HKSCS, Big5-2003 and other extensions put their characters."),
    ("symbols", "0xA140-0xA3BF", "Symbols, punctuation, Greek, bopomofo: the home of the classic "
     "mapping disputes (0xA145, 0xA14E, 0xA1C3, 0xA1C5, 0xA2CC, 0xA2CE)."),
    ("a3c0", "0xA3C0-0xA3FE", "Reserved in Big5; code page 950 put the Euro sign at 0xA3E1."),
    ("hanzi1", "0xA440-0xC67E", "The 5,401 frequently used hanzi."),
    ("c6a1", "0xC6A1-0xC8FE", "ETEN's kana, Cyrillic and other symbols; user-defined area 2 in "
     "code page 950; HKSCS characters."),
    ("hanzi2", "0xC940-0xF9D5", "The 7,652 less frequently used hanzi (two of them duplicates)."),
    ("f9d6", "0xF9D6-0xF9FE", "ETEN's extension: seven hanzi and box-drawing characters."),
    ("eudc-fa40", "0xFA40-0xFEFE", "User-defined area 3 of code page 950; HKSCS characters."),
    ("ascii-first", "Pairs starting with an ASCII byte", "Two-byte cases whose first byte is ASCII."),
]
REGION_IDS = [r[0] for r in DECODE_REGIONS]
CODE_REGIONS = ["eudc-8140", "symbols", "a3c0", "hanzi1", "c6a1", "hanzi2", "f9d6", "eudc-fa40"]


def is_trail(t: int) -> bool:
    return 0x40 <= t <= 0x7E or 0xA1 <= t <= 0xFE


def region(arg: str) -> str:
    """The region of a decode case (hex bytes)."""
    b = bytes.fromhex(arg)
    if len(b) == 1:
        x = b[0]
        if x < 0x80:
            return "ascii"
        if x in (0x80, 0xFF):
            return "byte-80-ff"
        return "lone-lead"
    lead, trail = b
    if lead < 0x80:
        return "ascii-first"
    if lead in (0x80, 0xFF):
        return "byte-80-ff"
    if trail < 0x80 and not is_trail(trail):
        return "ascii-after-lead"
    if not is_trail(trail):
        return "bad-trail"
    code = lead << 8 | trail
    if lead <= 0xA0:
        return "eudc-8140"
    if code <= 0xA3BF:
        return "symbols"
    if code <= 0xA3FE:
        return "a3c0"
    if code <= 0xC67E:
        return "hanzi1"
    if code <= 0xC8FE:
        return "c6a1"
    if code <= 0xF9D5:
        return "hanzi2"
    if code <= 0xF9FE:
        return "f9d6"
    return "eudc-fa40"


# ---------------------------------------------------------------------------------------------


@dataclass
class Model:
    base: Path = store.DATA
    impls: list[Impl] = field(default_factory=list)
    manifest: dict = field(default_factory=dict)
    dec: dict[str, dict[str, str]] = field(default_factory=dict)
    enc: dict[str, dict[str, str]] = field(default_factory=dict)
    dargs: list[str] = field(default_factory=list)
    eargs: list[str] = field(default_factory=list)

    @classmethod
    def load(cls, base: Path = store.DATA, only: list[str] | None = None) -> "Model":
        m = cls(base=base)
        m.manifest = store.read_manifest(base)
        m.dargs = store.case_args("d", base)
        m.eargs = store.case_args("e", base)
        for impl in IMPLS:
            if impl.id not in m.manifest["impls"] or (only and impl.id not in only):
                continue
            m.impls.append(impl)
            if "d" in impl.ops:
                raw = store.read_results(impl.id, "d", base, m.dargs)
                cache: dict[str, str] = {}
                m.dec[impl.id] = {a: cache.setdefault(r, norm_decode(r)) for a, r in raw.items()}
            if "e" in impl.ops:
                m.enc[impl.id] = store.read_results(impl.id, "e", base, m.eargs)
        return m

    @property
    def ids(self) -> list[str]:
        return [i.id for i in self.impls]

    def impl(self, impl_id: str) -> Impl:
        return next(i for i in self.impls if i.id == impl_id)

    def runs(self, op: str | None = None) -> list[str]:
        return [i.id for i in self.impls if i.kind == "run" and (op is None or op in i.ops)]

    def decoders(self) -> list[str]:
        return [i.id for i in self.impls if "d" in i.ops]

    def encoders(self) -> list[str]:
        return [i.id for i in self.impls if "e" in i.ops]

    @cached_property
    def lead_bytes(self) -> dict[str, set[int]]:
        """Bytes 0x80-0xFF that an implementation does not decode on their own."""
        out = {}
        for i, d in self.dec.items():
            # A byte outside a partial table's scope counts as a lead byte.
            out[i] = {x for x in range(0x80, 0x100) if f"{x:02X}" not in d or not is_clean(d[f"{x:02X}"])}
        return out

    @cached_property
    def chars(self) -> dict[str, dict[str, str]]:
        """Each decoder's character map: every non-ASCII single byte or two-byte sequence that it
        decodes, without error, as one character (byte sequence -> normalised code points)."""
        out: dict[str, dict[str, str]] = {}
        for i, d in self.dec.items():
            leads = self.lead_bytes[i]
            cm: dict[str, str] = {}
            for x in range(0x80, 0x100):
                a = f"{x:02X}"
                if a in d and x not in leads:
                    cm[a] = d[a]
            for lead in sorted(leads):
                for t in range(0x100):
                    a = f"{lead:02X}{t:02X}"
                    r = d.get(a)
                    if r is not None and is_clean(r):
                        cm[a] = r
            out[i] = cm
        return out

    def scope(self, impl_id: str) -> set[str] | None:
        """Decode cases a partial table covers (None: all)."""
        if impl_id == "ref.hkscs-2016":
            return set(self.dec[impl_id])
        return None
