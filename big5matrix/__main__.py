"""Command line: python3 -m big5matrix <command>.

  run [IDS...]     run the adapters (all, or the given implementation ids/runtimes) and
                   update data/; adapters whose runtime is missing are skipped with a notice
  check [IDS...]   re-run the available adapters into a temporary directory and compare with
                   the committed data (the CI drift check)
  analyze          compute the analysis (report/summary.json) from data/
  report           render report/REPORT.md and the README result blocks
  site             build the static site data under docs/
  all              run + analyze + report + site
  list             list the implementations
  build            build every adapter whose runtime is installed and print its version
  show INPUT       what every implementation does with a byte sequence (hex, e.g. A145)
                   or a character (U+2027, or the character itself); --all: one per line
  dump IMPL OP     print one result file with its inputs (OP is decode or encode)
"""

from __future__ import annotations

import sys


def main(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    cmd, rest = argv[0], argv[1:]
    if cmd == "list":
        from .registry import IMPLS

        for i in IMPLS:
            print(f"{i.id:28s} {i.kind:5s} {i.ops:2s} {i.error_model:7s} {i.label}")
        return 0
    if cmd == "build":
        from .registry import IMPLS, Unavailable, prepare
        from .run import adapter_version

        for runtime in dict.fromkeys(i.runtime for i in IMPLS if i.kind == "run"):
            codec = next(i.codec for i in IMPLS if i.runtime == runtime)
            try:
                cmd_ = prepare(runtime)
                print(f"{runtime:8s} {adapter_version(cmd_, codec)['version']}")
            except Unavailable as e:
                print(f"{runtime:8s} SKIPPED: {e}")
        return 0
    if cmd == "show":
        from .show import show

        args = [a for a in rest if a != "--all"]
        return show(" ".join(args), every="--all" in rest)
    if cmd == "dump":
        from . import store

        op = {"decode": "d", "encode": "e"}[rest[1]]
        for arg, res in store.read_results(rest[0], op).items():
            print(f"{arg}\t{res}")
        return 0
    if cmd == "run":
        from .run import collect

        collect(rest or None)
        return 0
    if cmd == "check":
        from .drift import check

        return check(rest or None)
    if cmd == "analyze":
        from .analyze import main as analyze_main

        analyze_main()
        return 0
    if cmd == "report":
        from .report import main as report_main

        report_main()
        return 0
    if cmd == "site":
        from .site import main as site_main

        site_main()
        return 0
    if cmd == "all":
        for c in (["run", *rest], ["analyze"], ["report"], ["site"]):
            if main(c):
                return 1
        return 0
    print(f"unknown command {cmd!r}\n{__doc__}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
