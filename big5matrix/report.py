"""Refresh the generated numbers and tables in the Markdown documents.

Markers: <!--n:KEY-->value<!--/n--> for a number and <!--t:NAME-->...<!--/t--> for a table,
both looked up in report/summary.json. An unknown key is an error, so a document cannot
quote a number that the analysis does not produce.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from .registry import ROOT

SUMMARY = ROOT / "report" / "summary.json"
DOCUMENTS = [ROOT / "report" / "REPORT.md", ROOT / "README.md", ROOT / "README.zh-TW.md"]

NUM = re.compile(r"<!--n:([^>]+?)-->(.*?)<!--/n-->", re.S)
TAB = re.compile(r"<!--t:([^>]+?)-->\n?(.*?)<!--/t-->", re.S)


class UnknownKey(KeyError):
    pass


def fmt(v) -> str:
    return f"{v:,}" if isinstance(v, int) else str(v)


def render(text: str, summary: dict) -> str:
    nums, tabs = summary["numbers"], summary["tables"]

    def n(m):
        k = m.group(1)
        if k not in nums:
            raise UnknownKey(f"unknown number {k!r}")
        return f"<!--n:{k}-->{fmt(nums[k])}<!--/n-->"

    def t(m):
        k = m.group(1)
        if k not in tabs:
            raise UnknownKey(f"unknown table {k!r}")
        return f"<!--t:{k}-->\n{tabs[k]}\n<!--/t-->"

    return TAB.sub(t, NUM.sub(n, text))


def refresh(paths: list[Path] | None = None, summary: dict | None = None) -> list[Path]:
    summary = summary or json.loads(SUMMARY.read_text())
    changed = []
    for p in paths or DOCUMENTS:
        if not p.exists():
            continue
        old = p.read_text()
        new = render(old, summary)
        if new != old:
            p.write_text(new)
            changed.append(p)
    return changed


def main() -> None:
    for p in refresh():
        print(f"updated {p.relative_to(ROOT)}")
