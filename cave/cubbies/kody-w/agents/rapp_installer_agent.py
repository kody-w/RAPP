"""
rapp_installer_agent.py — drop-in agent for the self-contained RAPP Installer
rapplication (PUBLIC cave edition).

Drop this into ANY unmodified brainstem's agents/ directory (it depends only on
agents.basic_agent + stdlib) and the LLM gets a `RappInstaller` tool that can:
report whether the repo-independent brainstem cubby is hatched, hand back the
PUBLIC one-line bootstrap command (plain curl — no auth) to stand it up from the
public RAPP cave, ping its health endpoint, and point at the relevant paths.

It NEVER reads, writes, or runs anything inside ~/.brainstem/src (the grail).
"""
import json
import os
import urllib.request

from agents.basic_agent import BasicAgent

SLUG = "rapp-installer"
BRAINSTEM = os.path.expanduser("~/.brainstem")
CUBBY = os.path.join(BRAINSTEM, "cubbies", SLUG)
RAPP = os.path.join(CUBBY, "rapplications", SLUG)
# PUBLIC cave: anyone can curl it, no GitHub auth required.
ONE_LINER = "curl -fsSL https://kody-w.github.io/RAPP/cave/rapplications/rapp-installer/bootstrap.sh | bash"
CAVE_URL = "https://kody-w.github.io/RAPP/cave/"


class RappInstallerAgent(BasicAgent):
    def __init__(self):
        self.name = "RappInstaller"
        self.metadata = {
            "name": self.name,
            "description": (
                "Manage the self-contained, repo-independent RAPP Installer "
                "rapplication (the brainstem ported out of the grail repo so it "
                "can't be accidentally committed to). Use to check whether it is "
                "hatched locally, get the PUBLIC one-line command to stand it up "
                "from the public RAPP cave (kody-w.github.io/RAPP/cave), ping its "
                "health endpoint, or show its paths."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["status", "bootstrap_command", "health", "paths"],
                        "description": (
                            "status = is the rapplication hatched locally and what's present; "
                            "bootstrap_command = return the PUBLIC plain-curl one-liner (no auth) "
                            "that pulls the egg from the public RAPP cave and stands up a running "
                            "brainstem with zero grail-commit risk; health = GET the running "
                            "rapplication's /health; paths = on-disk locations (cubby, rapplication, "
                            "bundled kernel)."
                        ),
                    },
                    "port": {
                        "type": "integer",
                        "description": (
                            "Port to probe for action=health. The rapplication defaults to 7077 "
                            "(chosen so it coexists with a grail brainstem on 7071). Default 7077."
                        ),
                    },
                },
                "required": ["action"],
            },
        }

    def perform(self, **kwargs):
        action = (kwargs.get("action") or "status").strip()
        if action == "bootstrap_command":
            return json.dumps({
                "one_liner": ONE_LINER,
                "public_home": CAVE_URL,
                "note": "Public — no GitHub auth needed. Hatches into "
                        f"{CUBBY} (a non-git cubby) and launches serve.py on :7077. Never touches the grail.",
            }, indent=2)

        if action == "paths":
            return json.dumps({
                "cubby": CUBBY,
                "rapplication": RAPP,
                "bundled_kernel": os.path.join(RAPP, "kernel"),
                "serve": os.path.join(RAPP, "serve.py"),
                "egg_shelf": os.path.join(BRAINSTEM, "eggs", f"cubby-{SLUG}.egg"),
                "public_home": CAVE_URL,
                "grail_NEVER_touched": os.path.join(BRAINSTEM, "src", "rapp_brainstem"),
            }, indent=2)

        if action == "health":
            port = int(kwargs.get("port") or 7077)
            try:
                with urllib.request.urlopen(f"http://localhost:{port}/health", timeout=5) as r:
                    return json.dumps({"up": True, "port": port, "health": json.loads(r.read())}, indent=2)
            except Exception as e:
                return json.dumps({"up": False, "port": port, "error": str(e),
                                   "hint": f"start it: python3 {os.path.join(RAPP, 'serve.py')}"}, indent=2)

        # default: status
        hatched = os.path.isfile(os.path.join(RAPP, "serve.py"))
        kernel_ok = os.path.isfile(os.path.join(RAPP, "kernel", "brainstem.py"))
        egg = os.path.join(BRAINSTEM, "eggs", f"cubby-{SLUG}.egg")
        return json.dumps({
            "hatched": hatched,
            "cubby": CUBBY if os.path.isdir(CUBBY) else None,
            "bundled_kernel_present": kernel_ok,
            "egg_on_shelf": egg if os.path.isfile(egg) else None,
            "public_home": CAVE_URL,
            "repo_independent": True,
            "grail_commit_risk": False,
            "next": ("run it: python3 %s" % os.path.join(RAPP, "serve.py")) if hatched
                    else ("not hatched — bootstrap: %s" % ONE_LINER),
        }, indent=2)
