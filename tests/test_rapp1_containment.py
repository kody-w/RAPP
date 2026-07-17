from __future__ import annotations

import hashlib
import importlib.util
import json
import stat
import subprocess
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]

RETIRED_HTML = (
    "pages/vbrainstem.html",
    "pages/vbrainstem/index.html",
    "pages/tether.html",
    "pages/vneighborhood.html",
    "pages/grail-brainstem/index.html",
    "pages/sphere.html",
    "rapp_swarm/index.html",
    "installer/plant.html",
    "installer/plant_qr.html",
    "installer/seed.html",
    "pages/metropolis/plant-from-discord.html",
)

HTML_EXECUTION_MARKERS = (
    "<script",
    "<iframe",
    "fetch(",
    "localstorage",
    "sessionstorage",
    "crypto.subtle",
    "new peer",
    "websocket",
    "/api/copilot/chat",
    "/chat/completions",
    "brainstem-egg/",
    "rapp-frame/",
    "http://",
    "https://",
)

RETIRED_SOURCE_MARKERS = {
    "installer/plant.sh": (
        "GRAIL_RAW=",
        "write_index_html()",
        "rapp-frame/1.0",
        "brainstem-egg/",
        "gh repo create",
        "git push",
    ),
    "cave/rapplications/rapp-installer/serve.py": (
        "import brainstem",
        "@brainstem.app.route",
        "brainstem.app.run",
        "/api/agent/",
    ),
    "cave/rapplications/rapp-installer/bootstrap.sh": (
        "cubby-rapp-installer.egg",
        "curl -fsSL",
        "hatch.py",
        "exec env",
    ),
    "cave/rapplications/rapp-installer/bootstrap.ps1": (
        "cubby-rapp-installer.egg",
        "Invoke-WebRequest",
        "hatch.py",
        "Compression.ZipFile",
    ),
    "cave/agents/cave_agent.py": (
        "CAVE_REPO",
        "subprocess",
        "git clone",
        "shutil.copy2",
        ".git/info/exclude",
    ),
    "tools/lan_advertise.py": (
        "_rapp-estate._tcp",
        "http.server",
        "dns-sd",
        "subprocess.Popen",
        "_stage_beacon",
    ),
    "tools/sign_release.py": (
        "cryptography",
        "private.pem",
        "Ed25519",
        "priv.sign",
        "pip install",
    ),
    "rapp_swarm/build.sh": (
        "rm -rf",
        "func azure functionapp publish",
        "rsync",
        "cp -R",
    ),
    "rapp_swarm/provision-twin.sh": (
        "az group create",
        "func azure functionapp publish",
        "azure deployment",
    ),
    "rapp_swarm/provision-twin-lite.sh": (
        "az group create",
        "func azure functionapp publish",
        "azure deployment",
    ),
    "tools/sim/loop_orchestrator.sh": (
        "tick_twin.py",
        "push_canvas.sh",
        "PUSH_CANVAS",
    ),
    "tools/sim/tick_twin.py": (
        "import subprocess",
        "call_claude",
        "execute_action",
    ),
    "tools/sim/push_canvas.sh": (
        "git add",
        "git commit",
        "git push",
    ),
    "deploy.sh": (
        "az login",
        "az group create",
        "az deployment",
        "azuredeploy.json",
    ),
    "installer/install-swarm.sh": (
        "git clone",
        "origin/main",
        "brainstem-swarm",
        "exec ",
    ),
    "installer/start-local.sh": (
        "http.server",
        "/tmp/",
        "rapp_brainstem/web/mobile",
        "kill -9",
    ),
    "installer/integration_plant.sh": (
        "gh repo",
        "git push",
        "curl ",
        "mktemp",
    ),
    "installer/hatchling": (
        "uuid.uuid4",
        "git fetch",
        "git merge",
        "git reset",
        "tarfile.open",
    ),
    "rapp_brainstem/tls_proxy.py": (
        "ThreadingHTTPServer",
        "0.0.0.0",
        "urllib.request.urlopen",
        "Access-Control-Allow-Origin",
        "openssl",
    ),
    "rapp_brainstem/start.sh": (
        "brainstem.py",
        "boot.py",
        "python",
        "pip",
        "venv",
        "exec ",
    ),
    "rapp_brainstem/start.ps1": (
        "brainstem.py",
        "boot.py",
        "python",
        "pip",
        "Start-Process",
    ),
    "rapp_brainstem/utils/boot.py": (
        "brainstem.py",
        "lineage_check",
        "import ",
        "__import__",
        "subprocess",
        "os.",
        "sys.",
        "exec",
    ),
}

