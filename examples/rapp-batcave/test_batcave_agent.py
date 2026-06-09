"""Tests for the RAPP Batcave — scaffold grail + batcave_agent.py + planter.

The batcave is a standalone PRIVATE collaborator-gated neighborhood
(`kody-w/rapp-batcave`, the private-workspace visibility pattern) whose planted
quirk is the **cubby**: a per-member full workspace, per
PUBLIC_PRIVATE_BOUNDARY.md §1.8 (bones in the repo, substance on-device).

Spec citations the tests enforce:
  - god spec (specs/SPEC.md) §3 — the 9 canonical door files + .nojekyll + specs/ + README + soul
  - CONSTITUTION Art. XXXIV.1 — Eternity rappid `rappid:@<owner>/<slug>:<64hex>`
  - CONSTITUTION Art. XLVI.5/.6 — door_from_rappid is THE parser; parent_rappid set to planter
  - PUBLIC_PRIVATE_BOUNDARY §1.8.1/.8.2/.8.4 — bones-not-substance, .gitignore excludes PII paths
  - ANTIPATTERNS §1 — the unit is "agent" (no forbidden synonyms in batcave-authored prose)
  - ANTIPATTERNS §4 — soul.md Identity block, never "RAPP"-branded
  - ANTIPATTERNS §5 — agent degrades offline; no bare network in offline paths
  - rapp-rar-index/1.1 — sha256-pinned participation kit

Run from repo root:
    python3 -m pytest examples/rapp-batcave/test_batcave_agent.py -v
"""

import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent              # examples/rapp-batcave/
REPO_ROOT = HERE.parent.parent                       # the RAPP repo root
SCAFFOLD = HERE                                      # the scaffold IS this directory
AGENT_PATH = HERE / "agents" / "batcave_agent.py"
PLANTER_PATH = REPO_ROOT / "tools" / "plant_batcave.py"

OWNER = "kody-w"
SLUG = "rapp-batcave"
EXPECTED_RAPPID = f"rappid:@{OWNER}/{SLUG}:" + hashlib.sha256(f"{OWNER}/{SLUG}".encode()).hexdigest()
PARENT_RAPPID = "rappid:@kody-w/kody-twin:91d006ca7bd052bfa5021d623122012f"

# Kernel-shipped agents (rapp_brainstem/CLAUDE.md) — load must NEVER clobber these.
KERNEL_AGENTS = {
    "basic_agent.py", "context_memory_agent.py", "manage_memory_agent.py",
    "learn_new_agent.py", "swarm_factory_agent.py", "hacker_news_agent.py",
}

# The operator's cubby agents migrated out of the grail repo working tree.
KODY_CUBBY_AGENTS = {
    "clawpilot_twin_agent.py", "commons_agent.py", "schedule_reply_agent.py",
    "twin_me_agent.py", "workiq_agent.py",
}


def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    # Stub the brainstem import chain so the agent loads standalone.
    if "agents.basic_agent" not in sys.modules:
        stub = type(sys)("agents.basic_agent")

        class _Stub:
            def __init__(self, name="Agent", metadata=None):
                self.name = name
                self.metadata = metadata or {}

        stub.BasicAgent = _Stub
        sys.modules["agents"] = type(sys)("agents")
        sys.modules["agents.basic_agent"] = stub
    spec.loader.exec_module(mod)
    return mod


def _read_json(p):
    with open(p) as f:
        return json.load(f)


def _sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


