"""The drift check: re-run what is available here and compare with the committed data.

For each implementation the committed manifest records a behaviour key (for example the x/text
module version for Go). If the key here is the same, the results must be identical, and any
difference fails the check: either the data was edited or the adapter changed. If the key is
different (a newer runtime on the CI runner), differences are expected to be possible; they are
reported, with examples, but do not fail the check. Implementations whose runtime is missing are
skipped with a notice.

In GitHub Actions the outcome is also written as annotations and to the job summary.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from . import store
from .registry import IMPLS
from .run import Runner


@dataclass
class Outcome:
    impl: str
    op: str
    status: str  # "same", "drift" (key changed), "changed" (same key, different results)
    old_key: str
    new_key: str
    differing: int = 0
    examples: list[tuple[str, str, str]] = field(default_factory=list)


def compare(impl_id: str, op: str, old_base: Path, new_base: Path, args: list[str]) -> tuple[int, list]:
    old = store.read_results(impl_id, op, old_base, args)
    new = store.read_results(impl_id, op, new_base, args)
    diff = [a for a in args if old.get(a) != new.get(a)]
    return len(diff), [(a, old.get(a, "*"), new.get(a, "*")) for a in diff[:8]]


def run_check(only: list[str] | None = None, base: Path = store.DATA, log=print) -> tuple[list[Outcome], dict]:
    manifest = store.read_manifest(base)
    impls = [i for i in IMPLS if i.id in manifest["impls"] and (not only or i.id in only or i.runtime in only)]
    outcomes: list[Outcome] = []
    with tempfile.TemporaryDirectory() as tmp:
        tmpd = Path(tmp)
        # The case list is the committed one, extra encode cases included.
        shutil.copy(base / "encode-extra.txt", tmpd / "encode-extra.txt")
        runner = Runner(tmpd, log=lambda s: None)
        ok, skipped = runner.available(impls)
        for impl_id, why in skipped.items():
            log(f"SKIP  {impl_id}: {why}")
        for op in ("d", "e"):
            args = store.case_args(op, base)
            todo = [i for i in ok if op in i.ops]
            entries = runner.run_op(todo, op, args)
            for impl in todo:
                committed = manifest["impls"][impl.id]
                new_key = entries[impl.id]["ver"]["key"]
                old_key = committed["key"]
                new_sha = entries[impl.id][store.OPS[op]]["sha256"]
                old_sha = committed[store.OPS[op]]["sha256"]
                if new_sha == old_sha:
                    outcomes.append(Outcome(impl.id, op, "same", old_key, new_key))
                    continue
                n, ex = compare(impl.id, op, base, tmpd, args)
                status = "changed" if new_key == old_key else "drift"
                outcomes.append(Outcome(impl.id, op, status, old_key, new_key, n, ex))
    return outcomes, skipped


def report(outcomes: list[Outcome], skipped: dict, log=print) -> int:
    gha = os.environ.get("GITHUB_ACTIONS") == "true"
    failed = 0
    lines = ["| Implementation | Op | Result | Committed key | Key here | Cases that differ |",
             "|---|---|---|---|---|---:|"]
    for o in outcomes:
        what = store.OPS[o.op]
        if o.status == "same":
            note = "identical" + ("" if o.old_key == o.new_key else " (newer version, same results)")
            log(f"OK    {o.impl} {what}: {note}")
        elif o.status == "drift":
            msg = (f"{o.impl} {what}: {o.differing} cases differ; version key {o.old_key} -> {o.new_key}, "
                   f"so this is reported, not failed. Examples (case, committed, here): {o.examples[:3]}")
            log(f"DRIFT {msg}")
            if gha:
                print(f"::notice title=Big5 behaviour drift::{msg}")
        else:
            failed += 1
            msg = (f"{o.impl} {what}: {o.differing} cases differ although the version key {o.old_key} is "
                   f"unchanged. Examples (case, committed, here): {o.examples[:3]}")
            log(f"FAIL  {msg}")
            if gha:
                print(f"::error title=Committed data does not match::{msg}")
        lines.append(f"| `{o.impl}` | {what} | {o.status} | {o.old_key} | {o.new_key} | {o.differing} |")
    for impl_id, why in skipped.items():
        lines.append(f"| `{impl_id}` | | skipped: {why} | | | |")
        if gha:
            print(f"::notice title=Skipped::{impl_id}: {why}")
    checked = sum(1 for o in outcomes if o.old_key == o.new_key)
    log(f"{len(outcomes)} result files compared ({checked} with the same version key), "
        f"{failed} failed, {len(skipped)} implementations skipped")
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a") as f:
            f.write("## Drift check\n\n" + "\n".join(lines) + "\n")
    return 1 if failed else 0


def check(only: list[str] | None = None) -> int:
    outcomes, skipped = run_check(only)
    return report(outcomes, skipped)
