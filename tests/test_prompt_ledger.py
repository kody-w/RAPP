"""Tests for the RAPP prompt ledger (pages/about/prompts.{json,html})."""
from __future__ import annotations

import json
import importlib.util
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "pages" / "about" / "prompts.json"
HTML = ROOT / "pages" / "about" / "prompts.html"
EMBED = ROOT / "tools" / "embed_prompts.py"


@pytest.fixture(scope="module")
def data() -> dict:
    return json.loads(DATA.read_text())


@pytest.fixture(scope="module")
def html() -> str:
    return HTML.read_text()


# ---------------------------------------------------------------- schema

def test_schema(data):
    assert data["schema"] == "rapp-prompt-ledger/1.0"
    assert isinstance(data["prompts"], list)
    assert data["next_id"] > max(p["id"] for p in data["prompts"])


def test_seeded_with_ten(data):
    assert len(data["prompts"]) >= 10, "need the original 10 seed prompts"


def test_prompt_fields(data):
    required = {"id", "title", "added", "prompt", "shows", "tags"}
    for p in data["prompts"]:
        missing = required - p.keys()
        assert not missing, f"prompt #{p.get('id')} missing fields: {missing}"
        assert isinstance(p["id"], int)
        assert p["title"].strip()
        assert p["prompt"].strip()
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", p["added"])
        assert isinstance(p["tags"], list)


def test_unique_ids(data):
    ids = [p["id"] for p in data["prompts"]]
    assert len(ids) == len(set(ids)), f"duplicate ids: {ids}"


def test_ids_dense_starting_at_one(data):
    ids = sorted(p["id"] for p in data["prompts"])
    assert ids[0] == 1
    # IDs may have gaps later if entries get retracted, but seed is dense.
    seed = [p for p in data["prompts"] if p["added"] == "2026-05-10"]
    seed_ids = sorted(p["id"] for p in seed)
    assert seed_ids == list(range(1, len(seed_ids) + 1))


def test_tags_lowercase_kebab(data):
    pattern = re.compile(r"^[a-z][a-z0-9-]*$")
    bad = []
    for p in data["prompts"]:
        for t in p["tags"]:
            if not pattern.fullmatch(t):
                bad.append((p["id"], t))
    assert not bad, f"non-kebab tags: {bad}"


# ---------------------------------------------------------------- HTML

def test_html_well_formed(html):
    assert html.lstrip().startswith("<!DOCTYPE html>")
    assert "</html>" in html


def test_html_has_controls(html):
    for ctrl in ["pl-search", "pl-sort", "pl-tags", "pl-cards"]:
        assert f'id="{ctrl}"' in html, f"missing #{ctrl}"


def test_html_is_read_only_history(html):
    assert "Superseded, read-only design archive" in html
    assert "navigator.clipboard" not in html
    assert "execCommand('copy')" not in html
    assert "copyPrompt(" not in html


def test_html_exposes_data_on_window(html):
    assert "window.__PROMPTS__" in html


def test_html_escapes_user_content(html):
    assert "escapeHtml" in html


# ---------------------------------------------------------------- embedder

def test_embedded_prompts_are_current_without_writeback():
    before = HTML.read_bytes()
    result = subprocess.run(
        ["python3", str(EMBED), "--check"],
        capture_output=True, text=True, timeout=15, cwd=str(ROOT),
    )
    assert result.returncode == 0, (
        f"embedder failed:\nstdout={result.stdout}\nstderr={result.stderr}"
    )
    assert HTML.read_bytes() == before
    html = HTML.read_text()
    m = re.search(
        r'<script id="prompts-data" type="application/json">(.*?)</script>',
        html, re.DOTALL,
    )
    assert m, "embed block not found after running embedder"
    payload = json.loads(m.group(1).strip())
    sidecar = json.loads(DATA.read_text())
    assert payload == sidecar


def test_embedder_check_mode_detects_drift_without_repair():
    scratch = ROOT / "tests/.rapp1-prompt-ledger-test"
    shutil.rmtree(scratch, ignore_errors=True)
    try:
        scratch.mkdir(parents=True)
        data_path = scratch / "prompts.json"
        html_path = scratch / "prompts.html"
        payload = {"prompts": [{"id": 1}]}
        stale = (
            '<script id="prompts-data" type="application/json">\n'
            '{"prompts":[]}\n'
            "</script>\n"
        )
        data_path.write_text(json.dumps(payload), encoding="utf-8")
        html_path.write_text(stale, encoding="utf-8")

        spec = importlib.util.spec_from_file_location("embed_prompts_test", EMBED)
        embedder = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        sys.modules[spec.name] = embedder
        spec.loader.exec_module(embedder)
        embedder.DATA = data_path
        embedder.HTML = html_path

        assert embedder.main(["--check"]) == 1
        assert html_path.read_text(encoding="utf-8") == stale
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


# ---------------------------------------------------------------- manifest

def test_listed_in_site_manifest():
    manifest = json.loads((ROOT / "pages" / "_site" / "index.json").read_text())
    paths = [
        p["path"] for section in manifest["sections"] for p in section["pages"]
    ]
    assert "about/prompts.html" in paths, (
        "prompts.html not registered in pages/_site/index.json"
    )
    entry = next(
        p
        for section in manifest["sections"]
        for p in section["pages"]
        if p["path"] == "about/prompts.html"
    )
    assert entry["status"] == "historical"
