"""Named numbers and Markdown tables derived from the analysis.

report/summary.json holds both. Documents refer to them with markers that
`python3 -m big5matrix report` refreshes in place:

    <!--n:decode.cases-->65,792<!--/n-->
    <!--t:error-handling-->
    | ... generated table ... |
    <!--/t-->

so every number in the README and the report names the value it came from.
"""

from __future__ import annotations

from collections import Counter, defaultdict

from .analyze import BY_NAME_BIG5, BY_NAME_CP950, ONEWAY_KINDS, TABLE_REFS
from .model import CODE_REGIONS, DECODE_REGIONS, region

REF_SHORT = {
    "ref.whatwg": "WHATWG",
    "ref.unicode-big5": "BIG5.TXT",
    "ref.ms-cp950": "CP950.TXT",
    "ref.ms-bestfit950": "bestfit950",
    "ref.hkscs-2016": "HKSCS-2016",
}
REGION_SHORT = {
    "eudc-8140": "8140–A0FE",
    "symbols": "A140–A3BF",
    "a3c0": "A3C0–A3FE",
    "hanzi1": "A440–C67E",
    "c6a1": "C6A1–C8FE",
    "hanzi2": "C940–F9D5",
    "f9d6": "F9D6–F9FE",
    "eudc-fa40": "FA40–FEFE",
    "ascii-first": "two ASCII bytes",
    "bad-trail": "lead + 80–A0 (IBM's extra trail bytes)",
    "ascii-after-lead": "lead + ASCII",
}
FAMILY_NAMES = {
    # anchor member -> name; a family is named after the first anchor it contains
    "ref.whatwg": "WHATWG Big5 (HKSCS characters at their Unicode code points)",
    "ref.ms-bestfit950": "Windows code page 950 (user-defined areas mapped to the Private Use Area)",
    "ref.ms-cp950": "Plain Big5: Unicode BIG5.TXT and Microsoft CP950.TXT, no user-defined areas",
    "icu.ibm-950": "IBM-950",
    "java.x-ms950-hkscs": "Microsoft's Big5-HKSCS (MS950_HKSCS)",
    "java.x-ms950-hkscs-xp": "Code page 951: Microsoft's HKSCS-2001 table as on Windows XP",
}


def fmt(n) -> str:
    return f"{n:,}" if isinstance(n, int) else str(n)


def table(header: list[str], rows: list[list], align: str | None = None) -> str:
    align = align or "l" * len(header)
    sep = ["---:" if a == "r" else "---" for a in align]
    out = ["| " + " | ".join(header) + " |", "| " + " | ".join(sep) + " |"]
    for r in rows:
        out.append("| " + " | ".join(fmt(c) if isinstance(c, int) else str(c) for c in r) + " |")
    return "\n".join(out)


def cp(h: str) -> str:
    return {"!": "error", "-": "nothing"}.get(h, "U+" + h)


def family_of(A: dict) -> dict[str, int]:
    out = {}
    for n, fam in enumerate(A["families"], 1):
        for i in fam:
            out[i] = n
    return out


def family_name(fam: list[str]) -> str:
    for anchor, name in FAMILY_NAMES.items():
        if anchor in fam:
            return name
    return "(single implementation)" if len(fam) == 1 else "(unnamed)"


def region_verdict(row: dict, chars_total: int) -> str:
    """Describe an implementation's character map in one region relative to the tables."""
    e = row
    if e["chars"] == 0:
        return "—"
    exact = [REF_SHORT[r] for r in TABLE_REFS if e.get(r) == 0]
    if exact:
        return "= " + ", ".join(exact)
    if e["pua"] == e["chars"]:
        return "PUA"
    best = min((r for r in TABLE_REFS if r in e), key=lambda r: e[r])
    note = f"≈ {REF_SHORT[best]} ({e[best]})"
    if e["pua"]:
        note += f", {e['pua']} PUA"
    return note


