"""
Regression tests for the rapp_brainstem package.

Stdlib-only, runs directly:

    python3 rapp_brainstem/test_regressions.py

Pinned regressions (each test references the PR that introduced the
guarantee, so a future contributor reading a failure understands
*why* the rule exists):

  - PR #29  brainstem UI: drop hardcoded :7071, use same-origin
            The frontend `API` constant must NOT bake in port 7071.
            Regressing this breaks every project-local install that
            picks a non-7071 port via `install.sh --here`.

  - PR #30  brainstem: read/write text files as UTF-8 explicitly
            Every text-mode open()/read_text/write_text MUST pass
            encoding="utf-8" so Windows users on non-UTF-8 locales
            (gbk, cp1252, …) don't crash on UnicodeDecodeError.
"""

from __future__ import annotations

import ast
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INDEX_HTML = ROOT / "index.html"

# Files we deliberately allow to mention 7071 — they are doc strings,
# graceful fallbacks for `file://` opens, or comments. The test below
# checks the *active* JS that talks to the brainstem.
_ALLOWED_7071_FALLBACK_FILES = {
    # binder.html: uses window.location.origin first, falls back to
    # localhost:7071 only when opened via file://.
    "utils/web/binder.html",
    # mobile tether default — separate concern, covered by mobile-specific tests.
    "utils/web/mobile/rapp-mobile.js",
    # Documentation strings.
    "utils/web/index.html",
}


# ── Test infra (stdlib only, matches tests/run-tests.mjs style) ──────

_pass = 0
_fail = 0
_failures: list[str] = []


def _check(name: str, ok: bool, detail: str = "") -> None:
    global _pass, _fail
    if ok:
        _pass += 1
        print(f"  PASS  {name}")
    else:
        _fail += 1
        line = f"{name}: {detail}" if detail else name
        _failures.append(line)
        print(f"  FAIL  {line}")


# ── Regression: PR #29 — index.html must not hardcode :7071 ──────────


def test_index_html_api_is_same_origin() -> None:
    """
    The chat UI's `API` constant defines the base URL for every fetch
    against the brainstem. It must be same-origin ('') so project-local
    installs on any port work out of the box. Hardcoding :7071 sends
    requests to a global brainstem that may not exist.

    Regression introduced by: kody-w/RAPP#29
    """
    src = INDEX_HTML.read_text(encoding="utf-8")

    # Find the `const API = …` declaration. We tolerate whitespace and
    # let/var aliases in case style drifts later.
    m = re.search(r"\b(?:const|let|var)\s+API\s*=\s*([^;]+);", src)
    _check(
        "index.html declares an `API` constant",
        m is not None,
        "no `const API = …` line found",
    )
    if m is None:
        return

    rhs = m.group(1).strip()

    # Allowed forms: empty string, location.origin, or any expression
    # that does NOT bake in a literal port number. Reject anything that
    # contains a numeric port literal — that's the smell of a regression.
    has_hardcoded_port = bool(re.search(r":\s*['\"`]?\d{2,5}['\"`]?", rhs))
    _check(
        "index.html `API` constant has no hardcoded port",
        not has_hardcoded_port,
        f"`API = {rhs}` contains a port literal — must be same-origin",
    )


def test_index_html_no_hardcoded_fetch_to_7071() -> None:
    """
    Beyond the `API` declaration, scan the rest of `index.html` for
    `fetch('http://localhost:7071/...')` shapes. These would bypass
    the same-origin convention and break project-local installs.
    """
    src = INDEX_HTML.read_text(encoding="utf-8")
    # Strip block + line comments so a stray comment doesn't fail the test.
    no_block = re.sub(r"/\*.*?\*/", "", src, flags=re.DOTALL)
    no_line = re.sub(r"//[^\n]*", "", no_block)

    bad = re.findall(
        r"""(?:fetch|XMLHttpRequest|axios|new\s+EventSource|new\s+WebSocket)
            \s*\(\s*[`'\"]
            (?:https?:)?//(?:localhost|127\.0\.0\.1):7071
        """,
        no_line,
        re.VERBOSE,
    )
    _check(
        "index.html has no hardcoded fetch/XHR/WebSocket to :7071",
        not bad,
        f"found {len(bad)} hardcoded :7071 call site(s)",
    )