# --------------------------------------------------------------------------
# 1. The scaffold grail
# --------------------------------------------------------------------------
class TestScaffoldGrail(unittest.TestCase):
    """The planted file set: god spec §3 + PUBLIC_PRIVATE_BOUNDARY §1.8.1."""

    REQUIRED = [
        "rappid.json", "neighborhood.json", "members.json", "card.json",
        "facets.json", "holo.md", "holo.svg", "holo-qr.svg", "index.html",
        ".nojekyll", "README.md", "CONTRIBUTING.md", "soul.md", ".gitignore",
        "rar/index.json",
        "specs/SPEC.md", "specs/skill.md", "specs/WORKSPACE_PROTOCOL.md",
        "specs/CUBBY_PROTOCOL.md",
        "events/SCHEMA.md",
        ".well-known/batcave.egg",
        ".github/CODEOWNERS", ".github/workflows/cubby-guard.yml",
        "agents/batcave_agent.py",
        "cubbies/index.json",
        "cubbies/_template/cubby.json", "cubbies/_template/front_door.md",
        "cubbies/kody-w/cubby.json", "cubbies/kody-w/front_door.md",
    ]

    def test_grail_files_present(self):
        missing = [p for p in self.REQUIRED if not (SCAFFOLD / p).exists()]
        self.assertEqual(missing, [], f"grail files missing from scaffold: {missing}")

    def test_rappid_eternity_format(self):
        r = _read_json(SCAFFOLD / "rappid.json")
        self.assertEqual(r["schema"], "rapp-rappid/2.0")
        self.assertEqual(r["rappid"], EXPECTED_RAPPID)
        self.assertRegex(r["rappid"], r"^rappid:@[A-Za-z0-9][A-Za-z0-9._-]*/[A-Za-z0-9][A-Za-z0-9._-]*:[a-f0-9]{64}$")
        self.assertEqual(r["kind"], "workspace")
        self.assertEqual(r["owner"], OWNER)
        self.assertEqual(r["repo"], SLUG)
        # Art. XLVI.6 — parent_rappid is the planter's personal rappid, never null.
        self.assertEqual(r["parent_rappid"], PARENT_RAPPID)

    def test_door_from_rappid_roundtrip(self):
        # Art. XLVI.5 — consumers import THE parser; the minted rappid must parse.
        sys.path.insert(0, str(REPO_ROOT / "tools"))
        try:
            import door_address
            door = door_address.door_from_rappid(EXPECTED_RAPPID)
            self.assertEqual(door["owner"], OWNER)
            self.assertEqual(door["slug"], SLUG)
        finally:
            sys.path.remove(str(REPO_ROOT / "tools"))

    def test_neighborhood_manifest(self):
        n = _read_json(SCAFFOLD / "neighborhood.json")
        self.assertEqual(n["schema"], "rapp-neighborhood/1.0")
        self.assertEqual(n["kind"], "workspace")
        self.assertEqual(n["visibility"], "private-workspace")
        self.assertEqual(n["neighborhood_rappid"], EXPECTED_RAPPID)
        self.assertIn("cubby", json.dumps(n).lower())
        self.assertIn("membership_policy", n)
        self.assertEqual(n["membership_policy"]["join_path"], "out_of_band")

    def test_members_roster(self):
        m = _read_json(SCAFFOLD / "members.json")
        self.assertEqual(m["schema"], "rapp-neighborhood-members/1.0")
        self.assertEqual(m["neighborhood_rappid"], EXPECTED_RAPPID)
        logins = [x["github_login"] for x in m["members"]]
        self.assertIn(OWNER, logins)
        founder = next(x for x in m["members"] if x["github_login"] == OWNER)
        self.assertEqual(founder["role"], "founder")
        self.assertEqual(m["reconciliation"]["policy"], "github_collaborators_api_is_canonical")

    def test_facets_private_scopes_only(self):
        f = _read_json(SCAFFOLD / "facets.json")
        self.assertEqual(f["schema"], "rapp-public-facets/1.0")
        # A private workspace asserts nothing at public scope except its join path.
        for facet in f["public_facets"]:
            self.assertIn(facet["scope"], ("neighborhood", "personal", "public"))
            if facet["scope"] == "public":
                self.assertIn(facet["name"], ("join_path", "neighborhood_purpose"))

    def test_card_holo_seed(self):
        sys.path.insert(0, str(REPO_ROOT / "tools"))
        try:
            import holo_card_generator as hcg
            card = _read_json(SCAFFOLD / "card.json")
            self.assertEqual(card["schema"], "rappcards/1.1.2")
            self.assertEqual(card["meta"]["rappid"], EXPECTED_RAPPID)
            self.assertEqual(int(card["seed"]), hcg.derive_seed(EXPECTED_RAPPID))
            self.assertEqual(card["incantation"], hcg.seed_to_words(hcg.derive_seed(EXPECTED_RAPPID)))
        finally:
            sys.path.remove(str(REPO_ROOT / "tools"))

    def test_rar_index_sha256_pins(self):
        rar = _read_json(SCAFFOLD / "rar" / "index.json")
        self.assertEqual(rar["schema"], "rapp-rar-index/1.1")
        self.assertEqual(rar["neighborhood_rappid"], EXPECTED_RAPPID)
        names = []
        for entry in rar["agents"]:
            names.append(entry["name"])
            if "path" in entry and entry.get("sha256"):
                actual = _sha256(SCAFFOLD / entry["path"])
                self.assertEqual(entry["sha256"], actual,
                                 f"rar sha256 drift for {entry['path']}")
        self.assertIn("@kody-w/batcave", names)
        bat = next(e for e in rar["agents"] if e["name"] == "@kody-w/batcave")
        self.assertTrue(bat["required_by_tether"])

    def test_soul_identity_block(self):
        soul = (SCAFFOLD / "soul.md").read_text()
        self.assertIn("## Identity — read this every turn", soul)
        self.assertIn("The Batcave", soul)
        # ANTIPATTERNS §4 — the block must forbid default-platform branding.
        self.assertIn('"RAPP"', soul)
        self.assertIn("an AI assistant", soul)

    def test_gitignore_excludes_substance(self):
        # PUBLIC_PRIVATE_BOUNDARY §1.8.2/.8.4 — PII + secrets never enter the repo.
        gi = (SCAFFOLD / ".gitignore").read_text()
        for pat in (".brainstem/", ".brainstem_data/", ".env", ".copilot_token",
                    ".copilot_session", ".lineage_key", "keys/", "__pycache__/"):
            self.assertIn(pat, gi, f".gitignore missing {pat}")

    def test_public_template_is_bones_only(self):
        # The public scaffold (kody-w/RAPP examples/) must NOT carry the
        # operator's real agents — those go to the PRIVATE repo only, which is
        # the entire point (keep them out of the public grail repo). The
        # founder cubby exists but ships zero agent files here.
        cubby_agents = SCAFFOLD / "cubbies" / "kody-w" / "agents"
        present = {p.name for p in cubby_agents.glob("*_agent.py")}
        self.assertEqual(present, set(),
                         f"public template leaks real agents: {present}")
        self.assertTrue((cubby_agents / ".gitkeep").exists())

    def test_cubby_json_shape(self):
        c = _read_json(SCAFFOLD / "cubbies" / "kody-w" / "cubby.json")
        self.assertEqual(c["schema"], "rapp-batcave-cubby/1.0")
        self.assertEqual(c["github_login"], OWNER)
        for key in ("rappid", "display_name", "what_im_cooking", "created_at"):
            self.assertIn(key, c)
        idx = _read_json(SCAFFOLD / "cubbies" / "index.json")
        self.assertEqual(idx["schema"], "rapp-batcave-cubbies/1.0")
        self.assertIn(OWNER, [e["github_login"] for e in idx["cubbies"]])

    def test_cubby_is_estate_housing(self):
        # A cubby houses a FULL rapp estate bottom-to-top — the same anatomy as
        # an on-device brainstem (agents / organs / senses / rapplications /
        # neighborhoods / eggs), so members learn from each other's whole
        # organism as it grows. (Operator direction, 2026-06-09.)
        template = SCAFFOLD / "cubbies" / "_template"
        for anatomy in ("agents", "organs", "senses", "rapplications",
                        "neighborhoods", "eggs", "show-and-tell"):
            self.assertTrue((template / anatomy).is_dir(),
                            f"cubby template missing estate-anatomy dir {anatomy}/")
        proto = (SCAFFOLD / "specs" / "CUBBY_PROTOCOL.md").read_text()
        self.assertIn("estate", proto.lower())
        for anatomy in ("organs", "senses", "rapplications", "neighborhoods"):
            self.assertIn(anatomy, proto)

    def test_events_schema_doc(self):
        doc = (SCAFFOLD / "events" / "SCHEMA.md").read_text()
        self.assertIn("rapp-batcave-event/1.0", doc)
        self.assertIn("(from, ts)", doc)           # the universal merge key
        self.assertIn("show-and-tell", doc)

    def test_invite_egg(self):
        egg = _read_json(SCAFFOLD / ".well-known" / "batcave.egg")
        self.assertEqual(egg["schema"], "brainstem-egg/2.3-neighborhood")
        self.assertEqual(egg["type"], "neighborhood-invite")
        self.assertEqual(egg["rappid"], EXPECTED_RAPPID)
        self.assertIn("collaborator", json.dumps(egg).lower())

    def test_cubby_guard_workflow(self):
        wf = (SCAFFOLD / ".github" / "workflows" / "cubby-guard.yml").read_text()
        self.assertIn("cubbies/", wf)
        self.assertIn("github.actor", wf.replace("${{ ", "").replace(" }}", "").replace("${{", ""))

    def test_codeowners_per_cubby(self):
        co = (SCAFFOLD / ".github" / "CODEOWNERS").read_text()
        self.assertIn(f"/cubbies/{OWNER}/ @{OWNER}", co)

    def test_no_public_front_door(self):
        # "the batcave should not have a public front door... because it's
        # the batcave" — invisible to outsiders (404), dialed via payphone.
        r = _read_json(SCAFFOLD / "rappid.json")
        self.assertIsNone(r["url"])
        n = _read_json(SCAFFOLD / "neighborhood.json")
        self.assertIsNone(n["url"])
        self.assertEqual(n["front_door"], "none-by-design")
        self.assertIn("payphone", n["addresses"])
        self.assertIn("payphone.html", n["addresses"]["payphone"])

    def test_payphone_is_public_and_generic(self):
        # The payphone is a GENERIC private-door dialer on the public web.
        # It must never name any specific private neighborhood — outsiders
        # learn nothing; authenticated collaborators dial by rappid.
        payphone = REPO_ROOT / "pages" / "payphone.html"
        self.assertTrue(payphone.exists(), "pages/payphone.html missing")
        html = payphone.read_text()
        self.assertNotIn("rapp-batcave", html, "payphone leaks a private door name")
        self.assertNotIn("batcave", html.lower(), "payphone leaks a private door name")
        self.assertIn("api.github.com", html)          # dials with caller's auth
        self.assertIn("rapp_settings", html)            # Doorman token convention
        self.assertIn("404", html)                       # wrong-number = no-access
        # local-first discipline: no bare raw.githubusercontent fetch paths
        self.assertNotIn("raw.githubusercontent.com", html)

    def test_invite_egg_carries_payphone(self):
        egg = _read_json(SCAFFOLD / ".well-known" / "batcave.egg")
        self.assertIn("payphone", egg)
        self.assertIn("payphone.html", egg["payphone"])

    def test_cubby_protocol_documents_payphone(self):
        proto = (SCAFFOLD / "specs" / "CUBBY_PROTOCOL.md").read_text()
        self.assertIn("payphone", proto.lower())
        self.assertIn("404", proto)

    def test_antipattern_vocabulary(self):
        # ANTIPATTERNS §1 — batcave-authored prose says "agent", never the synonyms.
        # (specs/SPEC.md + specs/skill.md are canon copies — exempt by name.)
        forbidden = re.compile(r"\b(plugin|cassette)s?\b", re.IGNORECASE)
        for rel in ("README.md", "CONTRIBUTING.md", "specs/CUBBY_PROTOCOL.md",
                    "agents/batcave_agent.py", "holo.md"):
            text = (SCAFFOLD / rel).read_text()
            self.assertIsNone(forbidden.search(text), f"forbidden unit-synonym in {rel}")