def build(A: dict) -> dict:
    impls = A["impls"]
    runs = [i for i, v in impls.items() if v["kind"] == "run"]
    refs = [i for i, v in impls.items() if v["kind"] == "table"]
    fam = family_of(A)
    N: dict[str, object] = {}
    T: dict[str, str] = {}

    N["impls.runs"] = len(runs)
    N["impls.tables"] = len(refs)
    N["impls.runtimes"] = len({impls[i]["runtime"] for i in runs})
    N["impls.decoders"] = sum(1 for i in runs if "d" in impls[i]["ops"])
    N["impls.encoders"] = sum(1 for i in runs if "e" in impls[i]["ops"])
    N["decode.cases"] = A["cases"]["decode"]["count"]
    N["encode.cases"] = A["cases"]["encode"]["count"]
    N["collected.platform"] = A["collected"].get("platform", "")
    N["collected.date"] = A["collected"].get("date", "")
    N["families.count"] = len(A["families"])
    N["families.multi"] = sum(1 for f in A["families"] if len(f) > 1)

    # --- implementations ------------------------------------------------------------------
    rows = []
    for i, v in impls.items():
        ops = {"de": "both", "d": "decode", "e": "encode"}[v["ops"]]
        rows.append([f"`{i}`", v["label"], v["version"] if v["kind"] == "run" else "table", ops])
    T["implementations"] = table(["Column", "What", "Version tested", "Ops"], rows)

    # --- families ---------------------------------------------------------------------------
    D = A["distance"]
    rows = []
    for n, f in enumerate(A["families"], 1):
        inner = max((D[a][b] for a in f for b in f), default=0)
        rows.append([n, family_name(f), ", ".join(f"`{x}`" for x in f), inner])
    T["families"] = table(["#", "Family", "Members", "Max. distance inside"], rows, "rllr")
    links = sorted(D[a][b] for f in A["families"] for a in f for b in f if a < b)
    N["families.max_inside"] = max(links) if links else 0
    between = [D[a][b] for a in D for b in D if a < b and fam.get(a) and fam.get(b) and fam[a] != fam[b]]
    N["families.min_between"] = min(between)

    # --- what each implementation implements -------------------------------------------------------
    F = A["fingerprint"]
    rows = []
    for i in F:
        if impls[i]["kind"] == "table" and i == "ref.hkscs-2016":
            continue
        nearest = min((r for r in TABLE_REFS if r != i and r != "ref.hkscs-2016"), key=lambda r: D[i][r])
        rows.append([f"`{i}`", fam.get(i, "–"), f"{REF_SHORT[nearest]} ({D[i][nearest]})"]
                    + [region_verdict(F[i][r], 0) for r in CODE_REGIONS])
    T["variants"] = table(["Column", "Family", "Nearest table (differences)"] + [REGION_SHORT[r] for r in CODE_REGIONS],
                          rows)

    # --- error handling ---------------------------------------------------------------------
    E = A["error_handling"]
    rows = []

    def share(d: dict, key: str) -> str:
        tot = sum(d.values())
        if not tot:
            return "none (all are characters)"
        parts = []
        for k in ("kept", "swallowed", "two errors", "stops", "dropped", "error", "character", "other"):
            if d.get(k):
                parts.append(f"{k} {d[k]:,}" if d[k] != tot else k)
        return ", ".join(parts)

    for i, e in E.items():
        rows.append([f"`{i}`", e["substitute"], share(e["ascii_nontrail"], ""), share(e["ascii_unmapped"], ""),
                     share(e["bad_trail"], ""), share(e["lone_lead"], ""),
                     f"{cp(e['byte_80'])} / {cp(e['byte_ff'])}"])
    T["error-handling"] = table(
        ["Decoder", "Error marker", "Lead + ASCII 00–3F/7F", "Lead + unmapped ASCII 40–7E",
         "Lead + 80–A0/FF", "Lead at end", "Bytes 80 / FF"], rows)
    nontrail_total = 126 * 65
    N["error.nontrail_cases"] = nontrail_total
    keep = [i for i, e in E.items() if e["ascii_nontrail"].get("kept") == nontrail_total and impls[i]["kind"] == "run"]
    swallow = [i for i, e in E.items() if e["ascii_nontrail"].get("swallowed") == nontrail_total and impls[i]["kind"] == "run"]
    N["error.keep_all"] = len(keep)
    N["error.swallow_all"] = len(swallow)
    N["error.swallow_list"] = ", ".join(f"`{x}`" for x in swallow)
    N["error.stops"] = sum(1 for e in E.values() if e["ascii_nontrail"].get("stops"))
    drop = {i: e["lone_lead"].get("dropped", 0) for i, e in E.items() if e["lone_lead"].get("dropped")}
    N["error.lone_dropped_impls"] = ", ".join(f"`{i}` ({n})" for i, n in drop.items())
    N["error.go_swallowed"] = E["go.big5"]["ascii_unmapped"].get("swallowed", 0) + E["go.big5"]["ascii_nontrail"].get("swallowed", 0)
    N["error.whatwg_kept_unmapped"] = E["ref.whatwg"]["ascii_unmapped"].get("kept", 0)
    N["error.php_big5_swallowed"] = E["php.big-5"]["ascii_unmapped"].get("swallowed", 0)

    # --- divergence classes -------------------------------------------------------------------
    C = A["decode_classes"]
    X = A["ascii_first_exceptions"]
    N["decode.ascii_first_exceptions"] = sum(X.values())
    N["decode.ascii_first_decoders"] = len(X)
    rows = []
    for rid, title, _ in DECODE_REGIONS:
        if rid == "ascii-first":
            continue  # derived from the single-byte cases (see decode.ascii_first_exceptions)
        c = C[rid]
        rows.append([f"[{title}](https://useless-husband.github.io/big5-matrix/class.html?id={rid})",
                     c["cases"], c["divergent"], len(c["patterns"])])
        N[f"class.{rid}.cases"] = c["cases"]
        N[f"class.{rid}.divergent"] = c["divergent"]
    T["classes"] = table(["Class", "Cases", "Cases with disagreement", "Distinct ways to disagree"], rows, "lrrr")
    N["decode.divergent_total"] = len({r["case"] for k, c in C.items() if k != "ascii-first" for r in c["rows"]})
    N["decode.nontrivial_cases"] = N["decode.cases"] - C["ascii-first"]["cases"]
    N["decode.hanzi_cases"] = C["hanzi1"]["cases"] + C["hanzi2"]["cases"]
    N["decode.hanzi_divergent"] = C["hanzi1"]["divergent"] + C["hanzi2"]["divergent"]

    # symbol disputes
    rows = []
    for r in C["symbols"]["rows"] + C["hanzi1"]["rows"]:
        groups = "; ".join(f"{cp(v) if v != '!' else 'error'} ({len(ids)})" for v, ids in r["groups"])
        rows.append([f"`{r['case']}`", groups])
    T["symbol-disputes"] = table(["Bytes", "Decoded as (number of columns)"], rows)
    N["symbols.disputed"] = C["symbols"]["divergent"]

    # --- encoding -------------------------------------------------------------------------
    R = A["repertoire"]
    rows = []
    for i, e in R.items():
        if "encode_nonascii" not in e:
            continue
        rows.append([f"`{i}`", e["encode_nonascii"], e["encode_pua"], e["encode_supplementary"],
                     e["encode_dropped"], e["encode_substituted"]])
    T["encode-repertoire"] = table(["Encoder", "Non-ASCII code points encoded", "of which PUA", "of which plane 2",
                                    "Dropped silently", "Written as '?'"], rows, "lrrrrr")
    O = A["oneway"]
    rows = []
    for e, lst in O.items():
        c = Counter(r[3] for r in lst)
        if not lst:
            continue
        asc = sorted({chr(int(r[1], 16)) for r in lst if r[3] == "to-ascii"})
        rows.append([f"`{e}`"] + [c.get(k, 0) for k in ONEWAY_KINDS] + [
            "`" + "".join(asc).replace("`", "ˋ").replace("|", "\\|") + "`" if asc else ""])
        N[f"oneway.{e}.to-ascii"] = c.get("to-ascii", 0)
    T["oneway"] = table(["Encoder", "To ASCII", "From PUA", "Undecodable", "Other", "As '?'",
                         "ASCII characters produced"], rows, "lrrrrrl")
    N["encode.choice"] = len(A["encode_choice"])

    # --- round trips ------------------------------------------------------------------------------
    W = A["roundtrips"]["within"]
    rows = []
    for e, v in W.items():
        b, t = v["bytes_text_bytes"], v["text_bytes_text"]
        rows.append([f"`{e}`", b["same"], b["changed"], b["lost"], t["same"], t["changed"] - t["changed_pua"],
                     t["changed_pua"], t["error"]])
    T["within"] = table(["Implementation", "bytes→text→bytes: same", "changed", "lost",
                         "text→bytes→text: same", "changed", "changed (PUA input)", "error"], rows, "lrrrrrrr")

    for key, names, label in (("big5", BY_NAME_BIG5, "by_name_big5"), ("cp950", BY_NAME_CP950, "by_name_cp950")):
        B = A[label]
        cell = {(p["writer"], p["reader"]): p for p in B["pairs"]}
        cols = [n[0] for n in B["names"]]
        rows = []
        for w in cols:
            row = [f"**{w}**"]
            for r in cols:
                p = cell.get((w, r))
                if p is None:
                    row.append("")
                    continue
                bad = p["changed"] + p["error"]
                row.append("0" if bad == 0 else f"{p['changed']:,} / {p['error']:,}")
                N[f"pair.{key}.{w}.{r}.changed"] = p["changed"]
                N[f"pair.{key}.{w}.{r}.error"] = p["error"]
                N[f"pair.{key}.{w}.{r}.same"] = p["same"]
            rows.append(row)
        T[f"by-name-{key}"] = table(["writer ↓ / reader →"] + cols, rows, "l" + "r" * len(cols))
        T[f"by-name-{key}-legend"] = table(["Runtime", "Name used", "Writer column", "Reader column"],
                                            [[n, lab, f"`{w}`", f"`{r}`"] for n, lab, w, r in B["names"]])
        clean = sum(1 for p in B["pairs"] if p["writer"] != p["reader"] and p["changed"] + p["error"] == 0)
        N[f"pair.{key}.clean"] = clean
        N[f"pair.{key}.total"] = sum(1 for p in B["pairs"] if p["writer"] != p["reader"])

    # --- what changes between named pairs ---------------------------------------------------------
    rows = []
    for key, w, r in PAIRS_OF_INTEREST:
        B = A[f"by_name_{key}"]
        p = next(x for x in B["pairs"] if x["writer"] == w and x["reader"] == r)
        groups = defaultdict(list)
        for a, b, back in p.get("rows", []):
            kind = "error" if "!" in back.split(" ") else "changed"
            reg = region(b) if len(b) == 4 else ("ASCII byte" if int(b[:2], 16) < 0x80 else "single byte")
            groups[(REGION_SHORT.get(reg, reg), kind)].append((a, b, back))
        first = True
        for (reg, kind), lst in sorted(groups.items(), key=lambda kv: -len(kv[1])):
            ex = "; ".join(f"{show(a)} → `{b}` → {show_back(back)}" for a, b, back in lst[:3])
            label = f"{w} → {r} (`{key}`)" if first else ""
            rows.append([label, f"{reg}: {'reader reports an error' if kind == 'error' else 'silently different text'}",
                         len(lst), ex])
            first = False
    T["pair-examples"] = table(["Writer → reader", "Bytes / outcome", "Characters", "Examples"], rows, "llrl")

    for k, v in A.get("facts", {}).items():
        N[f"fact.{k}"] = v

    # headline numbers used in the README
    N["chromium.vs_whatwg"] = A["distance"]["browser.chromium"]["ref.whatwg"] if "browser.chromium" in A["distance"] else 0
    N["rust.vs_whatwg"] = A["distance"]["rust.big5"]["ref.whatwg"]
    return {"numbers": N, "tables": T}