# ── Regression: PR #30 — text-mode I/O must pass encoding="utf-8" ────


def _iter_python_files() -> list[Path]:
    skip_dirs = {"venv", ".venv", "__pycache__", ".git", "node_modules"}
    out = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in skip_dirs]
        for fn in filenames:
            if fn.endswith(".py"):
                out.append(Path(dirpath) / fn)
    return out


def _is_text_mode(call: ast.Call) -> bool:
    """
    Return True if this call is a text-mode file open. We look at the
    `mode` arg of `open(...)` / `Path.open(...)` — defaults to "r"
    (text). Binary modes ("rb", "wb", "ab", ...) are exempt.
    """
    # mode is positional arg #1 for open(path, mode, ...) and #0 for
    # Path.open(mode, ...). Since we can't always tell which is which
    # statically, we check both candidate positions and any `mode=`
    # keyword.
    candidates: list[ast.expr] = []
    if len(call.args) >= 2:
        candidates.append(call.args[1])
    if len(call.args) >= 1:
        candidates.append(call.args[0])
    for kw in call.keywords:
        if kw.arg == "mode":
            candidates.append(kw.value)

    for node in candidates:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if "b" in node.value:
                return False
    # If we couldn't find a string literal mode, assume text-mode
    # (since text is the default).
    return True


def _has_encoding_kwarg(call: ast.Call) -> bool:
    return any(kw.arg == "encoding" for kw in call.keywords)


def _is_file_open_call(call: ast.Call) -> bool:
    """
    Recognize the file-opening calls we care about:

      open(...)                         → builtin
      X.open(...)        where X looks like a Path             → ambiguous, but flag conservatively
      X.read_text(...) / X.write_text(...)                     → pathlib

    We deliberately do NOT flag:
      zf.open(...)        → ZipFile.open returns binary IO
      urlopen(...) / urllib.request.urlopen(...)
      os.open(...)        → low-level int fd, no encoding concept
      subprocess.Popen, webbrowser.open
    """
    func = call.func
    if isinstance(func, ast.Name) and func.id == "open":
        return True
    if isinstance(func, ast.Attribute):
        attr = func.attr
        if attr in ("read_text", "write_text"):
            return True
        if attr == "open":
            # Exclude well-known non-file .open() calls. We check the
            # immediate receiver name; this catches the common cases
            # (zf.open, os.open, subprocess.Popen-via-attr, etc.) while
            # still flagging path.open(...) and Path(x).open(...).
            value = func.value
            recv_name = None
            if isinstance(value, ast.Name):
                recv_name = value.id
            elif isinstance(value, ast.Attribute):
                recv_name = value.attr
            if recv_name in {
                "zf", "zipfile", "ZipFile",
                "os",
                "subprocess",
                "webbrowser",
                "urllib", "request",
            }:
                return False
            return True
    return False


def test_no_text_open_without_encoding() -> None:
    """
    Every call to open(), Path.open(), Path.read_text(), or
    Path.write_text() in text mode must pass encoding="utf-8". On
    Windows the implicit default is the system locale codec (gbk,
    cp1252, …) which corrupts soul.md and crashes load_soul().

    Regression introduced by: kody-w/RAPP#30
    """
    offenders: list[str] = []

    for path in _iter_python_files():
        # Skip the test file itself — it talks about open() in strings.
        if path.name == "test_regressions.py":
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not _is_file_open_call(node):
                continue
            if not _is_text_mode(node):
                continue
            if _has_encoding_kwarg(node):
                continue
            rel = path.relative_to(ROOT)
            offenders.append(f"{rel}:{node.lineno}")

    _check(
        "no text-mode open() / read_text / write_text without encoding=utf-8",
        not offenders,
        "offenders:\n      "
        + "\n      ".join(offenders[:30])
        + (f"\n      …and {len(offenders) - 30} more" if len(offenders) > 30 else ""),
    )


# ── Driver ───────────────────────────────────────────────────────────


def main() -> int:
    print(f"rapp_brainstem regression tests (root: {ROOT})")
    test_index_html_api_is_same_origin()
    test_index_html_no_hardcoded_fetch_to_7071()
    test_no_text_open_without_encoding()
    print()
    print(f"  {_pass} passed, {_fail} failed")
    if _failures:
        print()
        print("FAILURES:")
        for f in _failures:
            print(f"  - {f}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