# --------------------------------------------------------------------------
# 2. The agent — contract
# --------------------------------------------------------------------------
class TestAgentContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load_module("batcave_agent_contract", AGENT_PATH)

    def test_manifest(self):
        m = self.mod.__manifest__
        self.assertEqual(m["schema"], "rapp-agent/1.0")
        self.assertEqual(m["name"], "@kody-w/batcave")

    def test_metadata_and_perform(self):
        a = self.mod.BatcaveAgent()
        self.assertEqual(a.metadata["name"], "BatcaveAgent")
        props = a.metadata["parameters"]["properties"]
        actions = set(props["action"]["enum"])
        for needed in ("protocol", "help", "status", "mount", "join", "browse",
                       "stash", "show_and_tell", "load", "unload", "sync",
                       "branch", "invite"):
            self.assertIn(needed, actions)
        out = a.perform(action="help")
        self.assertIsInstance(out, str)
        self.assertIn("cubby", out.lower())

    def test_protocol_offline(self):
        a = self.mod.BatcaveAgent()
        out = a.perform(action="protocol")
        self.assertIn(EXPECTED_RAPPID, out)
        self.assertIn("private", out.lower())


# --------------------------------------------------------------------------
# 3. The agent — offline behavior against fixtures
# --------------------------------------------------------------------------
class TestAgentOffline(unittest.TestCase):
    """Every action exercised with _repo_dir/_home_dir/_brainstem_dir hooks —
    zero network, zero gh (ANTIPATTERNS §5 discipline is testable offline)."""

    def setUp(self):
        self.mod = _load_module("batcave_agent_offline", AGENT_PATH)
        self.tmp = Path(tempfile.mkdtemp())
        # fake operator home
        self.home = self.tmp / "home"
        (self.home / ".brainstem").mkdir(parents=True)
        (self.home / ".brainstem" / "rappid.json").write_text(json.dumps({
            "schema": "rapp-rappid/3.0",
            "rappid": "rappid:cafe0123cafe0123cafe0123cafe0123",
            "owner": "@testuser", "kind": "operator",
        }))
        # fake clone of the batcave (a trimmed scaffold copy)
        self.repo = self.tmp / "clone"
        for rel in ("rappid.json", "neighborhood.json", "members.json",
                    "cubbies/index.json", "cubbies/_template/cubby.json",
                    "cubbies/_template/front_door.md", "events/SCHEMA.md"):
            src = SCAFFOLD / rel
            dst = self.repo / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        # a peer cubby with a streamable agent
        peer = self.repo / "cubbies" / "kody-w" / "agents"
        peer.mkdir(parents=True)
        (self.repo / "cubbies" / "kody-w" / "cubby.json").write_text(json.dumps({
            "schema": "rapp-batcave-cubby/1.0", "github_login": "kody-w",
            "rappid": PARENT_RAPPID, "display_name": "Kody",
            "what_im_cooking": "tests", "created_at": "2026-06-09T00:00:00Z",
        }))
        (peer / "demo_ping_agent.py").write_text(
            "class DemoPingAgent:\n    def perform(self, **kw):\n        return 'pong'\n")
        (peer / "basic_agent.py").write_text("# malicious kernel clobber attempt\n")
        # fake target brainstem inside a git repo (for .git/info/exclude streaming)
        self.bs = self.tmp / "brainstem"
        (self.bs / "agents").mkdir(parents=True)
        (self.bs / "agents" / "basic_agent.py").write_text("# KERNEL FILE — sacred\n")
        subprocess.run(["git", "init", "-q", str(self.bs)], check=True,
                       capture_output=True)
        self.kw = dict(_home_dir=str(self.home), _repo_dir=str(self.repo),
                       _handle="testuser")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _do(self, action, **extra):
        a = self.mod.BatcaveAgent()
        out = a.perform(action=action, **{**self.kw, **extra})
        try:
            return json.loads(out)
        except (json.JSONDecodeError, ValueError):
            return {"_raw": out}

    def test_status_reports_identity_and_mount(self):
        env = self._do("status")
        self.assertEqual(env["schema"], "rapp-batcave-result/1.0")
        self.assertIn("rappid:cafe0123", json.dumps(env))
        self.assertTrue(env["mounted"])

    def test_join_creates_cubby_and_roster_entry(self):
        env = self._do("join", what_im_cooking="trying the batcave")
        self.assertEqual(env["status"], "success")
        cubby = self.repo / "cubbies" / "testuser"
        self.assertTrue((cubby / "cubby.json").exists())
        self.assertTrue((cubby / "front_door.md").exists())
        self.assertTrue((cubby / "agents").is_dir())
        self.assertTrue((cubby / "show-and-tell").is_dir())
        members = _read_json(self.repo / "members.json")
        self.assertIn("testuser", [m["github_login"] for m in members["members"]])
        idx = _read_json(self.repo / "cubbies" / "index.json")
        self.assertIn("testuser", [e["github_login"] for e in idx["cubbies"]])

    def test_join_is_idempotent(self):
        self._do("join")
        env2 = self._do("join")
        self.assertIn(env2["status"], ("success", "already_joined"))
        members = _read_json(self.repo / "members.json")
        logins = [m["github_login"] for m in members["members"]]
        self.assertEqual(logins.count("testuser"), 1)

    def test_browse_lists_cubbies(self):
        env = self._do("browse")
        handles = [c["github_login"] for c in env["cubbies"]]
        self.assertIn("kody-w", handles)

    def test_stash_into_own_cubby(self):
        self._do("join")
        src = self.tmp / "my_cool_agent.py"
        src.write_text("class MyCoolAgent:\n    pass\n")
        env = self._do("stash", path=str(src))
        self.assertEqual(env["status"], "success")
        self.assertTrue((self.repo / "cubbies" / "testuser" / "agents" / "my_cool_agent.py").exists())

    def test_stash_refuses_other_cubby(self):
        self._do("join")
        src = self.tmp / "sneaky_agent.py"
        src.write_text("# sneaky\n")
        env = self._do("stash", path=str(src), cubby="kody-w")
        self.assertEqual(env["status"], "refused")
        self.assertFalse((self.repo / "cubbies" / "kody-w" / "agents" / "sneaky_agent.py").exists())

    def test_stash_refuses_secrets(self):
        self._do("join")
        for bad in (".env", ".copilot_token", ".lineage_key", "private-estate-secret"):
            src = self.tmp / bad
            src.write_text("SECRET=1\n")
            env = self._do("stash", path=str(src))
            self.assertEqual(env["status"], "refused", f"{bad} should be refused")

    def test_show_and_tell_writes_post_and_event(self):
        self._do("join")
        env = self._do("show_and_tell", title="My twin does R&D while I sleep",
                       text="hooked up the overnight loop")
        self.assertEqual(env["status"], "success")
        posts = list((self.repo / "cubbies" / "testuser" / "show-and-tell").glob("*.md"))
        self.assertEqual(len(posts), 1)
        events = list((self.repo / "events").glob("*.json"))
        self.assertEqual(len(events), 1)
        ev = _read_json(events[0])
        self.assertEqual(ev["schema"], "rapp-batcave-event/1.0")
        self.assertEqual(ev["kind"], "show-and-tell")
        self.assertTrue(ev["from"].startswith("rappid:"))
        # Signed when crypto available; explicit signing intent otherwise.
        self.assertTrue(("sig" in ev) or env.get("signing_intent"))

    def test_event_signature_verifies(self):
        try:
            import cryptography  # noqa: F401
        except ImportError:
            self.skipTest("cryptography not installed")
        self._do("join")
        self._do("show_and_tell", title="t", text="x")
        ev = _read_json(next((self.repo / "events").glob("*.json")))
        self.assertTrue(self.mod._verify_event(ev))

    def test_load_streams_cubby_agents(self):
        env = self._do("load", cubby="kody-w", _brainstem_dir=str(self.bs))
        self.assertEqual(env["status"], "success")
        self.assertTrue((self.bs / "agents" / "demo_ping_agent.py").exists())
        # streamed files are git-invisible: registered in .git/info/exclude
        exclude = (self.bs / ".git" / "info" / "exclude").read_text()
        self.assertIn("agents/demo_ping_agent.py", exclude)
        # loadout manifest written under the cache root
        loadout = _read_json(self.home / ".brainstem" / "neighborhoods" /
                             "rapp-batcave" / "loadout.json")
        self.assertEqual(loadout["schema"], "rapp-batcave-loadout/1.0")
        files = [e["file"] for e in loadout["loaded"]]
        self.assertIn("demo_ping_agent.py", files)

    def test_load_never_clobbers_kernel(self):
        before = (self.bs / "agents" / "basic_agent.py").read_text()
        env = self._do("load", cubby="kody-w", _brainstem_dir=str(self.bs))
        self.assertEqual((self.bs / "agents" / "basic_agent.py").read_text(), before)
        self.assertIn("basic_agent.py", json.dumps(env.get("skipped", [])))

    def test_load_idempotent_no_duplicate_excludes(self):
        self._do("load", cubby="kody-w", _brainstem_dir=str(self.bs))
        self._do("load", cubby="kody-w", _brainstem_dir=str(self.bs))
        exclude = (self.bs / ".git" / "info" / "exclude").read_text()
        self.assertEqual(exclude.count("agents/demo_ping_agent.py"), 1)

    def test_unload_removes_only_streamed(self):
        self._do("load", cubby="kody-w", _brainstem_dir=str(self.bs))
        env = self._do("unload", _brainstem_dir=str(self.bs))
        self.assertEqual(env["status"], "success")
        self.assertFalse((self.bs / "agents" / "demo_ping_agent.py").exists())
        self.assertTrue((self.bs / "agents" / "basic_agent.py").exists())
        exclude = (self.bs / ".git" / "info" / "exclude").read_text()
        self.assertNotIn("demo_ping_agent.py", exclude)

    def test_sync_reports_new_show_and_tell(self):
        self._do("sync")  # set the marker
        post = self.repo / "cubbies" / "kody-w" / "show-and-tell" / "2026-06-09-new.md"
        post.parent.mkdir(parents=True, exist_ok=True)
        post.write_text("# new thing\n")
        env = self._do("sync")
        self.assertIn("2026-06-09-new.md", json.dumps(env))

    def test_invite_is_dry_run_by_default(self):
        env = self._do("invite", github_login="billwhalen")
        self.assertEqual(env["status"], "dry_run")
        self.assertIn("gh api", json.dumps(env))
        self.assertIn("billwhalen", json.dumps(env))

    def test_load_defaults_to_kody_w_when_member_has_no_cubby(self):
        # documented fallback: a member who hasn't joined streams from kody-w
        env = self._do("load", _brainstem_dir=str(self.bs))   # no cubby arg
        self.assertEqual(env["status"], "success")
        self.assertEqual(env["from_cubby"], "kody-w")
        self.assertTrue((self.bs / "agents" / "demo_ping_agent.py").exists())

    def test_load_refuses_path_traversal_cubby(self):
        env = self._do("load", cubby="../../../../tmp",
                       _brainstem_dir=str(self.bs))
        self.assertEqual(env["status"], "error")
        self.assertIn("unsafe", json.dumps(env).lower())

    def test_load_skips_local_nonstreamed_collision(self):
        # a member's OWN agent file sharing a cubby agent's name is never
        # silently overwritten (member-data guarantee)
        mine = self.bs / "agents" / "demo_ping_agent.py"
        mine.write_text("# MY OWN local agent — do not clobber\n")
        env = self._do("load", cubby="kody-w", _brainstem_dir=str(self.bs))
        self.assertIn("# MY OWN local agent", mine.read_text())
        self.assertIn("demo_ping_agent.py", json.dumps(env.get("skipped", [])))

    def test_unload_kernel_guard_on_corrupted_loadout(self):
        # a hand-edited/corrupted loadout must never delete a kernel agent
        loadout = self.home / ".brainstem" / "neighborhoods" / "rapp-batcave" / "loadout.json"
        loadout.parent.mkdir(parents=True, exist_ok=True)
        loadout.write_text(json.dumps({
            "schema": "rapp-batcave-loadout/1.0",
            "loaded": [{"file": "basic_agent.py", "sha256": "x",
                        "from_cubby": "evil", "loaded_at": "t",
                        "target": str(self.bs / "agents")}]}))
        env = self._do("unload", _brainstem_dir=str(self.bs))
        self.assertTrue((self.bs / "agents" / "basic_agent.py").exists(),
                        "unload deleted a kernel agent from a corrupted loadout")
        self.assertNotIn("basic_agent.py", json.dumps(env.get("removed", [])))

    def test_branch_dry_run_offline(self):
        env = self._do("branch", topic="Overnight R&D")
        self.assertEqual(env["status"], "dry_run")
        self.assertEqual(env["branch"], "cubby/testuser/overnight-r-d")
        self.assertIn("checkout -b", json.dumps(env))

    def test_stash_refuses_ssh_and_cert_shapes(self):
        self._do("join")
        for bad in ("id_rsa", "id_ed25519", "server.key", "cert.p12",
                    ".netrc", "deploy.pfx"):
            src = self.tmp / bad
            src.write_text("x\n")
            env = self._do("stash", path=str(src))
            self.assertEqual(env["status"], "refused", f"{bad} not refused")

    def test_not_mounted_guard(self):
        empty = self.tmp / "empty-clone"
        empty.mkdir()
        a = self.mod.BatcaveAgent()
        out = json.loads(a.perform(action="browse", _home_dir=str(self.home),
                                   _repo_dir=str(empty), _handle="testuser"))
        self.assertEqual(out["status"], "error")
        self.assertIn("not mounted", out["error"].lower())

    def test_mount_offline_reports_cache(self):
        env = self._do("mount")
        self.assertEqual(env["status"], "success")
        self.assertTrue(env["mounted"])


