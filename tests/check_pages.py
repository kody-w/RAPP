#!/usr/bin/env python3
"""Dependency-free validation for the repository's GitHub Pages contract."""

from __future__ import annotations

import fnmatch
import json
import re
import sys
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qs, unquote, urljoin, urlsplit


ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "https://kody-w.github.io/RAPP"
MANIFEST_PATH = ROOT / "pages/_site/index.json"
RESTORED_HISTORY = {
    "docs/index.html",
    "docs/tutorial.html",
    "pages/rappid-deck.html",
    "pages/rappid-onepager.html",
    "pages/share/invention-backlog/index.html",
}
SAFE_INTERACTIVE_HISTORY = {
    "docs/index.html",
    "docs/tutorial.html",
    "pages/onboarding.html",
    "pages/rappid-deck.html",
    "pages/rappid-onepager.html",
    "pages/share/invention-backlog/index.html",
}
ADAPTED_HISTORY = {
    "installer/plant.html",
    "installer/plant_qr.html",
    "installer/seed.html",
    "installer/shortcuts/brainstem-voice/index.html",
    "installer/shortcuts/index.html",
    "pages/chat.html",
    "pages/grail-brainstem/index.html",
    "pages/lobby.html",
    "pages/metropolis/index.html",
    "pages/metropolis/plant-from-discord.html",
    "pages/payphone.html",
    "pages/sphere.html",
    "pages/summon.html",
    "pages/tether.html",
    "pages/vbrainstem.html",
    "pages/vbrainstem/index.html",
    "pages/vneighborhood.html",
}


class DocumentParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.refs: list[tuple[str, str, str]] = []
        self.ids: set[str] = set()
        self.base: str | None = None
        self.title_seen = False
        self.html_seen = False
        self.meta_robots = ""
        self.meta_refresh = ""
        self.meta_csp = ""
        self.meta_history_source = ""
        self.meta_history_boundary = ""
        self.forms = 0
        self.buttons = 0
        self.iframes = 0
        self.scripts: list[dict[str, str]] = []
        self.linked_resources: list[str] = []
        self._script_index: int | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        data = {key: value or "" for key, value in attrs}
        if tag == "html":
            self.html_seen = True
        elif tag == "title":
            self.title_seen = True
        elif tag == "base" and data.get("href"):
            self.base = data["href"]
        elif tag == "meta":
            name = data.get("name", "").lower()
            equiv = data.get("http-equiv", "").lower()
            if name == "robots":
                self.meta_robots = data.get("content", "").lower()
            if equiv == "refresh":
                self.meta_refresh = data.get("content", "")
            if equiv == "content-security-policy":
                self.meta_csp = data.get("content", "").lower()
            if name == "rapp-history-source":
                self.meta_history_source = data.get("content", "")
            if name in {"rapp-history-boundary", "rapp-historical-boundary"}:
                self.meta_history_boundary = data.get("content", "")
        elif tag == "form":
            self.forms += 1
        elif tag == "button":
            self.buttons += 1
        elif tag == "iframe":
            self.iframes += 1
        elif tag == "link" and data.get("rel", "").lower() in {
            "stylesheet",
            "preload",
            "modulepreload",
        }:
            if data.get("href"):
                self.linked_resources.append(data["href"])

        if data.get("id"):
            self.ids.add(data["id"])

        if tag == "script":
            self.scripts.append(
                {
                    "type": data.get("type", ""),
                    "src": data.get("src", ""),
                    "content": "",
                }
            )
            self._script_index = len(self.scripts) - 1

        if tag != "base":
            for attr in ("href", "src"):
                value = data.get(attr)
                if value:
                    self.refs.append((tag, attr, value))

    def handle_endtag(self, tag: str) -> None:
        if tag == "script":
            self._script_index = None

    def handle_data(self, data: str) -> None:
        if self._script_index is not None:
            self.scripts[self._script_index]["content"] += data


def parse_document(path: Path) -> DocumentParser:
    parser = DocumentParser()
    parser.feed(path.read_text(encoding="utf-8", errors="replace"))
    parser.close()
    return parser


