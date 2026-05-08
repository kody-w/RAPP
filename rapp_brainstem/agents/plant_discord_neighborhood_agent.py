"""plant_discord_neighborhood_agent.py — one-shot agent to plant a new RAPP
neighborhood whose human collaboration surface is a Discord channel.

Drop this file into your brainstem's `agents/` directory. Then ask your
brainstem to plant a neighborhood and give it a Discord webhook URL —
this agent does everything end to end:

  1. Validates inputs (name, webhook URL, optional template)
  2. Mints a fresh neighborhood_rappid (UUIDv4)
  3. Fetches the chosen template's seed content from raw.githubusercontent.com
  4. Customizes neighborhood.json with the new rappid, name, github URL,
     and a `discord` block linking the planted neighborhood to the channel
  5. Creates the new GitHub repo via the GitHub API (POST /user/repos)
  6. Uploads each file via the contents API (PUT /repos/<o>/<r>/contents/<path>)
  7. POSTs a welcome message to the Discord webhook so members can subscribe:
       brainstem join https://github.com/<owner>/<name>
  8. Returns the planted URLs + the gate-page CTA + the brainstem-join command

REQUIREMENTS:
  - Environment variable GITHUB_TOKEN (or GH_TOKEN) with `repo` scope
  - The seed template repo (default: kody-w/braintrust-template) must be
    public on GitHub for raw fetching

NO gh CLI required. Pure stdlib. Drop and use.

Pass `dry_run=true` to simulate everything WITHOUT creating a repo or
posting to Discord — useful for testing input flow."""
import base64
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

from agents.basic_agent import BasicAgent


GH_API = "https://api.github.com"
RAW = "https://raw.githubusercontent.com"


# Files we copy from the chosen template into the new neighborhood.
TEMPLATE_FILES = [
    "neighborhood.json",
    "card.json",
    "facets.json",
    "README.md",
    ".gitignore",
    "agents/__init__.py",
    "agents/basic_agent.py",
]

# Per-template extra files (the agents that make the pattern actually work).
TEMPLATE_EXTRA_FILES = {
    "braintrust-template": [
        "agents/braintrust_request_agent.py",
        "agents/library_query_agent.py",
        "agents/braintrust_contribute_agent.py",
        "agents/braintrust_synthesize_agent.py",
        "agents/braintrust_cite_agent.py",
        "members.json",
    ],
    "private-workspace-template": [
        "agents/workspace_init_agent.py",
        "agents/workspace_decision_agent.py",
        "agents/workspace_invite_agent.py",
        "agents/workspace_inbox_agent.py",
        "members.json",
    ],
    "public-art-collective": [
        "agents/art_submit_agent.py",
        "agents/art_curate_agent.py",
        "agents/art_vote_agent.py",
        "agents/art_remix_agent.py",
        "submissions/index.json",
        "index.html",
        ".nojekyll",
    ],
}


def _gh_token():
    return os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""


def _gh_request(method, path, body=None):
    token = _gh_token()
    headers = {
        "User-Agent": "rapp-plant-discord-neighborhood",
        "Accept": "application/vnd.github+json",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(
        path if path.startswith("http") else GH_API + path,
        data=data, method=method, headers=headers,
    )
    try:
        with urllib.request.urlopen(req, timeout=15.0) as r:
            payload = r.read()
            try:
                return json.loads(payload.decode("utf-8")), r.status
            except (ValueError, UnicodeDecodeError):
                return {"raw": payload.decode("utf-8", errors="replace")}, r.status
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read().decode("utf-8")), e.code
        except Exception:
            return {"error": str(e)}, e.code
    except (urllib.error.URLError, OSError, TimeoutError) as e:
        return {"error": str(e)}, 0


