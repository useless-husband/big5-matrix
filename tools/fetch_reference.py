#!/usr/bin/env python3
"""Download the reference tables again and check them against the pinned SHA-256 digests.

Usage: python3 tools/fetch_reference.py [--write]

Without --write the downloads go to a temporary directory and are only compared; with --write
a file that matches its digest replaces the copy in reference/. A mismatch is reported and never
written, because it means the source changed and the study's reference column would change too.
"""

from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

REF = Path(__file__).resolve().parent.parent / "reference"

SOURCES = {
    "index-big5.txt": ("https://encoding.spec.whatwg.org/index-big5.txt",
                       "08e24270c8e95d998c994c03f907e972480dc01f58743e078654cc466203c8ff"),
    "BIG5.TXT": ("https://www.unicode.org/Public/MAPPINGS/OBSOLETE/EASTASIA/OTHER/BIG5.TXT",
                 "d1b60c58a1d327918f1616a620162c60ad2079a229ee42a73488f186e11f3aac"),
    "CP950.TXT": ("https://www.unicode.org/Public/MAPPINGS/VENDORS/MICSFT/WINDOWS/CP950.TXT",
                  "ed403857b05e07ecd5667c7eff6b25898cb1fefe2d06cfe718d82d631e6058b6"),
    "bestfit950.txt": ("https://www.unicode.org/Public/MAPPINGS/VENDORS/MICSFT/WindowsBestFit/bestfit950.txt",
                       "cf8c23389a42a226ea707f7ec32c665556d1fc3364db25bd765ce64d54eaee2a"),
    "HKSCS2016.json": ("https://www.digitalpolicy.gov.hk/open_data/ccli/HKSCS2016.json",
                       "a28a3b74e469726c7df2174346e9a3992760f5842c02ac07b834529bc5b931e5"),
}


def download(url: str) -> bytes:
    """curl when available (it uses the system's certificate store, which some Python builds
    do not), urllib otherwise."""
    curl = shutil.which("curl")
    if curl:
        r = subprocess.run([curl, "-fsSL", "-m", "120", url], capture_output=True)
        if r.returncode != 0:
            raise OSError(r.stderr.decode(errors="replace").strip())
        return r.stdout
    with urllib.request.urlopen(url, timeout=120) as r:
        return r.read()


def main(argv: list[str]) -> int:
    write = "--write" in argv
    bad = 0
    with tempfile.TemporaryDirectory() as tmp:
        for name, (url, want) in SOURCES.items():
            local = REF / name
            have = hashlib.sha256(local.read_bytes()).hexdigest() if local.exists() else None
            try:
                data = download(url)
            except OSError as e:
                print(f"FAIL  {name}: {e}")
                bad += 1
                continue
            got = hashlib.sha256(data).hexdigest()
            (Path(tmp) / name).write_bytes(data)
            if got != want:
                print(f"DIFF  {name}: live source is {got}, pinned {want}")
                bad += 1
                continue
            status = "ok" if have == want else "local copy differs"
            if write and have != want:
                local.write_bytes(data)
                status = "written"
            print(f"OK    {name}: {status}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
