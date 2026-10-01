"""Running adapters and reference columns over the test cases."""

from __future__ import annotations

import datetime
import hashlib
import platform
import subprocess
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable

from . import cases, protocol, reference, store
from .registry import BY_ID, IMPLS, Impl, Unavailable, prepare

Log = Callable[[str], None]


class AdapterError(RuntimeError):
    pass


def adapter_version(cmd: list[str], codec: str) -> dict[str, str]:
    r = subprocess.run(cmd + ["--version"], capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        raise Unavailable(f"--version failed: {r.stderr.strip()[-200:]}")
    info = protocol.parse_version(r.stdout)
    key = info.get(f"key.{codec}", info["key"])
    return {"version": info["version"], "key": key}


def run_adapter(cmd: list[str], codec: str, op: str, args: list[str]) -> dict[str, str]:
    """Send every request to one adapter process and check each response line."""
    with tempfile.TemporaryDirectory() as tmp:
        req = Path(tmp) / "requests"
        resp = Path(tmp) / "responses"
        req.write_text("".join(protocol.format_request(op, a) for a in args))
        with req.open("rb") as fin, resp.open("wb") as fout:
            r = subprocess.run(cmd + [codec], stdin=fin, stdout=fout, stderr=subprocess.PIPE,
                               timeout=3600)
        if r.returncode != 0:
            raise AdapterError(f"{codec}: adapter exited {r.returncode}: "
                               f"{r.stderr.decode(errors='replace').strip()[-500:]}")
        lines = resp.read_text(encoding="ascii").splitlines()
    if len(lines) != len(args):
        raise AdapterError(f"{codec}: {len(args)} requests but {len(lines)} responses")
    out: dict[str, str] = {}
    for a, line in zip(args, lines):
        rsp = protocol.parse_response(line)
        if rsp.op != op or rsp.arg != a:
            raise AdapterError(f"{codec}: response {line!r} does not answer request {a!r}")
        out[a] = rsp.result
    return out


def extras_from_decodes(results: list[dict[str, str]]) -> list[tuple[int, ...]]:
    """Code point sequences produced by some decoder that the base encode cases do not cover:
    the output of a two-byte character that decodes to several code points, and code points
    outside the base ranges. Output containing a lone surrogate (Chromium produces some) is
    not text and is left out. A two-byte case is a character for a decoder when that decoder
    does not decode its first byte on its own (the first byte is a lead byte)."""
    found: set[tuple[int, ...]] = set()
    for res in results:
        for arg, r in res.items():
            toks = protocol.decode_tokens(r)
            if protocol.ERROR in toks or not toks:
                continue
            cps = tuple(int(t, 16) for t in toks)
            if any(0xD800 <= c <= 0xDFFF for c in cps):
                continue  # a lone surrogate is not a Unicode scalar value; nothing can encode it
            if len(arg) == 4 and len(cps) > 1:
                first = protocol.decode_tokens(res.get(arg[:2], protocol.ERROR))
                if not first or protocol.ERROR in first:
                    found.add(cps)
            for c in cps:
                if not (c < 0x10000 or 0x20000 <= c < 0x30000):
                    found.add((c,))
    return sorted(found, key=lambda s: (len(s), s))


class Runner:
    def __init__(self, base: Path = store.DATA, log: Log = print, workers: int = 4):
        self.base = base
        self.log = log
        self.workers = workers
        self._cmds: dict[str, list[str] | Unavailable] = {}

    def command(self, runtime: str) -> list[str]:
        if runtime not in self._cmds:
            try:
                self._cmds[runtime] = prepare(runtime)
            except Unavailable as e:
                self._cmds[runtime] = e
        c = self._cmds[runtime]
        if isinstance(c, Unavailable):
            raise c
        return c

    def version(self, impl: Impl) -> dict[str, str]:
        if impl.kind == "table":
            src = store.DATA.parent / impl.note
            digest = hashlib.sha256(src.read_bytes()).hexdigest()
            return {"version": f"{impl.note} sha256:{digest[:16]}", "key": digest}
        return adapter_version(self.command(impl.runtime), impl.codec)

    def results(self, impl: Impl, op: str, args: list[str]) -> dict[str, str]:
        if impl.kind == "table":
            return reference.run_reference(impl.id, op, args)
        return run_adapter(self.command(impl.runtime), impl.codec, op, args)

    def available(self, impls: list[Impl]) -> tuple[list[Impl], dict[str, str]]:
        """Split impls into those that can run here and skip notices for the rest."""
        ok, skipped = [], {}
        for impl in impls:
            if impl.kind == "table":
                ok.append(impl)
                continue
            try:
                self.command(impl.runtime)
                ok.append(impl)
            except Unavailable as e:
                skipped[impl.id] = str(e)
        return ok, skipped

    def run_op(self, impls: list[Impl], op: str, args: list[str], tolerate: bool = False) -> dict[str, dict]:
        """Run op for every impl (a few at a time) and write the result files. With tolerate, an
        adapter that fails is recorded as {"error": message} instead of stopping everything."""
        entries: dict[str, dict] = {}

        def one(impl: Impl):
            try:
                return attempt(impl)
            except (AdapterError, protocol.ProtocolError, Unavailable, OSError, subprocess.SubprocessError) as e:
                if not tolerate:
                    raise
                return impl.id, None, {"error": str(e)[-300:]}

        def attempt(impl: Impl):
            t0 = time.monotonic()
            ver = self.version(impl)
            res = self.results(impl, op, args)
            digest = store.write_results(impl.id, op, res, args, self.base)
            self.log(f"  {impl.id:28s} {store.OPS[op]:6s} {len(res):6d} cases "
                     f"{time.monotonic() - t0:6.1f}s  {ver['version']}")
            return impl.id, ver, {"cases": len(res), "sha256": digest}

        todo = [i for i in impls if op in i.ops]
        with ThreadPoolExecutor(max_workers=self.workers) as pool:
            for impl_id, ver, entry in pool.map(one, todo):
                entries[impl_id] = {"ver": ver, store.OPS[op]: entry}
                if "error" in entry:
                    entries[impl_id]["error"] = entry["error"]
        return entries


def manifest_entry(impl: Impl) -> dict:
    return {
        "label": impl.label,
        "runtime": impl.runtime,
        "codec": impl.codec,
        "kind": impl.kind,
        "error_model": impl.error_model,
        "ops": impl.ops,
        **({"note": impl.note} if impl.note else {}),
    }


def collect(only: list[str] | None = None, base: Path = store.DATA, log: Log = print,
            workers: int = 4) -> dict[str, str]:
    """Run everything (or the implementations whose id or runtime is in `only`) and update the
    committed data. Returns the skip notices."""
    impls = [i for i in IMPLS if not only or i.id in only or i.runtime in only]
    runner = Runner(base, log, workers)
    ok, skipped = runner.available(impls)
    for impl_id, why in skipped.items():
        log(f"SKIP {impl_id}: {why}")

    manifest = store.read_manifest(base)
    dargs = store.case_args("d", base)
    log(f"decode: {len(dargs)} cases x {len(ok)} implementations")
    entries = runner.run_op(ok, "d", dargs)

    # The encode case list includes sequences that any decoder produced.
    extra_path = base / "encode-extra.txt"
    all_decodes = [store.read_results(i.id, "d", base) for i in IMPLS if store.has_results(i.id, "d", base)]
    cases.write_extra(extra_path, extras_from_decodes(all_decodes))
    eargs = store.case_args("e", base)
    log(f"encode: {len(eargs)} cases x {sum('e' in i.ops for i in ok)} implementations")
    for impl_id, e in runner.run_op(ok, "e", eargs).items():
        entries.setdefault(impl_id, {}).update(e)

    for impl in ok:
        e = entries[impl.id]
        m = manifest_entry(impl)
        m.update(e.pop("ver"))
        m.update(e)
        manifest["impls"][impl.id] = m
    manifest["cases"] = {
        "decode": {"count": len(dargs), "sha256": cases.case_digest(dargs)},
        "encode": {"count": len(eargs), "sha256": cases.case_digest(eargs)},
    }
    manifest["collected"] = {
        "date": datetime.date.today().isoformat(),
        "platform": f"{platform.system()} {platform.mac_ver()[0] or platform.release()} {platform.machine()}",
    }
    store.write_manifest(manifest, base)
    stale = [i for i in manifest["impls"] if i not in {x.id for x in ok}
             and manifest["impls"][i].get("encode", {}).get("cases") not in (None, len(eargs))]
    for s in stale:
        log(f"WARNING {s}: its encode data predates the current case list; re-run it")
    return skipped


__all__ = ["collect", "Runner", "run_adapter", "BY_ID", "extras_from_decodes"]