def yaml_list(text: str, key: str) -> list[str]:
    lines = text.splitlines()
    values: list[str] = []
    active = False
    for line in lines:
        if re.fullmatch(rf"{re.escape(key)}:\s*", line):
            active = True
            continue
        if active:
            match = re.fullmatch(r"\s{2}-\s+(.+?)\s*", line)
            if match:
                values.append(match.group(1).strip("\"'"))
                continue
            if line.strip() and not line.startswith(" "):
                break
    return values


def is_under(path: str, prefix: str) -> bool:
    clean = prefix.rstrip("/")
    return path == clean or path.startswith(clean + "/")


def is_explicitly_excluded(path: str, excludes: list[str]) -> bool:
    for pattern in excludes:
        if any(char in pattern for char in "*?["):
            if fnmatch.fnmatch(path, pattern):
                return True
        elif is_under(path, pattern):
            return True
    return False


def is_hidden_by_jekyll(path: str, includes: list[str]) -> bool:
    components = Path(path).parts
    hidden = any(part.startswith((".", "_")) for part in components)
    if not hidden:
        return False
    return not any(is_under(path, item) or is_under(item, path) for item in includes)


def simulated_publication(includes: list[str], excludes: list[str]) -> set[str]:
    published: set[str] = set()
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(ROOT).as_posix()
        if relative == "_config.yml" or relative.startswith(".git/"):
            continue
        explicitly_included = any(is_under(relative, item) for item in includes)
        if is_explicitly_excluded(relative, excludes) and not explicitly_included:
            continue
        if is_hidden_by_jekyll(relative, includes):
            continue
        published.add(relative)
    return published


def candidate_targets(source: str, parser: DocumentParser, raw: str) -> list[str]:
    if raw.startswith("@/"):
        resolved_path = "pages/" + unquote(urlsplit(raw[2:]).path)
    else:
        parts = urlsplit(raw)
        path = unquote(parts.path)
        if parser.base and not path.startswith("/"):
            path = urlsplit(urljoin(parser.base, raw)).path
        if path == "/RAPP":
            resolved_path = "index.html"
        elif path.startswith("/RAPP/"):
            resolved_path = path[len("/RAPP/") :]
        elif path.startswith("/"):
            return []
        else:
            resolved_path = (Path(source).parent / path).as_posix()

    normalized = ROOT / resolved_path
    try:
        normalized = normalized.resolve().relative_to(ROOT.resolve())
    except ValueError:
        return []
    relative = normalized.as_posix()
    if relative == ".":
        relative = ""
    if raw.endswith("/") or (ROOT / relative).is_dir():
        return [f"{relative.rstrip('/') + '/' if relative else ''}index.html"]
    targets = [relative]
    if not Path(relative).suffix:
        targets.extend([f"{relative}.html", f"{relative}/index.html"])
    return targets


def doc_key_from_route(route: str) -> str | None:
    values = parse_qs(urlsplit(route).query).get("doc", [])
    return values[0] if len(values) == 1 else None


def parse_allowlist(text: str, variable: str) -> set[str]:
    match = re.search(
        rf"\b{re.escape(variable)}\s*=\s*\[([^\]]+)\]",
        text,
        flags=re.DOTALL,
    )
    if not match:
        return set()
    return set(re.findall(r"['\"]([^'\"]+)['\"]", match.group(1)))