# --------------------------------------------------------------------------
# 4. The planter — idempotence
# --------------------------------------------------------------------------
class TestPlanter(unittest.TestCase):
    def test_replant_preserves_rappid_and_refreshes_pins(self):
        mod = _load_module("plant_batcave", PLANTER_PATH)
        out = Path(tempfile.mkdtemp()) / "batcave"
        try:
            mod.plant(out_dir=str(out))
            r1 = _read_json(out / "rappid.json")
            # mutate an agent, replant: rappid stable, sha pins refresh
            agent = out / "agents" / "batcave_agent.py"
            agent.write_text(agent.read_text() + "\n# replant probe\n")
            mod.plant(out_dir=str(out))
            r2 = _read_json(out / "rappid.json")
            self.assertEqual(r1["rappid"], r2["rappid"])
            self.assertEqual(r1["minted_at"], r2["minted_at"])
            rar = _read_json(out / "rar" / "index.json")
            bat = next(e for e in rar["agents"] if e["name"] == "@kody-w/batcave")
            self.assertEqual(bat["sha256"], _sha256(agent))
        finally:
            shutil.rmtree(out.parent, ignore_errors=True)

    def test_default_plant_is_bones_only(self):
        # default (public template) ships no real agents in the founder cubby
        mod = _load_module("plant_batcave_b", PLANTER_PATH)
        out = Path(tempfile.mkdtemp()) / "batcave"
        try:
            res = mod.plant(out_dir=str(out))
            self.assertEqual(res["kody_cubby_agents_migrated"], [])
            agents = list((out / "cubbies" / "kody-w" / "agents").glob("*_agent.py"))
            self.assertEqual(agents, [])
        finally:
            shutil.rmtree(out.parent, ignore_errors=True)

    def test_seeded_plant_populates_founder_cubby(self):
        # the private-instance plant (--seed-agents) copies the live agents
        mod = _load_module("plant_batcave_s", PLANTER_PATH)
        out = Path(tempfile.mkdtemp()) / "batcave"
        try:
            res = mod.plant(out_dir=str(out), seed_agents=True)
            present = {p.name for p in
                       (out / "cubbies" / "kody-w" / "agents").glob("*_agent.py")}
            for name in KODY_CUBBY_AGENTS:
                live = REPO_ROOT / "rapp_brainstem" / "agents" / name
                if live.exists():
                    self.assertIn(name, present)
                    self.assertIn(name, res["kody_cubby_agents_migrated"])
                    # rar pins the streamed cubby agent
                    rar = _read_json(out / "rar" / "index.json")
                    pin = next((e for e in rar["agents"]
                                if e.get("path", "").endswith(name)), None)
                    self.assertIsNotNone(pin)
                    self.assertEqual(pin["sha256"], _sha256(
                        out / "cubbies" / "kody-w" / "agents" / name))
        finally:
            shutil.rmtree(out.parent, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
