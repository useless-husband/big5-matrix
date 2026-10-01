"""Committed results: one gzip'd text file per implementation and operation, plus a manifest.

data/decode/<impl>.txt.gz   one decode result per line, in case order
data/encode/<impl>.txt.gz   one encode result per line, in case order
data/encode-extra.txt       encode cases beyond the BMP and plane 2 (part of the case list)
data/manifest.json          versions, case-list digests, a SHA-256 of every result file's content

The case order is fixed (see cases.py), so the input is not repeated on every line; the first
line of each file names the case list it belongs to and reading checks it. A table that covers
only part of the code space writes ``*`` for cases outside its scope.
``python3 -m big5matrix dump <impl> <decode|encode>`` prints a file with its inputs.

Files are written deterministically (gzip with mtime 0 and no file name), and the manifest
hashes the uncompressed content, so a different zlib cannot cause spurious drift.
"""

from __future__ import annotations

import gzip
import hashlib
import io
import json
from functools import lru_cache
from pathlib import Path

from . import cases, protocol
from .registry import ROOT

DATA = ROOT / "data"
OPS = {"d": "decode", "e": "encode"}
OUT_OF_SCOPE = "*"


class StaleData(Exception):
    """A result file belongs to a different case list than the current one."""


@lru_cache(maxsize=None)
def _decode_args() -> tuple[str, ...]:
    return tuple(protocol.bytes_arg(b) for b in cases.decode_cases())


def case_args(op: str, base: Path = DATA) -> list[str]:
    if op == "d":
        return list(_decode_args())
    extra = cases.read_extra(base / "encode-extra.txt")
    return [protocol.cps_arg(s) for s in cases.encode_cases(extra)]


def header(op: str, args: list[str]) -> str:
    return f"#big5-matrix v1 op={OPS[op]} cases={len(args)} cases_sha256={cases.case_digest(args)}\n"


def result_path(impl_id: str, op: str, base: Path = DATA) -> Path:
    return base / OPS[op] / f"{impl_id}.txt.gz"


def serialise(op: str, results: dict[str, str], args: list[str]) -> bytes:
    body = "".join(f"{results.get(a, OUT_OF_SCOPE)}\n" for a in args)
    return (header(op, args) + body).encode("ascii")


def content_digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def write_results(impl_id: str, op: str, results: dict[str, str], args: list[str],
                  base: Path = DATA) -> str:
    raw = serialise(op, results, args)
    path = result_path(impl_id, op, base)
    path.parent.mkdir(parents=True, exist_ok=True)
    buf = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=buf, mtime=0, compresslevel=9) as gz:
        gz.write(raw)
    path.write_bytes(buf.getvalue())
    return content_digest(raw)


def read_raw(impl_id: str, op: str, base: Path = DATA) -> bytes:
    return gzip.decompress(result_path(impl_id, op, base).read_bytes())


def read_results(impl_id: str, op: str, base: Path = DATA, args: list[str] | None = None) -> dict[str, str]:
    """Results keyed by input; cases outside a table's scope are absent."""
    args = args if args is not None else case_args(op, base)
    text = read_raw(impl_id, op, base).decode("ascii")
    first, _, body = text.partition("\n")
    if first + "\n" != header(op, args):
        raise StaleData(f"{result_path(impl_id, op, base)} was written for another case list "
                        f"({first!r}); re-run `python3 -m big5matrix run {impl_id}`")
    lines = body.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    if len(lines) != len(args):
        raise StaleData(f"{result_path(impl_id, op, base)}: {len(lines)} results for {len(args)} cases")
    return {a: r for a, r in zip(args, lines) if r != OUT_OF_SCOPE}


def has_results(impl_id: str, op: str, base: Path = DATA) -> bool:
    return result_path(impl_id, op, base).exists()


def read_manifest(base: Path = DATA) -> dict:
    p = base / "manifest.json"
    if not p.exists():
        return {"cases": {}, "impls": {}}
    return json.loads(p.read_text())


def write_manifest(manifest: dict, base: Path = DATA) -> None:
    base.mkdir(parents=True, exist_ok=True)
    manifest["impls"] = dict(sorted(manifest["impls"].items()))
    (base / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
