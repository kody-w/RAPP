#!/usr/bin/env python3
"""boot.py — the brainstem boot wrapper / lineage guard.

start.sh / start.ps1 launch the organism through this wrapper (Constitution
Article XXXIII §4: the canonical kernel stays untouched; organs, senses, and the
/web mount are wired in additively around it). Before serving, it runs the
Article XXXIV lineage guard and refuses to boot an *uninitialized template
clone* — a repo whose rappid.json still carries a parent template's rappid while
its git remote points elsewhere — directing the operator to
installer/initialize-variant.sh.

It does NOT modify the kernel; it execs brainstem.py verbatim. (Organ/sense/web
mounting is an additive extension point — see pages/vault/Architecture/'Boot
Sidecar — Integrating Utils Without Modifying the Kernel.md'. Absent those
modules, the kernel runs unchanged.)
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))   # rapp_brainstem/utils
KERNEL_DIR = os.path.dirname(HERE)                   # rapp_brainstem
KERNEL = os.path.join(KERNEL_DIR, "brainstem.py")


def _guard():
    """Refuse to serve an uninitialized template clone (Article XXXIV)."""
    sys.path.insert(0, HERE)
    try:
        from lineage_check import check_lineage
        info = check_lineage()
    except Exception as e:
        # Fail open — never block boot on a guard error; just warn.
        print(f"[boot] lineage guard skipped: {e}", file=sys.stderr)
        return
    if info.get("status") == "variant_uninitialized":
        tmpl = info.get("template", "a template")
        remote = info.get("remote", "(unknown remote)")
        sys.stderr.write(
            "\n".join([
                "",
                "  ✗ Uninitialized template clone — refusing to boot.",
                f"    rappid.json still carries {tmpl}'s rappid, but this repo is {remote}.",
                "    Mint this variant's own rappid first:",
                "        bash installer/initialize-variant.sh",
                "    (Constitution Article XXXIV — single-parent rule.)",
                "",
            ])
        )
        sys.exit(1)


def main():
    _guard()
    if not os.path.isfile(KERNEL):
        sys.stderr.write(f"[boot] kernel not found at {KERNEL}\n")
        sys.exit(1)
    # Run the canonical kernel verbatim (Art. XXXIII §4 — kernel untouched).
    os.chdir(KERNEL_DIR)
    os.execv(sys.executable, [sys.executable, KERNEL])


if __name__ == "__main__":
    main()
