"""Analysis of the committed data.

Everything here is a pure function of data/ (and the registry), and `python3 -m big5matrix
analyze` writes the results to report/summary.json, from which the report, the README result
blocks and the site are generated. Terms used throughout:

* character map of a decoder: the non-ASCII single bytes and two-byte sequences it decodes,
  without error, as one character (see Model.chars).
* participants: the implementations whose behaviour is compared for a case. Published tables
  say nothing about malformed input, so only the WHATWG column joins the real converters in
  the error-handling comparisons; all tables join the mapping comparisons, a partial table only
  for the cases it covers.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

from .model import CODE_REGIONS, DECODE_REGIONS, EMPTY, ERR, Model, is_clean, region
from .registry import ROOT

REPORT = ROOT / "report"
WHATWG = "ref.whatwg"
TABLE_REFS = ["ref.whatwg", "ref.unicode-big5", "ref.ms-cp950", "ref.ms-bestfit950", "ref.hkscs-2016"]

# The decoder that pairs with each encoder for round trips (same converter unless noted).
DECODER_FOR = {"dotnet.950-default": "dotnet.950"}

# What a developer gets by asking each runtime for "big5" (writer = encoder, reader = decoder).
BY_NAME_BIG5 = [
    ("Python", "codecs 'big5'", "python.big5", "python.big5"),
    ("Go", "x/text Big5", "go.big5", "go.big5"),
    ("Node.js", "iconv-lite 'big5' / TextDecoder('big5')", "node.iconv-lite-big5", "node.textdecoder"),
    ("Rust", "encoding_rs BIG5", "rust.big5", "rust.big5"),
    ("Java", "Charset 'Big5'", "java.big5", "java.big5"),
    (".NET", "GetEncoding('big5') = 950", "dotnet.950-default", "dotnet.950"),
    ("PHP", "mbstring 'BIG5'", "php.big-5", "php.big-5"),
    ("Ruby", "'Big5'", "ruby.big5", "ruby.big5"),
    ("Perl", "Encode 'big5' = big5-eten", "perl.big5-eten", "perl.big5-eten"),
    ("ICU", "ucnv 'Big5' = windows-950-2000", "icu.windows-950-2000", "icu.windows-950-2000"),
    ("macOS iconv", "'BIG5'", "iconv.big5", "iconv.big5"),
]

# ... and for "cp950" (Go, Rust and Node's TextDecoder have no such name).
BY_NAME_CP950 = [
    ("Python", "codecs 'cp950'", "python.cp950", "python.cp950"),
    ("Node.js", "iconv-lite 'cp950'", "node.iconv-lite-cp950", "node.iconv-lite-cp950"),
    ("Java", "Charset 'cp950' = x-IBM950", "java.x-ibm950", "java.x-ibm950"),
    (".NET", "GetEncoding(950)", "dotnet.950-default", "dotnet.950"),
    ("PHP", "mbstring 'CP950'", "php.cp950", "php.cp950"),
    ("Ruby", "'CP950'", "ruby.cp950", "ruby.cp950"),
    ("Perl", "Encode 'cp950'", "perl.cp950", "perl.cp950"),
    ("ICU", "ucnv 'cp950' = ibm-950_P110-1999", "icu.ibm-950", "icu.ibm-950"),
    ("macOS iconv", "'CP950'", "iconv.cp950", "iconv.cp950"),
]


def is_pua(cp: int) -> bool:
    return 0xE000 <= cp <= 0xF8FF or 0xF0000 <= cp <= 0x10FFFD


def cps_of(nres: str) -> list[int]:
    return [int(t, 16) for t in nres.split(" ") if t not in (ERR, EMPTY)]


# ---------------------------------------------------------------------------------------------
# Error handling


def error_participants(m: Model) -> list[str]:
    return [i for i in m.decoders() if m.impl(i).kind == "run" or i == WHATWG]


def recovery_outcome(m: Model, impl_id: str, arg: str) -> str:
    """How a decoder handles a two-byte case that it does not decode as one character."""
    if arg in m.chars[impl_id]:
        return "character"
    r = m.dec[impl_id][arg]
    toks = r.split(" ") if r != EMPTY else []
    if m.impl(impl_id).error_model == "strict":
        return "stops" if toks and toks[-1] == ERR else "other"
    second = m.dec[impl_id].get(arg[2:], "")
    second_toks = second.split(" ") if second != EMPTY else []
    if toks == [ERR] + second_toks and second_toks and ERR not in second_toks:
        return "kept"  # one error for the lead byte, the second byte decoded on its own
    if toks == [ERR]:
        return "swallowed"
    if toks == [ERR, ERR]:
        return "two errors"
    if not toks:
        return "dropped"
    return "other"


def lone_lead_outcome(m: Model, impl_id: str, arg: str) -> str:
    r = m.dec[impl_id][arg]
    if r == EMPTY:
        return "dropped"
    if r == ERR:
        return "stops" if m.impl(impl_id).error_model == "strict" else "error"
    if is_clean(r):
        return "character"
    return "other"


def substitute_of(m: Model, impl_id: str) -> str:
    impl = m.impl(impl_id)
    if impl.error_model == "strict":
        return "none (stops)"
    from . import store

    raw = store.read_raw(impl_id, "d", m.base).decode("ascii")
    if "!001A" in raw:
        return "U+001A (marked), U+FFFD for some errors" if "FFFD" in raw else "U+001A"
    return "U+FFFD"


def error_handling(m: Model) -> dict:
    out = {}
    for i in error_participants(m):
        ascii_nontrail = Counter()  # lead + 0x00-0x3F or 0x7F: never a character
        ascii_unmapped = Counter()  # lead + 0x40-0x7E where this decoder has no character
        bad_trail = Counter()
        lone = Counter()
        leads = [x for x in range(0x81, 0xFF)]
        for lead in leads:
            lone[lone_lead_outcome(m, i, f"{lead:02X}")] += 1
            for t in range(0x100):
                a = f"{lead:02X}{t:02X}"
                if t < 0x80:
                    o = recovery_outcome(m, i, a)
                    if o == "character":
                        continue
                    (ascii_unmapped if 0x40 <= t <= 0x7E else ascii_nontrail)[o] += 1
                elif t <= 0xA0 or t == 0xFF:
                    bad_trail[recovery_outcome(m, i, a)] += 1
        out[i] = {
            "substitute": substitute_of(m, i),
            "ascii_nontrail": dict(ascii_nontrail),
            "ascii_unmapped": dict(ascii_unmapped),
            "bad_trail": dict(bad_trail),
            "lone_lead": dict(lone),
            "byte_80": m.dec[i]["80"],
            "byte_ff": m.dec[i]["FF"],
            "ascii_changed": [f"{b:02X}" for b in range(0x80) if m.dec[i][f"{b:02X}"] != f"{b:04X}"],
        }
    return out


# ---------------------------------------------------------------------------------------------
# Repertoires, identical groups, distances, families


def repertoire(m: Model) -> dict:
    out = {}
    for i in m.ids:
        e = {}
        if i in m.chars:
            cm = m.chars[i]
            vals = [cps_of(v) for v in cm.values()]
            e["decode_chars"] = len(cm)
            e["decode_pua"] = sum(1 for v in vals if any(is_pua(c) for c in v))
            e["decode_supplementary"] = sum(1 for v in vals if any(c > 0xFFFF for c in v))
            e["decode_multi"] = sum(1 for v in vals if len(v) > 1)
        if i in m.enc:
            enc = m.enc[i]
            singles = [a for a in m.eargs if " " not in a]
            ok = [a for a in singles if enc[a] not in (ERR, EMPTY) and not is_substitution(a, enc[a])
                  and int(a, 16) >= 0x80]
            e["encode_nonascii"] = len(ok)
            e["encode_dropped"] = sum(1 for a in singles if enc[a] == EMPTY)
            e["encode_substituted"] = sum(1 for a in singles if is_substitution(a, enc[a]))
            e["encode_pua"] = sum(1 for a in ok if is_pua(int(a, 16)))
            e["encode_supplementary"] = sum(1 for a in ok if int(a, 16) > 0xFFFF)
        out[i] = e
    return out


def identical_groups(m: Model) -> dict:
    def groups(items):
        by = defaultdict(list)
        for k, v in items:
            by[v].append(k)
        return [g for g in by.values() if len(g) > 1]

    dec_full = groups((i, hash(tuple(m.dec[i].get(a) for a in m.dargs))) for i in m.decoders()
                      if m.scope(i) is None)
    dec_chars = groups((i, hash(tuple(sorted(m.chars[i].items())))) for i in m.decoders()
                       if m.scope(i) is None)
    enc_full = groups((i, hash(tuple(m.enc[i][a] for a in m.eargs))) for i in m.encoders())
    return {"decode": dec_full, "decode_characters": dec_chars, "encode": enc_full}


def char_distance(m: Model, a: str, b: str) -> int:
    """Number of byte sequences that are a character for at least one of the two decoders and
    are not the same character for both (restricted to a partial table's scope)."""
    ca, cb = m.chars[a], m.chars[b]
    keys = set(ca) | set(cb)
    for s in (m.scope(a), m.scope(b)):
        if s is not None:
            keys &= s
    return sum(1 for k in keys if ca.get(k) != cb.get(k))


def distance_matrix(m: Model) -> dict[str, dict[str, int]]:
    ids = [i for i in m.decoders()]
    d: dict[str, dict[str, int]] = {i: {} for i in ids}
    for x in range(len(ids)):
        d[ids[x]][ids[x]] = 0
        for y in range(x + 1, len(ids)):
            v = char_distance(m, ids[x], ids[y])
            d[ids[x]][ids[y]] = d[ids[y]][ids[x]] = v
    return d


def families(m: Model, dist: dict[str, dict[str, int]], threshold: int = 400) -> list[list[str]]:
    """Single-linkage clusters of whole-space decoders whose character maps differ in at most
    `threshold` byte sequences, largest first (a partial table is left out)."""
    ids = [i for i in dist if m.scope(i) is None]
    parent = {i: i for i in ids}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a in ids:
        for b in ids:
            if a < b and dist[a][b] <= threshold:
                parent[find(a)] = find(b)
    groups = defaultdict(list)
    for i in ids:
        groups[find(i)].append(i)
    return sorted((sorted(g, key=ids.index) for g in groups.values()), key=lambda g: (-len(g), ids.index(g[0])))


def fingerprint(m: Model) -> dict:
    """Per decoder and code region: the region's size in the character map and the number of
    differences from each reference table."""
    by_region: dict[str, list[str]] = defaultdict(list)
    for a in m.dargs:
        if len(a) == 4:
            r = region(a)
            if r in CODE_REGIONS:
                by_region[r].append(a)
    out = {}
    for i in m.decoders():
        ci = m.chars[i]
        row = {}
        for r in CODE_REGIONS:
            codes = by_region[r]
            e = {"chars": sum(1 for a in codes if a in ci),
                 "pua": sum(1 for a in codes if a in ci and any(is_pua(c) for c in cps_of(ci[a])))}
            for ref in TABLE_REFS:
                cr = m.chars[ref]
                scope = m.scope(ref)
                keys = [a for a in codes if scope is None or a in scope]
                if not keys:
                    continue
                e[ref] = sum(1 for a in keys if ci.get(a) != cr.get(a))
            row[r] = e
        out[i] = row
    return out


def ascii_first_exceptions(m: Model) -> dict[str, int]:
    """For every whole-space decoder, the number of pairs whose first byte is ASCII that do not
    decode as the first byte followed by the second byte on its own (strict decoders: as the
    first byte, then the second byte's result). 0 means an ASCII byte never changes how the next
    byte is read, so those 32,768 cases add nothing beyond the single-byte cases."""
    out = {}
    for i in m.decoders():
        if m.scope(i) is not None:
            continue
        d = m.dec[i]
        bad = 0
        for x in range(0x80):
            first = d[f"{x:02X}"]
            for y in range(0x100):
                second = d[f"{y:02X}"]
                exp = " ".join(t for t in (first, second) if t != EMPTY) or EMPTY
                if d[f"{x:02X}{y:02X}"] != exp:
                    bad += 1
        out[i] = bad
    return out


# ---------------------------------------------------------------------------------------------
# Divergence classes


def _single_bytes_view(m: Model, i: str, a: str) -> str:
    return m.dec[i].get(a, "*")


def decode_classes(m: Model) -> dict:
    """For every decode region: the cases where the participants disagree, each with the
    implementations grouped by what they do."""
    err_parts = error_participants(m)
    all_parts = m.decoders()
    classes = {}
    by_region: dict[str, list[str]] = defaultdict(list)
    for a in m.dargs:
        by_region[region(a)].append(a)
    # A lead byte followed by an ASCII byte in the valid trail range (0x40-0x7E) belongs to a
    # code region for mapping purposes, and to "ascii-after-lead" for error recovery.
    recovery_cases = [a for a in m.dargs if len(a) == 4 and 0x81 <= int(a[:2], 16) <= 0xFE
                      and int(a[2:], 16) < 0x80]
    for rid, title, desc in DECODE_REGIONS:
        if rid == "ascii-after-lead":
            cases, kind = recovery_cases, "recovery"
        elif rid == "bad-trail":
            cases, kind = by_region[rid], "recovery"
        elif rid == "lone-lead":
            cases, kind = by_region[rid], "lone"
        elif rid in CODE_REGIONS:
            cases, kind = by_region[rid], "mapping"
        else:
            cases, kind = by_region[rid], "full"
        rows = []
        patterns: Counter = Counter()
        pattern_examples: dict = {}
        for a in cases:
            if kind == "mapping":
                parts = [i for i in all_parts if m.scope(i) is None or a in m.scope(i)]
                view = {i: m.chars[i].get(a, ERR) for i in parts}
            elif kind == "recovery":
                view = {i: recovery_outcome(m, i, a) for i in err_parts}
            elif kind == "lone":
                view = {i: lone_lead_outcome(m, i, a) for i in err_parts}
            else:
                parts = all_parts if (rid == "byte-80-ff" and len(a) == 2) else err_parts
                view = {i: m.dec[i].get(a, "*") for i in parts if m.scope(i) is None or a in m.scope(i)}
            groups = defaultdict(list)
            for i, v in view.items():
                groups[v].append(i)
            if len(groups) > 1:
                g = sorted(groups.items(), key=lambda kv: -len(kv[1]))
                rows.append({"case": a, "groups": [[v, ids] for v, ids in g]})
                sig = tuple(sorted(tuple(ids) for _, ids in g))
                patterns[sig] += 1
                pattern_examples.setdefault(sig, a)
        classes[rid] = {
            "title": title,
            "description": desc,
            "kind": kind,
            "cases": len(cases),
            "divergent": len(rows),
            "patterns": [{"count": n, "example": pattern_examples[sig], "groups": [list(x) for x in sig]}
                         for sig, n in patterns.most_common()],
            "rows": rows,
        }
    return classes


def is_substitution(a: str, b: str) -> bool:
    """An encoder wrote '?' bytes for a character it cannot encode (.NET's default fallback
    writes one '?' per UTF-16 code unit)."""
    return b != "" and set(b[i:i + 2] for i in range(0, len(b), 2)) == {"3F"} and "003F" not in a.split(" ")


ONEWAY_KINDS = ["to-ascii", "pua-input", "undecodable", "other", "substituted"]


def oneway_kind(a: str, b: str, back: str) -> str:
    """Why an encoder's output does not decode back to its input."""
    if is_substitution(a, b):
        return "substituted"
    if ERR in back.split(" ") or back == EMPTY:
        return "undecodable"
    first = int(a.split(" ")[0], 16)
    if is_pua(first):
        return "pua-input"
    if len(b) == 2 and int(b, 16) < 0x80 and first >= 0x80:
        return "to-ascii"
    return "other"


def oneway_encodings(m: Model) -> dict:
    """Code points an encoder maps to bytes that its own decoder turns into something else:
    best-fit mappings, legacy Private Use Area input, '?' substitution and plain errors."""
    out = {}
    for e in m.encoders():
        d = DECODER_FOR.get(e, e)
        if d not in m.dec:
            continue
        rows = []
        for a, b in m.enc[e].items():
            if b in (ERR, EMPTY) or len(b) > 4:
                continue
            back = m.dec[d].get(b)
            if back is not None and back != a:
                rows.append([a, b, back, oneway_kind(a, b, back)])
        out[e] = rows
    return out


def encode_choice(m: Model) -> list:
    """Code points that at least two encoders encode, to different bytes."""
    rows = []
    encs = m.encoders()
    for a in m.eargs:
        groups = defaultdict(list)
        for e in encs:
            b = m.enc[e][a]
            groups[b].append(e)
        ok = [b for b in groups if b not in (ERR, EMPTY) and not is_substitution(a, b)]
        if len(ok) > 1:
            rows.append({"case": a, "groups": [[b, ids] for b, ids in sorted(groups.items(), key=lambda kv: -len(kv[1]))]})
    return rows


# ---------------------------------------------------------------------------------------------
# Round trips


def _enc_ok(b: str | None) -> bool:
    return b is not None and b not in (ERR, EMPTY)


def interchange(m: Model, writer: str, reader: str, detail: bool = False) -> dict:
    """Text -> bytes with `writer` -> text with `reader`, over every encode case the writer
    encodes. 'same': the reader gives back the text; 'changed': other text, no error;
    'error': the reader reports an error."""
    enc, dec = m.enc[writer], m.dec[reader]
    scope = m.scope(reader)
    c = Counter()
    rows = []
    for a, b in enc.items():
        if not _enc_ok(b):
            continue
        if is_substitution(a, b):
            c["substituted"] += 1  # the writer already lost the character
            continue
        if len(b) > 4 or (scope is not None and b not in scope):
            c["untested"] += 1
            continue
        back = dec[b]
        if back == a:
            c["same"] += 1
            continue
        k = "changed" if is_clean(back) else "error"
        c[k] += 1
        if is_pua(int(a.split(" ")[0], 16)):
            c[k + "_pua"] += 1
        if detail:
            rows.append([a, b, back])
    res = {k: c[k] for k in ("same", "changed", "error", "changed_pua", "error_pua", "substituted", "untested")}
    if detail:
        res["rows"] = rows
    return res


def transcode(m: Model, reader: str, writer: str, detail: bool = False) -> dict:
    """Bytes -> text with `reader` -> bytes with `writer`, over every character in the reader's
    character map. 'same': the original bytes; 'changed': other bytes; 'lost': the writer
    cannot encode the text."""
    cm, enc = m.chars[reader], m.enc[writer]
    c = Counter()
    rows = []
    for code, text in cm.items():
        b = enc.get(text)
        if b is None:
            c["untested"] += 1
            continue
        if b == code:
            c["same"] += 1
            continue
        k = "changed" if _enc_ok(b) and not is_substitution(text, b) else "lost"
        c[k] += 1
        if is_pua(int(text.split(" ")[0], 16)):
            c[k + "_pua"] += 1
        if detail:
            rows.append([code, text, b])
    res = {k: c[k] for k in ("same", "changed", "lost", "changed_pua", "lost_pua", "untested")}
    if detail:
        res["rows"] = rows
    return res


def roundtrips(m: Model) -> dict:
    within = {}
    for e in m.encoders():
        d = DECODER_FOR.get(e, e)
        if d not in m.dec or m.scope(d) is not None:
            continue
        within[e] = {"bytes_text_bytes": transcode(m, d, e, detail=True),
                     "text_bytes_text": interchange(m, e, d, detail=True)}
    readers = [i for i in m.decoders() if m.scope(i) is None]
    writers = m.encoders()
    inter = {w: {r: interchange(m, w, r) for r in readers} for w in writers}
    trans = {r: {w: transcode(m, r, w) for w in writers} for r in readers}
    return {"within": within, "interchange": inter, "transcode": trans}


def by_name(m: Model, table) -> dict:
    """Interchange between what each runtime calls big5 (or cp950)."""
    rows = []
    for wn, wl, w, _ in table:
        if w not in m.enc:
            continue
        for rn, rl, _, r in table:
            if r not in m.dec:
                continue
            res = interchange(m, w, r, detail=True)
            rows.append({"writer": wn, "writer_impl": w, "reader": rn, "reader_impl": r, **res})
    return {"names": [[n, label, w, r] for n, label, w, r in table], "pairs": rows}


# ---------------------------------------------------------------------------------------------


def facts(m: Model) -> dict:
    """Specific numbers the report discusses, each computed from the data."""
    f: dict[str, int] = {}
    w_enc, g_enc = m.enc["ref.whatwg"], m.enc.get("go.big5", {})
    if g_enc:
        f["go.encodes_excluded"] = sum(1 for a in m.eargs if w_enc[a] == ERR and g_enc[a] not in (ERR, EMPTY))
        f["go.encode_other_choice"] = sum(1 for a in m.eargs if ERR not in (w_enc[a], g_enc[a]) and w_enc[a] != g_enc[a])
    if "iconv.big5-hkscs" in m.enc:
        e, d = m.enc["iconv.big5-hkscs"], m.dec["iconv.big5-hkscs"]
        hanzi = [a for a in m.chars["ref.ms-cp950"] if len(a) == 4 and region(a) in ("hanzi1", "hanzi2")]
        f["iconv.hkscs.hanzi_total"] = len(hanzi)
        f["iconv.hkscs.hanzi_unencodable"] = sum(1 for a in hanzi if e.get(m.chars["ref.ms-cp950"][a]) == ERR)
        n = 0
        for a, b in e.items():
            if " " in a or b in (ERR, EMPTY) or len(b) != 4:
                continue
            back = d.get(b, "")
            if is_clean(back) and " " not in back and int(back, 16) >= 0x20000 and int(back, 16) & 0xFFFF == int(a, 16):
                n += 1
        f["iconv.hkscs.plane_bits"] = n
        own = {v for v in m.chars["iconv.big5-hkscs"].values() if " " not in v and int(v, 16) >= 0x20000}
        f["iconv.hkscs.plane2_decoded"] = len(own)
        f["iconv.hkscs.plane2_unencodable"] = sum(1 for v in own if e.get(v) == ERR)
    if "dotnet.950" in m.chars:
        f["dotnet.rejects_cp950"] = sum(1 for a in m.chars["ref.ms-cp950"] if a not in m.chars["dotnet.950"])
    if "node.textdecoder" in m.chars:
        f["node.vs_whatwg"] = char_distance(m, "node.textdecoder", "ref.whatwg")
        f["node.vs_bestfit"] = char_distance(m, "node.textdecoder", "ref.ms-bestfit950")
    if "browser.chromium" in m.dec:
        f["chromium.differs"] = sum(1 for a in m.dargs if m.dec["browser.chromium"][a] != m.dec[WHATWG][a])
    f["rust.differs"] = sum(1 for a in m.dargs if m.dec["rust.big5"][a] != m.dec[WHATWG][a]) if "rust.big5" in m.dec else -1
    if "rust.big5" in m.enc:
        f["rust.encode_differs"] = sum(1 for a in m.eargs if m.enc["rust.big5"][a] != w_enc[a])
    return f


def analyze(m: Model) -> dict:
    dist = distance_matrix(m)
    return {
        "impls": {i.id: {"label": i.label, "kind": i.kind, "runtime": i.runtime, "codec": i.codec,
                         "ops": i.ops, "error_model": i.error_model,
                         "version": m.manifest["impls"][i.id]["version"],
                         "key": m.manifest["impls"][i.id]["key"]} for i in m.impls},
        "cases": m.manifest["cases"],
        "collected": m.manifest.get("collected", {}),
        "error_handling": error_handling(m),
        "repertoire": repertoire(m),
        "identical": identical_groups(m),
        "distance": dist,
        "families": families(m, dist),
        "fingerprint": fingerprint(m),
        "decode_classes": decode_classes(m),
        "ascii_first_exceptions": ascii_first_exceptions(m),
        "facts": facts(m),
        "oneway": oneway_encodings(m),
        "encode_choice": encode_choice(m),
        "roundtrips": roundtrips(m),
        "by_name_big5": by_name(m, BY_NAME_BIG5),
        "by_name_cp950": by_name(m, BY_NAME_CP950),
    }


def write(result: dict, path: Path | None = None) -> Path:
    path = path or REPORT / "analysis.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, separators=(",", ":"), sort_keys=True))
    return path


def main() -> dict:
    from . import summary

    m = Model.load()
    res = analyze(m)
    p = write(res, ROOT / "build" / "analysis.json")
    print(f"wrote {p.relative_to(ROOT)}")
    s = summary.build(res)
    REPORT.mkdir(exist_ok=True)
    (REPORT / "summary.json").write_text(json.dumps(s, indent=1, ensure_ascii=False, sort_keys=True) + "\n")
    print("wrote report/summary.json")
    return res