EXPECTED_GRAIL_PINS = {
    "rapp_brainstem/brainstem.py": "a293dd9f11eef915bf15776f08c736faa60cb749820871b6753ea98233142a71",
    "rapp_brainstem/agents/basic_agent.py": "701488bc00d536a7b23295e7da99c62f24e9b00f233daa325886430c736b78eb",
    "rapp_brainstem/VERSION": "13eb74b44be6e3a85a0efa0dedf56aec05e9e50140e1c8bbc0d0fbd8097b0717",
}

EXPECTED_CAVE_KERNEL = {
    "cave/rapplications/rapp-installer/kernel/.env.example": "55fac1160314d2c68017fe8d700953dfa23ed01f151efa36f8462e6822ec143a",
    "cave/rapplications/rapp-installer/kernel/VERSION": "87b241b275c591694846560e9879f50c9da3150f854efdabd782c539772f3033",
    "cave/rapplications/rapp-installer/kernel/agents/.gitkeep": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "cave/rapplications/rapp-installer/kernel/agents/basic_agent.py": "701488bc00d536a7b23295e7da99c62f24e9b00f233daa325886430c736b78eb",
    "cave/rapplications/rapp-installer/kernel/brainstem.py": "f7fb359bbe8b6ba3db3665d81cb8e573a266c716278d8d21d8962ea40821e5aa",
    "cave/rapplications/rapp-installer/kernel/index.html": "06aec5d5b2697acf494ae513bc34d497cd5137c4070a401a573b3ba4e9473455",
    "cave/rapplications/rapp-installer/kernel/local_storage.py": "3ee38a68ef725a6ab7a0724d2bbe004fc5f7febd44e49119bbd94cc6f08cb96f",
    "cave/rapplications/rapp-installer/kernel/requirements.txt": "6bc9a8d661873b4cfd6681f8c94b0a347cfcf6fb3a463b19c45bdc4a9cb165ef",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ContainmentTests(unittest.TestCase):
    def test_browser_surfaces_are_static_tombstones(self):
        for relative in RETIRED_HTML:
            with self.subTest(path=relative):
                text = (ROOT / relative).read_text(encoding="utf-8")
                lowered = text.lower()
                self.assertIn("http 410", lowered)
                self.assertIn("rapp1_status.md", lowered)
                for marker in HTML_EXECUTION_MARKERS:
                    self.assertNotIn(marker, lowered)

    def test_retired_sources_contain_no_legacy_execution_markers(self):
        for relative, markers in RETIRED_SOURCE_MARKERS.items():
            with self.subTest(path=relative):
                text = (ROOT / relative).read_text(encoding="utf-8")
                self.assertIn("410 Gone", text)
                for marker in markers:
                    self.assertNotIn(marker, text)

    def test_cli_tombstones_fail_explicitly(self):
        commands = (
            ("bash", "installer/plant.sh"),
            (sys.executable, "cave/rapplications/rapp-installer/serve.py"),
            ("bash", "cave/rapplications/rapp-installer/bootstrap.sh"),
            (sys.executable, "tools/lan_advertise.py"),
            (sys.executable, "tools/sign_release.py", "sign"),
            ("bash", "rapp_swarm/build.sh"),
            ("bash", "rapp_swarm/provision-twin.sh"),
            ("bash", "rapp_swarm/provision-twin-lite.sh"),
            (sys.executable, "rapp_swarm/function_app.py"),
            (sys.executable, "tools/test_brainstem_server.py"),
            (sys.executable, "tools/front_door_specs.py"),
            (sys.executable, "tools/sim/plant_two_brainstems.py"),
            (sys.executable, "tools/sim/observe.py"),
            ("bash", "tools/sim/loop_orchestrator.sh"),
            (sys.executable, "tools/sim/tick_twin.py"),
            ("bash", "tools/sim/push_canvas.sh"),
            ("bash", "rapp_swarm/twin-sim.sh"),
            ("bash", "deploy.sh"),
            ("bash", "installer/install-swarm.sh"),
            ("bash", "installer/start-local.sh"),
            ("bash", "installer/integration_plant.sh"),
            (sys.executable, "installer/hatchling"),
            (sys.executable, "rapp_brainstem/tls_proxy.py"),
            ("bash", "rapp_brainstem/start.sh"),
            (sys.executable, "rapp_brainstem/utils/boot.py"),
        )
        for command in commands:
            with self.subTest(command=command):
                result = subprocess.run(
                    command,
                    cwd=ROOT,
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 78)
                self.assertIn("410 Gone", result.stderr)

    def test_retired_host_skill_is_not_a_rapp_capability(self):
        source = (
            ROOT / "community_rapp/agent-repo-skill.md"
        ).read_text(encoding="utf-8")
        self.assertIn("Retired — not a RAPP agent", source)
        self.assertIn("kody-w/rapp-skills", source)
        self.assertNotIn("Install an agent via chat", source)
        self.assertNotIn("public_gateway:", source)

    def test_cave_agent_always_refuses(self):
        agents = types.ModuleType("agents")
        basic_agent = types.ModuleType("agents.basic_agent")
        basic_agent.BasicAgent = object
        path = ROOT / "cave/agents/cave_agent.py"
        spec = importlib.util.spec_from_file_location("contained_cave_agent", path)
        module = importlib.util.module_from_spec(spec)
        with patch.dict(
            sys.modules,
            {"agents": agents, "agents.basic_agent": basic_agent},
        ):
            spec.loader.exec_module(module)
        with self.assertRaisesRegex(RuntimeError, "410 Gone"):
            module.CaveAgent().perform(action="load", verify=False)

    def test_worker_inference_proxy_is_absent(self):
        source = (ROOT / "worker/worker.js").read_text(encoding="utf-8")
        self.assertIn("p === '/api/copilot/chat'", source)
        self.assertIn("status: 410", source)
        self.assertIn("capability-route-retired", source)
        self.assertNotIn("/chat/completions", source)

    def test_tier2_deployment_guard_blocks_packaging(self):
        guard = json.loads(
            (ROOT / "rapp_swarm/RAPP1_DEPLOYMENT_GUARD.json").read_text()
        )
        self.assertEqual(guard["status"], "retired")
        self.assertIs(guard["rapp1_packaging_allowed"], False)
        self.assertIs(guard["rapp1_advertising_allowed"], False)
        self.assertEqual(guard["guidance"], "../RAPP1_STATUS.md")
        ignored = (ROOT / "rapp_swarm/.funcignore").read_text().splitlines()
        self.assertIn("function_app.py", ignored)
        for relative in (
            "rapp_swarm/function_app.py",
            "tools/test_brainstem_server.py",
            "tools/sim/loop_orchestrator.sh",
            "tools/sim/push_canvas.sh",
            "tools/sim/tick_twin.py",
        ):
            self.assertFalse((ROOT / relative).stat().st_mode & stat.S_IXUSR)

        readme = (ROOT / "tools/sim/README.md").read_text(encoding="utf-8")
        self.assertIn("non-executable historical", readme)
        self.assertNotIn("cron", readme.lower())
        self.assertNotIn("python3 tools/sim", readme)

    def test_target_owned_legacy_emitters_are_inert(self):
        function_source = (
            ROOT / "rapp_swarm/function_app.py"
        ).read_text(encoding="utf-8")
        server_source = (
            ROOT / "tools/test_brainstem_server.py"
        ).read_text(encoding="utf-8")
        template = (
            ROOT / "tools/templates/rapp_estate_grail.html"
        ).read_text(encoding="utf-8")
        self.assertNotIn("azure.functions", function_source)
        self.assertNotIn("assistant_" + "response", function_source)
        self.assertNotIn("HTTPServer", server_source)
        self.assertNotIn("rapp-chat-response", server_source)
        self.assertIn("410 Gone", template)
        self.assertNotIn("conversation_" + "history", template)

    def test_browser_chat_uses_only_exact_facade_envelopes(self):
        source = (ROOT / "rapp_brainstem/index.html").read_text(
            encoding="utf-8"
        )
        chat = source.split("async function sendMessage()", 1)[1]
        chat = chat.split("// ── Voice", 1)[0]
        self.assertIn(
            "const RAPP1_FACADE_CHAT = 'http://127.0.0.1:7073/chat'",
            source,
        )
        self.assertIn("const body = { user_input: text }", chat)
        self.assertIn("validateFacadeEnvelope(r, d)", chat)
        self.assertIn("d.error.code", chat)
        self.assertNotIn("conversation_" + "history", chat)
        self.assertNotIn("agent_logs_text", chat)
        self.assertNotIn("voice_response", chat)

    def test_browser_accepts_exact_logs_and_error_steps_safely(self):
        source = (ROOT / "rapp_brainstem/index.html").read_text(
            encoding="utf-8"
        )
        start = source.index("function logsToText")
        end = source.index("function appendMsg", start)
        validators = source[start:end]
        script = validators + r"""
const ok = status => ({status});
const success = logs => ({
  response: "done", agent_logs: logs, session_id: "session"
});
const refusal = step => ({error: {code: "candidate", step}});
if (validateFacadeEnvelope(ok(200), success([])) !== "success") process.exit(1);
if (validateFacadeEnvelope(ok(200), success(["first", "<b>second</b>"])) !== "success") process.exit(2);
if (logsToText(["first", "<b>second</b>"]) !== "first\n<b>second</b>") process.exit(3);
for (const step of [null, "1", "1a", "2", "3", "4", "5", "6"]) {
  if (validateFacadeEnvelope(ok(422), refusal(step)) !== "error") process.exit(4);
}
for (const invalid of [[{}], [1], ["ok", null]]) {
  try { validateFacadeEnvelope(ok(200), success(invalid)); process.exit(5); }
  catch (_) {}
}
for (const step of [1, "1A", "7", undefined]) {
  try { validateFacadeEnvelope(ok(422), refusal(step)); process.exit(6); }
  catch (_) {}
}
"""
        result = subprocess.run(
            ["node", "--input-type=module"],
            cwd=ROOT,
            input=script,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

        renderer = source[
            source.index("function appendMsg"):
            source.index("function appendTyping")
        ]
        self.assertIn("logBox.textContent = logs", renderer)
        self.assertIn("nameSpan.textContent", renderer)
        self.assertNotIn("label.innerHTML", renderer)

    def test_payphone_keeps_exact_rappid_parser_separate(self):
        source = (ROOT / "pages/payphone.html").read_text(encoding="utf-8")
        parser = source.split("function parseRappid", 1)[1]
        parser = parser.split("async function gh", 1)[0]
        self.assertIn("[0-9a-f]{64}", parser)
        self.assertIn("m[1].length > 39", parser)
        self.assertIn("m[2].length > 100", parser)
        self.assertIn("function parseRepoLocator", parser)
        self.assertIn("return parseRappid(s) || parseRepoLocator(s)", parser)
        self.assertNotIn("[a-f0-9]{32,64}", parser)

    def test_site_inventory_does_not_present_live_surfaces(self):
        manifest = json.loads((ROOT / "pages/_site/index.json").read_text())
        surface = next(s for s in manifest["sections"] if s["key"] == "surface")
        self.assertEqual(surface["label"], "Retired surfaces")
        self.assertTrue(all(p["title"].startswith("Retired ·") for p in surface["pages"]))
        for relative in (
            "pages/metropolis/index.html",
            "pages/metropolis/plant-from-discord.html",
        ):
            text = (ROOT / relative).read_text()
            self.assertNotIn('href="../vbrainstem/"', text)
            self.assertNotIn("/RAPP/pages/vbrainstem/", text)
            self.assertNotIn("/RAPP/pages/sphere.html", text)

    def test_pinned_grail_and_cave_kernel_bytes_are_unchanged(self):
        pin = json.loads((ROOT / "KERNEL_PIN.json").read_text())
        self.assertEqual(pin["kernel"]["frozen"], EXPECTED_GRAIL_PINS)
        for relative, expected in {
            **EXPECTED_GRAIL_PINS,
            **EXPECTED_CAVE_KERNEL,
        }.items():
            with self.subTest(path=relative):
                self.assertEqual(sha256(ROOT / relative), expected)

    def test_required_entrypoints_remain_executable(self):
        for relative in (
            "installer/plant.sh",
            "tools/sign_release.py",
            "rapp_swarm/build.sh",
            "rapp_swarm/provision-twin.sh",
            "rapp_swarm/provision-twin-lite.sh",
            "deploy.sh",
            "installer/install-swarm.sh",
            "installer/start-local.sh",
            "installer/integration_plant.sh",
        ):
            with self.subTest(path=relative):
                mode = (ROOT / relative).stat().st_mode
                self.assertTrue(mode & stat.S_IXUSR)


if __name__ == "__main__":
    unittest.main()