PAIRS_OF_INTEREST = [
    ("big5", "Python", "Go"),
    ("big5", "Java", "Node.js"),
    ("big5", "PHP", ".NET"),
    ("big5", "Go", "Python"),
    ("big5", ".NET", "PHP"),
    ("cp950", "Java", ".NET"),
]


def show(h: str) -> str:
    """A code point sequence for a table cell: the characters when printable, and their numbers."""
    cps = [int(x, 16) for x in h.split(" ")]
    printable = all(0x20 < c < 0x7F or (c >= 0xA1 and not 0xD800 <= c <= 0xF8FF and c not in (0xAD,))
                    for c in cps)
    text = "".join(chr(c) for c in cps) if printable else ""
    text = text.replace("|", "\\|").replace("`", "ˋ")
    return (text + " " if text else "") + " ".join(f"U+{c:04X}" for c in cps)


def show_back(back: str) -> str:
    toks = back.split(" ")
    if "!" in toks:
        rest = [t for t in toks if t != "!"]
        return "error" + (" + " + show(" ".join(rest)) if rest else "")
    return show(back)


def detail_rows(A: dict) -> dict:
    """Per by-name pair, the code points that change or fail (for the site)."""
    out = defaultdict(dict)
    for label in ("by_name_big5", "by_name_cp950"):
        for p in A[label]["pairs"]:
            out[label][f"{p['writer']}|{p['reader']}"] = p.get("rows", [])
    return out