def _fetch_raw(slug, branch, path):
    url = f"{RAW}/{slug}/{branch}/{path}"
    req = urllib.request.Request(url, headers={"User-Agent": "rapp-plant"})
    try:
        with urllib.request.urlopen(req, timeout=10.0) as r:
            return r.read(), r.status
    except urllib.error.HTTPError as e:
        return None, e.code
    except (urllib.error.URLError, OSError, TimeoutError) as e:
        return None, 0


def _post_discord_webhook(webhook_url, content):
    if not webhook_url:
        return None, 0
    body = json.dumps({"content": content}).encode("utf-8")
    req = urllib.request.Request(
        webhook_url, data=body, method="POST",
        headers={"Content-Type": "application/json", "User-Agent": "rapp-plant"},
    )
    try:
        with urllib.request.urlopen(req, timeout=8.0) as r:
            return r.read().decode("utf-8", errors="replace"), r.status
    except urllib.error.HTTPError as e:
        return e.read().decode("utf-8", errors="replace"), e.code
    except (urllib.error.URLError, OSError, TimeoutError) as e:
        return str(e), 0


class PlantDiscordNeighborhoodAgent(BasicAgent):
    name = "plant_discord_neighborhood"
    metadata = {
        "name": "plant_discord_neighborhood",
        "description": "Plant a new RAPP neighborhood whose human collaboration surface is a Discord channel. Creates the GitHub repo, populates seed content from a template, links the Discord webhook in neighborhood.json, posts a welcome to the channel, and returns the brainstem-join command.",
        "parameters": {
            "type": "object",
            "properties": {
                "neighborhood_name": {
                    "type": "string",
                    "description": "Slug for the new repo. Must be lowercase, hyphenated. Example: 'design-team-2026'."
                },
                "display_name": {
                    "type": "string",
                    "description": "Human-readable display name. Example: 'Design Team 2026'."
                },
                "discord_webhook_url": {
                    "type": "string",
                    "description": "The Discord channel webhook URL where this neighborhood will announce events. Get it via Discord: Channel settings → Integrations → Webhooks → New Webhook → Copy URL."
                },
                "discord_server_id": {
                    "type": "string",
                    "description": "Optional Discord server ID for the bridge metadata. Right-click server → Copy Server ID (with developer mode on)."
                },
                "discord_channel_id": {
                    "type": "string",
                    "description": "Optional Discord channel ID for the bridge metadata."
                },
                "owner": {
                    "type": "string",
                    "description": "GitHub user or org to plant under. Defaults to the authed user."
                },
                "kind": {
                    "type": "string",
                    "enum": ["neighborhood", "workspace", "braintrust"],
                    "description": "Pattern. Defaults to 'braintrust' (federated research with bibliography)."
                },
                "visibility": {
                    "type": "string",
                    "enum": ["public", "public-gate", "private", "private-workspace"],
                    "description": "Defaults to 'private-workspace' for braintrust + workspace; 'public' for neighborhood."
                },
                "template": {
                    "type": "string",
                    "description": "The seed template to clone from. One of: 'braintrust-template', 'private-workspace-template', 'public-art-collective'. Defaults based on kind."
                },
                "template_owner": {
                    "type": "string",
                    "description": "Owner of the template repo. Defaults to 'kody-w'."
                },
                "purpose": {
                    "type": "string",
                    "description": "One-paragraph purpose statement that goes into neighborhood.json."
                },
                "dry_run": {
                    "type": "boolean",
                    "description": "When true, validates inputs + simulates the API calls without actually creating a repo or posting to Discord. Returns the would-do payloads."
                }
            },
            "required": ["neighborhood_name", "discord_webhook_url"]
        }
    }

    def _slugify(self, s):
        out = []
        for c in (s or "").lower():
            if c.isalnum():
                out.append(c)
            elif c in (" ", "-", "_"):
                out.append("-")
        slug = "".join(out).strip("-")
        return slug[:64] or "rapp-neighborhood"

    def _resolve_template(self, kind, explicit):
        if explicit:
            return explicit
        return {
            "braintrust": "braintrust-template",
            "workspace": "private-workspace-template",
            "neighborhood": "public-art-collective",
        }.get(kind, "braintrust-template")

    def _resolve_visibility(self, kind, explicit):
        if explicit:
            return explicit
        return {
            "braintrust": "private-workspace",
            "workspace": "private-workspace",
            "neighborhood": "public",
        }.get(kind, "private-workspace")

    def _gather_template_files(self, template_owner, template, kind):
        files = list(TEMPLATE_FILES) + TEMPLATE_EXTRA_FILES.get(template, [])
        out = []
        for path in files:
            body, status = _fetch_raw(f"{template_owner}/{template}", "main", path)
            if status == 200 and body is not None:
                out.append((path, body))
        return out

    def _customize_neighborhood_json(self, original_bytes, new_owner, new_name, display,
                                     kind, visibility, rappid, purpose,
                                     webhook_url, server_id, channel_id):
        try:
            n = json.loads(original_bytes.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            n = {"schema": "rapp-neighborhood/1.0"}
        n["neighborhood_rappid"] = rappid
        n["name"] = new_name
        n["display_name"] = display
        n["kind"] = kind
        n["visibility"] = visibility
        n["github"] = f"https://github.com/{new_owner}/{new_name}"
        n["url"] = (
            f"https://{new_owner}.github.io/{new_name}/"
            if visibility in ("public", "public-gate") else None
        )
        n["planted_by"] = new_owner
        n["planted_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        if purpose:
            n["purpose"] = purpose
        n["discord"] = {
            "schema": "rapp-discord-bridge/1.0",
            "webhook_url": webhook_url,
            "server_id": server_id,
            "channel_id": channel_id,
            "bridge_role": "human-realtime-layer",
            "note": "Discord is the human realtime surface; GitHub stays canonical. If Discord disappears, the neighborhood continues on GitHub.",
        }
        return json.dumps(n, indent=2).encode("utf-8")

    def perform(self, neighborhood_name, discord_webhook_url,
                display_name=None, discord_server_id=None, discord_channel_id=None,
                owner=None, kind="braintrust", visibility=None, template=None,
                template_owner="kody-w", purpose=None, dry_run=False, **kwargs):

        # 1. Validate + normalize
        slug = self._slugify(neighborhood_name)
        display = display_name or slug.replace("-", " ").title()
        kind = kind if kind in ("neighborhood", "workspace", "braintrust") else "braintrust"
        vis = self._resolve_visibility(kind, visibility)
        template = self._resolve_template(kind, template)
        rappid = str(uuid.uuid4())

        if not discord_webhook_url or not discord_webhook_url.startswith(("http://", "https://")):
            return json.dumps({
                "ok": False,
                "error": "discord_webhook_url must be an HTTP(S) URL (Discord webhook)",
            }, indent=2)

        # Resolve owner (authed user if not given)
        if not owner:
            if dry_run:
                owner = "<authed-user>"
            else:
                me, status = _gh_request("GET", "/user")
                owner = (me or {}).get("login")
                if not owner:
                    return json.dumps({
                        "ok": False,
                        "error": "could not determine GitHub user (set owner= or ensure GITHUB_TOKEN has /user scope)",
                        "status": status,
                    }, indent=2)

        # 2. Gather template files
        if dry_run:
            files = [(p, b"<dry-run-content>") for p in TEMPLATE_FILES + TEMPLATE_EXTRA_FILES.get(template, [])]
        else:
            files = self._gather_template_files(template_owner, template, kind)
            if not files:
                return json.dumps({
                    "ok": False,
                    "error": f"could not fetch any files from template {template_owner}/{template}",
                }, indent=2)

        # 3. Customize neighborhood.json
        nj_idx = next((i for i, (p, _) in enumerate(files) if p == "neighborhood.json"), -1)
        if nj_idx < 0:
            files.append(("neighborhood.json", b"{}"))
            nj_idx = len(files) - 1
        files[nj_idx] = (
            "neighborhood.json",
            self._customize_neighborhood_json(
                files[nj_idx][1], owner, slug, display, kind, vis, rappid, purpose,
                discord_webhook_url, discord_server_id, discord_channel_id,
            ),
        )

        if dry_run:
            return json.dumps({
                "ok": True,
                "dry_run": True,
                "would_create_repo": f"{owner}/{slug}",
                "visibility": vis,
                "kind": kind,
                "template_used": f"{template_owner}/{template}",
                "neighborhood_rappid": rappid,
                "files_count": len(files),
                "files": [p for p, _ in files],
                "would_post_to_webhook": discord_webhook_url[:60] + "…",
                "note": "dry_run=true — no repo created, no Discord post sent.",
            }, indent=2)

        # 4. Create the GitHub repo
        repo_body = {
            "name": slug,
            "description": f"Planted via plant_discord_neighborhood — {display} ({kind})",
            "private": vis.startswith("private"),
            "auto_init": False,
        }
        # If owner is an org, use /orgs/<owner>/repos
        org_check, _ = _gh_request("GET", f"/orgs/{urllib.parse.quote(owner)}")
        is_org = isinstance(org_check, dict) and org_check.get("type") == "Organization"
        create_path = f"/orgs/{owner}/repos" if is_org else "/user/repos"
        created, status = _gh_request("POST", create_path, repo_body)
        if status not in (201, 200):
            return json.dumps({
                "ok": False,
                "error": "could not create repo",
                "status": status,
                "github_response": created,
            }, indent=2)

        # 5. Upload files via contents API (one PUT per file)
        upload_results = []
        for path, content in files:
            put_body = {
                "message": f"Plant from {template_owner}/{template} via plant_discord_neighborhood",
                "content": base64.b64encode(content).decode("ascii"),
                "branch": "main",
            }
            url = f"/repos/{owner}/{slug}/contents/{urllib.parse.quote(path)}"
            resp, st = _gh_request("PUT", url, put_body)
            upload_results.append({
                "path": path,
                "status": st,
                "ok": st in (200, 201),
            })

        upload_failures = [u for u in upload_results if not u["ok"]]

        # 6. Post welcome to Discord
        webhook_msg = (
            f"🏘  **New RAPP neighborhood planted: {display}**\n\n"
            f"• kind: `{kind}`  •  visibility: `{vis}`\n"
            f"• repo: <https://github.com/{owner}/{slug}>\n"
            f"• rappid: `{rappid}`\n\n"
            f"**To subscribe** (any RAPP brainstem):\n"
            f"```\nbrainstem join https://github.com/{owner}/{slug}\n```\n"
            f"GitHub remains the canonical state. This Discord channel is the human realtime layer."
        )
        webhook_resp, webhook_status = _post_discord_webhook(discord_webhook_url, webhook_msg)

        # 7. Return the full envelope
        return json.dumps({
            "schema": "rapp-discord-plant-envelope/1.0",
            "ok": len(upload_failures) == 0,
            "owner": owner,
            "name": slug,
            "display_name": display,
            "kind": kind,
            "visibility": vis,
            "neighborhood_rappid": rappid,
            "github": f"https://github.com/{owner}/{slug}",
            "url": f"https://{owner}.github.io/{slug}/" if vis in ("public", "public-gate") else None,
            "template_used": f"{template_owner}/{template}",
            "files_uploaded": [u for u in upload_results if u["ok"]],
            "files_failed": upload_failures,
            "discord": {
                "webhook_status": webhook_status,
                "webhook_response_preview": (webhook_resp or "")[:200],
            },
            "next_steps": [
                f"Tell collaborators: brainstem join https://github.com/{owner}/{slug}",
                f"Add Discord members as GitHub collaborators on {owner}/{slug} for write access",
                "Visit the channel — the welcome message includes the join command",
            ],
        }, indent=2)
