#!/usr/bin/env python3
"""
hatch.py — the self-bootstrapper. Turn a cubby-rapp-installer.egg into a
running, repo-independent RAPP brainstem from nothing. PURE STDLIB.

This is the "fully self-bootstrapping brainstem" piece: the .egg plus this one
file are sufficient to reconstitute an entire working brainstem on a bare
machine (given Python 3.9+). No git, no grail repo. The only network it needs
beyond fetching the egg is PyPI, to build the venv (flask/requests/python-dotenv);
pass --no-venv to skip that if the deps are already present. The egg is a
`brainstem-egg/2.3-cubby` ZIP; hatching extracts
its `cubby/` tree into ~/.brainstem/cubbies/rapp-installer/, builds the venv,
installs the kernel's requirements, and (optionally) launches serve.py.

USAGE
    python3 hatch.py [EGG] [--into DIR] [--run] [--port N] [--no-venv]

    EGG       Path or http(s):// URL to a cubby-rapp-installer.egg. If omitted,
              auto-discovers: ./cubby-rapp-installer.egg, ~/.brainstem/eggs/…,
              or — if this file is already sitting inside an extracted cubby —
              hatches in place (no egg needed).
    --into    Cubby root to hatch into (default ~/.brainstem/cubbies/<slug>).
    --run     After hatching, launch the rapplication (serve.py).
    --port N  Port for --run (default 7077, coexists with a :7071 grail).
    --no-venv Skip venv creation / pip install (just lay down the files).

EXAMPLES
    python3 hatch.py ~/Downloads/cubby-rapp-installer.egg --run
    python3 hatch.py https://example.com/cubby-rapp-installer.egg --run
    python3 hatch.py --run            # auto-find the egg (or hatch in place)

GUARANTEE
    Never touches ~/.brainstem/src (the grail). Everything lands in the cubby,
    which is not a git repo — so there is nothing to accidentally commit.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

EGG_SCHEMA  = "brainstem-egg/2.3-cubby"
SLUG        = "rapp-installer"
BRAINSTEM   = Path(os.path.expanduser("~/.brainstem"))
GRAIL       = BRAINSTEM / "src" / "rapp_brainstem"     # the repo we must NEVER write to


def _say(msg: str) -> None:
    print(f"[hatch] {msg}", flush=True)


def _read_egg_bytes(egg: str) -> bytes:
    if egg.startswith("http://"):
        sys.exit("[hatch] refusing plaintext http:// egg URL (MITM risk) — use https:// "
                 "or a local path. For the public cave, use bootstrap.sh (plain curl).")
    if egg.startswith("https://"):
        _say(f"fetching egg → {egg}")
        with urllib.request.urlopen(egg, timeout=60) as r:
            return r.read()
    p = Path(os.path.expanduser(egg))
    if not p.exists():
        sys.exit(f"[hatch] egg not found: {egg}")
    return p.read_bytes()


def _auto_find_egg() -> str | None:
    here = Path(__file__).resolve().parent
    for cand in (
        here / f"cubby-{SLUG}.egg",
        Path.cwd() / f"cubby-{SLUG}.egg",
        BRAINSTEM / "eggs" / f"cubby-{SLUG}.egg",
    ):
        if cand.exists():
            return str(cand)
    return None


def _hatch_in_place_root() -> Path | None:
    """If hatch.py is already living inside an extracted cubby
    (…/<slug>/rapplications/<slug>/hatch.py), return the cubby root so we can
    bootstrap with no egg at all."""
    here = Path(__file__).resolve()
    # …/<cubby>/rapplications/<slug>/hatch.py  → parents[2] is the cubby root
    if len(here.parents) >= 3 and here.parents[1].name == "rapplications":
        root = here.parents[2]
        if (root / "cubby.json").exists():
            return root
    return None


def _extract_egg(blob: bytes, into: Path) -> int:
    """Extract a cubby egg's `cubby/` tree into `into`. Verifies schema, refuses
    zip-slip paths and any attempt to write outside `into`."""
    import io
    z = zipfile.ZipFile(io.BytesIO(blob))
    try:
        manifest = json.loads(z.read("manifest.json"))
    except KeyError:
        sys.exit("[hatch] not a cubby egg (no manifest.json)")
    schema = manifest.get("schema")
    if schema != EGG_SCHEMA:
        sys.exit(f"[hatch] unexpected egg schema {schema!r} (want {EGG_SCHEMA!r})")
    _say(f"egg ok: schema={schema} slug={manifest.get('slug')} files≈{len(manifest.get('files', [])) or '?'}")
    into.mkdir(parents=True, exist_ok=True)
    into_real = into.resolve()
    n = 0
    for name in z.namelist():
        if not name.startswith("cubby/") or name.endswith("/"):
            continue
        rel = name[len("cubby/"):]
        dest = (into / rel).resolve()
        if not str(dest).startswith(str(into_real) + os.sep) and dest != into_real:
            sys.exit(f"[hatch] refusing unsafe path in egg: {name}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(z.read(name))
        n += 1
    return n


def _ensure_venv() -> Path:
    """Ensure ~/.brainstem/venv exists and return its python. Stdlib `venv`."""
    venv = BRAINSTEM / "venv"
    py = venv / ("Scripts" if os.name == "nt" else "bin") / ("python.exe" if os.name == "nt" else "python")
    if not py.exists():
        _say("creating venv at ~/.brainstem/venv")
        import venv as _venv
        _venv.EnvBuilder(with_pip=True).create(str(venv))
    return py


def _pip_install(py: Path, req: Path) -> None:
    """Install the kernel's deps and VERIFY they import. Fails loud (no silent
    'success' that crashes on launch) — the venv build needs PyPI access."""
    if not req.exists():
        return
    _say(f"installing deps from {req} (needs PyPI access)")
    r = subprocess.run([str(py), "-m", "pip", "install", "-q", "-r", str(req)])
    if r.returncode != 0:
        sys.exit("[hatch] pip install failed — no network/PyPI? Re-run online, or "
                 "install flask/requests/python-dotenv into ~/.brainstem/venv yourself.")
    check = subprocess.run([str(py), "-c", "import flask, requests, dotenv"])
    if check.returncode != 0:
        sys.exit("[hatch] kernel deps still missing after install (flask/requests/dotenv). "
                 "The brainstem will not start until these import.")
    _say("deps ok (flask, requests, dotenv import)")


def main() -> None:
    ap = argparse.ArgumentParser(description="Hatch the rapp-installer egg into a running brainstem.")
    ap.add_argument("egg", nargs="?", help="egg path or URL (auto-discovered if omitted)")
    ap.add_argument("--into", help="cubby root (default ~/.brainstem/cubbies/<slug>)")
    ap.add_argument("--run", action="store_true", help="launch serve.py after hatching")
    ap.add_argument("--port", type=int, default=7077)
    ap.add_argument("--no-venv", action="store_true")
    args = ap.parse_args()

    into = Path(os.path.expanduser(args.into)) if args.into else (BRAINSTEM / "cubbies" / SLUG)

    # Prime directive: never hatch into the grail.
    if into.resolve() == GRAIL.resolve() or str(into.resolve()).startswith(str(GRAIL.resolve()) + os.sep):
        sys.exit("[hatch] refusing to hatch into the grail repo")

    in_place = _hatch_in_place_root()
    if args.egg is None and in_place is not None and (args.into is None):
        # Already extracted (e.g. you cloned the public cave) — bootstrap in place.
        into = in_place
        _say(f"hatching in place — cubby already present at {into}")
    else:
        egg = args.egg or _auto_find_egg()
        if egg is None:
            sys.exit("[hatch] no egg given and none found. Pass a path/URL, or run from inside an extracted cubby.")
        blob = _read_egg_bytes(egg)
        n = _extract_egg(blob, into)
        _say(f"hatched {n} files → {into}")

    rapp = into / "rapplications" / SLUG
    serve = rapp / "serve.py"
    if not serve.exists():
        sys.exit(f"[hatch] hatched, but serve.py missing at {serve}")

    py: Path | None = None
    if not args.no_venv:
        py = _ensure_venv()
        _pip_install(py, rapp / "kernel" / "requirements.txt")

    _say("✅ hatched. Repo-independent brainstem ready (grail untouched).")
    _say(f"   cubby:   {into}")
    _say(f"   run it:  {(py or 'python3')} {serve}   (PORT={args.port})")

    if args.run:
        runner = str(py) if py else sys.executable
        env = dict(os.environ, PORT=str(args.port))
        _say(f"launching → http://localhost:{args.port}")
        os.chdir(rapp)
        os.execve(runner, [runner, str(serve)], env)


if __name__ == "__main__":
    main()
