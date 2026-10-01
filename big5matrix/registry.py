"""Every implementation under test: which adapter runs it, how to build and find the runtime."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from .reference import REFERENCES

ROOT = Path(__file__).resolve().parent.parent
ADAPTERS = ROOT / "adapters"
BUILD = ROOT / "build"


@dataclass(frozen=True)
class Impl:
    id: str
    runtime: str
    codec: str
    label: str
    ops: str = "de"  # "d" = decode only
    error_model: str = "replace"  # "replace": errors become U+FFFD; "strict": conversion stops
    kind: str = "run"  # "run" (a real converter) or "table" (computed from a published table)
    note: str = ""


def _impls() -> list[Impl]:
    out: list[Impl] = []

    def add(runtime, codec, label, slug=None, **kw):
        slug = slug or codec.lower().replace(":", "-").replace("_", "-").replace("/", "-")
        out.append(Impl(f"{runtime}.{slug}", runtime, codec, label, **kw))

    for c in ("big5", "cp950", "big5hkscs"):
        add("python", c, f"Python codecs {c}")
    add("go", "big5", "Go x/text traditionalchinese.Big5")
    add("node", "textdecoder:big5", "Node.js TextDecoder('big5')", slug="textdecoder", ops="d")
    add("node", "iconv-lite:big5", "Node.js iconv-lite big5", slug="iconv-lite-big5")
    add("node", "iconv-lite:cp950", "Node.js iconv-lite cp950", slug="iconv-lite-cp950")
    add("rust", "big5", "Rust encoding_rs BIG5")
    for c in ("Big5", "x-windows-950", "x-IBM950", "x-Big5-Solaris", "Big5-HKSCS",
              "x-Big5-HKSCS-2001", "x-MS950-HKSCS", "x-MS950-HKSCS-XP"):
        add("java", c, f"Java {c}")
    add("dotnet", "950", ".NET code page 950 (strict)")
    add("dotnet", "950/default", ".NET code page 950 (default fallbacks)", slug="950-default",
        note="Encoding.GetEncoding(950) as configured by default: best-fit encoding, '?' on "
             "decoding errors. Encode results are the bytes produced, so '3F' can mean a lost character.")
    add("php", "BIG-5", "PHP mbstring BIG-5")
    add("php", "CP950", "PHP mbstring CP950")
    for c in ("Big5", "CP950", "Big5-HKSCS", "Big5-HKSCS:2008", "Big5-UAO"):
        add("ruby", c, f"Ruby {c}")
    for c in ("big5-eten", "cp950", "big5-hkscs"):
        add("perl", c, f"Perl Encode {c}")
    for c, alias in (("windows-950-2000", "Big5, windows-950"), ("ibm-950_P110-1999", "cp950, x-IBM950"),
                     ("ibm-1373_P100-2002", "ibm-1373"), ("ibm-1375_P100-2008", "Big5-HKSCS"),
                     ("ibm-5471_P100-2006", "MS950_HKSCS, x-MS950-HKSCS")):
        add("icu", c, f"ICU {c} ({alias})", slug=c.split("_")[0])
    for c in ("BIG5", "CP950", "BIG5-HKSCS", "BIG5-2003", "BIG5-IBM", "BIG5-PLUS"):
        add("iconv", c, f"macOS iconv {c}", error_model="strict")
    for r in REFERENCES:
        out.append(Impl(r.id, "ref", r.id, r.label, ops=r.ops, error_model=r.error_model, kind="table",
                        note=r.source))
    return out


IMPLS: list[Impl] = _impls()
BY_ID = {i.id: i for i in IMPLS}


# ---------------------------------------------------------------------------------------------
# Finding runtimes and building adapters


class Unavailable(Exception):
    """The runtime for an adapter is missing or the adapter does not build."""


def _which(*cands: str) -> str | None:
    for c in cands:
        if not c:
            continue
        if os.sep in c:
            if os.path.isfile(c) and os.access(c, os.X_OK):
                return c
        else:
            p = shutil.which(c)
            if p:
                return p
    return None


def _run(cmd: list[str], cwd: Path | None = None, env: dict | None = None) -> str:
    try:
        r = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=900)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise Unavailable(f"{' '.join(cmd)}: {e}") from e
    if r.returncode != 0:
        tail = (r.stderr or r.stdout).strip().splitlines()[-3:]
        raise Unavailable(f"{' '.join(cmd)} failed: {' / '.join(tail)}")
    return r.stdout


def _java() -> str:
    home = os.environ.get("JAVA_HOME")
    for cand in ([os.path.join(home, "bin", "java")] if home else []) + [
        "java", "/opt/homebrew/opt/openjdk/bin/java", "/usr/local/opt/openjdk/bin/java"
    ]:
        p = _which(cand)
        if not p:
            continue
        # /usr/bin/java on macOS is a stub that fails when no JDK is installed.
        r = subprocess.run([p, "-version"], capture_output=True, text=True)
        if r.returncode == 0:
            return p
    raise Unavailable("no working java (set JAVA_HOME)")


def _cargo() -> str:
    p = _which("cargo", "/opt/homebrew/opt/rustup/bin/cargo", os.path.expanduser("~/.cargo/bin/cargo"))
    if not p:
        raise Unavailable("cargo not found")
    return p


def _icu_flags() -> list[str]:
    if shutil.which("pkg-config"):
        r = subprocess.run(["pkg-config", "--cflags", "--libs", "icu-uc"], capture_output=True, text=True)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.split()
    prefixes = [os.environ.get("ICU_PREFIX", ""), "/opt/homebrew/opt/icu4c", "/usr/local/opt/icu4c"]
    if shutil.which("brew"):
        r = subprocess.run(["brew", "--prefix", "icu4c"], capture_output=True, text=True)
        if r.returncode == 0:
            prefixes.insert(1, r.stdout.strip())
    for p in prefixes:
        if p and os.path.exists(os.path.join(p, "include", "unicode", "ucnv.h")):
            return [f"-I{p}/include", f"-L{p}/lib", f"-Wl,-rpath,{p}/lib", "-licuuc", "-licudata"]
    if os.path.exists("/usr/include/unicode/ucnv.h"):
        return ["-licuuc", "-licudata"]
    raise Unavailable("ICU4C headers not found (install icu4c or set ICU_PREFIX)")


def _cc() -> str:
    p = _which(os.environ.get("CC", ""), "cc", "clang", "gcc")
    if not p:
        raise Unavailable("no C compiler")
    return p


def prepare(runtime: str) -> list[str]:
    """Build the adapter for a runtime if needed and return the command prefix that runs it."""
    BUILD.mkdir(exist_ok=True)
    a = ADAPTERS
    if runtime == "python":
        return [os.environ.get("B5M_PYTHON", sys.executable), str(a / "python" / "adapter.py")]
    if runtime == "go":
        go = _which("go")
        if not go:
            raise Unavailable("go not found")
        out = BUILD / "go-adapter"
        _run([go, "build", "-o", str(out), "."], cwd=a / "go")
        return [str(out)]
    if runtime == "node":
        node, npm = _which("node"), _which("npm")
        if not node:
            raise Unavailable("node not found")
        if not (a / "node" / "node_modules" / "iconv-lite").exists():
            if not npm:
                raise Unavailable("npm not found")
            _run([npm, "ci", "--no-audit", "--no-fund"], cwd=a / "node")
        return [node, str(a / "node" / "adapter.mjs")]
    if runtime == "rust":
        cargo = _cargo()
        env = dict(os.environ)
        env["PATH"] = os.path.dirname(cargo) + os.pathsep + env.get("PATH", "")
        _run([cargo, "build", "--release", "--locked", "-j4", "--target-dir", str(BUILD / "rust")],
             cwd=a / "rust", env=env)
        return [str(BUILD / "rust" / "release" / "big5-matrix-rust-adapter")]
    if runtime == "java":
        return [_java(), str(a / "java" / "Adapter.java")]
    if runtime == "dotnet":
        dotnet = _which("dotnet")
        if not dotnet:
            raise Unavailable("dotnet not found")
        out = BUILD / "dotnet"
        _run([dotnet, "build", str(a / "dotnet"), "-c", "Release", "-o", str(out), "-nologo", "-v", "q"])
        return [dotnet, str(out / "big5-matrix-dotnet-adapter.dll")]
    if runtime == "php":
        php = _which("php")
        if not php:
            raise Unavailable("php not found")
        if _run([php, "-r", "echo extension_loaded('mbstring') ? 'yes' : 'no';"]).strip() != "yes":
            raise Unavailable("php has no mbstring extension")
        return [php, str(a / "php" / "adapter.php")]
    if runtime == "ruby":
        ruby = _which("ruby")
        if not ruby:
            raise Unavailable("ruby not found")
        return [ruby, str(a / "ruby" / "adapter.rb")]
    if runtime == "perl":
        perl = _which("perl")
        if not perl:
            raise Unavailable("perl not found")
        _run([perl, "-MEncode::TW", "-e", "1"])
        return [perl, str(a / "perl" / "adapter.pl")]
    if runtime == "icu":
        out = BUILD / "icu-adapter"
        _run([_cc(), "-O2", str(a / "icu" / "adapter.c"), *_icu_flags(), "-o", str(out)])
        return [str(out)]
    if runtime == "iconv":
        if platform.system() != "Darwin":
            # The committed data is macOS's iconv; glibc's is a different implementation.
            raise Unavailable("system iconv data in this study is macOS's (this is not macOS)")
        out = BUILD / "iconv-adapter"
        _run([_cc(), "-O2", str(a / "iconv" / "adapter.c"), "-liconv", "-o", str(out)])
        return [str(out)]
    raise ValueError(f"unknown runtime {runtime}")


def runtimes() -> list[str]:
    seen: list[str] = []
    for i in IMPLS:
        if i.kind == "run" and i.runtime not in seen:
            seen.append(i.runtime)
    return seen