def main() -> int:
    errors: list[str] = []

    def require(condition: bool, message: str) -> None:
        if not condition:
            errors.append(message)

    config_path = ROOT / "_config.yml"
    require(config_path.is_file(), "_config.yml is required for root Pages containment")
    require(not (ROOT / ".nojekyll").exists(), ".nojekyll must be removed")
    config = config_path.read_text(encoding="utf-8") if config_path.exists() else ""
    includes = yaml_list(config, "include")
    excludes = yaml_list(config, "exclude")

    for required in {
        ".well-known/rapp-network-seed.json",
        "_site",
        "pages/_site",
        "pages/vault/index.html",
        "pages/vault/manifest.json",
        "pages/vault/content-bundle.json",
        "pages/vault/marked.min.js",
        "pages/vault/vendor/marked-LICENSE.txt",
        "pages/vault/sw.js",
    }:
        require(required in includes, f"_config.yml must include {required}")
    for required in {
        "tests",
        "tools",
        "scripts",
        "worker",
        "historical/source-archive",
        "rapp_brainstem",
        "rapp_swarm",
        "cave/rapplications/rapp-installer",
        "cave/card.json",
        "cave/facets.json",
        "cave/holo.md",
        "cave/holo.svg",
        "cave/INVITE.md",
        "cave/members.json",
        "cave/neighborhood.json",
        "cave/rappid.json",
        "cave/tests",
        "pages/_lib",
        "pages/tutorials/egg_hatcher_agent.py",
        "pages/vault/*.md",
        "pages/vault/**/*.md",
    }:
        require(required in excludes, f"_config.yml must exclude {required}")

    published = simulated_publication(includes, excludes)
    for required in {
        "index.html",
        "404.html",
        "docs/index.html",
        "installer/index.html",
        "pages/index.html",
        "pages/kernel.html",
        "pages/_site/index.json",
        "pages/_site/partials/header.html",
        "pages/vault/manifest.json",
        "pages/vault/sw.js",
        ".well-known/rapp-network-seed.json",
        "pages/metropolis/index.json",
        "pages/metropolis/federated-demo.json",
        "pages/metropolis/activity-snapshot.json",
        "cave/index.html",
        "sitemap.xml",
        "robots.txt",
    }:
        require(required in published, f"publication simulation omitted {required}")
    for forbidden in {
        "tests/e2e/08-html-pages.sh",
        "rapp_brainstem/index.html",
        "rapp_swarm/index.html",
        "cave/rapplications/rapp-installer/kernel/index.html",
        "cave/rapplications/rapp-installer/web/index.html",
        "cave/card.json",
        "cave/facets.json",
        "cave/members.json",
        "cave/neighborhood.json",
        "cave/rappid.json",
        "cave/tests/test_catalog_containment.py",
        "pages/_lib/rapp-sealed.js",
        "pages/tutorials/egg_hatcher_agent.py",
        "pages/vault/Architecture/Rappid.md",
        "installer/install.sh",
        "install.sh",
        "MSFTAIBASMultiAgentCopilot_1_0_0_5.zip",
    }:
        require(forbidden not in published, f"publication simulation exposes {forbidden}")

    front_matter_sources = {
        relative
        for relative in published
        if Path(relative).suffix.lower() in {".md", ".markdown"}
        and (ROOT / relative).read_text(encoding="utf-8", errors="replace").startswith("---\n")
    }
    require(
        front_matter_sources == {"pages/docs/skill.md"},
        "publication would generate unclassified HTML from front-matter Markdown",
    )
    require(
        "permalink: /pages/docs/skill.md" in config,
        "pages/docs/skill.md must retain its advertised virtual source path",
    )

    html_paths = sorted(path for path in published if path.endswith(".html"))
    parsers: dict[str, DocumentParser] = {}
    vault_route_paths = {
        note["path"]
        for note in json.loads(
            (ROOT / "pages/vault/manifest.json").read_text(encoding="utf-8")
        )["notes"]
    }
    for relative in html_paths:
        parser = parse_document(ROOT / relative)
        parsers[relative] = parser
        if "_site/partials/" not in relative:
            require(parser.html_seen, f"{relative}: missing <html>")
            require(parser.title_seen, f"{relative}: missing <title>")
        text = (ROOT / relative).read_text(encoding="utf-8", errors="replace")
        require(
            not re.search(r"\b(?:HTTP\s*410|410\s+Gone)\b", text, flags=re.IGNORECASE),
            f"{relative}: static Pages HTML must say retired semantic tombstone, not HTTP 410",
        )

    for source, parser in parsers.items():
        for tag, attr, raw in parser.refs:
            value = raw.strip()
            if not value or value.startswith("#"):
                continue
            parts = urlsplit(value)
            if parts.scheme in {"http", "https", "mailto", "tel", "data", "javascript", "blob"}:
                continue
            if value.startswith("//"):
                continue
            targets = candidate_targets(source, parser, value)
            require(bool(targets), f"{source}: project-unsafe {attr}={value!r}")
            if not targets:
                continue
            target = next((item for item in targets if (ROOT / item).exists()), None)
            require(target is not None, f"{source}: broken {attr}={value!r}")
            if target is None:
                continue
            require(target in published, f"{source}: {attr}={value!r} targets excluded {target}")
            if parts.fragment and target.endswith(".html"):
                if target == "pages/vault/index.html":
                    require(
                        unquote(parts.fragment) in vault_route_paths,
                        f"{source}: {value!r} targets an unknown vault note",
                    )
                else:
                    target_parser = parsers.get(target)
                    if target_parser is not None:
                        require(
                            parts.fragment in target_parser.ids,
                            f"{source}: {value!r} targets missing fragment #{parts.fragment}",
                        )

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    valid_classes = set(manifest["classifications"])
    entries = [page for section in manifest["sections"] for page in section["pages"]]
    listed = [page["path"] for page in entries]
    actual_pages = sorted(
        path.relative_to(ROOT / "pages").as_posix()
        for path in (ROOT / "pages").rglob("*.html")
        if "_site/partials/" not in path.as_posix()
    )
    require(len(listed) == len(set(listed)), "pages manifest contains duplicate physical paths")
    require(sorted(listed) == actual_pages, "pages manifest does not classify every physical HTML path exactly once")
    for page in entries:
        path = page["path"]
        require(page.get("classification") in valid_classes, f"manifest {path}: invalid classification")
        require(isinstance(page.get("navigation"), bool), f"manifest {path}: navigation must be boolean")
        require(f"pages/{path}" in published, f"manifest {path}: route is not published")
        if page.get("classification") != "current_entrypoint":
            require(not page["navigation"], f"manifest {path}: historical/retired route pollutes normal navigation")

    docs_index = (ROOT / "pages/docs/index.html").read_text(encoding="utf-8")
    docs_parser = parsers["pages/docs/index.html"]
    card_docs = {
        key
        for _tag, _attr, href in docs_parser.refs
        if "viewer.html?doc=" in href
        for key in [doc_key_from_route(href)]
        if key
    }
    viewer_text = (ROOT / "pages/docs/viewer.html").read_text(encoding="utf-8")
    viewer_allowed = parse_allowlist(viewer_text, "allowed")
    loader_text = (ROOT / "pages/_site/js/doc-viewer.js").read_text(encoding="utf-8")
    loader_allowed = parse_allowlist(loader_text, "ALLOWED")
    virtual_docs = {doc_key_from_route(item["path"]) for item in manifest["virtual_routes"]}
    virtual_docs.discard(None)
    require("README" in card_docs, "docs index must advertise the README route")
    require("QR_FRONT_GATE" in card_docs, "docs index must advertise QR_FRONT_GATE")
    require(
        card_docs == viewer_allowed == loader_allowed == virtual_docs,
        "docs cards, both allowlists, and manifest virtual routes must agree",
    )
    for key in sorted(virtual_docs):
        relative = f"pages/docs/{key}.md"
        require((ROOT / relative).is_file(), f"docs virtual route {key}: missing source")
        require(relative in published, f"docs virtual route {key}: source is not published")
    require(docs_index.count("viewer.html?doc=README") == 1, "README docs card must appear exactly once")
    require(docs_index.count("viewer.html?doc=QR_FRONT_GATE") == 1, "QR_FRONT_GATE card must appear exactly once")

    not_found = parsers["404.html"]
    require(not_found.base == "/RAPP/", "404.html must declare <base href=\"/RAPP/\">")

    for relative in RESTORED_HISTORY:
        text = (ROOT / relative).read_text(encoding="utf-8", errors="replace")
        parser = parsers[relative]
        require("noindex" in parser.meta_robots, f"{relative}: historical page must remain noindex")
        require("RAPP1-HISTORICAL-SECTION-START" in text, f"{relative}: missing historical start marker")
        require("RAPP1-HISTORICAL-SECTION-END" in text, f"{relative}: missing historical end marker")
        require(
            not re.search(r"<div\b[^>]*\bhidden\b[^>]*aria-hidden=[\"']true", text, flags=re.IGNORECASE),
            f"{relative}: retained content is still hidden",
        )
        if relative in SAFE_INTERACTIVE_HISTORY:
            require(
                re.search(
                    r"class=[\"']historical-snapshot[\"'][^>]*\binert\b",
                    text,
                )
                is None
                and (
                    parser.buttons > 0
                    or any(
                        script["type"]
                        in {"", "text/javascript", "module", "application/javascript"}
                        for script in parser.scripts
                    )
                ),
                f"{relative}: safe local presentation controls must remain enabled",
            )
        else:
            require(
                re.search(
                    r"class=[\"']historical-snapshot[\"'][^>]*\binert\b",
                    text,
                ) is None,
                f"{relative}: restored snapshot must remain visible",
            )
        for script in parser.scripts:
            body = script["content"]
            if re.search(r"\b(?:fetch|XMLHttpRequest|WebSocket|EventSource)\s*\(", body):
                require(
                    script["type"] == "application/rapp-history",
                    f"{relative}: network-capable historical script remains executable",
                )
        for tag, attr, value in parser.refs:
            if tag in {"img", "iframe", "script", "link", "audio", "video", "source"}:
                require(
                    urlsplit(value).scheme not in {"http", "https"},
                    f"{relative}: restored snapshot auto-loads remote {tag} {attr}={value!r}",
                )

    for relative in sorted(ADAPTED_HISTORY):
        text = (ROOT / relative).read_text(encoding="utf-8", errors="replace")
        parser = parsers[relative]
        lowered = text.lower()
        require("noindex" in parser.meta_robots, f"{relative}: adapted history must remain noindex")
        require(
            "retired semantic tombstone" not in lowered,
            f"{relative}: full historical body was replaced by a semantic tombstone",
        )
        require(
            bool(parser.meta_history_source)
            or "rapp-source-commit" in lowered
            or "fullest_source_commit" in lowered,
            f"{relative}: missing historical source provenance",
        )
        require(
            bool(parser.meta_history_boundary)
            or "rapp-record-kind" in lowered
            or "rapp-history-boundary" in lowered,
            f"{relative}: missing current historical/adaptation boundary",
        )
        require(bool(parser.meta_csp), f"{relative}: missing browser containment policy")
        for directive in ("object-src 'none'", "base-uri 'none'", "form-action 'none'"):
            require(
                directive in parser.meta_csp,
                f"{relative}: CSP must include {directive}",
            )
        connect_match = re.search(r"(?:^|;)\s*connect-src\s+([^;]+)", parser.meta_csp)
        require(connect_match is not None, f"{relative}: CSP must declare connect-src")
        if connect_match is not None:
            connect_policy = connect_match.group(1)
            require(
                "http:" not in connect_policy
                and "https:" not in connect_policy
                and "*" not in connect_policy,
                f"{relative}: CSP permits external connections",
            )
        require(not parser.meta_refresh, f"{relative}: adapted history must not redirect")
        executable_script = "\n".join(
            script["content"]
            for script in parser.scripts
            if script["type"]
            in {"", "text/javascript", "module", "application/javascript"}
        )
        for marker in (
            "navigator.geolocation",
            "navigator.mediaDevices",
            "navigator.share",
            "speechSynthesis",
            "URL.createObjectURL",
            "window.print(",
            "showSaveFilePicker",
            "PaymentRequest",
        ):
            require(
                marker not in executable_script,
                f"{relative}: active local replay invokes sensitive browser API {marker}",
            )
        for tag, attr, value in parser.refs:
            if tag in {"img", "iframe", "script", "audio", "video", "source"}:
                require(
                    urlsplit(value).scheme not in {"http", "https"},
                    f"{relative}: adapted history auto-loads remote {tag} {attr}={value!r}",
                )
        require(
            all(
                urlsplit(value).scheme not in {"http", "https"}
                for value in parser.linked_resources
            ),
            f"{relative}: adapted history auto-loads a remote linked resource",
        )

    manifest_by_path = {page["path"]: page for page in entries}
    for path, page in manifest_by_path.items():
        if page["classification"] == "current_entrypoint":
            continue
        if page["classification"] == "adapted_historical_page":
            require(
                f"pages/{path}" in ADAPTED_HISTORY,
                f"manifest {path}: adapted page is absent from the safety contract",
            )

    copy_requirements = {
        "index.html": ("not yet fully rapp/1 conformant", "no active installer"),
        "pages/index.html": ("rapp-current-status", "kernel_pin.json"),
        "pages/kernel.html": ("not yet fully rapp/1 conformant", "kernel_pin.json"),
        "installer/index.html": ("rapp-current-status", "kernel_pin.json"),
        "blog.html": ("superseded historical record", "no current installer"),
        "release-notes.html": ("superseded historical record", "no current installer"),
        "pages/about/ecosystem.html": ("generated historical observation", "not an active catalog"),
        "pages/vault/index.html": ("historical, read-only note archive", "not current capability claims"),
    }
    for relative, phrases in copy_requirements.items():
        lowered = (ROOT / relative).read_text(encoding="utf-8", errors="replace").lower()
        for phrase in phrases:
            require(phrase in lowered, f"{relative}: missing current-vs-historical copy {phrase!r}")
    vault_html = (ROOT / "pages/vault/index.html").read_text(encoding="utf-8")
    require("serviceWorker.register" not in vault_html, "vault viewer must not register a service worker")
    require('rel="manifest"' not in vault_html, "vault viewer must not claim installable PWA status")
    require("<kbd>o</kbd>" not in vault_html, "vault viewer still advertises the Obsidian shortcut")
    vault_js = (ROOT / "pages/vault/vault.js").read_text(encoding="utf-8")
    require("openInObsidian" not in vault_js, "vault viewer still exposes Obsidian launch code")
    require("obsidian://" not in vault_js, "vault viewer still contains an external application URI")
    require(
        "wikilink-aliases.json" in vault_js
        and "content-bundle.json" in vault_js
        and "repositoryUrlFor" in vault_js
        and "VAULT.aliases" in vault_js,
        "vault viewer does not load and resolve the checked alias table",
    )
    require(
        "raw.githubusercontent.com" not in vault_js
        and "rawUrlFor" not in vault_js,
        "vault viewer retains a moving remote content fallback",
    )
    require(
        './marked.min.js' in vault_html
        and all(
            urlsplit(script["src"]).scheme not in {"http", "https"}
            for script in parsers["pages/vault/index.html"].scripts
        ),
        "vault viewer does not use the local pinned Markdown renderer",
    )
    docs_runtime = (ROOT / "pages/_site/js/doc-viewer.js").read_text(
        encoding="utf-8"
    )
    require(
        "../vault/marked.min.js" in docs_runtime
        and "cdn.jsdelivr.net" not in docs_runtime
        and "sanitizeHtml" in docs_runtime,
        "docs viewer does not use the local sanitized Markdown renderer",
    )
    vault_manifest = json.loads(
        (ROOT / "pages/vault/manifest.json").read_text(encoding="utf-8")
    )
    public_vault_paths = {note["path"] for note in vault_manifest["notes"]}
    excluded_vault_paths = {
        note["path"] for note in vault_manifest.get("excluded_notes", [])
    }
    draft_paths = {
        path.relative_to(ROOT / "pages/vault").as_posix()
        for path in (ROOT / "pages/vault/Blog Drafts").rglob("*.md")
    }
    require(
        not (public_vault_paths & draft_paths),
        "vault manifest publishes explicitly unpublished Blog Drafts",
    )
    require(
        excluded_vault_paths == draft_paths,
        "vault manifest does not explicitly account for every unpublished Blog Draft",
    )
    retirement_worker = (ROOT / "pages/vault/sw.js").read_text(encoding="utf-8")
    require(
        "caches.delete" in retirement_worker
        and "registration.unregister" in retirement_worker
        and "client.navigate" in retirement_worker,
        "vault retirement worker does not clear, unregister, and reload",
    )
    require(
        "addEventListener('fetch'" not in retirement_worker
        and "cache.add" not in retirement_worker,
        "vault retirement worker still intercepts or precaches requests",
    )
    historical_spec = (ROOT / "pages/docs/SPEC.md").read_text(encoding="utf-8")
    require(
        "](../../specs/" not in historical_spec
        and "https://github.com/kody-w/RAPP/blob/main/specs/SPEC.md" in historical_spec
        and "https://github.com/kody-w/RAPP/blob/main/specs/README.md" in historical_spec,
        "published historical SPEC links to excluded specs/ paths",
    )
    ecosystem_html = (ROOT / "pages/about/ecosystem.html").read_text(encoding="utf-8")
    require("repo.id === 'rapp-zoo'" in ecosystem_html, "ecosystem must retire the rapp-zoo link")
    require("retired link" in ecosystem_html, "ecosystem must label the retired rapp-zoo reference")

    sitemap_root = ET.parse(ROOT / "sitemap.xml").getroot()
    namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    locations = [node.text or "" for node in sitemap_root.findall("sm:url/sm:loc", namespace)]
    require(len(locations) == len(set(locations)), "sitemap.xml contains duplicate URLs")
    for required in {
        f"{BASE_URL}/",
        f"{BASE_URL}/pages/",
        f"{BASE_URL}/pages/kernel.html",
        f"{BASE_URL}/pages/docs/",
    }:
        require(required in locations, f"sitemap.xml omitted current entrypoint {required}")

    banned_sitemap_prefixes = (
        f"{BASE_URL}/tests/",
        f"{BASE_URL}/worker/",
        f"{BASE_URL}/rapp_brainstem/",
        f"{BASE_URL}/cave/",
        f"{BASE_URL}/installer/",
        f"{BASE_URL}/pages/chat.html",
        f"{BASE_URL}/pages/lobby.html",
        f"{BASE_URL}/pages/payphone.html",
        f"{BASE_URL}/pages/summon.html",
        f"{BASE_URL}/pages/metropolis/",
        f"{BASE_URL}/pages/vbrainstem",
        f"{BASE_URL}/pages/vneighborhood.html",
        f"{BASE_URL}/pages/sphere.html",
        f"{BASE_URL}/pages/tether.html",
    )
    for location in locations:
        require(location.startswith(BASE_URL + "/"), f"sitemap URL outside project: {location}")
        require(
            not location.startswith(banned_sitemap_prefixes),
            f"sitemap exposes runtime, test, cave, or retired route: {location}",
        )
        parts = urlsplit(location)
        relative = unquote(parts.path[len("/RAPP/") :])
        if not relative:
            relative = "index.html"
        elif relative.endswith("/"):
            relative += "index.html"
        require(relative in published, f"sitemap URL is not published: {location}")
        parser = parsers.get(relative)
        if parser:
            require("noindex" not in parser.meta_robots, f"sitemap includes noindex page: {location}")

    robots_lines = [
        line.strip()
        for line in (ROOT / "robots.txt").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    sitemap_directives = [line.split(":", 1)[1].strip() for line in robots_lines if line.lower().startswith("sitemap:")]
    require(sitemap_directives == [f"{BASE_URL}/sitemap.xml"], "robots.txt must advertise the curated sitemap once")
    disallows = [line.split(":", 1)[1].strip() for line in robots_lines if line.lower().startswith("disallow:")]
    for required in {
        "/RAPP/tests/",
        "/RAPP/worker/",
        "/RAPP/rapp_brainstem/",
        "/RAPP/cave/rapplications/",
        "/RAPP/pages/_lib/",
    }:
        require(required in disallows, f"robots.txt omitted {required}")
    for location in locations:
        path = urlsplit(location).path
        require(
            not any(path.startswith(rule) for rule in disallows if rule),
            f"robots.txt disallows sitemap URL {location}",
        )

    if errors:
        print(f"FAIL: Pages validation found {len(errors)} defect(s):", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print(
        "PASS: Pages contract "
        f"({len(html_paths)} published HTML files, {len(entries)} classified pages, "
        f"{len(locations)} sitemap URLs)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
