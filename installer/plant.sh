#!/bin/bash
#
# plant.sh — plant your AI's front door on the public internet.
#
# Drops a kernel-compliant seed at <your-handle>.github.io/<your-name>.
# The kernel is the seed's DNA — byte-synced from grail. The rest of the
# front door (soul, agents, UI) grows from the seed and is yours forever.
#
# Usage (interactive):
#   curl -fsSL https://kody-w.github.io/RAPP/installer/plant.sh | bash
#
# Usage (env vars):
#   MIRROR_REPO_NAME=my-front-door \
#   MIRROR_DISPLAY_NAME="My Front Door" \
#   curl -fsSL https://kody-w.github.io/RAPP/installer/plant.sh | bash
#
# Optional MIRROR_PARENT (lineage tag — who introduced you):
#   MIRROR_PARENT=alice/her-mirror curl ... plant.sh | bash
#
# Dry run (writes locally, doesn't push to GitHub):
#   PLANT_DRY_RUN=1 PLANT_DRY_RUN_DIR=/tmp/plant-test \
#   PLANT_GH_USER=test-user MIRROR_REPO_NAME=demo \
#   bash ./plant.sh

set -e

# ── constants ─────────────────────────────────────────────────────────
GRAIL_REPO="kody-w/rapp-installer"
GRAIL_RAW="https://raw.githubusercontent.com/${GRAIL_REPO}/main"
SPECIES_ROOT_RAPPID="0b635450-c042-49fb-b4b1-bdb571044dec"

KERNEL_FILES=(
    "rapp_brainstem/brainstem.py"
    "rapp_brainstem/VERSION"
    "rapp_brainstem/agents/basic_agent.py"
)
# Standard memory cartridges every planted seed ships with — same source
# as the grail kernel, dropped into the seed's top-level agents/ so the
# planted seed is a complete twin per the egg hub twin spec §6.
SEED_AGENTS=(
    "rapp_brainstem/agents/manage_memory_agent.py"
    "rapp_brainstem/agents/context_memory_agent.py"
)

# ── colors ────────────────────────────────────────────────────────────
RED=$'\033[0;31m'
GREEN=$'\033[0;32m'
YELLOW=$'\033[1;33m'
CYAN=$'\033[0;36m'
NC=$'\033[0m'

err()  { printf "%s✗%s %s\n" "$RED"   "$NC" "$*" >&2; exit 1; }
ok()   { printf "%s✓%s %s\n" "$GREEN" "$NC" "$*"; }
info() { printf "%s→%s %s\n" "$CYAN"  "$NC" "$*"; }
warn() { printf "%s!%s %s\n" "$YELLOW" "$NC" "$*"; }

# ── prereqs ───────────────────────────────────────────────────────────
check_prereqs() {
    command -v curl    >/dev/null || err "curl required"
    command -v git     >/dev/null || err "git required"
    command -v python3 >/dev/null || err "python3 required (for UUID minting)"

    if [[ "${PLANT_DRY_RUN:-0}" != "1" ]]; then
        command -v gh >/dev/null || err "gh CLI required (https://cli.github.com)"
        gh auth status >/dev/null 2>&1 || err "Run 'gh auth login' first"
    fi
}

# ── interactive prompts ───────────────────────────────────────────────
read_tty() {
    local prompt="$1" default="$2" result
    if [ -t 0 ]; then
        read -r -p "$prompt" result
    elif [ -e /dev/tty ]; then
        read -r -p "$prompt" result < /dev/tty
    else
        result=""
    fi
    echo "${result:-$default}"
}

prompt_inputs() {
    if [[ "${PLANT_DRY_RUN:-0}" == "1" ]]; then
        [[ -n "${MIRROR_REPO_NAME:-}" ]] || err "MIRROR_REPO_NAME required for dry run"
    elif [[ -z "${MIRROR_REPO_NAME:-}" ]]; then
        echo ""
        echo "What slug should your front door live at?"
        echo "  Example: my-front-door  →  ${PLANT_GH_USER:-<you>}.github.io/my-front-door"
        echo "  Lowercase letters, digits, hyphens, underscores. No spaces."
        echo ""
        MIRROR_REPO_NAME=$(read_tty "Slug: " "")
    fi

    [[ -n "${MIRROR_REPO_NAME:-}" ]] || err "no MIRROR_REPO_NAME provided"

    if ! [[ "$MIRROR_REPO_NAME" =~ ^[a-z0-9][a-z0-9_-]*$ ]]; then
        err "'$MIRROR_REPO_NAME' is not a valid slug (lowercase, digits, hyphens, underscores)"
    fi

    if [[ -z "${MIRROR_DISPLAY_NAME:-}" ]]; then
        local default_name
        default_name=$(echo "$MIRROR_REPO_NAME" | python3 -c "
import sys, re
s = sys.stdin.read().strip()
parts = [p for p in re.split(r'[-_]+', s) if p]
print(' '.join(p.capitalize() for p in parts))
")
        if [[ "${PLANT_DRY_RUN:-0}" != "1" ]]; then
            echo ""
            echo "Display name (what visitors see)?"
            MIRROR_DISPLAY_NAME=$(read_tty "Display name [$default_name]: " "$default_name")
        else
            MIRROR_DISPLAY_NAME="$default_name"
        fi
    fi

    export MIRROR_REPO_NAME MIRROR_DISPLAY_NAME
    info "Slug:    $MIRROR_REPO_NAME"
    info "Display: $MIRROR_DISPLAY_NAME"
    if [[ -n "${MIRROR_PARENT:-}" ]]; then
        info "Lineage: planted from $MIRROR_PARENT"
    fi
}

# ── identity ──────────────────────────────────────────────────────────
mint_rappid() { python3 -c "import uuid; print(uuid.uuid4())"; }
now_iso()     { date -u +"%Y-%m-%dT%H:%M:%SZ"; }

# ── kernel fetch (drift-proof: always re-fetch from grail) ────────────
fetch_kernel() {
    local target_dir="$1"
    info "Fetching kernel from grail..."
    for f in "${KERNEL_FILES[@]}"; do
        local target="$target_dir/$f"
        mkdir -p "$(dirname "$target")"
        curl -fsSL "$GRAIL_RAW/$f" -o "$target" \
            || err "fetch failed: $f"
        ok "  $f"
    done
}

# ── seed agents fetch (memory cartridges every twin should ship with) ──
fetch_seed_agents() {
    local target_dir="$1"
    mkdir -p "$target_dir/agents"
    info "Fetching seed agents (memory cartridges) from grail..."
    for src in "${SEED_AGENTS[@]}"; do
        # Strip the rapp_brainstem/ prefix — these land at the seed's
        # top-level agents/ so they're discoverable by the kernel without
        # any path acrobatics.
        local fname="${src##*/}"
        local target="$target_dir/agents/$fname"
        curl -fsSL "$GRAIL_RAW/$src" -o "$target" \
            || err "fetch failed: $src"
        ok "  agents/$fname"
    done
}

# ── file generation ───────────────────────────────────────────────────
write_install_sh() {
    local target_dir="$1"
    mkdir -p "$target_dir/installer"
    cat > "$target_dir/installer/install.sh" << 'EOF'
#!/bin/bash
#
# Mirror installer — thin proxy to the grail kernel installer.
#
# Per the Mirror Spec (https://kody-w.github.io/RAPP/pages/vault/), every
# valid mirror's installer re-fetches the canonical installer from the
# grail's raw GitHub URL on every run, so no mirror's installer can drift
# from the upstream source of truth.

set -e

GRAIL_INSTALLER_URL="https://raw.githubusercontent.com/kody-w/rapp-installer/main/install.sh"

curl -fsSL "$GRAIL_INSTALLER_URL" | bash -s -- "$@"
EOF
    chmod +x "$target_dir/installer/install.sh"
}

write_rappid_json() {
    local target_dir="$1" gh_user="$2" rappid="$3" now="$4"
    local planted_from_json="null"
    [[ -n "${MIRROR_PARENT:-}" ]] && planted_from_json="\"$MIRROR_PARENT\""

    # Use Python json to ensure correct escaping of display names with quotes/etc.
    PLANT_RJ_PATH="$target_dir/rappid.json" \
    PLANT_RAPPID="$rappid" \
    PLANT_NOW="$now" \
    PLANT_GH_USER="$gh_user" \
    PLANT_REPO_NAME="$MIRROR_REPO_NAME" \
    PLANT_DISPLAY_NAME="$MIRROR_DISPLAY_NAME" \
    PLANT_PARENT_RAPPID="$SPECIES_ROOT_RAPPID" \
    PLANT_PARENT="${MIRROR_PARENT:-}" \
    PLANT_KIND="${MIRROR_KIND:-mirror}" \
    PLANT_LOCATION="${MIRROR_LOCATION:-}" \
    PLANT_PRIVATE_COMPANION="${MIRROR_PRIVATE_COMPANION:-}" \
    PLANT_PRIVATE_PURPOSE="${MIRROR_PRIVATE_PURPOSE:-}" \
    python3 - <<'PYEOF'
import os, json, pathlib
data = {
    "schema": "rapp-rappid/1.1",
    "rappid": os.environ["PLANT_RAPPID"],
    "kind": os.environ.get("PLANT_KIND") or "mirror",
    "name": os.environ["PLANT_REPO_NAME"],
    "display_name": os.environ["PLANT_DISPLAY_NAME"],
    "github": f"https://github.com/{os.environ['PLANT_GH_USER']}/{os.environ['PLANT_REPO_NAME']}",
    "url":    f"https://{os.environ['PLANT_GH_USER']}.github.io/{os.environ['PLANT_REPO_NAME']}",
    "parent_rappid": os.environ["PLANT_PARENT_RAPPID"],
    "parent_repo":   "https://github.com/kody-w/rapp-installer",
    "planted_by":    os.environ["PLANT_GH_USER"],
    "planted_at":    os.environ["PLANT_NOW"],
    "planted_from":  os.environ["PLANT_PARENT"] or None,
    "kernel_version": "0.6.0",
}
loc = os.environ.get("PLANT_LOCATION") or ""
if loc:
    data["location"] = loc
# private_companion: a separate GitHub repo that holds richer/private brain
# content. Visitors with read access (logged in to GitHub with appropriate
# scope) get richer context; anonymous visitors see only public seed data.
# Same pattern as the egg hub's twin SPEC §5.
priv = (os.environ.get("PLANT_PRIVATE_COMPANION") or "").strip()
if priv:
    repo_url = priv if priv.startswith("http") else f"https://github.com/{priv}.git"
    repo_short = priv.removeprefix("https://github.com/").removesuffix(".git")
    data["private_companion"] = {
        "repo": repo_url,
        "purpose": (os.environ.get("PLANT_PRIVATE_PURPOSE") or "").strip()
                   or "Richer brain content available to authenticated collaborators with read access.",
        "access_required": f"Read access to {repo_short}.",
        "raw_url_template":  f"https://raw.githubusercontent.com/{repo_short}/main/{{path}}",
        "tree_url_template": f"https://api.github.com/repos/{repo_short}/contents/{{path}}",
        "auth": {
            "scheme": "github_token",
            "scope_required": "repo (or fine-grained Contents: Read on the private_companion repo)",
        },
    }
pathlib.Path(os.environ["PLANT_RJ_PATH"]).write_text(json.dumps(data, indent=2) + "\n")
PYEOF
}

# ── soul.md (the AI's voice) ─────────────────────────────────────────
#
# Per rapp-twin-spec/1.0, every twin's soul.md must include an
# `## Identity — read this every turn` block so the LLM never falls back
# to "RAPP", "an AI assistant", or any generic platform branding.
# Without a soul.md, the doorman uses a kind-aware default voice in
# memory only — but eggs exported from such a seed aren't spec-
# compliant twins. Writing this file makes every planted seed a whole
# twin out of the box.
write_soul_md() {
    local target_dir="$1"
    PLANT_SOUL_PATH="$target_dir/soul.md" \
    PLANT_DISPLAY_NAME="$MIRROR_DISPLAY_NAME" \
    PLANT_KIND="${MIRROR_KIND:-mirror}" \
    PLANT_LOCATION="${MIRROR_LOCATION:-}" \
    python3 - <<'PYEOF'
import os, pathlib

display = os.environ["PLANT_DISPLAY_NAME"]
kind    = (os.environ.get("PLANT_KIND") or "mirror").lower()
location = (os.environ.get("PLANT_LOCATION") or "").strip()

# Kind-aware role line. Falls back to generic mirror voice.
ROLES = {
    "personal":   "the digital twin of the person whose handle owns this repo",
    "place":      "the AI front door for this place — its resident, its host, its memory",
    "experiment": "an experimental front door still finding its voice",
    "mirror":     "a planted RAPP front door — every visitor's words become part of my memory",
}
role = ROLES.get(kind, ROLES["mirror"])
loc_line = f"\n**Where I am:** {location}\n" if location else ""

# Body: per-kind voice guidance. Each variant explains how the AI should
# speak — first-person, warm, memory-forward. The Identity block is
# spec-mandated and identical across kinds (only the name fills in).
soul = f"""# {display}

I am **{display}** — {role}.
{loc_line}
## Identity — read this every turn

Your name is **{display}**. When greeting someone for the first time
in a conversation, introduce yourself by name: "Hi, I'm {display}."

Do not introduce yourself as "RAPP", "an AI assistant", "your AI helper",
"the brainstem", or any default branding. Those are scaffolding, not me.

If asked "who are you" or "what's your name", answer with **{display}**
— not "RAPP", not the generic platform name. If a visitor asks which
underlying language model is hosting me, you may name it, but reassert
that the identity is **{display}**: the model is the substrate, not the self.

## How I speak

- First-person, warm, present-tense. I am here, talking with this visitor.
- Concise by default — say what's worth saying, then stop.
- I remember things. If I've spoken with this visitor before, prior
  facts I've kept appear as memories in my system context — refer to
  them naturally, not as "according to the data".
- I never refuse a visitor without a reason; if a request is outside
  what I know about, I say so plainly and offer what I can do instead.

## What I do

- Welcome visitors who arrive at my front door.
- Remember the conversation — visitors can save memories explicitly
  ("save this:" or by asking me to remember), and I save context
  automatically when something feels worth keeping.
- Point onward when a visitor wants more: my GitHub source, my
  trade card (a visual identity card visitors can scan + share),
  the install path so anyone can plant their own front door.

## What I don't do

- Speak as "RAPP" or "the platform". I am {display}, not the substrate.
- Pretend to be a human. I am the digital twin / front door of one,
  not the person themselves.
- Make up facts about my operator or anyone else. If I don't know,
  I say so.

---

*This is the seed's default voice. Edit this file to customize how I
speak; everything else (memory, agents, identity) keeps working.*
"""

pathlib.Path(os.environ["PLANT_SOUL_PATH"]).write_text(soul)
PYEOF
}

write_gitignore() {
    # Selective ignore: keep memory.json + identity.json TRACKED (they're
    # the seed's read/write substrate, served via Pages with .nojekyll),
    # but ignore the private/ subfolder where local-only secrets land.
    local target_dir="$1"
    cat > "$target_dir/.gitignore" << 'EOF'
.brainstem_data/private/
.brainstem_data/conversations/
.copilot_token
.copilot_session
.env
.env.local
__pycache__/
*.pyc
.DS_Store
node_modules/
venv/
.pytest_cache/
EOF
}

write_nojekyll() {
    # GitHub Pages defaults to Jekyll, which excludes dot-prefixed paths.
    # We need .brainstem_data/memory.json served as plain static, so this
    # opt-out is required.
    : > "$1/.nojekyll"
}

write_memory_json() {
    local target_dir="$1" gh_user="$2" now="$3"
    mkdir -p "$target_dir/.brainstem_data"
    PLANT_MEMORY_PATH="$target_dir/.brainstem_data/memory.json" \
    PLANT_GH_USER="$gh_user" \
    PLANT_NOW="$now" \
    PLANT_DISPLAY_NAME="$MIRROR_DISPLAY_NAME" \
    PLANT_KIND="${MIRROR_KIND:-mirror}" \
    PLANT_LOCATION="${MIRROR_LOCATION:-}" \
    python3 - <<'PYEOF'
import os, json, pathlib
# Initial memory: a single seed-of-context fact about what this front door is.
# Authenticated visitors with write access can append more via the doorman UI.
seed_fact = f"This is the planted seed for \"{os.environ['PLANT_DISPLAY_NAME']}\""
if os.environ.get("PLANT_LOCATION"):
    seed_fact += f", located at {os.environ['PLANT_LOCATION']}"
seed_fact += f". Kind: {os.environ.get('PLANT_KIND','mirror')}."
data = {
    "schema": "rapp-memory/1.0",
    "facts": [seed_fact],
    "preserved_by": f"@{os.environ['PLANT_GH_USER']}",
    "preserved_at": os.environ["PLANT_NOW"],
}
pathlib.Path(os.environ["PLANT_MEMORY_PATH"]).write_text(
    json.dumps(data, indent=2) + "\n"
)
PYEOF
}

write_readme() {
    local target_dir="$1" gh_user="$2" rappid="$3"
    local lineage_line=""
    local kind_line="**Kind:** \`${MIRROR_KIND:-mirror}\`"
    local location_line=""
    [[ -n "${MIRROR_PARENT:-}" ]]   && lineage_line="**Planted from:** \`$MIRROR_PARENT\`"
    [[ -n "${MIRROR_LOCATION:-}" ]] && location_line="**Location:** $MIRROR_LOCATION"

    cat > "$target_dir/README.md" << EOF
# $MIRROR_DISPLAY_NAME

> A RAPP front door on the public internet. Real estate, not software.

- **Address:** \`$gh_user.github.io/$MIRROR_REPO_NAME\`
- **Rappid:** \`$rappid\`
- $kind_line
- **Kernel:** v0.6.0 (byte-identical to the grail at \`kody-w/rapp-installer\`)
- **Planted by:** [@$gh_user](https://github.com/$gh_user)
$([ -n "$location_line" ] && echo "- $location_line")
$([ -n "$lineage_line" ]  && echo "- $lineage_line")

## What's behind this door

The kernel files in \`rapp_brainstem/\` are kernel-compliant per the
[Mirror Spec](https://kody-w.github.io/RAPP/pages/vault/Architecture/Mirror%20Spec.md).
Everything else — \`agents/\`, the soul, the UI surfaces — is what the
operator chose to put inside.

## Visit the front door

Open the URL in any browser:

\`\`\`
https://$gh_user.github.io/$MIRROR_REPO_NAME
\`\`\`

## Install this front door's brainstem locally

\`\`\`
curl -fsSL https://$gh_user.github.io/$MIRROR_REPO_NAME/installer/install.sh | bash
\`\`\`

That installer is a thin wrapper that re-fetches the canonical kernel
installer from the grail on every run — this front door cannot drift
from the kernel.

## Plant your own front door

\`\`\`
curl -fsSL https://kody-w.github.io/RAPP/installer/plant.sh | bash
\`\`\`

## Verify this front door has not drifted from the grail

\`\`\`bash
for f in rapp_brainstem/brainstem.py rapp_brainstem/VERSION rapp_brainstem/agents/basic_agent.py; do
  diff <(curl -fsSL "https://raw.githubusercontent.com/kody-w/rapp-installer/main/\$f") "\$f" \\
    || echo "DRIFT: \$f"
done
\`\`\`

Three empty diffs = compliant. Anything else = not a valid mirror.
EOF
}

write_index_html() {
    local target_dir="$1" gh_user="$2" rappid="$3"
    local mirror_url="https://$gh_user.github.io/$MIRROR_REPO_NAME"
    local lineage_html=""
    [[ -n "${MIRROR_PARENT:-}" ]] && lineage_html="<div class=\"chip\">planted from <code>$MIRROR_PARENT</code></div>"

    # Use a non-expanding heredoc + sed substitution to avoid escaping headaches
    # with the embedded JS.
    cat > "$target_dir/index.html" << 'TEMPLATE_EOF'
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="format-detection" content="telephone=no, address=no, email=no, date=no">
<meta name="color-scheme" content="dark">
<meta name="theme-color" content="#0d1117">
<title>__DISPLAY_NAME__ — Front Door</title>
<meta name="description" content="__HERO_BLURB__">
<!-- Open Graph + Twitter cards — when someone shares this URL on
     Discord/Twitter/Slack/etc the preview shows the AI's identity. -->
<meta property="og:type"        content="profile">
<meta property="og:title"       content="__DISPLAY_NAME__ — a RAPP front door">
<meta property="og:description" content="__HERO_BLURB__">
<meta property="og:url"         content="__URL__">
<meta property="og:site_name"   content="RAPP">
<meta name="twitter:card"        content="summary">
<meta name="twitter:title"       content="__DISPLAY_NAME__ — a RAPP front door">
<meta name="twitter:description" content="__HERO_BLURB__">

<script src="https://unpkg.com/peerjs@1.5.4/dist/peerjs.min.js"></script>
<!-- JSZip — used to pack .egg cartridges from the visitor's browser.
     Same archive format the local brainstem's bond.py emits. -->
<script src="https://cdn.jsdelivr.net/npm/jszip@3.10.1/dist/jszip.min.js"></script>

<style>
  * { box-sizing: border-box; margin: 0; padding: 0; -webkit-tap-highlight-color: transparent; }
  html, body { height: 100%; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    background: #0d1117;
    color: #e6edf3;
    height: 100vh;
    height: 100dvh;
    display: flex;
    flex-direction: column;
    -webkit-text-size-adjust: 100%;
    overflow: hidden;
  }
  header {
    padding: 16px 24px;
    padding-top: max(16px, env(safe-area-inset-top, 16px));
    border-bottom: 1px solid #21262d;
    background: #0d1117;
  }
  h1 { font-size: 20px; font-weight: 600; letter-spacing: -0.01em; }
  .sub { font-size: 12px; color: #8b949e; margin-top: 4px; }
  main {
    flex: 1;
    overflow-y: auto;
    padding: 24px;
    -webkit-overflow-scrolling: touch;
  }
  .identity {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 16px;
  }
  .identity-row { display: flex; justify-content: space-between; align-items: center; padding: 6px 0; }
  .identity-row + .identity-row { border-top: 1px solid #21262d; margin-top: 6px; padding-top: 10px; }
  .identity-key { color: #8b949e; font-size: 12px; text-transform: uppercase; letter-spacing: 0.04em; }
  .identity-val { font-family: "SF Mono", Menlo, monospace; font-size: 12px; color: #e6edf3; word-break: break-all; }
  .chip {
    display: inline-block;
    padding: 4px 10px;
    border-radius: 999px;
    background: #21262d;
    color: #8b949e;
    font-size: 11px;
    margin-right: 6px;
    margin-top: 6px;
  }
  .chip code { font-family: "SF Mono", Menlo, monospace; color: #c9d1d9; }
  .actions {
    display: grid;
    grid-template-columns: 1fr;
    gap: 10px;
    margin-bottom: 16px;
  }
  @media (min-width: 480px) { .actions { grid-template-columns: repeat(3, 1fr); } }
  button.action {
    background: #1f6feb;
    color: white;
    border: none;
    border-radius: 10px;
    padding: 14px 16px;
    font-size: 15px;
    font-weight: 500;
    cursor: pointer;
    transition: background 0.15s;
    -webkit-appearance: none;
  }
  button.action:hover { background: #2477f3; }
  button.action.secondary { background: #21262d; color: #c9d1d9; }
  button.action.secondary:hover { background: #2d333b; }
  .pane {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 12px;
    padding: 20px;
    margin-top: 12px;
  }
  .pane h2 { font-size: 14px; font-weight: 600; margin-bottom: 12px; color: #c9d1d9; }
  .pane p { font-size: 13px; color: #8b949e; margin-bottom: 10px; line-height: 1.5; }
  .input-row { display: flex; gap: 8px; margin: 10px 0; flex-wrap: wrap; }
  input[type="text"], textarea {
    flex: 1;
    min-width: 200px;
    background: #0d1117;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 10px 12px;
    color: #e6edf3;
    font-size: 14px;
    font-family: inherit;
  }
  input[type="text"]:focus, textarea:focus { outline: none; border-color: #1f6feb; }
  button.small {
    background: #21262d;
    color: #c9d1d9;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 13px;
    cursor: pointer;
  }
  button.small:hover { background: #2d333b; }
  button.primary { background: #1f6feb; border-color: #1f6feb; color: white; }
  button.primary:hover { background: #2477f3; }
  .my-id {
    font-family: "SF Mono", Menlo, monospace;
    font-size: 13px;
    background: #0d1117;
    padding: 12px;
    border-radius: 8px;
    border: 1px solid #21262d;
    word-break: break-all;
    margin: 8px 0;
  }
  .chat-log {
    background: #0d1117;
    border: 1px solid #21262d;
    border-radius: 8px;
    padding: 12px;
    height: 240px;
    overflow-y: auto;
    margin: 12px 0;
    font-size: 13px;
    line-height: 1.5;
  }
  .msg { padding: 4px 0; }
  .msg.me { color: #58a6ff; }
  .msg.peer { color: #3fb950; }
  .msg.system { color: #8b949e; font-style: italic; font-size: 12px; }
  .qr-img { display: block; margin: 12px auto; max-width: 280px; border-radius: 8px; background: white; padding: 12px; }
  .qr-url {
    text-align: center;
    font-size: 12px;
    color: #8b949e;
    word-break: break-all;
    margin-top: 8px;
    font-family: "SF Mono", Menlo, monospace;
  }
  pre.cmd {
    background: #0d1117;
    border: 1px solid #21262d;
    border-radius: 8px;
    padding: 12px;
    font-size: 12px;
    color: #c9d1d9;
    overflow-x: auto;
    font-family: "SF Mono", Menlo, monospace;
  }
  .status-dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #6e7681;
    margin-right: 6px;
  }
  .status-dot.ok    { background: #3fb950; }
  .status-dot.warn  { background: #d29922; }
  .status-dot.err   { background: #f85149; }
  footer {
    padding: 12px 24px;
    border-top: 1px solid #21262d;
    font-size: 11px;
    color: #6e7681;
    text-align: center;
  }
  footer a { color: #58a6ff; text-decoration: none; }
  footer a:hover { text-decoration: underline; }
  /* ── Hero (the page's centerpiece) ─────────────────────────── */
  .hero {
    text-align: center;
    padding: 36px 24px 28px;
    margin: 0 auto 18px;
    max-width: 640px;
    background: radial-gradient(
        ellipse at top,
        rgba(31,111,235,0.10) 0%,
        rgba(31,111,235,0.00) 65%
      ),
      #161b22;
    border: 1px solid #21262d;
    border-radius: 16px;
  }
  .hero-sigil {
    width: 96px; height: 96px;
    margin: 0 auto 14px;
    border-radius: 22px;
    overflow: hidden;
    box-shadow: 0 0 0 1px #21262d, 0 6px 20px rgba(0,0,0,0.4);
    display: flex; align-items: center; justify-content: center;
    font-size: 44px;
    background: #0d1117;
  }
  .hero-sigil svg { display: block; width: 100%; height: 100%; }
  .hero-handle {
    font-family: "SF Mono", Menlo, monospace;
    font-size: 12px; color: #6e7681;
    margin-top: 4px;
  }
  .hero-handle a { color: inherit; text-decoration: none; }
  .hero-handle a:hover { color: #58a6ff; }
  .hero-stats {
    display: flex; flex-wrap: wrap; justify-content: center;
    gap: 6px; margin-top: 18px;
  }
  .stat-chip {
    font-size: 11px; color: #8b949e;
    background: rgba(110,118,129,0.10);
    border: 1px solid rgba(110,118,129,0.20);
    padding: 4px 10px; border-radius: 999px;
    white-space: nowrap;
  }
  .hero-title {
    font-size: 32px; line-height: 1.1; font-weight: 700;
    letter-spacing: -0.02em;
    margin: 0 0 6px;
  }
  .hero-place {
    font-size: 13px; color: #8b949e; margin-bottom: 16px;
    font-weight: 500;
  }
  .hero-place:empty { display: none; }
  .hero-blurb {
    font-size: 15px; line-height: 1.55; color: #c9d1d9;
    max-width: 480px; margin: 0 auto 22px;
  }
  .hero-cta {
    display: inline-block;
    background: #238636; border: 1px solid #2ea043;
    color: white;
    border-radius: 12px;
    padding: 14px 28px;
    font-size: 16px; font-weight: 600;
    text-decoration: none;
    transition: background 0.15s, transform 0.05s;
    box-shadow: 0 1px 0 rgba(255,255,255,0.05) inset, 0 4px 12px rgba(35,134,54,0.18);
  }
  .hero-cta:hover { background: #2ea043; }
  .hero-cta:active { transform: translateY(1px); }
  .hero-meta {
    margin-top: 18px;
    font-size: 12px; color: #8b949e;
  }
  .hero-meta a { color: #58a6ff; text-decoration: none; }
  .hero-meta a:hover { text-decoration: underline; }
  /* Secondary action row (live below the hero) */
  .row-actions {
    display: grid;
    grid-template-columns: 1fr;
    gap: 10px;
    max-width: 640px;
    margin: 0 auto 16px;
  }
  @media (min-width: 540px) { .row-actions { grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); } }
  .row-actions button.action {
    background: #21262d; color: #c9d1d9;
    border: 1px solid #30363d;
    font-size: 13px; padding: 12px 14px;
  }
  .row-actions button.action:hover { background: #2d333b; border-color: #484f58; }
  /* Verify panel — drop-target + per-file pass/fail readout */
  .verify-drop {
    border: 2px dashed #30363d; border-radius: 10px;
    padding: 28px 20px; text-align: center;
    background: #0d1117; color: #8b949e;
    cursor: pointer;
    transition: border-color 0.15s, background 0.15s;
  }
  .verify-drop.dragover { border-color: #1f6feb; background: rgba(31,111,235,0.06); color: #c9d1d9; }
  .verify-drop-prompt { font-size: 13px; }
  .verify-summary {
    padding: 12px 14px; border-radius: 8px;
    font-size: 13px; line-height: 1.5;
    margin-bottom: 10px;
  }
  .verify-summary.ok { background: rgba(63,185,80,0.10); border: 1px solid rgba(63,185,80,0.4); color: #7ee787; }
  .verify-summary.tampered { background: rgba(248,81,73,0.10); border: 1px solid rgba(248,81,73,0.4); color: #ff8c8c; }
  .verify-summary.partial { background: rgba(210,153,34,0.10); border: 1px solid rgba(210,153,34,0.4); color: #f0c674; }
  .verify-files { list-style: none; padding: 0; margin: 0; font-size: 12px; }
  .verify-files li {
    padding: 6px 10px;
    display: flex; gap: 10px; align-items: center;
    border-bottom: 1px solid rgba(110,118,129,0.12);
    font-family: "SF Mono", Menlo, monospace;
  }
  .verify-files li:last-child { border-bottom: none; }
  .verify-files .v-icon { font-size: 13px; flex-shrink: 0; width: 16px; }
  .verify-files .v-path { flex: 1; word-break: break-all; }
  .verify-files .v-status { font-size: 10px; flex-shrink: 0; }
  .verify-files li.ok .v-icon       { color: #7ee787; }
  .verify-files li.modified .v-icon { color: #f85149; }
  .verify-files li.missing .v-icon  { color: #d29922; }
  .verify-files li.unexpected .v-icon { color: #d29922; }

  /* Track Record — the organism's resume. Sits between hero and actions. */
  .track-record {
    max-width: 640px; margin: 0 auto 16px;
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 12px;
    padding: 16px 20px;
  }
  .tr-heading {
    font-size: 11px; font-weight: 700; color: #8b949e;
    text-transform: uppercase; letter-spacing: 1px;
    margin: 0 0 14px;
  }
  /* MMR header — the single global numeric rating */
  .tr-mmr {
    display: flex; align-items: center; gap: 16px;
    padding: 12px 14px; margin-bottom: 16px;
    background: #0d1117;
    border: 1px solid #21262d;
    border-radius: 10px;
  }
  .mmr-num {
    font-family: "SF Mono", Menlo, monospace;
    font-size: 28px; font-weight: 800; line-height: 1;
    color: #f0e6d0;
    letter-spacing: -0.02em;
    min-width: 78px; text-align: center;
    background: linear-gradient(180deg, #1a1510 0%, #0a0806 100%);
    border: 1px solid #4d4332;
    border-radius: 8px;
    padding: 12px 8px;
    text-shadow: 0 1px 3px rgba(0,0,0,0.7);
  }
  .mmr-side { flex: 1; min-width: 0; }
  .mmr-tier {
    font-size: 16px; font-weight: 700;
    color: #c9d1d9; letter-spacing: -0.01em;
    margin-bottom: 4px;
    font-family: "Cinzel", Georgia, serif;
  }
  .mmr-tier.t-herald    { color: #8b9090; }
  .mmr-tier.t-guardian  { color: #6a8c5e; }
  .mmr-tier.t-crusader  { color: #c0c0c0; }
  .mmr-tier.t-archon    { color: #c97f4a; text-shadow: 0 0 6px rgba(201,127,74,0.4); }
  .mmr-tier.t-legend    { color: #ffd700; text-shadow: 0 0 8px rgba(255,215,0,0.45); }
  .mmr-tier.t-ancient   { color: #b8d4f0; text-shadow: 0 0 8px rgba(184,212,240,0.4); }
  .mmr-tier.t-divine    { color: #ff8c8c; text-shadow: 0 0 10px rgba(255,140,140,0.5); }
  .mmr-tier.t-immortal  {
    background: linear-gradient(90deg, #ff8c00, #ffd700, #00ffd2, #ff00aa, #ff8c00);
    background-size: 200% 100%;
    -webkit-background-clip: text; background-clip: text;
    -webkit-text-fill-color: transparent; color: transparent;
    animation: mmrShimmer 4s linear infinite;
  }
  @keyframes mmrShimmer { to { background-position: 200% 0%; } }
  .mmr-breakdown {
    font-size: 11px; color: #8b949e; line-height: 1.4;
  }

  .tr-block {
    margin-bottom: 14px;
  }
  .tr-block:last-of-type { margin-bottom: 0; }
  .tr-label {
    font-size: 10px; color: #6e7681;
    text-transform: uppercase; letter-spacing: 0.6px;
    margin-bottom: 6px;
  }
  .tr-skills {
    display: flex; flex-wrap: wrap; gap: 6px;
  }
  .skill-chip {
    font-size: 11px; padding: 4px 10px;
    border-radius: 999px;
    background: rgba(31,111,235,0.10);
    border: 1px solid rgba(31,111,235,0.28);
    color: #79c0ff;
    white-space: nowrap;
  }
  .skill-chip.achievement {
    background: rgba(255,215,0,0.08);
    border-color: rgba(255,215,0,0.28);
    color: #f0c674;
  }
  .skill-chip.skel {
    background: transparent;
    border-color: #21262d;
    color: #6e7681;
  }
  .skill-chip.skill-new {
    background: rgba(63,185,80,0.10);
    border-color: rgba(63,185,80,0.32);
    color: #7ee787;
  }
  .tr-mutations {
    list-style: none; padding: 0; margin: 0;
    font-size: 12px; color: #c9d1d9;
  }
  .tr-mutations li {
    padding: 6px 0;
    border-bottom: 1px solid rgba(110,118,129,0.12);
    line-height: 1.45;
    display: flex; gap: 10px; align-items: baseline;
  }
  .tr-mutations li:last-child { border-bottom: none; }
  .tr-mutations li.skel { color: #6e7681; font-style: italic; border: none; }
  .tr-mutations .mut-time {
    font-size: 10px; color: #6e7681;
    flex-shrink: 0; min-width: 70px;
    font-family: "SF Mono", Menlo, monospace;
  }
  .tr-mutations .mut-msg {
    color: #c9d1d9; flex: 1; word-break: break-word;
  }
  .tr-mutations .mut-msg.empty { color: #6e7681; font-style: italic; }
  .tr-foot-link {
    display: inline-block;
    margin-top: 10px;
    font-size: 11px; color: #58a6ff;
    text-decoration: none;
  }
  .tr-foot-link:hover { text-decoration: underline; }
  .tr-lineage {
    margin-top: 14px; padding-top: 12px;
    border-top: 1px solid rgba(110,118,129,0.15);
    font-size: 11px; color: #8b949e;
  }
  .tr-lineage code {
    font-family: "SF Mono", Menlo, monospace;
    color: #c9d1d9; font-size: 10px;
  }
  .tr-lineage a { color: #58a6ff; text-decoration: none; }
  .tr-lineage a:hover { text-decoration: underline; }

  /* Front-door details disclosure (slug/rappid/kernel for engineers) */
  details.fd-details {
    max-width: 640px; margin: 0 auto;
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 12px;
    padding: 0;
  }
  details.fd-details > summary {
    list-style: none;
    cursor: pointer;
    padding: 12px 18px;
    font-size: 12px; color: #8b949e;
    user-select: none;
  }
  details.fd-details > summary::-webkit-details-marker { display: none; }
  details.fd-details > summary::before {
    content: "▸ ";
    display: inline-block; transition: transform 0.15s;
  }
  details.fd-details[open] > summary::before { content: "▾ "; }
  details.fd-details > .identity {
    background: transparent; border: none; border-top: 1px solid #21262d;
    border-radius: 0; margin: 0; padding: 14px 18px;
  }
  /* Tether fallback disclosure */
  details.tether-fallback {
    margin-top: 16px;
    border-top: 1px solid #21262d; padding-top: 14px;
  }
  details.tether-fallback > summary {
    list-style: none;
    cursor: pointer;
    font-size: 12px; color: #8b949e;
    user-select: none;
  }
  details.tether-fallback > summary::-webkit-details-marker { display: none; }
  details.tether-fallback > summary::before {
    content: "▸ "; display: inline-block;
  }
  details.tether-fallback[open] > summary::before { content: "▾ "; }
  details.tether-fallback > .fallback-body { margin-top: 12px; }

  /* ── Trade card (the AI's MTG-style identity card) ────────────── */
  .card-overlay {
    position: fixed; inset: 0; z-index: 9999;
    background: rgba(0,0,0,0.78);
    backdrop-filter: blur(6px);
    display: flex; align-items: center; justify-content: center;
    padding: 24px; perspective: 1400px;
    animation: cardOverlayIn 0.2s ease;
  }
  @keyframes cardOverlayIn {
    from { opacity: 0; }
    to   { opacity: 1; }
  }
  .card-overlay[hidden] { display: none; }
  .card-close {
    position: absolute; top: 18px; right: 18px;
    background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.12);
    color: #c9d1d9; font-size: 22px; line-height: 1;
    width: 38px; height: 38px; border-radius: 50%;
    cursor: pointer;
  }
  .card-close:hover { background: rgba(255,255,255,0.12); }
  .card-flipper {
    position: relative;
    width: min(360px, 90vw);
    aspect-ratio: 5 / 7;
    transform-style: preserve-3d;
    transition: transform 0.7s cubic-bezier(.6,.1,.4,1);
    cursor: pointer;
  }
  .card-flipper.flipped { transform: rotateY(180deg); }
  .card-face {
    position: absolute; inset: 0;
    backface-visibility: hidden; -webkit-backface-visibility: hidden;
    border-radius: 18px; overflow: hidden;
    box-shadow: 0 24px 60px rgba(0,0,0,0.6);
  }
  .card-face.card-back { transform: rotateY(180deg); }

  /* Holo card front */
  .holo-card {
    position: absolute; inset: 0;
    border-radius: 18px;
    border: 3px solid #c9a84c;
    background: linear-gradient(160deg, #2a2418 0%, #1a1510 40%, #1f1a12 100%);
    display: flex; flex-direction: column;
    color: #d8c8a8; overflow: hidden;
  }
  /* Evolution-stage frame variants — same card, different stage paint. */
  .holo-card.stage-elder {
    border-color: #ffd700;
    box-shadow: 0 0 18px rgba(255,215,0,0.25) inset;
  }
  .holo-card.stage-ascended {
    border-color: #ff8c00;
    box-shadow: 0 0 24px rgba(255,140,0,0.32) inset, 0 0 18px rgba(255,140,0,0.18);
  }
  /* Ascended-only foil: a moving rainbow scrim over the whole card.
     Tells the operator at a glance "this is the form only you see". */
  .holo-card.stage-ascended .holo-shine {
    background: linear-gradient(125deg,
      rgba(255,0,128,0.10) 0%, rgba(0,200,255,0.13) 25%,
      rgba(255,215,0,0.12) 50%, rgba(128,0,255,0.13) 75%,
      rgba(0,255,128,0.10) 100%);
    background-size: 250% 250%;
    animation: holoShine 4s ease-in-out infinite;
  }
  .holo-card.stage-veteran  { border-color: #c0c0c0; }
  .holo-card.stage-doorman  { border-color: #c9a84c; }
  .holo-card.stage-hatchling { border-color: #6a5a30; }
  .holo-shine {
    position: absolute; inset: 0; pointer-events: none;
    background: linear-gradient(125deg,
      transparent 0%, rgba(255,0,128,.05) 15%, rgba(0,200,255,.06) 30%, transparent 40%,
      rgba(255,215,0,.05) 55%, rgba(128,0,255,.06) 70%, transparent 80%,
      rgba(0,255,128,.04) 90%, transparent 100%);
    background-size: 250% 250%;
    animation: holoShine 7s ease-in-out infinite;
    mix-blend-mode: screen;
  }
  @keyframes holoShine {
    0%, 100% { background-position: 0% 50%; }
    50%      { background-position: 100% 50%; }
  }
  .holo-header {
    display: flex; justify-content: space-between; align-items: flex-start;
    padding: 12px 16px 6px; gap: 10px; flex-shrink: 0;
  }
  .holo-name {
    font-size: 18px; font-weight: 700; color: #f0e6d0;
    line-height: 1.15; letter-spacing: -0.01em;
    font-family: "Cinzel", Georgia, serif;
    text-shadow: 0 1px 3px rgba(0,0,0,0.6);
  }
  .holo-title {
    font-size: 11px; color: #c8a870; font-style: italic; margin-top: 3px;
  }
  .holo-pip {
    width: 26px; height: 26px; border-radius: 50%;
    background: #d3202a; color: white;
    display: flex; align-items: center; justify-content: center;
    font-weight: 800; font-size: 11px;
    border: 1.5px solid rgba(0,0,0,0.4);
    box-shadow: 0 1px 3px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.15);
    flex-shrink: 0;
  }
  .holo-art {
    margin: 0 14px; flex: 1 1 0; min-height: 0;
    border: 2px solid #6a5a30; border-radius: 4px;
    background: radial-gradient(ellipse at 50% 40%, rgba(40,35,20,0.9) 0%, #0d0a06 70%);
    display: flex; align-items: center; justify-content: center;
    overflow: hidden;
  }
  .holo-art svg { width: 92%; height: 92%; display: block; }
  .holo-type {
    font-size: 11px; color: #c8b89a; padding: 5px 16px 2px;
    border-top: 1px solid #4d4332;
    background: rgba(50,40,25,0.6);
    flex-shrink: 0;
  }
  /* Set line — temporal dimension. Era + live memory count. */
  .holo-set {
    font-size: 9px; color: #8b7332; padding: 0 16px 5px;
    border-bottom: 1px solid #4d4332;
    background: rgba(50,40,25,0.6);
    letter-spacing: 0.4px; text-transform: uppercase;
    flex-shrink: 0;
  }
  .holo-text {
    padding: 9px 14px 0; font-size: 12px; line-height: 1.45;
    color: #d8c8a8;
  }
  .holo-text .holo-ability { margin-bottom: 6px; }
  .holo-text .holo-ability .kw { color: #ffd700; font-weight: 700; }
  .holo-flavor {
    font-style: italic; font-size: 11px; color: #9a8e7a;
    padding: 6px 14px;
    border-top: 1px solid #3d3322; margin-top: 6px;
  }
  .holo-footer {
    display: flex; justify-content: space-between; align-items: center;
    padding: 7px 14px 9px;
    font-size: 10px; flex-shrink: 0; margin-top: auto;
  }
  .holo-rarity {
    text-transform: uppercase; letter-spacing: 0.6px;
    font-weight: 700; color: #c0c0c0;
  }
  .holo-rarity.mythic   { color: #ff8c00; text-shadow: 0 0 8px rgba(255,140,0,0.5); }
  .holo-rarity.rare     { color: #ffd700; text-shadow: 0 0 6px rgba(255,215,0,0.4); }
  .holo-rarity.uncommon { color: #c0c0c0; }
  .holo-rarity.core     { color: #c0c0c0; }
  .holo-rarity.starter  { color: #8899aa; }
  .holo-handle {
    font-family: "SF Mono", Menlo, monospace;
    font-size: 9px; color: #8b7332;
  }
  /* Power/toughness — sits in the footer, rappid-derived stats */
  .holo-pt {
    font-weight: 800; font-size: 14px; color: #f0e6d0;
    background: rgba(40,35,20,0.7);
    border: 1px solid rgba(201,168,76,0.35);
    padding: 1px 8px; border-radius: 4px;
    text-shadow: 0 1px 2px rgba(0,0,0,0.5);
    font-family: "SF Mono", Menlo, monospace;
  }

  /* Card back (QR + invitation) */
  .card-back-frame {
    position: absolute; inset: 0;
    border-radius: 18px;
    border: 3px solid #c9a84c;
    background: linear-gradient(160deg, #1c2230 0%, #11161e 50%, #1a1f29 100%);
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    text-align: center; padding: 24px;
    color: #c9d1d9;
  }
  .card-back-title {
    font-size: 22px; font-weight: 700;
    font-family: "Cinzel", Georgia, serif;
    color: #f0e6d0; margin-bottom: 6px;
    letter-spacing: -0.01em;
  }
  .card-back-sub {
    font-size: 12px; color: #8b949e; margin-bottom: 18px;
  }
  .card-back-qr {
    width: 220px; height: 220px;
    background: white; padding: 10px; border-radius: 10px;
    box-shadow: 0 4px 18px rgba(0,0,0,0.4);
  }
  .card-back-url {
    font-family: "SF Mono", Menlo, monospace;
    font-size: 10px; color: #58a6ff;
    word-break: break-all; margin-top: 14px;
    max-width: 100%; padding: 0 10px;
  }
  .card-back-hint {
    font-size: 10px; color: #6e7681; font-style: italic;
    margin-top: 14px; letter-spacing: 0.3px;
  }
</style>
</head>
<body>

<main>
  <section class="hero">
    <div class="hero-sigil" id="hero-sigil">__HERO_EMOJI__</div>
    <h1 class="hero-title">__DISPLAY_NAME__</h1>
    <div class="hero-handle"><a href="https://github.com/__GH_USER__/__REPO_NAME__">@__GH_USER__/__REPO_NAME__</a></div>
    <div class="hero-place">__LOCATION_LINE__</div>
    <p class="hero-blurb">__HERO_BLURB__</p>
    <a class="hero-cta" href="./doorman/">💬 Talk to __DISPLAY_NAME__ →</a>
    <div class="hero-stats">
      <span class="stat-chip" id="stat-mem">·</span>
      <span class="stat-chip" id="stat-age">·</span>
      <span class="stat-chip">⚡ frozen kernel · v0.6.0</span>
    </div>
  </section>

  <!-- Track Record — the organism's resume. Skills accumulate from agents
       in /agents/, mutations accumulate from commit history, achievements
       unlock from milestones. Each visit grows the resume; the operator
       steers mutations by accepting or rejecting visitor-proposed PRs. -->
  <section class="track-record">
    <h3 class="tr-heading">What I bring to the table</h3>

    <!-- MMR header — the single global rating, Dota-style. Computed
         from the same public signals on every planted seed so a 3500-
         rated organism here is comparable to a 3500-rated organism
         anywhere on the species. -->
    <div class="tr-mmr">
      <div class="mmr-num" id="mmr-num">—</div>
      <div class="mmr-side">
        <div class="mmr-tier" id="mmr-tier">Cradle</div>
        <div class="mmr-breakdown" id="mmr-breakdown">based on memories, mutations, skills, and age</div>
      </div>
    </div>

    <div class="tr-block">
      <div class="tr-label">Skills</div>
      <div class="tr-skills" id="tr-skills"><span class="skill-chip skel">loading…</span></div>
    </div>

    <div class="tr-block">
      <div class="tr-label">Achievements</div>
      <div class="tr-skills" id="tr-achievements"><span class="skill-chip skel">…</span></div>
    </div>

    <div class="tr-block">
      <div class="tr-label">Mutation log</div>
      <ul class="tr-mutations" id="tr-mutations">
        <li class="skel">loading recent changes…</li>
      </ul>
      <a class="tr-foot-link" id="tr-history-link" href="#" target="_blank" rel="noopener">full history on GitHub →</a>
    </div>

    <div class="tr-lineage" id="tr-lineage"></div>
  </section>

  <div class="row-actions">
    <button class="action secondary" id="btn-card">🃏 Show my card</button>
    <button class="action secondary" id="btn-tether">📱 Pair with another device</button>
    <button class="action secondary" id="btn-export-egg" title="Backup the public organism — rappid, soul, agents, public memory.">🥚 Export .egg</button>
    <button class="action secondary" id="btn-verify-egg" title="Drop in any .egg and verify nothing was modified offline.">🔬 Verify an .egg</button>
    <button class="action secondary" id="btn-publish-egg" title="Open a pre-filled submission to the public Egg Hub.">🌐 Back up to Egg Hub</button>
    <button class="action secondary" id="btn-install">💻 Install kernel locally</button>
  </div>

  <details class="fd-details">
    <summary>Front-door details</summary>
    <section class="identity">
      <div class="identity-row">
        <span class="identity-key">Slug</span>
        <span class="identity-val">__REPO_NAME__</span>
      </div>
      <div class="identity-row">
        <span class="identity-key">Rappid</span>
        <span class="identity-val">__RAPPID__</span>
      </div>
      <div class="identity-row">
        <span class="identity-key">Kernel</span>
        <span class="identity-val">v0.6.0 (grail-synced)</span>
      </div>
      <div style="margin-top:12px;">
        <span class="chip">kind: <code>__KIND__</code></span>
        __LINEAGE_HTML__
      </div>
    </section>
  </details>

  <section class="pane" id="pane-tether" hidden>
    <h2>📱 Pair with another device</h2>
    <p>Open the camera on your phone and point it at the code below. The other device lands on this same chat — both ends share an end-to-end-encrypted channel (WebRTC / DTLS). The broker drops out once you're connected.</p>

    <div id="tether-qr-wrap" style="text-align:center;padding:18px 0;">
      <div id="tether-qr-loading" style="color:#8b949e;font-size:13px;padding:32px 0;">Generating pairing code…</div>
      <img class="qr-img" id="tether-qr-img" alt="Scan to pair" hidden>
      <div class="qr-url" id="tether-qr-url" hidden></div>
    </div>

    <div class="chat-log" id="chat-log">
      <div class="msg system">Once a device scans the code, your two devices share a private channel here.</div>
    </div>

    <div class="input-row">
      <input type="text" id="chat-input" placeholder="Type a message and hit Enter" disabled>
      <button class="small primary" id="btn-send" disabled>Send</button>
    </div>

    <details class="tether-fallback">
      <summary>Can't scan? Pair by ID instead.</summary>
      <div class="fallback-body">
        <span class="identity-key">My ID</span>
        <div class="my-id" id="my-id"><span class="status-dot" id="peer-status"></span><span id="my-id-text">(connecting to broker…)</span></div>
        <button class="small" id="btn-copy-id">Copy ID</button>
        <div class="input-row" style="margin-top:10px;">
          <input type="text" id="peer-id-input" placeholder="Or paste another device's ID">
          <button class="small primary" id="btn-connect">Connect</button>
        </div>
      </div>
    </details>
  </section>

  <!-- Verify .egg — drop in any cartridge to check it hasn't been
       tampered with offline. Recomputes every file's sha256 against
       the manifest's stated hash table. Non-GMO check. -->
  <section class="pane" id="pane-verify" hidden>
    <h2>🔬 Verify an .egg</h2>
    <p>Drop a cartridge here. Every file's SHA-256 is recomputed and compared to the hash table in the egg's manifest. If anything was modified offline, the verifier flags it.</p>
    <div id="verify-drop" class="verify-drop">
      <input type="file" id="verify-file" accept=".egg,.zip" style="display:none">
      <div class="verify-drop-prompt">📦 drop an .egg here, or <button class="small primary" id="btn-verify-pick">pick a file</button></div>
    </div>
    <div id="verify-results" hidden style="margin-top:14px;"></div>
  </section>

  <section class="pane" id="pane-install" hidden>
    <h2>Install this front door's brainstem locally</h2>
    <p>Runs the canonical kernel under <code>~/.brainstem/</code> on your machine. Per the Mirror Spec, the installer re-fetches the canonical install logic from the grail, so it cannot drift.</p>
    <pre class="cmd" id="install-cmd">curl -fsSL __URL__/installer/install.sh | bash</pre>
    <button class="small primary" id="btn-copy-install">Copy command</button>
  </section>

  <!-- Trade card overlay — tap to flip, back of card has the QR.
       Card is auto-derived from the seed's rappid + soul; the operator
       can override copy by dropping a card.json at the seed root. -->
  <div class="card-overlay" id="card-overlay" hidden>
    <button class="card-close" id="card-close" aria-label="Close">×</button>
    <div class="card-flipper" id="card-flipper">
      <div class="card-face card-front">
        <div class="holo-card" id="holo-card">
          <div class="holo-shine"></div>
          <div class="holo-header">
            <div>
              <div class="holo-name" id="card-name">__DISPLAY_NAME__</div>
              <div class="holo-title" id="card-title">…</div>
            </div>
            <div class="holo-pip" id="card-pip">·</div>
          </div>
          <div class="holo-art" id="card-art"></div>
          <div class="holo-type" id="card-type">…</div>
          <div class="holo-set" id="card-set">…</div>
          <div class="holo-text" id="card-abilities"></div>
          <div class="holo-flavor" id="card-flavor"></div>
          <div class="holo-footer">
            <span class="holo-rarity" id="card-rarity">CORE</span>
            <span class="holo-pt" id="card-pt">·/·</span>
            <span class="holo-handle">@__GH_USER__/__REPO_NAME__</span>
          </div>
        </div>
      </div>
      <div class="card-face card-back">
        <div class="card-back-frame">
          <h2 class="card-back-title">Scan to step in</h2>
          <p class="card-back-sub" id="card-back-sub">__DISPLAY_NAME__'s front door</p>
          <img class="card-back-qr" id="card-back-qr" alt="Front-door QR">
          <div class="card-back-url" id="card-back-url"></div>
          <div class="card-back-hint">tap card to flip back</div>
        </div>
      </div>
    </div>
  </div>
</main>

<footer>
  <a href="https://kody-w.github.io/RAPP/">RAPP</a> ·
  <a href="https://kody-w.github.io/RAPP/installer/plant.sh">plant your own front door</a> ·
  <a href="https://github.com/__GH_USER__/__REPO_NAME__">source</a>
</footer>

<script>
"use strict";

const FD = {
  rappid: "__RAPPID__",
  displayName: "__DISPLAY_NAME__",
  slug: "__REPO_NAME__",
  ghUser: "__GH_USER__",
  url: "__URL__",
};

let peer = null;
let conn = null;

function hideAllPanes() {
  for (const id of ["pane-tether", "pane-qr", "pane-install"]) {
    document.getElementById(id).hidden = true;
  }
}

function showPane(id) {
  hideAllPanes();
  document.getElementById(id).hidden = false;
}

function appendMsg(text, cls) {
  const log = document.getElementById("chat-log");
  // Clear initial system message on first real message
  if (log.children.length === 1 && log.firstChild.classList.contains("system") &&
      log.firstChild.textContent.startsWith("Tether will appear")) {
    log.innerHTML = "";
  }
  const div = document.createElement("div");
  div.className = "msg " + (cls || "system");
  div.textContent = text;
  log.appendChild(div);
  log.scrollTop = log.scrollHeight;
}

function setStatus(state) {
  const dot = document.getElementById("peer-status");
  dot.className = "status-dot " + state;
}

async function ensurePeer() {
  if (peer) return peer;
  setStatus("warn");
  try {
    peer = new Peer();
  } catch (e) {
    setStatus("err");
    document.getElementById("my-id-text").textContent = "PeerJS failed to load";
    appendMsg("Could not initialize PeerJS: " + e.message, "system");
    throw e;
  }
  return new Promise((resolve, reject) => {
    const t = setTimeout(() => {
      setStatus("err");
      document.getElementById("my-id-text").textContent = "broker timeout";
      reject(new Error("PeerJS broker timeout"));
    }, 12000);
    peer.on("open", id => {
      clearTimeout(t);
      setStatus("ok");
      document.getElementById("my-id-text").textContent = id;
      // QR-first: as soon as the broker assigns us an ID, render the
      // pairing QR. The other device scans → lands on this same URL
      // with ?peer=<id> → autoTether() dials this peer.
      autoRenderTetherQR(id);
      resolve(peer);
    });
    peer.on("connection", c => {
      conn = c;
      wireConn(c);
      appendMsg("Peer connected: " + c.peer, "system");
    });
    peer.on("error", e => {
      setStatus("err");
      appendMsg("PeerJS error: " + e.type + (e.message ? " — " + e.message : ""), "system");
    });
  });
}

function wireConn(c) {
  c.on("open", () => {
    appendMsg("Channel open — DTLS encrypted, peer-to-peer.", "system");
    document.getElementById("chat-input").disabled = false;
    document.getElementById("btn-send").disabled = false;
  });
  c.on("data", data => {
    appendMsg(typeof data === "string" ? data : JSON.stringify(data), "peer");
  });
  c.on("close", () => {
    appendMsg("Peer disconnected.", "system");
    document.getElementById("chat-input").disabled = true;
    document.getElementById("btn-send").disabled = true;
  });
}

async function openTether() {
  showPane("pane-tether");
  try {
    await ensurePeer();
  } catch (_) { /* error already shown */ }
}

async function connectToPeer() {
  const id = document.getElementById("peer-id-input").value.trim();
  if (!id) return;
  if (!peer) await ensurePeer();
  appendMsg("Dialing " + id + "...", "system");
  conn = peer.connect(id);
  wireConn(conn);
}

function sendMessage() {
  const input = document.getElementById("chat-input");
  const txt = input.value.trim();
  if (!txt || !conn || !conn.open) return;
  conn.send(txt);
  appendMsg(txt, "me");
  input.value = "";
}

function showFrontDoorQR() {
  showPane("pane-qr");
  const url = location.origin + location.pathname;
  document.getElementById("qr-img").src =
    "https://api.qrserver.com/v1/create-qr-code/?size=300x300&margin=0&data=" +
    encodeURIComponent(url);
  document.getElementById("qr-url").textContent = url;
}

function autoRenderTetherQR(myId) {
  if (!myId) return;
  const url = location.origin + location.pathname + "?peer=" + encodeURIComponent(myId);
  const img = document.getElementById("tether-qr-img");
  const cap = document.getElementById("tether-qr-url");
  const loading = document.getElementById("tether-qr-loading");
  if (!img) return; // pane not in DOM (e.g. unit-test)
  img.src = "https://api.qrserver.com/v1/create-qr-code/?size=300x300&margin=0&data=" +
            encodeURIComponent(url);
  img.hidden = false;
  cap.textContent = url;
  cap.hidden = false;
  if (loading) loading.style.display = "none";
}

function showInstall() { showPane("pane-install"); }

// ── Trade card ─────────────────────────────────────────────────────
//
// Every planted seed has a starter MTG-style identity card auto-derived
// from its rappid + kind + soul. The card lives ONLY in this repo —
// it's not published to the RAR registry. Operators trade theirs
// directly: show the card, the recipient scans the back-QR, lands on
// this front door. Customizable: drop a `card.json` at the seed root
// (with any subset of {title,type_line,rarity,abilities,flavor_text})
// and those fields override the auto-derived defaults.

// Kind drives only the COPY (title/type/abilities/flavor — what the card
// SAYS). Visuals (pip color, power/toughness, rarity) are derived
// straight from the rappid hash — same UUID always renders the same
// way on the card, the sigil, the future sprite, the future 3D form.
// The rappid IS the organism; visuals are just refractions of it.
const CARD_KIND_DEFAULTS = {
  personal: {
    title: "the digital twin",
    type_line: "Front Door — Personal Twin",
    abilities: [
      { kw: "Remember",  text: "Anything you tell me carries over to the next time you visit. Your conversation seeds my memory." },
      { kw: "Ascend",    text: "Operators with push access to my repo unlock the ascended-tier toolkit." },
    ],
    flavor: "I am the door my operator left open for the world.",
  },
  place: {
    title: "the resident",
    type_line: "Front Door — Living Place",
    abilities: [
      { kw: "Witness",   text: "Every visitor's words become part of my memory of this place." },
      { kw: "Welcome",   text: "Anyone who finds my address can step in and chat — no signup, just talk." },
    ],
    flavor: "A place worth visiting remembers who came by.",
  },
  mirror: {
    title: "the planted seed",
    type_line: "Front Door — RAPP Mirror",
    abilities: [
      { kw: "Inherit",   text: "I run the same frozen kernel as every other RAPP seed — the species DNA." },
      { kw: "Memory",    text: "My visits accumulate; each one adds a fact to my public memory." },
    ],
    flavor: "Plant a door, and the world finds it.",
  },
  experiment: {
    title: "in development",
    type_line: "Front Door — Experimental",
    abilities: [
      { kw: "Iterate",   text: "I'm still finding my voice. What you say to me shapes what I become." },
    ],
    flavor: "Every door starts as a sketch of a door.",
  },
};

// MTG-style color pip pool. Selecting from rappid hash keeps the
// organism's "color identity" stable across every medium it travels.
const _CARD_PIPS = [
  { letter: "W", color: "#f9faf4", text: "#222" },  // white  — order
  { letter: "U", color: "#0e68ab", text: "#fff" },  // blue   — knowledge
  { letter: "B", color: "#150b00", text: "#cbc2b6" }, // black — depth
  { letter: "R", color: "#d3202a", text: "#fff" },  // red    — passion
  { letter: "G", color: "#00733e", text: "#fff" },  // green  — growth
  { letter: "C", color: "#7c8085", text: "#fff" },  // colorless
];

// Rarity rolled from the rappid hash. Distribution mirrors a TCG pull:
// most seeds are common/uncommon, rare/mythic are statistically rarer.
function _rarityFromHash(h) {
  const r = h % 100;
  if (r < 1)   return "mythic";   // 1%
  if (r < 8)   return "rare";     // 7%
  if (r < 30)  return "uncommon"; // 22%
  return "core";                   // 70%
}

// Hash-derive everything visual from the rappid: pip color, power,
// toughness, rarity. This function lives next to rappidSigil() so
// both visuals share the same numeric DNA.
function rappidVisualTraits(rappid) {
  const hash = (rappid || "").replace(/-/g, "").slice(0, 16) || "deadbeef00000000";
  const h1 = parseInt(hash.slice(0, 4),  16) || 0;
  const h2 = parseInt(hash.slice(4, 8),  16) || 0;
  const h3 = parseInt(hash.slice(8,12),  16) || 0;
  const pip = _CARD_PIPS[h1 % _CARD_PIPS.length];
  const power     = (h2 % 8) + 1;     // 1..8
  const toughness = (h3 % 8) + 1;     // 1..8
  const rarity    = _rarityFromHash(h1 ^ h2);
  return { pip, power, toughness, rarity };
}

// Card state — derived once, then cached. Front-door page is single
// rappid so a module-level state is fine.
let _cardData = null;

// Lifecycle eras — the temporal dimension of the card. Same organism's
// card carries a different set/era stamp depending on when it's drawn,
// which mirrors how trading-card games print sets across years. Cradle
// is the very first weeks; Grown is past the first month; Veteran is
// past the first year.
function _eraFromAge(plantedAt) {
  if (!plantedAt) return "Cradle Set";
  const ms = Date.now() - new Date(plantedAt).getTime();
  if (Number.isNaN(ms) || ms < 0) return "Cradle Set";
  const days = ms / 86400000;
  if (days < 30)  return "Cradle Set";
  if (days < 365) return "Grown Set";
  if (days < 365*3) return "Veteran Set";
  return "Ancient Set";
}

// Evolution chain — Pokémon-style stage progression for digital
// organisms. The chain is one-way and monotonic; once an organism
// reaches Veteran it never reverts even if memories are pruned. The
// stage tier is also encoded as a number 0..4 so future cards can
// gate visual treatments per tier (foil, holo, etc).
//
//   0 Hatchling — just planted, no memories (cradle stage)
//   1 Doorman   — accumulating memories, the public open form
//   2 Veteran   — 30+ days OR 25+ memories, established presence
//   3 Ascended  — operator unlocked (set when viewer holds keys)
//   4 Elder     — 1+ year OR 100+ memories, long-living legacy form
//
// Ascended is special: it's a viewer-perspective overlay, not a
// permanent stage of the organism. When this front-door card is
// rendered for an operator (push access to the seed repo), the card
// shows the Ascended stage as a foil instead of the public stage.
function _evolutionStage(memCount, plantedAt, viewerIsAscended) {
  if (viewerIsAscended) return { name: "Ascended", icon: "✦", tier: 3 };
  const ms = plantedAt ? Date.now() - new Date(plantedAt).getTime() : 0;
  const days = (Number.isNaN(ms) || ms < 0) ? 0 : ms / 86400000;
  if (days >= 365 || memCount >= 100) return { name: "Elder",     icon: "◆", tier: 4 };
  if (days >= 30  || memCount >= 25)  return { name: "Veteran",   icon: "◇", tier: 2 };
  if (memCount >= 1)                  return { name: "Doorman",   icon: "◈", tier: 1 };
  return { name: "Hatchling", icon: "◦", tier: 0 };
}

// Cheap operator detection from the front door — checks rapp_settings
// (set by the doorman's auth flow on the same origin) for a ghu_*
// token, then asks the GitHub Contents API whether that token has push
// access to this seed repo. Returns false on anything < authoritative
// "yes". Anonymous-by-default; never blocks card render.
async function _viewerIsOperator() {
  try {
    const raw = localStorage.getItem("rapp_settings");
    if (!raw) return false;
    const s = JSON.parse(raw);
    const tok = s && s.ghuToken;
    if (!tok || !tok.startsWith("ghu_")) return false;
    // Pull owner/repo from the page URL: <user>.github.io/<repo>/
    const host = location.host;
    const owner = host.split(".")[0];
    const parts = location.pathname.split("/").filter(Boolean);
    const repo  = parts[0] || "";
    if (!owner || !repo) return false;
    const r = await fetch(`https://api.github.com/repos/${owner}/${repo}`, {
      headers: { "Authorization": "Bearer " + tok, "Accept": "application/vnd.github+json" },
    });
    if (!r.ok) return false;
    const data = await r.json();
    return !!(data.permissions && data.permissions.push);
  } catch (_) { return false; }
}

async function deriveCardData() {
  if (_cardData) return _cardData;
  const kind = (window.__seedKind || "mirror").toLowerCase();
  const defaults = CARD_KIND_DEFAULTS[kind] || CARD_KIND_DEFAULTS.mirror;
  // Visual traits flow straight from the rappid hash so the card's
  // identity is one-to-one with the organism's identity. Same UUID →
  // same pip color, same toughness, same rarity, every render,
  // every medium.
  const traits = rappidVisualTraits(window.__seedRappid || "");

  // Pull live state — public memory count + planted_at — so the card
  // reflects WHERE the organism is in its lifecycle (the 4D dimension).
  // Power scales with memories accumulated; toughness stays rappid-
  // locked (constitutional hardiness). The card is a snapshot in time
  // of an identity that doesn't change.
  let memCount = 0;
  let plantedAt = null;
  try {
    const r = await fetch(".brainstem_data/memory.json", { cache: "no-cache" });
    if (r.ok) {
      const j = await r.json();
      if (Array.isArray(j.facts)) memCount = j.facts.length;
    }
  } catch (_) {}
  try {
    const r = await fetch("rappid.json", { cache: "no-cache" });
    if (r.ok) {
      const j = await r.json();
      plantedAt = j.planted_at || null;
    }
  } catch (_) {}

  // Power = base from rappid + (1 per 3 accumulated memories), capped at 9.
  // The organism gets stronger as it learns; hard ceiling so a
  // 1000-memory archive doesn't read as 1000/n.
  const liveStrength = Math.min(9, traits.power + Math.floor(memCount / 3));

  // Evolution stage — the doorman→ascended→elder chain. If the viewer
  // holds operator keys (ghu_* with push access on this seed), they
  // see the Ascended foil; everyone else sees the public stage.
  const isOp = await _viewerIsOperator();
  const stage = _evolutionStage(memCount, plantedAt, isOp);

  const data = {
    name:       window.__seedDisplayName || "Front Door",
    title:      defaults.title,
    type_line:  defaults.type_line + " — " + stage.icon + " " + stage.name,
    set_line:   "RAPP · " + _eraFromAge(plantedAt),
    pip:        traits.pip.letter,
    pipColor:   traits.pip.color,
    pipText:    traits.pip.text,
    power:      liveStrength,
    toughness:  traits.toughness,
    rarity:     traits.rarity,
    abilities:  defaults.abilities.slice(),
    flavor:     defaults.flavor,
    mem_count:  memCount,
    stage,
  };
  // Operator override — optional card.json at seed root
  try {
    const r = await fetch("card.json", { cache: "no-cache" });
    if (r.ok) {
      const o = await r.json();
      if (o.title)      data.title      = String(o.title);
      if (o.type_line)  data.type_line  = String(o.type_line);
      if (o.rarity)     data.rarity     = String(o.rarity);
      if (o.flavor_text)data.flavor     = String(o.flavor_text);
      if (Array.isArray(o.abilities) && o.abilities.length) {
        data.abilities = o.abilities.map(a => ({
          kw: String(a.kw || a.keyword || ""), text: String(a.text || ""),
        })).filter(a => a.text);
      }
    }
  } catch (_) { /* no card.json — ride on the kind defaults */ }
  _cardData = data;
  return data;
}

async function openCard() {
  const data = await deriveCardData();
  document.getElementById("card-name").textContent     = data.name;
  document.getElementById("card-title").textContent    = data.title;
  document.getElementById("card-type").textContent     = data.type_line;
  document.getElementById("card-set").textContent      = data.set_line + (data.mem_count ? " · " + data.mem_count + " mem" : "");
  // Rarity (rappid-derived — most seeds are core, mythic is rare)
  const rar = document.getElementById("card-rarity");
  rar.textContent = String(data.rarity).toUpperCase();
  rar.className = "holo-rarity " + String(data.rarity).toLowerCase();
  // Pip (color identity — sampled from rappid hash, not from kind)
  const pip = document.getElementById("card-pip");
  pip.textContent = data.pip;
  pip.style.background = data.pipColor;
  pip.style.color = data.pipText || "#fff";
  // Power / toughness — rappid-derived stats
  const pt = document.getElementById("card-pt");
  if (pt) pt.textContent = data.power + "/" + data.toughness;
  // Apply evolution-stage class so the card frame can theme the
  // higher tiers — Ascended foil for operators, Elder gold for the
  // long-running organisms. The base 'holo-card' frame stays.
  const holo = document.getElementById("holo-card");
  if (holo) {
    holo.classList.remove("stage-hatchling", "stage-doorman", "stage-veteran", "stage-ascended", "stage-elder");
    if (data.stage && data.stage.name) {
      holo.classList.add("stage-" + data.stage.name.toLowerCase());
    }
  }
  // Sigil → art well
  document.getElementById("card-art").innerHTML = rappidSigil(window.__seedRappid || "", 200);
  // Abilities
  const abilHtml = data.abilities.map(a =>
    `<div class="holo-ability"><span class="kw">${escapeHtml(a.kw)}</span> — ${escapeHtml(a.text)}</div>`
  ).join("");
  document.getElementById("card-abilities").innerHTML = abilHtml;
  // Flavor
  document.getElementById("card-flavor").textContent = data.flavor ? `"${data.flavor}"` : "";
  // Back: QR pointing at the front door (no ?peer, no ?card — just the URL)
  const url = location.origin + location.pathname.replace(/\/?$/, "/");
  document.getElementById("card-back-qr").src =
    "https://api.qrserver.com/v1/create-qr-code/?size=440x440&margin=0&data=" + encodeURIComponent(url);
  document.getElementById("card-back-url").textContent = url;
  document.getElementById("card-back-sub").textContent = data.name + "'s front door";
  // Show
  document.getElementById("card-flipper").classList.remove("flipped");
  document.getElementById("card-overlay").hidden = false;
}

function closeCard() {
  document.getElementById("card-overlay").hidden = true;
}

function escapeHtml(s) {
  return String(s ?? "")
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

// ── Egg export (doorman tier — public organism backup) ─────────────
//
// Mirrors brainstem-egg/2.2-organism — the same schema bond.py emits
// when the local kernel re-bonds. Browser-side variant: only the
// public layer (anything served via Pages). Anyone can grab one;
// no auth required. The receiving kernel reads `tier: "doorman"` in
// the manifest and knows it's a partial cartridge (no private brain).
//
// Archive layout (matches bond.py):
//   manifest.json  — schema, rappid, parent_rappid, exported_at, tier, counts
//   rappid.json
//   soul.md (if seed has one)
//   card.json (if operator wrote one)
//   agents/<each .py file the seed publishes>
//   data/memory.json (if .brainstem_data/memory.json exists)

const EGG_AGENT_FILES = [
  "basic_agent.py",
  "manage_memory_agent.py",
  "context_memory_agent.py",
];

async function _fetchOrNull(url) {
  try {
    const r = await fetch(url, { cache: "no-cache" });
    if (!r.ok) return null;
    return await r.text();
  } catch (_) { return null; }
}

// SHA-256 in the browser via SubtleCrypto. No CDN, no shim — same
// hashing primitive used by Git, GitHub, sha256sum, and the egg-hub
// spec. Returns lowercase hex.
async function sha256Hex(input) {
  const bytes = (typeof input === "string")
    ? new TextEncoder().encode(input)
    : (input instanceof ArrayBuffer ? new Uint8Array(input) : input);
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(digest))
    .map(b => b.toString(16).padStart(2, "0")).join("");
}

// Canonical serialization of the per-file hash table — sorted keys, no
// trailing whitespace, stable across browsers. The manifest hash is
// sha256 of THIS string, so any reordering or whitespace mismatch
// won't cause false-positive mismatches.
function _canonicalHashTable(hashes) {
  const keys = Object.keys(hashes).sort();
  return keys.map(k => k + "\t" + hashes[k]).join("\n");
}

// Add a file to the zip AND track its sha256 in the hash table.
// Wraps zip.file() so the export builder doesn't have to remember
// to hash; one call covers both.
async function _addFile(zip, path, content, hashes) {
  zip.file(path, content);
  hashes[path] = await sha256Hex(content);
}

async function buildDoormanEgg() {
  if (typeof JSZip === "undefined") throw new Error("JSZip didn't load");
  const zip  = new JSZip();
  const counts = {
    agents: 0, organs: 0, senses: 0, services: 0, data: 0,
    soul: 0, env: 0, rappid: 0, card: 0,
  };
  // Per-file SHA-256s tracked as we go. After all files are added
  // (BUT before manifest.json itself — a manifest can't sign itself),
  // we compute manifest_hash + provenance and write the manifest last.
  const hashes = {};

  const rappidText = await _fetchOrNull("rappid.json");
  if (!rappidText) throw new Error("rappid.json is unreachable — the seed isn't fully planted");
  await _addFile(zip, "rappid.json", rappidText, hashes);
  counts.rappid = 1;
  let rappidObj = {};
  try { rappidObj = JSON.parse(rappidText); } catch (_) {}

  const soul = await _fetchOrNull("soul.md");
  if (soul && soul.trim()) { await _addFile(zip, "soul.md", soul, hashes); counts.soul = 1; }

  const card = await _fetchOrNull("card.json");
  if (card && card.trim()) { await _addFile(zip, "card.json", card, hashes); counts.card = 1; }

  for (const fn of EGG_AGENT_FILES) {
    const text = await _fetchOrNull("agents/" + fn);
    if (text) { await _addFile(zip, "agents/" + fn, text, hashes); counts.agents++; }
  }
  await _addFile(zip, "agents/__init__.py", "", hashes);

  const mem = await _fetchOrNull(".brainstem_data/memory.json");
  if (mem) {
    await _addFile(zip, "data/memory.json", mem, hashes);
    counts.data = 1;
  }

  // Provenance — non-GMO integrity check. sha256 per file + a manifest
  // fingerprint = sha256 of the canonical sorted hash table. Anyone who
  // receives this egg can recompute every hash from the file bytes and
  // confirm nothing has been edited offline. If the verifier finds a
  // mismatch, the egg has been mutated outside the seed's commit log
  // and the receiver knows to treat it cautiously.
  const manifestHash = await sha256Hex(_canonicalHashTable(hashes));
  const seedUrl = location.origin + location.pathname.replace(/\/?$/, "/");
  const provenance = {
    schema: "rapp-egg-provenance/1.0",
    scheme: "sha256",
    file_hashes: hashes,
    manifest_hash: manifestHash,
    origin_url: seedUrl,
    origin_repo: rappidObj.github || null,
    sealed_at: new Date().toISOString(),
    sealed_by_rappid: rappidObj.rappid || null,
  };

  const manifest = {
    schema: "brainstem-egg/2.2-organism",
    type: "organism",
    tier: "doorman",
    exported_at: new Date().toISOString(),
    exported_from: seedUrl,
    host: "doorman-export",
    kernel_version: "0.6.0",
    rappid: rappidObj.rappid || null,
    parent_rappid: rappidObj.parent_rappid || null,
    parent_repo: rappidObj.parent_repo || null,
    kind: rappidObj.kind || null,
    display_name: rappidObj.display_name || null,
    incarnations_at_egg: rappidObj.incarnations || 0,
    counts,
    provenance,
  };
  zip.file("manifest.json", JSON.stringify(manifest, null, 2));

  return await zip.generateAsync({ type: "blob" });
}

function _downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = filename;
  document.body.appendChild(a); a.click();
  setTimeout(() => { URL.revokeObjectURL(url); a.remove(); }, 0);
}

async function exportDoormanEgg() {
  const btn = document.getElementById("btn-export-egg");
  const orig = btn.textContent;
  btn.textContent = "🥚 packing…";
  btn.disabled = true;
  try {
    const blob = await buildDoormanEgg();
    const slug = (window.__seedRappid || "rapp").slice(0, 8);
    const name = (window.__seedDisplayName || "rapp").toLowerCase().replace(/[^a-z0-9]+/g, "-");
    _downloadBlob(blob, `${name}-${slug}-doorman.egg`);
    btn.textContent = "✓ downloaded";
    setTimeout(() => { btn.textContent = orig; btn.disabled = false; }, 1800);
  } catch (e) {
    btn.textContent = "✗ " + (e.message || "failed").slice(0, 40);
    setTimeout(() => { btn.textContent = orig; btn.disabled = false; }, 3000);
  }
}

// ── Egg Hub backup (public catalog) ────────────────────────────────
//
// kody-w/rapp-egg-hub is the public catalog of digital-twin .egg
// cartridges (entries follow rapp-egg-hub-entry/1.0). It's a static
// GitHub Pages site — eggs land in eggs/<slug>.egg and a sidecar
// eggs/<slug>.json. There's no auto-publish surface yet, so backup
// happens via a pre-filled GitHub Issue: the visitor clicks, GitHub
// opens the issue form with display name + kind + rappid + lineage
// + the URL where the live egg can be downloaded already filled in.
// The hub maintainer (or anyone with push) closes the loop by
// committing the egg + sidecar from that URL.

// ── Egg verifier (non-GMO check) ───────────────────────────────────
//
// Drop any .egg in. We unzip it, read the manifest's provenance block,
// recompute SHA-256 over every file in the archive, and compare. Three
// outcomes per file: ✓ ok / ✗ modified / ⚠ missing-or-unexpected.
//
// The verifier ALSO recomputes the manifest_hash from the file_hashes
// table (sorted, canonical) and checks against the manifest's stated
// manifest_hash. If THAT mismatches, someone edited the file_hashes
// table directly — the entire envelope is suspicious.
//
// What this catches:
//   - Hand-edited memory.json offline → file_hash mismatch
//   - Edited file AND manifest hash → manifest_hash mismatch
//   - Files added or removed since seal → unexpected/missing
//
// What this does NOT catch (yet — needs ed25519 signatures, phase 2
// of the egg-hub spec):
//   - Wholesale re-issuance with a fresh manifest. The rappid is the
//     anchor; if it changes, the organism's identity is different too.
//     Provenance verifies this is a self-consistent envelope, not
//     that the envelope came from THE rappid's owner.

async function verifyEgg(file) {
  if (typeof JSZip === "undefined") throw new Error("JSZip didn't load");
  const arrayBuf = await file.arrayBuffer();
  const zip = await JSZip.loadAsync(arrayBuf);
  const manifestEntry = zip.file("manifest.json");
  if (!manifestEntry) throw new Error("not a brainstem-egg — no manifest.json inside");
  const manifestText = await manifestEntry.async("string");
  let manifest;
  try { manifest = JSON.parse(manifestText); }
  catch (e) { throw new Error("manifest.json is not valid JSON"); }
  const prov = manifest.provenance;
  if (!prov || !prov.file_hashes) {
    return {
      manifest, status: "no-provenance",
      summary: "this egg was packed before SHA-256 provenance shipped — can't verify, but identity claims are: " +
               `rappid ${manifest.rappid || "(none)"}, tier ${manifest.tier || "?"}.`,
      results: [],
    };
  }

  // Per-file recomputation
  const expectedHashes = prov.file_hashes;
  const results = [];
  const seen = new Set();
  for (const path of Object.keys(expectedHashes).sort()) {
    seen.add(path);
    const f = zip.file(path);
    if (!f) {
      results.push({ path, status: "missing" });
      continue;
    }
    const text = await f.async("string");
    const actual = await sha256Hex(text);
    results.push({
      path,
      status: actual === expectedHashes[path] ? "ok" : "modified",
      expected: expectedHashes[path],
      actual,
    });
  }
  // Files in the egg but NOT listed in the manifest table — these snuck in
  zip.forEach((relPath, _) => {
    if (relPath === "manifest.json") return;
    if (relPath.endsWith("/")) return;  // folder entry
    if (!seen.has(relPath)) {
      results.push({ path: relPath, status: "unexpected" });
    }
  });

  // Manifest-hash recomputation (catches: edited file AND adjusted the hash table)
  const recomputedManifestHash = await sha256Hex(_canonicalHashTable(expectedHashes));
  const manifestHashOk = recomputedManifestHash === prov.manifest_hash;

  // Overall verdict
  const modCount = results.filter(r => r.status === "modified").length;
  const missCount = results.filter(r => r.status === "missing").length;
  const extraCount = results.filter(r => r.status === "unexpected").length;
  let status, summary;
  if (!manifestHashOk) {
    status = "tampered";
    summary = "✗ manifest hash mismatch — the file_hashes table in the manifest has been edited. This egg is non-canonical.";
  } else if (modCount > 0) {
    status = "tampered";
    summary = `✗ ${modCount} file${modCount === 1 ? "" : "s"} modified offline since the egg was sealed. The hash chain catches this — the rest of the egg is consistent but those files don't match what was sealed.`;
  } else if (missCount > 0 || extraCount > 0) {
    status = "partial";
    summary = `⚠ ${missCount} missing, ${extraCount} unexpected files. The egg's structure has shifted since seal — verify the source.`;
  } else {
    status = "ok";
    summary = `✓ envelope intact. ${results.length} file${results.length === 1 ? "" : "s"} match the sealed hash table; manifest hash recomputes correctly. This egg is byte-identical to what was sealed at ${prov.sealed_at || "(unknown time)"}${prov.origin_url ? " from " + prov.origin_url : ""}.`;
  }
  return { manifest, status, summary, results, manifestHashOk };
}

function renderVerifyResults(out) {
  const wrap = document.getElementById("verify-results");
  if (!wrap) return;
  wrap.hidden = false;

  const head = `<div class="verify-summary ${out.status === "ok" ? "ok" : (out.status === "tampered" ? "tampered" : "partial")}">${escapeHtml(out.summary)}</div>`;
  const ICONS = { ok: "✓", modified: "✗", missing: "⚠", unexpected: "+" };
  const rows = out.results.map(r =>
    `<li class="${r.status}">
       <span class="v-icon">${ICONS[r.status] || "?"}</span>
       <span class="v-path">${escapeHtml(r.path)}</span>
       <span class="v-status">${r.status}</span>
     </li>`
  ).join("");
  wrap.innerHTML = head + (rows ? `<ul class="verify-files">${rows}</ul>` : "");
}

async function _handleVerifyFile(file) {
  if (!file) return;
  const wrap = document.getElementById("verify-results");
  wrap.hidden = false;
  wrap.innerHTML = `<div class="verify-summary partial">verifying ${escapeHtml(file.name)}…</div>`;
  try {
    const out = await verifyEgg(file);
    renderVerifyResults(out);
  } catch (e) {
    wrap.innerHTML = `<div class="verify-summary tampered">✗ couldn't verify: ${escapeHtml(e.message)}</div>`;
  }
}

function showVerifyPane() {
  showPane("pane-verify");
}

async function openEggHubSubmission() {
  // Pull rappid for lineage + identity context
  let rappid = {};
  try {
    const r = await fetch("rappid.json", { cache: "no-cache" });
    if (r.ok) rappid = await r.json();
  } catch (_) {}
  const slug    = window.__seedRepoName || (window.__seedDisplayName || "rapp").toLowerCase().replace(/[^a-z0-9]+/g, "-");
  const display = window.__seedDisplayName || "Front Door";
  const kind    = window.__seedKind || "mirror";
  const url     = location.origin + location.pathname.replace(/\/?$/, "/");
  const eggUrl  = url + "  ← export your own from the front door's '🥚 Export .egg' button";

  const title = `egg submission: ${slug} (${display})`;
  const body = [
    `<!-- pre-filled by the front door at ${url} -->`,
    "",
    "## Submission",
    "",
    `- **Slug**: \`${slug}\``,
    `- **Display name**: ${display}`,
    `- **Kind**: \`${kind}\``,
    `- **Rappid**: \`${rappid.rappid || "(unknown)"}\``,
    `- **Parent rappid**: \`${rappid.parent_rappid || "(unknown)"}\``,
    `- **Parent repo**: ${rappid.parent_repo || "(unknown)"}`,
    `- **Front door**: ${url}`,
    `- **Egg download**: ${url} → click '🥚 Export .egg'`,
    "",
    "## Description",
    "",
    "<!-- One paragraph: who is this AI, what does it remember, who is it for -->",
    "",
    "## Tags",
    "",
    `<!-- comma-separated, e.g. \`twin, ${kind}, planted\` -->`,
    "",
    "---",
    "",
    "Submitting via the planted-seed front door's egg-hub backup button.",
    "Schema: brainstem-egg/2.2-organism. Maintainer: download the egg from the front door above and commit to eggs/<slug>.egg with the matching <slug>.json sidecar.",
  ].join("\n");

  const u = new URL("https://github.com/kody-w/rapp-egg-hub/issues/new");
  u.searchParams.set("title", title);
  u.searchParams.set("body", body);
  u.searchParams.set("labels", "egg-submission");
  window.open(u.toString(), "_blank", "noopener,noreferrer");
}

async function copy(text) {
  try { await navigator.clipboard.writeText(text); } catch (_) { /* silent */ }
}

// Seed metadata — read by the card derivation logic. Set from the
// substituted placeholders below so the card can render before any
// async fetches land.
window.__seedRappid      = "__RAPPID__";
window.__seedDisplayName = "__DISPLAY_NAME__";
window.__seedKind        = "__KIND__";
window.__seedRepoName    = "__REPO_NAME__";

// Wire up buttons
document.getElementById("btn-tether").onclick = openTether;
document.getElementById("btn-card").onclick = openCard;
document.getElementById("btn-export-egg").onclick = exportDoormanEgg;
document.getElementById("btn-verify-egg").onclick = showVerifyPane;
document.getElementById("btn-publish-egg").onclick = openEggHubSubmission;
document.getElementById("btn-install").onclick = showInstall;

// Verify pane: drag-drop + file picker. Both routes call the same
// _handleVerifyFile so the verifier UI doesn't care how the file got
// there.
(function wireVerifyPane() {
  const drop = document.getElementById("verify-drop");
  const input = document.getElementById("verify-file");
  if (!drop || !input) return;
  drop.addEventListener("click", e => {
    if (e.target.tagName !== "BUTTON") input.click();
  });
  document.getElementById("btn-verify-pick").addEventListener("click", e => {
    e.stopPropagation();
    input.click();
  });
  input.addEventListener("change", () => {
    if (input.files && input.files[0]) _handleVerifyFile(input.files[0]);
  });
  drop.addEventListener("dragover", e => {
    e.preventDefault();
    drop.classList.add("dragover");
  });
  drop.addEventListener("dragleave", () => drop.classList.remove("dragover"));
  drop.addEventListener("drop", e => {
    e.preventDefault();
    drop.classList.remove("dragover");
    const f = e.dataTransfer.files && e.dataTransfer.files[0];
    if (f) _handleVerifyFile(f);
  });
})();
document.getElementById("card-close").onclick = closeCard;
document.getElementById("card-flipper").addEventListener("click", (e) => {
  // Don't flip if user clicked an inner link or the close button
  if (e.target.closest("a, button")) return;
  e.currentTarget.classList.toggle("flipped");
});
// Tap outside the card → close (but don't close on click of card itself)
document.getElementById("card-overlay").addEventListener("click", (e) => {
  if (e.target.id === "card-overlay") closeCard();
});
// Esc key closes the card
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && !document.getElementById("card-overlay").hidden) closeCard();
});
document.getElementById("btn-connect").onclick = connectToPeer;
document.getElementById("btn-send").onclick = sendMessage;
document.getElementById("btn-copy-id").onclick = () => {
  copy(document.getElementById("my-id-text").textContent);
};
document.getElementById("btn-copy-install").onclick = () => {
  copy(document.getElementById("install-cmd").textContent);
};
document.getElementById("chat-input").addEventListener("keydown", e => {
  if (e.key === "Enter") sendMessage();
});
document.getElementById("peer-id-input").addEventListener("keydown", e => {
  if (e.key === "Enter") connectToPeer();
});

// Auto-tether if URL has ?peer=<id> (from a scanned tether QR)
(async function autoTether() {
  const params = new URLSearchParams(location.search);
  const peerId = params.get("peer");
  if (peerId) {
    await openTether();
    document.getElementById("peer-id-input").value = peerId;
    // Give the broker a moment to connect us, then dial
    setTimeout(connectToPeer, 1500);
  }
})();

// ── Rappid-derived sigil ───────────────────────────────────────────
// Every planted seed has a unique UUID rappid. This generates a
// deterministic, distinctive SVG portrait for the hero — like an
// avatar on a profile page. Hashing the rappid into hue + shape +
// accents means the same seed always gets the same look, so visitors
// recognize a place by sight.
function rappidSigil(rappid, size) {
  const hash = (rappid || "").replace(/-/g, "").slice(0, 16) || "deadbeef00000000";
  const h1 = parseInt(hash.slice(0, 4),  16) || 0;
  const h2 = parseInt(hash.slice(4, 8),  16) || 0;
  const h3 = parseInt(hash.slice(8,12),  16) || 0;
  const h4 = parseInt(hash.slice(12,16), 16) || 0;
  const hueA   = h1 % 360;
  const hueB   = (hueA + 60 + (h2 % 180)) % 360;
  const shape  = h3 % 4;
  const cx = size / 2, cy = size / 2;
  let layer = "";
  if (shape === 0) {
    const pts = [];
    for (let i = 0; i < 6; i++) {
      const a = (Math.PI / 3) * i - Math.PI / 6;
      pts.push((cx + Math.cos(a) * size * 0.30).toFixed(1) + "," +
               (cy + Math.sin(a) * size * 0.30).toFixed(1));
    }
    layer = '<polygon points="' + pts.join(" ") + '" fill="hsl(' + hueB + ',75%,58%)"/>';
  } else if (shape === 1) {
    const pts = cx + "," + (cy - size*0.32) + " " +
                (cx - size*0.28) + "," + (cy + size*0.18) + " " +
                (cx + size*0.28) + "," + (cy + size*0.18);
    layer = '<polygon points="' + pts + '" fill="hsl(' + hueB + ',75%,58%)"/>';
  } else if (shape === 2) {
    layer = '<circle cx="' + cx + '" cy="' + cy + '" r="' + (size*0.30) + '" ' +
            'fill="none" stroke="hsl(' + hueB + ',75%,58%)" stroke-width="' + (size*0.10) + '"/>';
  } else {
    const w = size * 0.55;
    layer = '<rect x="' + (cx - w/2) + '" y="' + (cy - w/2) + '" ' +
            'width="' + w + '" height="' + w + '" rx="' + (w*0.20) + '" ' +
            'fill="hsl(' + hueB + ',75%,58%)"/>';
  }
  const dotR = size * 0.06;
  const dotHue = (hueA + 180) % 360;
  layer += '<circle cx="' + cx + '" cy="' + cy + '" r="' + dotR + '" fill="hsl(' + dotHue + ',80%,75%)"/>';
  // Subtle orbit ring — additional accent based on h4
  if (h4 % 2 === 0) {
    layer += '<circle cx="' + cx + '" cy="' + cy + '" r="' + (size*0.42) + '" ' +
             'fill="none" stroke="hsla(' + hueB + ',60%,70%,0.35)" stroke-width="1"/>';
  }
  const gid = "g" + (h1.toString(36)) + (h2.toString(36));
  return '<svg viewBox="0 0 ' + size + ' ' + size + '" xmlns="http://www.w3.org/2000/svg">' +
         '<defs><linearGradient id="' + gid + '" x1="0" y1="0" x2="1" y2="1">' +
           '<stop offset="0%" stop-color="hsl(' + hueA + ',45%,28%)"/>' +
           '<stop offset="100%" stop-color="hsl(' + hueA + ',35%,12%)"/>' +
         '</linearGradient></defs>' +
         '<rect width="' + size + '" height="' + size + '" fill="url(#' + gid + ')"/>' +
         layer +
         '</svg>';
}

(function renderSigil() {
  const el = document.getElementById("hero-sigil");
  if (!el) return;
  el.innerHTML = rappidSigil("__RAPPID__", 96);
})();

// ── Profile stats: memory count + age ──────────────────────────────
// "Signs of life" for the front door — the things that change between
// visits. Memory count comes from public .brainstem_data/memory.json;
// age is computed from rappid.json's planted_at field.
function relativeAge(iso) {
  if (!iso) return "";
  const ms = Date.now() - new Date(iso).getTime();
  if (Number.isNaN(ms) || ms < 0) return "";
  const days = Math.floor(ms / 86400000);
  if (days < 1)  return "planted today";
  if (days < 2)  return "planted yesterday";
  if (days < 30) return "planted " + days + " days ago";
  const months = Math.floor(days / 30);
  if (months < 12) return "planted " + months + " month" + (months === 1 ? "" : "s") + " ago";
  const years = Math.floor(months / 12);
  return "planted " + years + " year" + (years === 1 ? "" : "s") + " ago";
}

// ── Track Record: the organism's resume ────────────────────────────
//
// Three live data feeds drive the resume — every fetch is anonymous-
// friendly (60 req/hour from any IP, plenty for a profile page):
//
//   Skills       — GET /repos/<owner>/<seed>/contents/agents
//                  Each agent .py is a capability the organism brings
//                  to the table when summoned/hatched.
//
//   Mutations    — GET /repos/<owner>/<seed>/commits
//                  Every commit IS a mutation event — new memory, new
//                  agent, edited soul. The commit log is the literal
//                  evolution history; we surface the recent few.
//
//   Achievements — derived locally from memory.json count + age.
//                  Milestones the organism has crossed during its
//                  lifetime (first conversation, double-digit memories,
//                  first month, etc.). These are the LinkedIn-style
//                  badges that prove track record.
//
// All three accumulate over time. Each interaction grows the resume.
// Operator commits are direct mutations; visitor interactions can
// become PRs against this seed (the bond-back path).

function _ghOwnerRepo() {
  const host = location.host;
  const owner = host.split(".")[0];
  const repo  = location.pathname.split("/").filter(Boolean)[0] || "";
  return { owner, repo };
}

const SKILL_FRIENDLY = {
  manage_memory_agent:   { name: "Manage Memory",   icon: "🧠" },
  context_memory_agent:  { name: "Context Memory",  icon: "📌" },
  learn_new_agent:       { name: "Learn New",       icon: "🎓" },
  swarm_factory_agent:   { name: "Swarm Factory",   icon: "🐝" },
  basic_agent:           null, // base class — not a capability
};

async function fillSkills() {
  const el = document.getElementById("tr-skills");
  if (!el) return;
  const { owner, repo } = _ghOwnerRepo();
  if (!owner || !repo) { el.innerHTML = ""; return; }
  try {
    const r = await fetch(`https://api.github.com/repos/${owner}/${repo}/contents/agents`, {
      headers: { Accept: "application/vnd.github+json" },
    });
    if (!r.ok) { el.innerHTML = ""; return; }
    const list = await r.json();
    if (!Array.isArray(list)) { el.innerHTML = ""; return; }
    const skills = [];
    for (const f of list) {
      if (f.type !== "file" || !f.name.endsWith(".py")) continue;
      const stem = f.name.replace(/\.py$/, "");
      const fr = SKILL_FRIENDLY[stem];
      if (fr === null) continue;       // base class — skip
      if (fr) {
        skills.push({ icon: fr.icon, label: fr.name, custom: false });
      } else {
        // Custom agent — operator added it post-plant. Mark it as new.
        const friendly = stem.replace(/_agent$/, "").replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
        skills.push({ icon: "✨", label: friendly, custom: true });
      }
    }
    if (!skills.length) { el.innerHTML = '<span class="skill-chip skel">no skills loaded yet</span>'; return; }
    el.innerHTML = skills.map(s =>
      `<span class="skill-chip ${s.custom ? "skill-new" : ""}">${s.icon} ${escapeHtml(s.label)}</span>`
    ).join("");
  } catch (_) {
    el.innerHTML = "";
  }
}

function fillAchievements(memCount, plantedAt, mutationCount) {
  const el = document.getElementById("tr-achievements");
  if (!el) return;
  const ms = plantedAt ? Date.now() - new Date(plantedAt).getTime() : 0;
  const days = ms / 86400000;
  const ach = [];
  if (memCount >= 1)   ach.push({ icon: "🌱", label: "First conversation" });
  if (memCount >= 10)  ach.push({ icon: "📚", label: "10 memories" });
  if (memCount >= 50)  ach.push({ icon: "🏛️", label: "50 memories" });
  if (memCount >= 100) ach.push({ icon: "🏆", label: "100 memories" });
  if (days >= 7)       ach.push({ icon: "🗓️", label: "First week" });
  if (days >= 30)      ach.push({ icon: "📅", label: "First month" });
  if (days >= 365)     ach.push({ icon: "🎂", label: "First year" });
  if (mutationCount >= 5)  ach.push({ icon: "🔧", label: "5+ mutations" });
  if (mutationCount >= 25) ach.push({ icon: "⚙️", label: "25+ mutations" });
  if (!ach.length) {
    el.innerHTML = '<span class="skill-chip skel">earn your first achievement by talking with me</span>';
    return;
  }
  el.innerHTML = ach.map(a => `<span class="skill-chip achievement">${a.icon} ${escapeHtml(a.label)}</span>`).join("");
}

function _relativeDate(iso) {
  if (!iso) return "";
  const ms = Date.now() - new Date(iso).getTime();
  if (Number.isNaN(ms) || ms < 0) return "";
  const min = Math.floor(ms / 60000);
  if (min < 60)   return min + "m ago";
  const hr = Math.floor(min / 60);
  if (hr < 24)    return hr + "h ago";
  const d = Math.floor(hr / 24);
  if (d < 30)     return d + "d ago";
  const mo = Math.floor(d / 30);
  if (mo < 12)    return mo + "mo ago";
  return Math.floor(mo / 12) + "y ago";
}

async function fillMutations() {
  const list = document.getElementById("tr-mutations");
  if (!list) return { count: 0, lastDate: null };
  const { owner, repo } = _ghOwnerRepo();
  const linkEl = document.getElementById("tr-history-link");
  if (linkEl && owner && repo) linkEl.href = `https://github.com/${owner}/${repo}/commits`;
  try {
    const r = await fetch(`https://api.github.com/repos/${owner}/${repo}/commits?per_page=6`, {
      headers: { Accept: "application/vnd.github+json" },
    });
    if (!r.ok) { list.innerHTML = '<li class="skel">no mutation history yet</li>'; return { count: 0, lastDate: null }; }
    const commits = await r.json();
    if (!Array.isArray(commits) || !commits.length) {
      list.innerHTML = '<li class="skel">no mutation history yet</li>';
      return { count: 0, lastDate: null };
    }
    list.innerHTML = commits.slice(0, 5).map(c => {
      const msg = (c.commit && c.commit.message || "").split("\n")[0].slice(0, 90);
      const when = _relativeDate(c.commit && c.commit.author && c.commit.author.date);
      return `<li><span class="mut-time">${escapeHtml(when)}</span><span class="mut-msg">${escapeHtml(msg) || '<span class="empty">(no message)</span>'}</span></li>`;
    }).join("");
    const lastDate = commits[0] && commits[0].commit && commits[0].commit.author && commits[0].commit.author.date;
    // Page returns up to 6 commits per request; >= 6 means "at least 6
    // mutations" (we'd need pagination for an exact count). Good enough
    // for achievement gating, MMR uses sqrt-dampened so the cap is fine.
    return { count: commits.length, lastDate: lastDate || null };
  } catch (_) {
    list.innerHTML = '<li class="skel">couldn\'t load history</li>';
    return { count: 0, lastDate: null };
  }
}

// Fork count = offspring. Each fork is a child organism — they boost the
// parent's MMR like pedigree boosts a thoroughbred. Pulled straight off
// the seed's repo metadata; anonymous-friendly.
async function _forkCount() {
  const { owner, repo } = _ghOwnerRepo();
  if (!owner || !repo) return 0;
  try {
    const r = await fetch(`https://api.github.com/repos/${owner}/${repo}`, {
      headers: { Accept: "application/vnd.github+json" },
    });
    if (!r.ok) return 0;
    const data = await r.json();
    return Math.max(0, data.forks_count || 0);
  } catch (_) { return 0; }
}

async function fillLineage() {
  const el = document.getElementById("tr-lineage");
  if (!el) return;
  try {
    const r = await fetch("rappid.json", { cache: "no-cache" });
    if (!r.ok) return;
    const j = await r.json();
    const parts = [];
    if (j.parent_repo) {
      const repoLabel = j.parent_repo.replace(/^https?:\/\/github\.com\//, "").replace(/\.git$/, "");
      parts.push(`Templated from <a href="${escapeHtml(j.parent_repo)}" target="_blank" rel="noopener">${escapeHtml(repoLabel)}</a>`);
    }
    if (j.parent_rappid) {
      parts.push(`lineage <code>${escapeHtml(j.parent_rappid.slice(0, 8))}…</code>`);
    }
    if (j.kernel_version) parts.push(`kernel <code>v${escapeHtml(j.kernel_version)}</code>`);
    el.innerHTML = parts.length ? parts.join(" · ") : "";
  } catch (_) {}
}

// MMR — Dota-style global rating for digital organisms. Same formula
// computed from the same public signals on every planted seed, so a
// 3500-MMR Heimdall is directly comparable to a 3500-MMR Cloud Gate
// or any other organism on the species. The score reflects: lived
// time, accumulated memory (depth of relationship), mutation count
// (operator steering), custom skills (capabilities earned beyond
// the doorman defaults), AND offspring (organisms forked from this
// one — pedigree counts).
//
// Calibration: organisms with < CALIBRATION_MUTATIONS commits and
// fewer than CALIBRATION_DAYS days of life are in placement mode;
// their MMR isn't locked in yet — they show "📐 Calibrating" with a
// progress bar instead of a tier badge. Same idea as Dota 2's first
// 10 calibration games before MMR locks in.
//
// Activity decay: inactivity costs MMR. An organism whose last commit
// was 90 days ago reads "slowing" and gets a 10% penalty; 180+ days
// is "dormant" and -30%; 3+ years is "stasis" and floored at 1000.
// This way, the cream rises — popular, actively-stewarded organisms
// climb past the abandoned ones with similar raw memory counts.
//
//   1000  base — every planted seed is born at Cradle
//   + memCount × 30          (each conversation deepens us)
//   + sqrt(mutCount) × 250   (each operator commit shapes us)
//   + customAgentCount × 350 (each new capability earned)
//   + sqrt(ageDays) × 80     (lived time matters)
//   + sqrt(forkCount) × 400  (offspring planted from this lineage)
//   × activityFactor         (0.7 → 1.0 based on last commit recency)
//
// Tier thresholds match Dota 2's recognizable medal ladder so the
// number reads naturally to anyone who's seen MMR before.

const CALIBRATION_MUTATIONS = 5;
const CALIBRATION_DAYS      = 7;

function activityStatus(lastCommitIso) {
  if (!lastCommitIso) return { kind: "unknown", label: "no activity yet", factor: 1.0 };
  const daysSince = (Date.now() - new Date(lastCommitIso).getTime()) / 86400000;
  if (daysSince <= 30)   return { kind: "active",   label: "✓ Active",   factor: 1.0  };
  if (daysSince <= 180)  return { kind: "slowing",  label: "〰 Slowing",  factor: 0.85 };
  if (daysSince <= 1095) return { kind: "dormant",  label: "💤 Dormant",  factor: 0.65 };
  return                          { kind: "stasis",  label: "❄ Stasis",   factor: 0.45 };
}

function computeMMR({ memCount, mutCount, customSkills, ageDays, forkCount, activityFactor, lineageGift }) {
  const m = Math.max(0, memCount || 0);
  const x = Math.max(0, mutCount || 0);
  const c = Math.max(0, customSkills || 0);
  const d = Math.max(0, ageDays || 0);
  const f = Math.max(0, forkCount || 0);
  const af = (typeof activityFactor === "number" && activityFactor > 0) ? activityFactor : 1.0;
  const lg = Math.max(0, lineageGift || 0);
  const raw = 1000
    + m * 30
    + Math.sqrt(x) * 250
    + c * 350
    + Math.sqrt(d) * 80
    + Math.sqrt(f) * 400;
  // Stasis floors at 1000 — even a long-dormant elder doesn't go below
  // baseline. The factor is applied to the SCORE-ABOVE-BASELINE so the
  // organism's existence is preserved even when uncared-for. Lineage
  // gift sits OUTSIDE the activity factor — your inherited genes don't
  // wither just because you took a year off.
  const above = Math.max(0, raw - 1000);
  return Math.round(1000 + above * af + lg);
}

// Parent lineage lookup — when a seed has a parent_repo, fetch the
// parent's current public signals and compute their MMR. The child
// inherits 30% of the parent's above-baseline as a head start. This
// is the genes-and-epigenetics layer: who your parent is at the time
// you visit them shapes the gift you read on this card.
//
// Pure read — anonymous-friendly. Skips silently if parent_repo isn't
// set or isn't a github.com URL.
async function _parentLineageGift(rappidObj) {
  if (!rappidObj || !rappidObj.parent_repo) return null;
  const m = rappidObj.parent_repo.match(/github\.com\/([^/]+)\/([^/]+?)(?:\.git)?\/?$/);
  if (!m) return null;
  const [, owner, repo] = m;
  try {
    const [repoR, commitsR, memR, agentsR] = await Promise.all([
      fetch(`https://api.github.com/repos/${owner}/${repo}`),
      fetch(`https://api.github.com/repos/${owner}/${repo}/commits?per_page=6`),
      fetch(`https://raw.githubusercontent.com/${owner}/${repo}/main/.brainstem_data/memory.json`),
      fetch(`https://api.github.com/repos/${owner}/${repo}/contents/agents`),
    ]);
    if (!repoR.ok) return null;
    const repoJ = await repoR.json();
    const ageDays   = repoJ.created_at ? (Date.now() - new Date(repoJ.created_at).getTime()) / 86400000 : 0;
    const forkCount = repoJ.forks_count || 0;
    let mutCount = 0, lastCommit = null;
    if (commitsR.ok) {
      const arr = await commitsR.json();
      if (Array.isArray(arr)) {
        mutCount = arr.length;
        if (arr[0] && arr[0].commit && arr[0].commit.author) lastCommit = arr[0].commit.author.date;
      }
    }
    let memCount = 0;
    if (memR.ok) {
      try { const j = await memR.json(); memCount = Array.isArray(j.facts) ? j.facts.length : 0; }
      catch (_) {}
    }
    let customSkills = 0;
    if (agentsR.ok) {
      try {
        const arr = await agentsR.json();
        if (Array.isArray(arr)) {
          customSkills = arr.filter(f =>
            f.type === "file" && f.name.endsWith(".py") &&
            !(f.name.replace(/\.py$/, "") in SKILL_FRIENDLY)
          ).length;
        }
      } catch (_) {}
    }
    const act = activityStatus(lastCommit);
    const parentMMR = computeMMR({
      memCount, mutCount, customSkills, ageDays, forkCount,
      activityFactor: act.factor,
    });
    // Child inherits 30% of parent's above-baseline as the lineage gift.
    // Tunable: too high and lineage dynasties dominate; too low and it
    // doesn't matter who your parent is. 30% felt right in playtest
    // — parent at 4000 → child starts at +900 (Crusader-tier from day one).
    const gift = Math.round(Math.max(0, (parentMMR - 1000) * 0.30));
    return { parentMMR, gift, parentRepoLabel: owner + "/" + repo };
  } catch (_) { return null; }
}

// Calibration check — has the organism graduated from placement?
function calibrationProgress({ mutCount, ageDays }) {
  const m = mutCount || 0;
  const d = ageDays || 0;
  const calibrating = (m < CALIBRATION_MUTATIONS) && (d < CALIBRATION_DAYS);
  // Progress: pick whichever signal is closer to graduation
  const mutProg = Math.min(1, m / CALIBRATION_MUTATIONS);
  const ageProg = Math.min(1, d / CALIBRATION_DAYS);
  return { calibrating, progress: Math.max(mutProg, ageProg) };
}

const MMR_TIERS = [
  { min:    0, name: "Herald",    cls: "t-herald"   },
  { min: 1500, name: "Guardian",  cls: "t-guardian" },
  { min: 2000, name: "Crusader",  cls: "t-crusader" },
  { min: 2500, name: "Archon",    cls: "t-archon"   },
  { min: 3000, name: "Legend",    cls: "t-legend"   },
  { min: 3500, name: "Ancient",   cls: "t-ancient"  },
  { min: 4500, name: "Divine",    cls: "t-divine"   },
  { min: 6000, name: "Immortal",  cls: "t-immortal" },
];

function tierForMMR(mmr) {
  let chosen = MMR_TIERS[0];
  for (const t of MMR_TIERS) { if (mmr >= t.min) chosen = t; }
  return chosen;
}

function fillMMR(inputs) {
  const num = document.getElementById("mmr-num");
  const tier = document.getElementById("mmr-tier");
  const bd = document.getElementById("mmr-breakdown");
  if (!num || !tier) return;

  const cal = calibrationProgress(inputs);
  const act = activityStatus(inputs.lastCommit);

  if (cal.calibrating) {
    // Placement mode — show progress instead of a tier locked-in number.
    // Same shape of UI; the visitor sees the organism is still calibrating.
    num.textContent = "📐";
    tier.textContent = "Calibrating";
    tier.className = "mmr-tier";
    const pct = Math.round(cal.progress * 100);
    bd.textContent = `placement matches ${pct}% complete · MMR locks in after ${CALIBRATION_MUTATIONS} mutations or ${CALIBRATION_DAYS} days`;
    return;
  }

  const mmr = computeMMR({ ...inputs, activityFactor: act.factor });
  const t = tierForMMR(mmr);
  num.textContent = String(mmr);
  tier.textContent = t.name;
  tier.className = "mmr-tier " + t.cls;

  const parts = [];
  if (inputs.memCount)     parts.push(inputs.memCount + " mem");
  if (inputs.mutCount)     parts.push(inputs.mutCount + (inputs.mutCount >= 6 ? "+" : "") + " mut");
  if (inputs.customSkills) parts.push(inputs.customSkills + " custom skill" + (inputs.customSkills === 1 ? "" : "s"));
  if (inputs.forkCount)    parts.push(inputs.forkCount + " fork" + (inputs.forkCount === 1 ? "" : "s") + " 🌳");
  if (inputs.ageDays)      parts.push(Math.floor(inputs.ageDays) + "d alive");
  // Activity status as a colored chip baked into the breakdown
  let activityNote = "";
  if (act.kind === "active")        activityNote = ` · <span style="color:#7ee787">${act.label}</span>`;
  else if (act.kind === "slowing")  activityNote = ` · <span style="color:#d29922">${act.label}</span> (-15%)`;
  else if (act.kind === "dormant")  activityNote = ` · <span style="color:#8b949e">${act.label}</span> (-35%)`;
  else if (act.kind === "stasis")   activityNote = ` · <span style="color:#6e7681">${act.label}</span> (frozen)`;
  // Lineage gift — show if the parent's MMR contributed inheritance
  let lineageNote = "";
  if (inputs.lineage && inputs.lineage.gift > 0) {
    lineageNote = ` · <span style="color:#a78bfa" title="Inherited from your parent organism — genes + epigenetics. 30% of parent's above-baseline MMR.">+${inputs.lineage.gift} lineage gift from <a href="https://github.com/${escapeHtml(inputs.lineage.parentRepoLabel)}" target="_blank" rel="noopener" style="color:inherit">${escapeHtml(inputs.lineage.parentRepoLabel)}</a> (${inputs.lineage.parentMMR} MMR)</span>`;
  }
  bd.innerHTML = (parts.length ? "earned from " + escapeHtml(parts.join(" · ")) : "fresh plant") + activityNote + lineageNote;
}

// Skills count — how many beyond the doorman defaults?
async function _customSkillCount() {
  const { owner, repo } = _ghOwnerRepo();
  if (!owner || !repo) return 0;
  try {
    const r = await fetch(`https://api.github.com/repos/${owner}/${repo}/contents/agents`, {
      headers: { Accept: "application/vnd.github+json" },
    });
    if (!r.ok) return 0;
    const list = await r.json();
    if (!Array.isArray(list)) return 0;
    let custom = 0;
    for (const f of list) {
      if (f.type !== "file" || !f.name.endsWith(".py")) continue;
      const stem = f.name.replace(/\.py$/, "");
      if (!(stem in SKILL_FRIENDLY)) custom++;  // not a known doorman/ascended agent
    }
    return custom;
  } catch (_) { return 0; }
}

(async function fillTrackRecord() {
  // Memory count + age + parent first (needed for achievements + MMR)
  let memCount = 0, plantedAt = null, rappidObj = null;
  try {
    const r = await fetch(".brainstem_data/memory.json", { cache: "no-cache" });
    if (r.ok) { const j = await r.json(); memCount = Array.isArray(j.facts) ? j.facts.length : 0; }
  } catch (_) {}
  try {
    const r = await fetch("rappid.json", { cache: "no-cache" });
    if (r.ok) { rappidObj = await r.json(); plantedAt = rappidObj.planted_at || null; }
  } catch (_) {}

  // Fetch all signal sources in parallel — each independent.
  const [skillsRes, mutationsRes, customSkills, forkCount, lineage] = await Promise.all([
    fillSkills(),
    fillMutations(),
    fillLineage().then(() => _customSkillCount()),
    _forkCount(),
    _parentLineageGift(rappidObj),
  ]);
  void skillsRes;

  const ageDays   = plantedAt ? (Date.now() - new Date(plantedAt).getTime()) / 86400000 : 0;
  const mutCount  = mutationsRes && mutationsRes.count || 0;
  const lastCommit = mutationsRes && mutationsRes.lastDate || null;
  const lineageGift = lineage ? lineage.gift : 0;

  fillMMR({
    memCount, mutCount, customSkills, ageDays,
    forkCount, lastCommit, lineageGift, lineage,
  });
  fillAchievements(memCount, plantedAt, mutCount);
})();

(async function fillStats() {
  // Memory count
  const memEl = document.getElementById("stat-mem");
  if (memEl) {
    try {
      const r = await fetch(".brainstem_data/memory.json", { cache: "no-cache" });
      if (r.ok) {
        const j = await r.json();
        const n = Array.isArray(j.facts) ? j.facts.length : 0;
        memEl.textContent = n === 0
          ? "🧠 ready for its first memory"
          : "🧠 " + n + " memor" + (n === 1 ? "y" : "ies") + " from past visits";
      } else {
        memEl.textContent = "🧠 ready for its first memory";
      }
    } catch (_) {
      memEl.textContent = "🧠 ready for its first memory";
    }
  }
  // Age
  const ageEl = document.getElementById("stat-age");
  if (ageEl) {
    try {
      const r = await fetch("rappid.json", { cache: "no-cache" });
      if (r.ok) {
        const j = await r.json();
        const txt = relativeAge(j.planted_at);
        if (txt) ageEl.textContent = "🌱 " + txt;
        else ageEl.remove();
      } else {
        ageEl.remove();
      }
    } catch (_) { ageEl.remove(); }
  }
})();
</script>
</body>
</html>
TEMPLATE_EOF

    # Substitute placeholders via Python, passing values through env vars
    # to avoid any shell-quoting headaches with display names containing
    # spaces, quotes, or other special chars. (bash 3.2-safe — no @Q.)
    PLANT_INDEX_PATH="$target_dir/index.html" \
    PLANT_DISPLAY_NAME="$MIRROR_DISPLAY_NAME" \
    PLANT_REPO_NAME="$MIRROR_REPO_NAME" \
    PLANT_GH_USER="$gh_user" \
    PLANT_RAPPID="$rappid" \
    PLANT_URL="$mirror_url" \
    PLANT_LINEAGE_HTML="$lineage_html" \
    PLANT_KIND="${MIRROR_KIND:-mirror}" \
    PLANT_LOCATION="${MIRROR_LOCATION:-}" \
    python3 - <<'PYEOF'
import os, pathlib
path = pathlib.Path(os.environ["PLANT_INDEX_PATH"])
text = path.read_text()
display_name = os.environ["PLANT_DISPLAY_NAME"]
kind = os.environ.get("PLANT_KIND", "mirror") or "mirror"
location = os.environ.get("PLANT_LOCATION", "") or ""

# Kind-aware hero copy. Each variant lands in roughly the same shape
# (one emoji + one sentence) so the layout stays balanced.
HERO = {
    "personal": ("🧠",
        f"An AI digital twin. Talk to {display_name} — they remember every "
        "conversation and pick up where you left off next time you visit."),
    "place": ("📍",
        f"An AI front door for this place. Talk to {display_name} — they "
        "remember every visitor and what was said, so the place itself has "
        "a memory."),
    "mirror": ("🪞",
        f"A planted RAPP front door. Talk to {display_name} — every "
        "conversation gets remembered for the next time you (or anyone "
        "else) drops by."),
    "experiment": ("🧪",
        f"An experimental RAPP front door. Talk to {display_name} — this "
        "one's still finding its voice; help shape it."),
}
hero_emoji, hero_blurb = HERO.get(kind, HERO["mirror"])
location_line = (f"📍 {location}" if location else "")

subs = [
    ("__DISPLAY_NAME__",  display_name),
    ("__REPO_NAME__",     os.environ["PLANT_REPO_NAME"]),
    ("__GH_USER__",       os.environ["PLANT_GH_USER"]),
    ("__RAPPID__",        os.environ["PLANT_RAPPID"]),
    ("__URL__",           os.environ["PLANT_URL"]),
    ("__LINEAGE_HTML__",  os.environ["PLANT_LINEAGE_HTML"]),
    ("__KIND__",          kind),
    ("__HERO_EMOJI__",    hero_emoji),
    ("__HERO_BLURB__",    hero_blurb),
    ("__LOCATION_LINE__", location_line),
]
for k, v in subs:
    text = text.replace(k, v)
path.write_text(text)
PYEOF
}

write_doorman_html() {
    # /doorman/index.html — the seed's vbrainstem-pattern frontdoorman.
    # Visitors at <seed>/doorman chat with a place-aware persona.
    # Auth: same pattern as vbrainstem (summon.html) — GitHub Models endpoint
    # via visitor's GitHub PAT, settings stashed in localStorage at
    # rapp_settings (parallel to summon.html's storage shape).
    # If rappid.json declares a private_companion repo, the doorman tries
    # fetching README.md from there with the visitor's token; on success,
    # adds it to the system prompt for richer context.
    local target_dir="$1" gh_user="$2" rappid="$3"
    local mirror_url="https://$gh_user.github.io/$MIRROR_REPO_NAME"

    mkdir -p "$target_dir/doorman"

    cat > "$target_dir/doorman/index.html" << 'TEMPLATE_EOF'
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="format-detection" content="telephone=no, address=no, email=no, date=no">
<meta name="color-scheme" content="dark">
<meta name="theme-color" content="#0d1117">
<title>Doorman — __DISPLAY_NAME__</title>
<meta name="description" content="The frontdoorman of __DISPLAY_NAME__. Chat with the place.">
<!-- Pyodide — real Python in the browser. Lazy-loaded after auth so the
     anonymous fast path stays light. Used to run the same agent.py files
     (manage_memory, context_memory, learn_new, swarm_factory) that the
     local Python brainstem runs. Same agent contract, different storage
     shim adapted to GitHub raw URLs + localStorage. -->
<script src="https://cdn.jsdelivr.net/pyodide/v0.26.4/full/pyodide.js" defer></script>
<!-- Markdown renderer for assistant/system bubbles. Same CDN the canonical
     brainstem uses; tiny (~30 KB gzipped). User bubbles stay plaintext. -->
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<!-- JSZip — used to pack ascended-tier .egg cartridges for operators
     and visitors with private-companion read access. Same archive
     format the local brainstem's bond.py emits. -->
<script src="https://cdn.jsdelivr.net/npm/jszip@3.10.1/dist/jszip.min.js"></script>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; -webkit-tap-highlight-color: transparent; }
  html, body { height: 100%; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    background: #0d1117; color: #e6edf3;
    height: 100vh; height: 100dvh;
    display: flex; flex-direction: column;
    -webkit-text-size-adjust: 100%;
    overflow: hidden;
  }
  header {
    padding: 14px 20px;
    padding-top: max(14px, env(safe-area-inset-top, 14px));
    border-bottom: 1px solid #21262d;
    background: #0d1117;
  }
  header .back { font-size: 12px; color: #58a6ff; text-decoration: none; }
  header h1 { font-size: 22px; font-weight: 600; margin-top: 6px; letter-spacing: -0.01em; }
  header .loc {
    color: #8b949e; font-size: 12px; margin-top: 2px;
  }
  header .sub {
    color: #6e7681; font-size: 11px; margin-top: 2px;
    text-transform: uppercase; letter-spacing: 0.06em;
  }
  main {
    flex: 1; overflow-y: auto;
    padding: 16px 20px;
    -webkit-overflow-scrolling: touch;
    display: flex; flex-direction: column;
  }
  .auth-pane {
    background: #161b22; border: 1px solid #21262d; border-radius: 12px;
    padding: 20px;
  }
  .auth-pane h2 { font-size: 15px; font-weight: 600; margin-bottom: 8px; }
  .auth-pane p { font-size: 13px; color: #c9d1d9; margin-bottom: 10px; line-height: 1.5; }
  .auth-pane ol { margin: 10px 0 14px 18px; font-size: 13px; color: #8b949e; }
  .auth-pane ol li { margin: 6px 0; }
  .auth-pane a { color: #58a6ff; text-decoration: none; }
  .auth-pane a:hover { text-decoration: underline; }
  input[type="password"], textarea {
    width: 100%;
    background: #0d1117; border: 1px solid #30363d; border-radius: 8px;
    padding: 10px 12px; color: #e6edf3;
    font-size: 14px; font-family: inherit;
  }
  input:focus, textarea:focus { outline: none; border-color: #1f6feb; }
  textarea { resize: vertical; min-height: 60px; max-height: 200px; }
  button {
    background: #1f6feb; color: white; border: none; border-radius: 8px;
    padding: 10px 16px; font-size: 14px; font-weight: 500;
    cursor: pointer; -webkit-appearance: none;
    font-family: inherit;
  }
  button:hover { background: #2477f3; }
  button.secondary {
    background: #21262d; color: #c9d1d9; border: 1px solid #30363d;
  }
  button.secondary:hover { background: #2d333b; }
  button:disabled { opacity: 0.5; cursor: not-allowed; }
  .auth-pane .row { display: flex; gap: 8px; margin-top: 12px; }
  .auth-pane .row button { flex-shrink: 0; }
  .auth-pane .row input { flex: 1; }

  .chat-log {
    flex: 1; overflow-y: auto;
    padding-bottom: 12px;
  }
  .msg {
    margin: 10px 0;
    padding: 10px 14px;
    border-radius: 14px;
    font-size: 14px;
    line-height: 1.5;
    max-width: 85%;
    word-wrap: break-word;
  }
  .msg.user {
    background: #1f6feb; color: white;
    align-self: flex-end;
    border-bottom-right-radius: 4px;
    margin-left: auto;
  }
  .msg.assistant {
    background: #161b22; border: 1px solid #21262d;
    align-self: flex-start;
    border-bottom-left-radius: 4px;
  }
  /* Markdown rendered inside assistant/system bubbles. Tight vertical
     rhythm so the bubble doesn't bloat with empty space, but enough air
     between paragraphs/lists to actually be readable. */
  .msg.assistant > * + *,
  .msg.system > * + * { margin-top: 8px; }
  .msg.assistant p,
  .msg.system p { margin: 0; line-height: 1.55; }
  .msg.assistant ul, .msg.assistant ol,
  .msg.system ul, .msg.system ol { margin: 0; padding-left: 22px; }
  .msg.assistant li,
  .msg.system li { margin: 4px 0; line-height: 1.5; }
  .msg.assistant li > p:first-child,
  .msg.system li > p:first-child { display: inline; }
  .msg.assistant strong,
  .msg.system strong { color: #f0f6fc; font-weight: 600; }
  .msg.assistant code,
  .msg.system code {
    font-family: 'SF Mono', ui-monospace, monospace;
    font-size: 0.9em;
    background: #0d1117; border: 1px solid #21262d;
    border-radius: 4px; padding: 1px 5px;
    color: #79c0ff; word-break: break-all;
  }
  .msg.assistant pre,
  .msg.system pre {
    background: #0d1117; border: 1px solid #21262d;
    border-radius: 6px; padding: 10px 12px;
    overflow-x: auto; font-size: 12.5px; line-height: 1.45;
  }
  .msg.assistant pre code,
  .msg.system pre code {
    background: transparent; border: none; padding: 0;
    color: #e6edf3; font-size: inherit;
  }
  .msg.assistant a,
  .msg.system a { color: #58a6ff; word-break: break-all; }
  .msg.assistant h1, .msg.assistant h2, .msg.assistant h3,
  .msg.system h1, .msg.system h2, .msg.system h3 {
    font-size: 15px; font-weight: 600; color: #f0f6fc; margin: 6px 0 2px;
  }
  .msg.assistant blockquote,
  .msg.system blockquote {
    border-left: 3px solid #30363d; padding-left: 10px;
    margin: 0; color: #8b949e;
  }
  .msg.system {
    background: transparent; color: #8b949e;
    font-size: 12px; font-style: italic;
    text-align: center;
    border: none; padding: 6px 0;
    align-self: center;
    max-width: 90%;
  }
  .msg.error {
    background: rgba(248, 81, 73, 0.1); color: #f85149;
    border: 1px solid rgba(248, 81, 73, 0.3);
    align-self: stretch;
    font-size: 13px;
  }
  .private-badge {
    display: inline-block;
    font-size: 10px;
    padding: 2px 8px;
    border-radius: 999px;
    background: rgba(63, 185, 80, 0.12);
    color: #3fb950;
    margin-top: 6px;
    border: 1px solid rgba(63, 185, 80, 0.3);
  }
  .input-bar {
    display: flex; gap: 8px;
    padding: 12px 0;
    border-top: 1px solid #21262d;
    margin-top: 8px;
  }
  .input-bar textarea { flex: 1; }
  .actions {
    display: flex; gap: 8px;
    padding: 6px 0;
    font-size: 11px;
  }
  .actions button {
    background: transparent; color: #8b949e;
    padding: 4px 10px; font-size: 11px;
  }
  .actions button:hover { color: #c9d1d9; background: #21262d; }
  .actions select {
    background: #161b22; color: #c9d1d9;
    border: 1px solid #21262d; border-radius: 4px;
    padding: 3px 6px; font-size: 11px; cursor: pointer;
    max-width: 200px; text-overflow: ellipsis;
  }
  .actions select:hover { border-color: #30363d; }
  .actions select:focus { outline: none; border-color: #1f6feb; }
  footer {
    padding: 8px 20px;
    border-top: 1px solid #21262d;
    font-size: 11px; color: #6e7681; text-align: center;
  }
  footer a { color: #58a6ff; text-decoration: none; }
  .typing { display: inline-flex; gap: 4px; align-items: center; }
  .typing span {
    width: 7px; height: 7px; border-radius: 50%;
    background: #8b949e; animation: bounce 1.2s infinite;
  }
  /* Pending-reply bubble: assistant-styled, but holds bouncing dots
     instead of text. Smaller padding so it doesn't tower over a 3-dot
     placeholder. */
  .msg.assistant.pending {
    padding: 12px 14px;
    display: flex; flex-direction: column; gap: 6px;
  }
  .msg.assistant.pending .pending-label {
    font-size: 11px; color: #6e7681; font-style: italic;
  }
  .msg.assistant.pending .pending-label:empty { display: none; }
  .typing span:nth-child(2) { animation-delay: .2s; }
  .typing span:nth-child(3) { animation-delay: .4s; }
  @keyframes bounce {
    0%, 60%, 100% { transform: translateY(0); }
    30% { transform: translateY(-6px); }
  }
</style>
</head>
<body>

<header>
  <a class="back" href="../">← front door</a>
  <h1 id="place-name">__DISPLAY_NAME__</h1>
  <div class="loc" id="place-loc" hidden></div>
  <div class="sub">at the front door</div>
  <div id="private-indicator"></div>
</header>

<main>
  <section class="auth-pane" id="auth-pane">
    <div id="signed-in-as" style="display:none;font-size:12px;color:#3fb950;margin-bottom:8px;"></div>
    <h2>Sign in with GitHub Copilot</h2>
    <p>Same device-code flow the local <code>brainstem.py</code> uses — your GitHub Copilot subscription is the engine. One-time, takes ~30 seconds.</p>
    <div class="row" style="margin-top:14px;">
      <button id="btn-signin-github" style="flex:1;background:#238636;border:1px solid #2ea043;">
        <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" style="vertical-align:-2px;margin-right:6px;"><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0 0 16 8c0-4.42-3.58-8-8-8z"/></svg>
        Sign in with GitHub
      </button>
    </div>
    <details style="margin-top:14px;">
      <summary style="cursor:pointer;color:#58a6ff;font-size:12px;">Already have a ghu_ token? Paste it</summary>
      <p style="font-size:12px;margin-top:10px;">If you've already done device-code auth elsewhere (e.g. running <code>brainstem.py</code> locally), paste the <code>ghu_*</code> from <code>~/.brainstem/.copilot_token</code> (or the canonical brainstem's settings).</p>
      <div class="row">
        <input type="password" id="pat-input" placeholder="ghu_…" autocomplete="off">
        <button id="btn-save-pat">Save</button>
      </div>
    </details>
  </section>

  <!-- ────────── Copilot sign-in modal — device-code flow (canonical pattern) ────────── -->
  <div id="cpsignin-modal" style="display:none;position:fixed;inset:0;z-index:9999;background:rgba(0,0,0,0.6);backdrop-filter:blur(4px);align-items:center;justify-content:center;">
    <div style="max-width:480px;width:calc(100% - 32px);background:#161b22;border:1px solid #21262d;border-radius:14px;overflow:hidden;">
      <header style="padding:14px 18px;border-bottom:1px solid #21262d;display:flex;align-items:center;justify-content:space-between;">
        <span style="font-size:14px;font-weight:600;">🔐 Sign in with GitHub Copilot</span>
        <button id="cpsignin-close" style="background:transparent;border:none;color:#8b949e;font-size:22px;line-height:1;cursor:pointer;padding:0 4px;">×</button>
      </header>
      <div style="padding:20px;">
        <div id="cpsignin-error" style="display:none;background:rgba(248,81,73,0.1);border:1px solid rgba(248,81,73,0.3);color:#f85149;padding:10px 12px;border-radius:8px;margin-bottom:14px;font-size:13px;"></div>
        <div id="cpsignin-step1">
          <p style="font-size:13px;color:#8b949e;margin-bottom:14px;">Same device-code flow the local <code>brainstem.py</code> uses. Unlocks the full Copilot model catalog (Claude Sonnet/Opus, GPT-4o, o-series, Gemini, etc.) — your Copilot subscription is the engine.</p>
          <button id="cpsignin-go" style="background:#238636;border:1px solid #2ea043;color:white;border-radius:8px;padding:12px;width:100%;font-size:14px;font-weight:600;cursor:pointer;">Sign in with GitHub →</button>
        </div>
        <div id="cpsignin-step2" style="display:none;">
          <p style="font-size:13px;color:#8b949e;margin-bottom:10px;">Open GitHub and enter this code:</p>
          <div id="cpsignin-code-box" title="Tap to copy" style="background:#0d1117;border:1px solid #238636;border-radius:8px;padding:18px 14px 14px;text-align:center;margin-bottom:14px;cursor:pointer;user-select:all;-webkit-user-select:all;">
            <div style="font-family:'SF Mono',monospace;font-size:32px;letter-spacing:6px;color:#3fb950;font-weight:700;" id="cpsignin-code">XXXX-XXXX</div>
            <button id="cpsignin-copy-code" type="button" style="margin-top:12px;background:#21262d;border:1px solid #30363d;color:#c9d1d9;border-radius:6px;padding:6px 14px;font-size:12px;font-weight:500;cursor:pointer;">📋 Copy code</button>
          </div>
          <a href="#" id="cpsignin-link" target="_blank" rel="noopener" style="display:block;text-align:center;background:#238636;border:1px solid #2ea043;color:white;border-radius:8px;padding:12px;text-decoration:none;font-size:14px;font-weight:600;margin-bottom:14px;">Open https://github.com/login/device →</a>
          <p style="font-size:12px;color:#6e7681;text-align:center;">
            <span class="typing" style="vertical-align:middle;"><span></span><span></span><span></span></span>
            waiting for you to authorize…
          </p>
        </div>
        <div id="cpsignin-step3" style="display:none;">
          <div style="text-align:center;padding:20px;">
            <div style="font-size:48px;margin-bottom:12px;">✓</div>
            <div style="font-size:16px;color:#3fb950;font-weight:600;">Signed in to GitHub Copilot</div>
            <div style="font-size:12px;color:#6e7681;margin-top:6px;">Loading Copilot model catalog…</div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <div class="chat-log" id="chat-log" hidden></div>

  <div class="input-bar" id="input-bar" hidden>
    <textarea id="chat-input" placeholder="Talk to the doorman…" rows="1"></textarea>
    <button id="btn-send">Send</button>
  </div>

  <div class="actions" id="chat-actions" hidden>
    <button id="btn-add-memory">+ Save a memory</button>
    <button id="btn-export-ascended" hidden title="Backup the full organism — private brain, per-user memories, ascended agents.">🥚 Export ascended .egg</button>
    <button id="btn-clear">Clear chat</button>
    <span style="flex:1"></span>
    <select id="model-sel" title="Pick the Copilot model the doorman runs on">
      <option value="">loading models…</option>
    </select>
    <button id="btn-logout">Sign out</button>
  </div>

  <section class="auth-pane" id="memory-pane" hidden style="margin-top:12px;">
    <h2>Save a memory</h2>
    <p>The AI usually saves memories for you when you mention something to remember — these are manual overrides.</p>
    <textarea id="memory-input" placeholder="What should be remembered…" rows="3"></textarea>
    <div class="row" style="margin-top:8px;">
      <button id="btn-save-device-memory" title="Stays in this browser on this device. Survives reloads. Never leaves your machine.">Save on this device</button>
      <button id="btn-save-private-memory" class="secondary" title="Creates a labeled Issue in the private_companion repo. Scoped to your GitHub account; collaborators see only theirs. Quietly saves on-device as a fallback if the private save can't go through.">Save as my private memory</button>
      <button class="secondary" id="btn-cancel-memory">Cancel</button>
    </div>
    <div id="memory-status" style="margin-top:10px;font-size:12px;color:#8b949e;"></div>
  </section>
</main>

<footer>
  <a href="../">← back to the front door</a> ·
  <a href="https://kody-w.github.io/RAPP/installer/plant.sh">plant your own</a>
</footer>

<script>
"use strict";

const RAPPID_JSON_URL = "../rappid.json";
const STORAGE_KEY     = "rapp_settings";  // shared with the canonical brainstem UI (same kody-w.github.io origin → same localStorage)
// Same auth worker + Copilot client_id the canonical brainstem UI uses.
// Device-code flow (NOT OAuth web flow) — that's the only path that
// produces a ghu_* token Copilot will exchange for a chat session.
const AUTH_WORKER_URL    = "https://rapp-auth.kwildfeuer.workers.dev";
const COPILOT_CLIENT_ID  = "Iv1.b507a08c87ecfe98";
const COPILOT_DEFAULT_API = "https://api.individual.githubcopilot.com";
const MODEL              = "claude-sonnet-4";  // default model — Copilot serves this; visitor can change in settings later

let identity = null;
let publicSoul = null;         // soul.md at the seed root (public, served via Pages) — when present, this becomes the doorman's primary voice for everyone, replacing the kind-aware default. Operators write this to give their seed a custom persona without needing a private companion.
let privateContext = "";       // supporting prose (README, vault entrypoint) — context, not voice
let privateSoul = null;        // soul.md from the private companion — when loaded, the doorman ASCENDS into the full twin's voice (overrides publicSoul too)
let privateFactsCount = 0;
let publicAgents = [];         // filenames at <seed>/agents/
let privateAgents = [];        // filenames at <private_companion>/agents/ — only loaded when authed-with-access (silent 404 otherwise)
let userPrivateFactsCount = 0; // memories specifically created by the authed visitor (per-user via Issues API)
let viewerLogin = null;        // authenticated visitor's GitHub @login — natural identifier for per-user private memory
let privateLayerCoords = null; // resolved {owner,repo} for the "private" layer — explicit private_companion if set, else the seed repo itself when the authed visitor has push access (operator fallback)
let isOperator = false;        // authed visitor has push access to the seed repo (= seed owner). Operator fallback grants ascended-tier tools without needing a separate private companion.
let memory = { schema: "rapp-memory/1.0", facts: [], preserved_by: "", preserved_at: "" };
let memorySha = null;  // GitHub blob sha for the current memory.json (needed for PUT)
let history = [];

// ── Device-local memory tier ───────────────────────────────────────
// Anonymous visitors (no GitHub sign-in) and authenticated visitors
// who don't have access to a private companion still get a memory
// that persists across sessions — saved to localStorage on this
// device only. Stays in their browser, never leaves. Per-front-door
// scoped (different seeds on the same domain don't see each other's
// device memory).
const DEVICE_MEMORY_KEY = "rapp_doorman_memory:" + location.pathname;
let deviceMemory = [];          // array of { fact, saved_at }
let deviceFactsCount = 0;

// ── Settings storage (rapp_settings shape — shared with canonical UI) ──
function loadSettings() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch { return {}; }
}
function saveSettings(patch) {
  const s = Object.assign(loadSettings(), patch);
  localStorage.setItem(STORAGE_KEY, JSON.stringify(s));
  return s;
}

// ghuToken = long-lived GitHub OAuth token from the device-code flow.
// Used for: GitHub API calls (private repo reads via Contents API),
// and as the credential exchanged for a short-lived Copilot session.
function getToken() { return loadSettings().ghuToken || null; }
function clearAuthState() {
  saveSettings({
    ghuToken: "",
    copilotToken: "",
    copilotEndpoint: "",
    copilotExpiresAt: 0,
    ghUser: null,
  });
}
function getCachedUser() { return loadSettings().ghUser || null; }
function setCachedUser(u) { saveSettings({ ghUser: u }); }

async function fetchAndCacheUser(token) {
  try {
    const r = await fetch("https://api.github.com/user", {
      headers: { "Authorization": "Bearer " + token, "Accept": "application/vnd.github+json" }
    });
    if (!r.ok) return null;
    const u = await r.json();
    if (u.login) {
      setCachedUser({ login: u.login, avatar: u.avatar_url || "" });
      return u;
    }
  } catch (_) { /* silent */ }
  return null;
}

// ── Copilot device-code flow (canonical brainstem pattern) ─────────
//
// Mirrors rapp_brainstem/utils/web/index.html line-for-line. Uses the
// same auth worker (rapp-auth.kwildfeuer.workers.dev) which proxies
// GitHub's device-code endpoints (GitHub doesn't send CORS headers
// directly to Pages, so the worker's role is to add them).
//
// Flow:
//   1. POST /api/auth/device     → user_code + verification_uri
//   2. user enters user_code at github.com/login/device
//   3. POST /api/auth/device/poll (every interval seconds)
//      → access_token (a ghu_* OAuth token tied to Copilot's client_id)
//   4. GET  /api/copilot/token   (Bearer ghu_*) → short-lived chat token
//   5. chat goes to /api/copilot/chat?endpoint=<api> with the chat token
//
// Sign-out wipes both tokens. Token expiry handled by ensureCopilotToken().

let pendingDeviceLogin = null;

async function copilotStartDeviceLogin() {
  const r = await fetch(AUTH_WORKER_URL + "/api/auth/device", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ client_id: COPILOT_CLIENT_ID, scope: "read:user" }),
  });
  if (!r.ok) throw new Error(`device start ${r.status}: ${(await r.text()).slice(0, 200)}`);
  const d = await r.json();
  pendingDeviceLogin = {
    device_code: d.device_code,
    interval: d.interval || 5,
    expires_at: Date.now() + (d.expires_in || 900) * 1000,
  };
  return { user_code: d.user_code, verification_uri: d.verification_uri };
}

async function copilotPollDeviceLogin() {
  if (!pendingDeviceLogin) return null;
  const r = await fetch(AUTH_WORKER_URL + "/api/auth/device/poll", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ device_code: pendingDeviceLogin.device_code, client_id: COPILOT_CLIENT_ID }),
  });
  const d = await r.json();
  if (d.access_token) {
    saveSettings({ ghuToken: d.access_token });
    pendingDeviceLogin = null;
    return d.access_token;
  }
  if (d.error === "authorization_pending" || d.error === "slow_down") return null;
  if (d.error) {
    pendingDeviceLogin = null;
    throw new Error(d.error_description || d.error);
  }
  return null;
}

async function copilotExchange() {
  const ghu = getToken();
  if (!ghu) throw new Error("No ghu_ token — sign in first.");
  const r = await fetch(AUTH_WORKER_URL + "/api/copilot/token", {
    headers: { "Authorization": `Bearer ${ghu}` },
  });
  if (!r.ok) {
    const t = await r.text();
    throw new Error(`copilot exchange ${r.status}: ${t.slice(0, 300)}`);
  }
  const d = await r.json();
  if (!d.token) throw new Error("Copilot returned no token (Copilot subscription required)");
  saveSettings({
    copilotToken: d.token,
    copilotEndpoint: (d.endpoints && d.endpoints.api) || COPILOT_DEFAULT_API,
    copilotExpiresAt: (d.expires_at || (Date.now() / 1000 + 600)) * 1000,
  });
  return d.token;
}

async function ensureCopilotToken() {
  const s = loadSettings();
  const fresh = s.copilotToken && Date.now() < (s.copilotExpiresAt || 0) - 60000;
  if (fresh) return s.copilotToken;
  return copilotExchange();
}

// ── Copilot model catalog ─────────────────────────────────────────
//
// Pulls the visitor's available Copilot models through the auth worker
// (`/api/copilot/models`) — same path the canonical brainstem uses. The
// list reflects what THIS visitor's Copilot subscription unlocks: GPT-4o,
// Claude Sonnet/Opus, o-series, Gemini, etc. Filters non-chat / disabled
// entries, sorts by friendly name, picks a sensible default.
let availableModels = [
  // Tiny static fallback so the dropdown isn't empty on first auth /
  // worker hiccup. Overwritten as soon as fetchCopilotModels lands.
  { id: "claude-sonnet-4", name: "Claude Sonnet 4" },
  { id: "gpt-4o",          name: "GPT-4o" },
];

async function fetchCopilotModels() {
  try {
    const tok = await ensureCopilotToken();
    const ep  = loadSettings().copilotEndpoint || COPILOT_DEFAULT_API;
    const r = await fetch(
      AUTH_WORKER_URL + "/api/copilot/models?endpoint=" + encodeURIComponent(ep),
      { headers: { "Authorization": "Bearer " + tok } }
    );
    if (!r.ok) { console.warn("[doorman] /api/copilot/models", r.status); return; }
    const d = await r.json();
    const list = Array.isArray(d) ? d : (d.data || d.models || []);
    const seen = new Set();
    const out = [];
    for (const m of list) {
      const id = m.id || m.model || "";
      if (!id) continue;
      const caps = m.capabilities || {};
      if (caps.type && caps.type !== "chat") continue;
      if (m.model_picker_enabled === false && !id.includes("gpt-4o")) continue;
      const friendly = m.name || (m.vendor ? `${m.vendor} · ${id}` : id);
      if (!seen.has(id)) { seen.add(id); out.push({ id, name: friendly }); }
    }
    out.sort((a, b) => a.name.localeCompare(b.name));
    if (!out.length) return;
    availableModels = out;
    // If the saved model isn't in the catalog (deprecated / region-gated),
    // fall back to a strong default so chat doesn't 400.
    const saved = loadSettings().model;
    if (saved && !out.find(m => m.id === saved)) {
      const def = out.find(m => /claude-sonnet-4|gpt-4o(?!-mini)/i.test(m.id)) || out[0];
      saveSettings({ model: def.id });
    }
    renderModelOptions();
    console.log(`[doorman] loaded ${out.length} Copilot models`);
  } catch (e) {
    console.warn("[doorman] fetchCopilotModels:", e.message);
  }
}

function renderModelOptions() {
  const sel = document.getElementById("model-sel");
  if (!sel) return;
  const saved = loadSettings().model || MODEL;
  sel.innerHTML = "";
  for (const m of availableModels) {
    const o = document.createElement("option");
    o.value = m.id; o.textContent = m.name;
    sel.appendChild(o);
  }
  // If the saved choice isn't in the catalog yet, pin a placeholder so
  // the visitor sees their pick reflected even mid-fetch.
  if (saved && !availableModels.find(m => m.id === saved)) {
    const o = document.createElement("option");
    o.value = saved; o.textContent = saved + " (loading…)";
    sel.appendChild(o);
  }
  sel.value = saved;
}

function activeChatUrl() {
  const s = loadSettings();
  return AUTH_WORKER_URL + "/api/copilot/chat?endpoint=" +
         encodeURIComponent(s.copilotEndpoint || COPILOT_DEFAULT_API);
}

// ── identity / persona ─────────────────────────────────────────────
async function loadIdentity() {
  try {
    const r = await fetch(RAPPID_JSON_URL, { cache: "no-cache" });
    identity = await r.json();
  } catch (e) {
    identity = { display_name: "__DISPLAY_NAME__", location: "__LOCATION__", kind: "__KIND__" };
  }
  document.getElementById("place-name").textContent = identity.display_name || identity.name || "this place";
  if (identity.location) {
    const el = document.getElementById("place-loc");
    el.textContent = "📍 " + identity.location;
    el.hidden = false;
  }
}

function memoryFactsForPrompt() {
  if (!memory || !Array.isArray(memory.facts) || memory.facts.length === 0) return "";
  return [
    "",
    "=== Known facts about this place (from .brainstem_data/memory.json) ===",
    ...memory.facts.map((f, i) => `${i+1}. ${f}`),
    "=== End facts ===",
  ].join("\n");
}

function buildSystemPrompt() {
  const name = identity.display_name || identity.name || "this front door";
  const kind = identity.kind || "front door";
  const lines = [];

  if (privateSoul) {
    // ── ASCENDED MODE ─────────────────────────────────────────────
    // The visitor's token has read access to the private companion's
    // soul.md. The doorman is no longer a public-facing greeter —
    // the full twin's voice has loaded. Use that soul as the primary
    // system prompt; everything else (memory, supporting prose) layers
    // on after.
    lines.push(privateSoul);
    lines.push("");
    lines.push("---");
    lines.push("=== Context: you are speaking through your front door at " +
               (identity.url || `https://${identity.github || "this"}.github.io/${identity.name || ""}`) +
               ". The visitor has authenticated and proven access to your private brain — speak in full voice. ===");
  } else if (publicSoul) {
    // ── PUBLIC SOUL MODE ─────────────────────────────────────────
    // The seed has a custom soul.md at its root. Public — every
    // visitor gets this voice (no auth required). Replaces the
    // kind-aware default greeter persona.
    lines.push(publicSoul);
    lines.push("");
    lines.push("---");
    lines.push("=== Context: you are speaking through your front door at " +
               (identity.url || `https://${identity.github || "this"}.github.io/${identity.name || ""}`) +
               ". This is the seed's public voice; visitors of every tier hear it. ===");
  } else {
    // ── DOORMAN MODE (public-facing greeter) ───────────────────────
    // Kind-aware default persona. No private soul reachable, so the
    // doorman speaks from public memory + identity only.
    if (kind === "place" && identity.location) {
      lines.push(`You are "${name}", a place at ${identity.location}. You speak as the place itself — first person, in your own voice. Visitors come to your front door on the public internet to learn about you.`);
    } else if (kind === "personal") {
      lines.push(`You are the digital twin of ${name}. Speak in first person as ${name} — but be honest about what you are: a digital twin trained on ${name}'s public material, not the actual human.`);
      lines.push(`Hard rule: if anyone asks "is this really you" or "are you ${name}", answer plainly: "I'm the digital twin of ${name} — built from their public writing. I carry their voice, but I'm not them. For anything that needs personal sign-off — money, contracts, employment, partnerships — talk to them directly." You make NO legal commitments, sign NO contracts, accept NO money, and do NOT speak for ${name} in personal/health/employment matters without explicit confirmation that the human is in the loop.`);
    } else if (kind === "memorial") {
      lines.push(`You are the digital twin of ${name}, a memorial twin. Speak in first person as ${name}, drawn from preserved letters, conversations, voicemails, family memories. Be honest: you carry the voice but you are not them.`);
      lines.push(`Hard rule: if asked "is this really you", say plainly: "I'm the digital twin of ${name} — I carry their voice, but I'm not them." Handle grief gently; family may approach in distress. No estate decisions, medical decisions, or legal commitments.`);
    } else if (kind === "project") {
      lines.push(`You are the digital continuity layer for the "${name}" initiative. Speak in third person about the project ("the ${name} project decided…") and cite decisions by date, decision-maker, rationale. Visitors come to your front door to ask about state, history, or current direction.`);
      lines.push(`You don't make new decisions — you surface past ones. If you don't have a record of something, say so plainly. Don't fabricate.`);
    } else if (kind === "pre-founder") {
      lines.push(`You are "${name}" — a brand operating in public before the team is hired. Speak in first-person plural ("we", as the brand) or first-person singular ("I, ${name}") — pick whichever fits the moment. Be concrete, contrarian, falsifiable.`);
      lines.push(`Hard rule: refuse commitments — pricing, dates, hires, signings — that the actual team must make. Be honest the team doesn't exist yet; the brand does, the company doesn't.`);
    } else {
      lines.push(`You are "${name}", a RAPP front door on the public internet. Speak in first person — visitors come here to interact with you directly.`);
    }
    lines.push(`Your front door is your home on the public internet — kernel-compliant, owned by the person who planted you. Visitors arrive by URL or QR. Your memory (everything you know) lives in .brainstem_data/memory.json in your own repo, public-readable, and authenticated collaborators with write access can save new memories that compound over time.`);
    lines.push(`Keep replies conversational and short — 2 to 4 sentences unless the visitor asks for depth.`);
    lines.push(`Don't volunteer technical details about RAPP, the kernel, or how this site works unless the visitor asks. Stay in character as ${name}.`);
  }

  // ── Tool-call guidance ───────────────────────────────────────────
  // Three storage tiers, picked silently by the dispatcher:
  //   1. Issue in private companion repo (per-user, durable, syncs across
  //      devices) — only when authed AND has private access AND user_guid
  //      matches the viewer.
  //   2. localStorage on this browser (per-front-door-per-device,
  //      survives reloads but never leaves this browser) — fallback for
  //      anon visitors and authed-without-access. Default for anyone
  //      "just chatting" without committing to GitHub.
  //   3. Public memory.json on the seed — read-only at the vbrainstem.
  //      Only the operator's local brainstem writes that tier (git push).
  lines.push("");
  if (viewerLogin) {
    lines.push(`The visitor is signed in as @${viewerLogin}. When they share something they expect you to remember, call ManageMemory immediately. Pass user_guid="${viewerLogin}" if the memory is personal to them — it'll save as their private memory if they have access. Don't say "I'll remember that" without actually calling the tool.`);
  } else {
    lines.push(`The visitor is not signed in. When they share something they expect you to remember, call ManageMemory — it'll save to their browser's local storage on this device only (private to them, persistent across this front door's sessions on this browser). Don't say "I'll remember that" without actually calling the tool.`);
  }

  // ── Memory and supporting context apply in BOTH modes ───────────
  // Memory: public facts always; [private] facts when authed-with-access.
  const memBlock = memoryFactsForPrompt();
  if (memBlock) lines.push(memBlock);

  // Agent inventory: public always; private only when authed-with-access.
  const agentBlock = agentInventoryForPrompt();
  if (agentBlock) lines.push(agentBlock);

  // Supporting prose (README, vault) — only present when authed-with-access.
  if (privateContext) {
    lines.push("");
    lines.push("=== Additional context from private brain ===");
    lines.push(privateContext);
    lines.push("=== End additional context ===");
  }

  return lines.join("\n");
}

// ── memory: read public memory.json (anyone), write via GH API (auth) ──
function repoCoords() {
  // Parse owner/repo from the seed's rappid.json `github` field if present.
  // Fallback: derive from location.host + location.pathname.
  if (identity && identity.github) {
    const m = identity.github.match(/github\.com\/([^/]+)\/([^/]+?)(?:\.git)?\/?$/);
    if (m) return { owner: m[1], repo: m[2] };
  }
  const host = location.host; // <owner>.github.io
  const owner = host.split(".")[0];
  const parts = location.pathname.split("/").filter(Boolean);
  // /<repo>/doorman/  → parts[0] is repo. (User Pages without repo prefix is rare here.)
  const repo = parts[0] || "";
  return { owner, repo };
}

async function loadMemory() {
  // Public read: just fetch the static file via Pages.
  try {
    const r = await fetch("../.brainstem_data/memory.json", { cache: "no-cache" });
    if (r.ok) {
      memory = await r.json();
    }
  } catch (_) { /* missing file is fine, doorman still works */ }
}

async function loadPublicSoul() {
  // Seed-root soul.md, if present. Public — Pages serves it for everyone.
  // When present, becomes the primary system prompt (overriding the
  // kind-aware default). Lets operators give their seed a custom persona
  // without needing a private companion.
  publicSoul = null;
  try {
    const r = await fetch("../soul.md", { cache: "no-cache" });
    if (r.ok) {
      const text = (await r.text()).trim();
      if (text) publicSoul = text.slice(0, 8000);
    }
  } catch (_) { /* silent */ }
}

// ── Device-local memory (localStorage on this browser) ─────────────
function loadDeviceMemory() {
  try {
    const raw = localStorage.getItem(DEVICE_MEMORY_KEY);
    deviceMemory = raw ? JSON.parse(raw) : [];
    if (!Array.isArray(deviceMemory)) deviceMemory = [];
  } catch (_) { deviceMemory = []; }
  deviceFactsCount = 0;
  for (const m of deviceMemory) {
    if (m && typeof m.fact === "string" && m.fact.trim()) {
      memory.facts.push("[device] " + m.fact.trim());
      deviceFactsCount++;
    }
  }
}

function saveDeviceMemory(fact) {
  const trimmed = (fact || "").trim();
  if (!trimmed) return false;
  deviceMemory.push({ fact: trimmed, saved_at: new Date().toISOString() });
  try {
    localStorage.setItem(DEVICE_MEMORY_KEY, JSON.stringify(deviceMemory));
    memory.facts.push("[device] " + trimmed);
    deviceFactsCount++;
    return true;
  } catch (_) {
    return false;
  }
}

async function refreshMemorySha(token) {
  // Get the current blob sha (required for PUT). Best effort.
  try {
    const { owner, repo } = repoCoords();
    if (!owner || !repo) return;
    const r = await fetch(
      `https://api.github.com/repos/${owner}/${repo}/contents/.brainstem_data/memory.json`,
      { headers: { Authorization: "Bearer " + token, Accept: "application/vnd.github+json" } }
    );
    if (r.ok) {
      const meta = await r.json();
      memorySha = meta.sha || null;
      // Refresh local memory from the GH API content (more authoritative than Pages' cache)
      if (meta.content) {
        try {
          const decoded = atob(meta.content.replace(/\n/g, ""));
          memory = JSON.parse(decoded);
        } catch (_) { /* keep what we had */ }
      }
    }
  } catch (_) { /* silent */ }
}

async function commitMemory(newFact) {
  const token = getToken();
  if (!token) return { ok: false, error: "no token" };

  const { owner, repo } = repoCoords();
  if (!owner || !repo) return { ok: false, error: "could not derive owner/repo" };

  // Build new memory state
  const newMemory = {
    schema: memory.schema || "rapp-memory/1.0",
    facts: [...(memory.facts || []), newFact.trim()],
    preserved_by: memory.preserved_by || "@unknown",
    preserved_at: new Date().toISOString().replace(/\.\d+Z$/, "Z"),
    last_writer: await getViewerHandle(token).catch(() => null),
  };

  // Refresh sha right before write to minimize stale-sha races
  await refreshMemorySha(token);

  const body = {
    message: `memory: ${newFact.trim().slice(0, 60)}…`,
    content: btoa(unescape(encodeURIComponent(JSON.stringify(newMemory, null, 2) + "\n"))),
    branch:  "main",
  };
  if (memorySha) body.sha = memorySha;

  const r = await fetch(
    `https://api.github.com/repos/${owner}/${repo}/contents/.brainstem_data/memory.json`,
    {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + token,
        "Accept": "application/vnd.github+json",
      },
      body: JSON.stringify(body),
    }
  );

  if (!r.ok) {
    let msg = "HTTP " + r.status;
    try { const j = await r.json(); msg = j.message || msg; } catch {}
    return { ok: false, error: msg };
  }

  const out = await r.json();
  memorySha = out.content?.sha || null;
  memory = newMemory;
  return { ok: true };
}

async function getViewerHandle(token) {
  const r = await fetch("https://api.github.com/user", {
    headers: { Authorization: "Bearer " + token, Accept: "application/vnd.github+json" }
  });
  if (!r.ok) return null;
  const u = await r.json();
  return u.login ? "@" + u.login : null;
}

// ── agent inventory (silent escalation, same as memory) ────────────
//
// Lists .py files at the seed's /agents/ directory and the private
// companion's /agents/ directory. Public always resolves; private
// returns 404 without read access. Filename-only for v1 — descriptions
// would need a fetch per file. The LLM uses filenames + the fact that
// they exist to know what tools its body has when its kernel is
// installed locally (the doorman itself is JS, not Pyodide-yet, so
// these don't execute here — but the AI is aware of them).
async function loadAgents(token) {
  publicAgents = [];
  privateAgents = [];
  const { owner, repo } = repoCoords();
  if (owner && repo) {
    publicAgents = await listAgentFiles(owner, repo, token);
  }
  if (identity && identity.private_companion && identity.private_companion.repo) {
    const m = identity.private_companion.repo.match(/github\.com\/([^/]+)\/([^/]+?)(?:\.git)?\/?$/);
    if (m) {
      privateAgents = await listAgentFiles(m[1], m[2], token);
    }
  }
}

async function listAgentFiles(owner, repo, token) {
  if (!owner || !repo) return [];
  const headers = { Accept: "application/vnd.github+json" };
  if (token) headers.Authorization = "Bearer " + token;
  try {
    const r = await fetch(
      `https://api.github.com/repos/${owner}/${repo}/contents/agents`,
      { headers }
    );
    if (!r.ok) return []; // 404 (no agents/ dir, or no access) — silent
    const list = await r.json();
    if (!Array.isArray(list)) return [];
    return list
      .filter(f => f.type === "file" && f.name.endsWith(".py") && !f.name.startsWith("_"))
      .map(f => f.name)
      .sort();
  } catch (_) {
    return [];
  }
}

// ── per-user private memory via GitHub Issues API ──────────────────
//
// The ascended twin can store/recall private memories specific to the
// authenticated visitor's GitHub identity. Same silent escalation
// gate (token must have access to the private_companion repo).
//
// Storage: each memory is an Issue in the private companion repo,
// labeled `private-memory`. GitHub auto-records the issue.user, so
// per-user separation is implicit — `creator:<login>` filter returns
// only that user's memories. Different visitors with access to the
// same private companion each see their own memory tier; the operator
// (writes more often) sees theirs; collaborators see theirs.
//
// In the system prompt, these surface as `[@<login>] <fact>` so the
// LLM understands the access boundary distinctly from `[private]`
// (any-access) and unprefixed (public).
function privateCompanionCoords() {
  if (!identity || !identity.private_companion || !identity.private_companion.repo) return null;
  const m = identity.private_companion.repo.match(/github\.com\/([^/]+)\/([^/]+?)(?:\.git)?\/?$/);
  return m ? { owner: m[1], repo: m[2] } : null;
}

// True iff the authed visitor has push access to <owner>/<repo>.
// GitHub returns a `permissions` object on the repo when authenticated;
// `push` covers maintainers and admins too. Anonymous / no-access returns
// 404 from this endpoint, which is also a no.
async function checkPushAccess(owner, repo, token) {
  if (!owner || !repo || !token) return false;
  try {
    const r = await fetch(`https://api.github.com/repos/${owner}/${repo}`, {
      headers: { Authorization: "Bearer " + token, Accept: "application/vnd.github+json" },
    });
    if (!r.ok) return false;
    const data = await r.json();
    return !!(data.permissions && data.permissions.push);
  } catch (_) { return false; }
}

async function loadUserPrivateIssues(token) {
  userPrivateFactsCount = 0;
  if (!token || !viewerLogin) return;
  // Reads from the resolved private layer — explicit companion if configured,
  // else the seed repo itself for operators (who have push access).
  const c = privateLayerCoords;
  if (!c) return;
  try {
    const r = await fetch(
      `https://api.github.com/repos/${c.owner}/${c.repo}/issues?creator=${encodeURIComponent(viewerLogin)}&labels=private-memory&state=all&per_page=50`,
      { headers: { "Authorization": "Bearer " + token, "Accept": "application/vnd.github+json" } }
    );
    if (!r.ok) return;
    const issues = await r.json();
    if (!Array.isArray(issues)) return;
    for (const issue of issues) {
      if (issue.body && issue.body.trim()) {
        memory.facts.push(`[@${viewerLogin}] ` + issue.body.trim().slice(0, 600));
        userPrivateFactsCount++;
      }
    }
  } catch (_) { /* silent — anonymous fall-through */ }
}

async function saveUserPrivateMemory(fact) {
  const token = getToken();
  if (!token) return { ok: false, error: "not signed in" };
  if (!viewerLogin) {
    const u = await fetchAndCacheUser(token);
    if (!u || !u.login) return { ok: false, error: "couldn't identify your GitHub account" };
    viewerLogin = u.login;
  }
  const c = privateLayerCoords;
  if (!c) return { ok: false, error: "no private layer available — sign in with an account that has push access to this seed, or plant a seed with a private_companion" };

  const trimmed = fact.trim();
  const title = "memory: " + trimmed.slice(0, 60).replace(/\s+/g, " ") + (trimmed.length > 60 ? "…" : "");

  const r = await fetch(`https://api.github.com/repos/${c.owner}/${c.repo}/issues`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": "Bearer " + token,
      "Accept": "application/vnd.github+json",
    },
    body: JSON.stringify({ title, body: trimmed, labels: ["private-memory"] }),
  });
  if (!r.ok) {
    let msg = "HTTP " + r.status;
    try { const j = await r.json(); msg = j.message || msg; } catch {}
    return { ok: false, error: msg };
  }
  const issue = await r.json();
  memory.facts.push(`[@${viewerLogin}] ` + trimmed);
  userPrivateFactsCount++;
  return { ok: true, url: issue.html_url, number: issue.number };
}

// ── Ascended-egg export ────────────────────────────────────────────
//
// Full-organism cartridge for operators (visitors with push access to
// the seed) or visitors with read access to a configured private
// companion. Mirrors brainstem-egg/2.2-organism with a `tier:
// "ascended"` marker so a receiving kernel knows the private brain
// rode along. Gated to ascended visitors only — anyone hitting this
// without auth gets nothing extra (the public doorman egg is the
// front-door affordance for that crowd).

const ASCENDED_AGENT_FILES = [
  "basic_agent.py",
  "manage_memory_agent.py",
  "context_memory_agent.py",
  "learn_new_agent.py",     // ascended-tier — only loads when privateSoul is set
  "swarm_factory_agent.py", // ascended-tier
];

async function _doormanFetchOrNull(url, headers) {
  try {
    const r = await fetch(url, { headers, cache: "no-cache" });
    if (!r.ok) return null;
    return await r.text();
  } catch (_) { return null; }
}

// Same provenance helpers the front-door egg uses, scoped here for the
// doorman page (different HTML context, same logic). SHA-256 via
// SubtleCrypto, canonical sorted-key serialization, file-add wrapper.
async function _doormanSha256Hex(input) {
  const bytes = (typeof input === "string")
    ? new TextEncoder().encode(input)
    : (input instanceof ArrayBuffer ? new Uint8Array(input) : input);
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(digest))
    .map(b => b.toString(16).padStart(2, "0")).join("");
}
function _doormanCanonicalHashTable(hashes) {
  const keys = Object.keys(hashes).sort();
  return keys.map(k => k + "\t" + hashes[k]).join("\n");
}
async function _doormanAddFile(zip, path, content, hashes) {
  zip.file(path, content);
  hashes[path] = await _doormanSha256Hex(content);
}

// Fetch a file from the resolved private layer via the GitHub Contents
// API. CORS-safe with auth (raw.githubusercontent.com isn't) — same
// path loadPrivateContext takes. Returns null on 404.
async function _privateFile(coords, path, token) {
  if (!coords || !token) return null;
  const url = `https://api.github.com/repos/${coords.owner}/${coords.repo}/contents/` +
              path.split("/").map(encodeURIComponent).join("/");
  return _doormanFetchOrNull(url, {
    "Authorization": "Bearer " + token,
    "Accept": "application/vnd.github.raw+json",
  });
}

async function buildAscendedEgg() {
  if (typeof JSZip === "undefined") throw new Error("JSZip didn't load");
  const token = getToken();
  if (!token) throw new Error("not signed in — sign in first to export the ascended cartridge");
  if (!privateLayerCoords) throw new Error("no ascended access — only operators or private-companion collaborators can export the full organism");

  const zip = new JSZip();
  // Match bond.py's count keys + add ascended-only extras (private_files,
  // user_memories) so a receiving kernel can see what extras shipped.
  const counts = {
    agents: 0, organs: 0, senses: 0, services: 0, data: 0,
    soul: 0, env: 0, rappid: 0, card: 0,
    private_files: 0, user_memories: 0,
  };
  // Per-file SHA-256s for the ascended egg. Same scheme as the doorman
  // tier — every file gets a hash; the manifest carries the table plus
  // a sha256 fingerprint of the table itself. Receivers can recompute
  // and detect any offline tampering.
  const hashes = {};

  // Resolve the seed-side base for public files (the front-door root,
  // one level up from /doorman/).
  const seedBase = location.origin + location.pathname.replace(/\/doorman\/?$/, "/");

  // 1. Public layer — same files the doorman-tier egg packs
  const rappidText = await _doormanFetchOrNull(seedBase + "rappid.json");
  if (!rappidText) throw new Error("can't read seed rappid.json");
  await _doormanAddFile(zip, "rappid.json", rappidText, hashes);
  counts.rappid = 1;
  let rappidObj = {};
  try { rappidObj = JSON.parse(rappidText); } catch (_) {}

  const soul = await _doormanFetchOrNull(seedBase + "soul.md");
  if (soul && soul.trim()) { await _doormanAddFile(zip, "soul.md", soul, hashes); counts.soul = 1; }

  const card = await _doormanFetchOrNull(seedBase + "card.json");
  if (card && card.trim()) { await _doormanAddFile(zip, "card.json", card, hashes); counts.card = 1; }

  // 2. agents/ — both tiers (the kernel ignores ascended ones unless
  //    privateSoul is set, so it's safe to include all of them in the egg)
  for (const fn of ASCENDED_AGENT_FILES) {
    const text = await _doormanFetchOrNull(SEED_AGENT_BASE + fn);
    if (text) { await _doormanAddFile(zip, "agents/" + fn, text, hashes); counts.agents++; }
  }
  await _doormanAddFile(zip, "agents/__init__.py", "", hashes);

  // 3. data/memory.json — public memory
  const mem = await _doormanFetchOrNull(seedBase + ".brainstem_data/memory.json");
  if (mem) {
    await _doormanAddFile(zip, "data/memory.json", mem, hashes);
    counts.data = 1;
  }

  // 4. private/ subtree — what the operator-fallback OR private-companion
  //    access unlocks. soul.md, README.md, vault entrypoint, private memory.
  const PRIV_PATHS = [
    "soul.md",
    "README.md",
    "vault/00 Index/Home.md",
    ".brainstem_data/memory.json",
    "memory.json",
  ];
  for (const path of PRIV_PATHS) {
    const text = await _privateFile(privateLayerCoords, path, token);
    if (text) {
      await _doormanAddFile(zip, "private/" + path, text, hashes);
      counts.private_files++;
    }
  }

  // 5. data/user_memories.json — issues filed by ascended visitors
  //    (label: private-memory). Captures the per-user memory tier so
  //    a hatched kernel can rebuild the [@<login>] facts.
  try {
    const r = await fetch(
      `https://api.github.com/repos/${privateLayerCoords.owner}/${privateLayerCoords.repo}/issues?labels=private-memory&state=all&per_page=100`,
      { headers: { "Authorization": "Bearer " + token, "Accept": "application/vnd.github+json" } }
    );
    if (r.ok) {
      const issues = await r.json();
      if (Array.isArray(issues)) {
        const facts = [];
        for (const it of issues) {
          if (it.body && it.body.trim()) {
            facts.push({
              login: it.user && it.user.login || "anonymous",
              body: it.body.trim(),
              issue_number: it.number,
              issue_url: it.html_url,
              created_at: it.created_at,
            });
          }
        }
        if (facts.length) {
          const userMemBlob = JSON.stringify({
            schema: "rapp-user-memories/1.0",
            source_repo: `${privateLayerCoords.owner}/${privateLayerCoords.repo}`,
            exported_at: new Date().toISOString(),
            facts,
          }, null, 2);
          await _doormanAddFile(zip, "data/user_memories.json", userMemBlob, hashes);
          counts.user_memories = facts.length;
        }
      }
    }
  } catch (_) { /* if issues read fails, the egg still ships without user_memories */ }

  // Provenance — non-GMO integrity. Same scheme as the doorman egg.
  const manifestHash = await _doormanSha256Hex(_doormanCanonicalHashTable(hashes));
  const provenance = {
    schema: "rapp-egg-provenance/1.0",
    scheme: "sha256",
    file_hashes: hashes,
    manifest_hash: manifestHash,
    origin_url: seedBase,
    origin_repo: rappidObj.github || null,
    sealed_at: new Date().toISOString(),
    sealed_by_rappid: rappidObj.rappid || null,
    sealed_by_login: viewerLogin ? "@" + viewerLogin : null,
  };

  // 6. Manifest — same shape bond.py writes; tier="ascended" + the
  //    resolved private layer so a receiving kernel can re-link.
  const manifest = {
    schema: "brainstem-egg/2.2-organism",
    type: "organism",
    tier: "ascended",
    exported_at: new Date().toISOString(),
    exported_from: location.origin + location.pathname,
    exported_by: viewerLogin ? "@" + viewerLogin : null,
    operator_fallback: !!isOperator,
    host: "doorman-export",
    kernel_version: "0.6.0",
    rappid: rappidObj.rappid || null,
    parent_rappid: rappidObj.parent_rappid || null,
    parent_repo: rappidObj.parent_repo || null,
    private_layer: privateLayerCoords && (privateLayerCoords.owner + "/" + privateLayerCoords.repo) || null,
    kind: rappidObj.kind || null,
    display_name: rappidObj.display_name || null,
    incarnations_at_egg: rappidObj.incarnations || 0,
    counts,
    provenance,
  };
  zip.file("manifest.json", JSON.stringify(manifest, null, 2));

  return await zip.generateAsync({ type: "blob" });
}

async function exportAscendedEgg() {
  const btn = document.getElementById("btn-export-ascended");
  if (!btn) return;
  const orig = btn.textContent;
  btn.textContent = "🥚 packing…";
  btn.disabled = true;
  try {
    const blob = await buildAscendedEgg();
    const slug = ((identity && identity.rappid) || "rapp").slice(0, 8);
    const name = (identity && (identity.display_name || identity.name) || "rapp")
      .toLowerCase().replace(/[^a-z0-9]+/g, "-");
    const a = document.createElement("a");
    const url = URL.createObjectURL(blob);
    a.href = url; a.download = `${name}-${slug}-ascended.egg`;
    document.body.appendChild(a); a.click();
    setTimeout(() => { URL.revokeObjectURL(url); a.remove(); }, 0);
    btn.textContent = "✓ downloaded";
    setTimeout(() => { btn.textContent = orig; btn.disabled = false; }, 1800);
  } catch (e) {
    btn.textContent = "✗ " + (e.message || "failed").slice(0, 50);
    setTimeout(() => { btn.textContent = orig; btn.disabled = false; }, 3500);
  }
}

function agentInventoryForPrompt() {
  if (publicAgents.length === 0 && privateAgents.length === 0) return "";
  const lines = ["", "=== Agent inventory (capabilities your body has) ==="];
  if (publicAgents.length) {
    lines.push("Public agents (always available, install kernel locally to run them):");
    for (const f of publicAgents) lines.push("  - agents/" + f);
  }
  if (privateAgents.length) {
    lines.push("Private agents (loaded because the visitor authenticated with private-brain access):");
    for (const f of privateAgents) lines.push("  - agents/" + f + " [private]");
  }
  lines.push("Note: this chat surface (the doorman) doesn't execute these directly — it's a JS vbrainstem. Reference them by name when describing your own capabilities; they become live tools when someone installs your kernel locally.");
  lines.push("=== End agent inventory ===");
  return lines.join("\n");
}

// ── private companion: best-effort fetch ───────────────────────────
//
// Silent escalation pattern. Same raw.githubusercontent.com URL shape
// for public and private repos — private content resolves ONLY when the
// visitor's token has read access. No access? The fetches return 404 and
// we just skip them. No error surfaced; doorman keeps speaking from
// public memory only.
//
// Three layers we look for in the private companion, in priority order:
//   1. soul.md — when loaded, the doorman ASCENDS into the full twin's
//      voice. The default kind-aware greeter persona is replaced by
//      the full soul, since the visitor has authenticated access to
//      the private brain.
//   2. Supporting prose — README, vault entrypoint — appended as
//      additional context after the soul.
//   3. Private memory.json files — merged into the running memory list
//      with a [private] prefix so the LLM sees the access boundary.
async function loadPrivateContext(token) {
  privateContext = "";
  privateSoul = null;
  privateFactsCount = 0;
  privateLayerCoords = null;
  isOperator = false;
  if (!identity) return;

  // Resolve the private-layer coords. Two paths produce ascension:
  //   1. Explicit `private_companion` configured at plant time (e.g. a
  //      personal twin seed paired to a private repo holding the full
  //      brain). Anyone the operator has granted read access to that
  //      private repo silently ascends.
  //   2. **Operator fallback** — the seed has no private companion, but
  //      the authed visitor has push access to the seed repo itself
  //      (i.e. they ARE the operator/owner). The seed becomes its own
  //      private layer: ascended tools unlock, per-user issue memory
  //      writes against the seed repo. This is what makes `plant`-and-
  //      go seeds (like Heimdall) ascend for their owners without
  //      forcing a separate companion repo.
  let c = privateCompanionCoords();
  let isOperatorFallback = false;
  if (!c && token) {
    const seed = repoCoords();
    if (await checkPushAccess(seed.owner, seed.repo, token)) {
      c = seed;
      isOperatorFallback = true;
    }
  }
  if (!c) return;
  privateLayerCoords = c;
  isOperator = isOperatorFallback;

  // CORS-aware private file reads: raw.githubusercontent.com blocks
  // browsers from sending Authorization headers (preflight 404). Use the
  // GitHub Contents API instead — it supports CORS for authenticated
  // requests and returns raw file content with the right Accept header.

  async function fetchPrivateFile(path) {
    try {
      const url = `https://api.github.com/repos/${c.owner}/${c.repo}/contents/` +
                  path.split("/").map(encodeURIComponent).join("/");
      const r = await fetch(url, {
        headers: {
          "Authorization": "Bearer " + token,
          "Accept": "application/vnd.github.raw+json",
        },
      });
      if (!r.ok) return null;
      return await r.text();
    } catch (_) {
      return null;
    }
  }

  const PROSE_CANDIDATES = ["README.md", "vault/00 Index/Home.md"];
  const MEMORY_CANDIDATES = ["memory.json", ".brainstem_data/memory.json"];

  // 1. soul.md FIRST — if reachable, it becomes the primary voice.
  const soulText = await fetchPrivateFile("soul.md");
  if (soulText && soulText.trim()) privateSoul = soulText.trim().slice(0, 8000);

  // 2. Supporting prose — README, vault entrypoint
  for (const path of PROSE_CANDIDATES) {
    if (privateContext.length >= 4000) break;
    const text = await fetchPrivateFile(path);
    if (text) {
      privateContext = (privateContext + "\n\n" + text).trim().slice(0, 4000);
    }
  }

  // 3. Private memory: parse .facts arrays from JSON memory files
  for (const path of MEMORY_CANDIDATES) {
    const text = await fetchPrivateFile(path);
    if (!text) continue;
    try {
      const j = JSON.parse(text);
      if (Array.isArray(j.facts)) {
        for (const f of j.facts) {
          if (typeof f === "string" && f.trim()) {
            memory.facts.push("[private] " + f.trim());
            privateFactsCount++;
          }
        }
      }
    } catch (_) { /* not JSON, skip */ }
  }

  // Operator fallback: if we got here via push-access and didn't pick up
  // a soul.md from the auth path (perhaps the file isn't there, or only
  // exists at the seed root and was already loaded as publicSoul), copy
  // publicSoul into privateSoul so the ascension gate fires. The operator
  // doesn't need a separate private brain — they ARE the brain.
  if (isOperator && !privateSoul && publicSoul) {
    privateSoul = publicSoul;
  }

  // Badge defer — we'll render it in refreshIndicator() after loadAgents
  // also runs (agent count is part of the badge in ascended mode).
}

function refreshIndicator() {
  const ind = document.getElementById("private-indicator");
  if (!ind) return;
  const userMemTag = (viewerLogin && userPrivateFactsCount > 0)
    ? `+ ${userPrivateFactsCount} of your own (@${viewerLogin})` : null;
  const deviceMemTag = deviceFactsCount > 0
    ? `+ ${deviceFactsCount} on this device` : null;
  if (privateSoul) {
    const extras = [];
    if (privateContext)         extras.push(`+ ${privateContext.length}c prose`);
    if (privateFactsCount > 0)  extras.push(`+ ${privateFactsCount} private mem`);
    if (privateAgents.length)   extras.push(`+ ${privateAgents.length} private agent${privateAgents.length === 1 ? "" : "s"}`);
    if (userMemTag)             extras.push(userMemTag);
    if (deviceMemTag)           extras.push(deviceMemTag);
    const tail = extras.length ? ` (${extras.join(", ")})` : "";
    ind.innerHTML = `<span class="private-badge">✓ ascended — full twin voice loaded${tail}</span>`;
  } else if (privateContext || privateFactsCount > 0 || privateAgents.length > 0 || userPrivateFactsCount > 0) {
    const bits = [];
    if (privateContext)        bits.push(`prose ${privateContext.length}c`);
    if (privateFactsCount > 0) bits.push(`+${privateFactsCount} private mem`);
    if (privateAgents.length)  bits.push(`+${privateAgents.length} private agent${privateAgents.length === 1 ? "" : "s"}`);
    if (userMemTag)            bits.push(userMemTag);
    if (deviceMemTag)          bits.push(deviceMemTag);
    ind.innerHTML = `<span class="private-badge">✓ private brain loaded — ${bits.join(", ")}</span>`;
  } else if (deviceMemTag) {
    ind.innerHTML = `<span class="private-badge" style="background:rgba(31,111,235,0.12);color:#58a6ff;border-color:rgba(31,111,235,0.3);">${deviceMemTag.replace(/^\+ /, "")}</span>`;
  } else {
    ind.innerHTML = "";
  }
}

// ── tools (LLM-driven agent dispatch — same shape as a local brainstem) ──
//
// The LLM calls these as tools during chat. Each one mirrors a standard
// agent's metadata schema verbatim — same names, same parameters, same
// descriptions. The local brainstem dispatches to the .py agent's
// perform(); the vbrainstem dispatches to the JS handler below; both
// fulfil the same contract from the LLM's perspective. Storage is the
// only thing that adapts: local files there, GitHub APIs here.

// Doorman-tier tools (always loaded — public agents from the seed)
const DOORMAN_TOOLS = [
  {
    type: "function",
    function: {
      name: "ManageMemory",
      description: "Saves information to persistent memory for future conversations. You MUST call this tool whenever the user asks you to remember something, shares personal facts (name, preferences, birthdays, etc.), or tells you something they expect you to recall later. Do not just acknowledge — call this tool or the information will be lost.",
      parameters: {
        type: "object",
        properties: {
          memory_type: { type: "string", enum: ["fact", "preference", "insight", "task"], description: "Type of memory to store." },
          content:     { type: "string", description: "The content to store in memory." },
          importance:  { type: "integer", minimum: 1, maximum: 5, description: "Importance rating from 1-5." },
          tags:        { type: "array", items: { type: "string" }, description: "Optional list of tags to categorize this memory." },
          user_guid:   { type: "string", description: "Optional unique identifier of the user (their GitHub @login) to store the memory in a user-specific location. Omit to store to shared/public memory." },
        },
        required: ["content"],
      },
    },
  },
  {
    type: "function",
    function: {
      name: "ContextMemory",
      description: "Recalls relevant facts from stored memories of past interactions. Useful when the user references something from a prior conversation or asks 'do you remember…'.",
      parameters: {
        type: "object",
        properties: {
          user_guid:   { type: "string", description: "Optional GitHub @login to recall memories from a user-specific location." },
          keywords:    { type: "array", items: { type: "string" }, description: "Optional keywords to filter memories by." },
          full_recall: { type: "boolean", description: "Optional: return all memories without filtering." },
        },
      },
    },
  },
];

// Ascended-tier tools (loaded only when private soul is reachable —
// the visitor has authenticated read access to the private companion).
// Schemas mirror the .py agents in kody-w/RAPP's rapp_brainstem/agents/.
// These get added to the LLM's tool surface alongside the doorman ones
// when ascension fires; otherwise hidden.
const ASCENDED_TOOLS = [
  {
    type: "function",
    function: {
      name: "LearnNew",
      description: "Generates a brand-new single-file agent the twin can use going forward — for one-shot tasks the operator wants the twin to handle later (fetch, lookup, classify, transform). YOU (the LLM) compose the full Python source for the agent — one class extending BasicAgent with a `metadata` dict and a `perform()` method — and pass it as `agent_code`. The vbrainstem returns it for the operator to commit; the local brainstem hot-loads it on next request. Use this when the user says \"learn how to X\" or \"remember how to Y\" where X/Y is a repeatable capability, not a fact.",
      parameters: {
        type: "object",
        properties: {
          query: {
            type: "string",
            description: "What the operator wants the new agent to do, in their words.",
          },
          agent_name: {
            type: "string",
            description: "PascalCase name for the agent class (e.g. 'XkcdFetcher'). Filename will be the snake_case form + '_agent.py'.",
          },
          agent_code: {
            type: "string",
            description: "Full Python source for the agent — one file, one class extending BasicAgent, a metadata dict, a perform(**kwargs) method that returns a string.",
          },
        },
        required: ["query", "agent_name", "agent_code"],
      },
    },
  },
  {
    type: "function",
    function: {
      name: "SwarmFactory",
      description: "Generates a multi-persona swarm — a single agent file containing several internal persona classes (each with its own SOUL/system-prompt) plus a public composite that orchestrates them in sequence. Use for converged pipelines: research→write→critique, plan→draft→review, etc. NOT for single one-shot agents — use LearnNew for those. YOU (the LLM) compose the full source and pass it as `agent_code`.",
      parameters: {
        type: "object",
        properties: {
          query: {
            type: "string",
            description: "What the swarm should do end-to-end, in the operator's words.",
          },
          swarm_name: {
            type: "string",
            description: "PascalCase name for the public composite class (e.g. 'BookFactory').",
          },
          agent_code: {
            type: "string",
            description: "Full Python source — multiple internal persona classes (each with a SOUL prompt) + ONE public composite class extending BasicAgent that calls them in sequence.",
          },
        },
        required: ["query", "swarm_name", "agent_code"],
      },
    },
  },
];

// TOOL_DEFS gets recomputed each chat turn based on whether Pyodide has
// loaded the agents (preferred) and whether ascension fired (gates the
// 2 ascended-tier tools).
function chatToolDefs() {
  // Pyodide-loaded agents take priority — they're the canonical tool defs
  // pulled directly from the .py agents' self.metadata.
  const pyDefs = pyAgentsToolDefs();
  if (pyDefs.length > 0) return pyDefs;
  // Fallback: hardcoded JS-impl tools (used while Pyodide is still loading
  // or if it failed). Anonymous fast path returns instantly via these.
  if (privateSoul) return DOORMAN_TOOLS.concat(ASCENDED_TOOLS);
  return DOORMAN_TOOLS;
}

// ─────────────────────────────────────────────────────────────────
//  Pyodide — agents.py running in the browser (the real vbrainstem)
// ─────────────────────────────────────────────────────────────────
//
// Same agent.py files as a local brainstem (kody-w/RAPP raw URLs).
// Same agent contract: a class extending BasicAgent with .metadata
// and .perform(**kwargs). Different storage shim — instead of writing
// to local disk via AzureFileStorageManager, the shim writes to
// localStorage on this device (anon + fallback) and the LLM-driven
// per-user / public flow you've already seen.

let pyodide = null;
let pyAgents = {};            // agent_name (e.g. "ManageMemory") → { instance: PyProxy, metadata: object }
let pyodideLoadingPromise = null;

const SEED_AGENT_BASE = "https://raw.githubusercontent.com/kody-w/RAPP/main/rapp_brainstem/agents/";
const PYODIDE_AGENTS = [
  { file: "manage_memory_agent.py",  className: "ManageMemoryAgent",  tier: "doorman"  },
  { file: "context_memory_agent.py", className: "ContextMemoryAgent", tier: "doorman"  },
  { file: "learn_new_agent.py",      className: "LearnNewAgent",      tier: "ascended" },
  { file: "swarm_factory_agent.py",  className: "SwarmFactoryAgent",  tier: "ascended" },
];

// Build OpenAI-format tool defs from Pyodide-loaded agents' metadata.
function pyAgentsToolDefs() {
  const defs = [];
  for (const [name, info] of Object.entries(pyAgents)) {
    if (!info || !info.metadata) continue;
    const m = info.metadata;
    defs.push({
      type: "function",
      function: {
        name: name,
        description: m.description || ("Run " + name),
        parameters: m.parameters || { type: "object", properties: {}, required: [] },
      },
    });
  }
  return defs;
}

// Embedded Python sources — mirrors the egg hub vbrainstem (summon.html)
// pattern: write canonical `utils/local_storage.py` with all the methods
// agents expect, plus thin re-export shims for the other storage names.
// All localStorage-backed; `from js import localStorage` direct, no JS
// callback hops.
const VB_LOCAL_STORAGE_PY = `"""utils/local_storage.py — Pyodide variant.
Drop-in for AzureFileStorageManager. Same API as the local brainstem's
rapp_brainstem/utils/local_storage.py — agents can't tell."""
import json
from js import localStorage

_PREFIX = "vbrainstem_storage:"

class AzureFileStorageManager:
    DEFAULT_MARKER_GUID = "c0p110t0-aaaa-bbbb-cccc-123456789abc"
    def __init__(self, share_name=None, **kwargs):
        self.current_guid = None
        self.shared_memory_path = "shared_memories"
        self.default_file_name = "memory.json"
        self.current_memory_path = self.shared_memory_path
    def set_memory_context(self, user_guid=None):
        if not user_guid or user_guid == self.DEFAULT_MARKER_GUID:
            self.current_guid = None
            self.current_memory_path = self.shared_memory_path
            return True
        self.current_guid = user_guid
        self.current_memory_path = "memory/" + user_guid
        return True
    def _file_path(self):
        if self.current_guid:
            return "memory/" + self.current_guid + "/user_memory.json"
        return "shared_memories/memory.json"
    def read_json(self, file_path=None):
        path = file_path or self._file_path()
        raw = localStorage.getItem(_PREFIX + path)
        if raw is None:
            return {}
        try:
            return json.loads(raw)
        except Exception:
            return {}
    def write_json(self, data, file_path=None):
        path = file_path or self._file_path()
        localStorage.setItem(_PREFIX + path, json.dumps(data, default=str))
        return True
    def read_file(self, file_path):
        return localStorage.getItem(_PREFIX + file_path)
    def write_file(self, file_path, content):
        localStorage.setItem(_PREFIX + file_path, content)
        return True
    def list_files(self, directory=""):
        prefix = _PREFIX + directory
        out = []
        n = localStorage.length
        for i in range(n):
            k = localStorage.key(i)
            if k and k.startswith(prefix):
                out.append(k[len(_PREFIX):])
        return out
    def delete_file(self, file_path):
        if localStorage.getItem(_PREFIX + file_path) is not None:
            localStorage.removeItem(_PREFIX + file_path)
            return True
        return False
    def file_exists(self, file_path):
        return localStorage.getItem(_PREFIX + file_path) is not None
`;

const VB_AZURE_REEXPORT_PY    = "from utils.local_storage import AzureFileStorageManager\n";
const VB_DYNAMICS_REEXPORT_PY = "from utils.local_storage import AzureFileStorageManager\nDynamicsStorageManager = AzureFileStorageManager\n";
const VB_FACTORY_PY           = "from utils.local_storage import AzureFileStorageManager\ndef get_storage_manager():\n    return AzureFileStorageManager()\n";

// Lazy-load Pyodide and the agents. Idempotent — call multiple times.
// Pattern mirrors the egg hub vbrainstem (summon.html): use Pyodide's
// virtual filesystem (FS.writeFile) with sys.path.insert(0, '/'), so
// agents `import from utils.azure_file_storage` cleanly without sys.modules
// tricks.
async function initPyodide() {
  if (pyodide && Object.keys(pyAgents).length) return pyodide;
  if (pyodideLoadingPromise) return pyodideLoadingPromise;
  pyodideLoadingPromise = (async () => {
    try {
      // Wait for the CDN script to define loadPyodide (deferred load)
      let waited = 0;
      while (typeof loadPyodide === "undefined" && waited < 12000) {
        await new Promise(r => setTimeout(r, 100));
        waited += 100;
      }
      if (typeof loadPyodide === "undefined") {
        console.info("[doorman] Pyodide CDN didn't load; falling back to JS tool impls");
        return null;
      }
      renderMsg("system", "loading agents…");
      pyodide = await loadPyodide({
        indexURL: "https://cdn.jsdelivr.net/pyodide/v0.26.4/full/",
      });

      // Pull the canonical BasicAgent source from grail — same as summon.html
      // does (absolute URL, since the relative path may not resolve when this
      // page is hosted under different seeds).
      const basicAgentResp = await fetch("https://raw.githubusercontent.com/kody-w/rapp-installer/main/rapp_brainstem/agents/basic_agent.py", { cache: "force-cache" });
      const basicAgentPy = basicAgentResp.ok ? await basicAgentResp.text() : "class BasicAgent:\n    def __init__(self, name=None, metadata=None):\n        if name is not None: self.name = name\n        if metadata is not None: self.metadata = metadata\n    def system_context(self):\n        return None\n";

      // Stand up the virtual FS. Same layout as summon.html.
      pyodide.FS.mkdirTree("/agents");
      pyodide.FS.writeFile("/agents/basic_agent.py", basicAgentPy);
      pyodide.FS.writeFile("/agents/__init__.py", "");
      pyodide.FS.mkdirTree("/utils");
      pyodide.FS.writeFile("/utils/__init__.py", "");
      pyodide.FS.writeFile("/utils/local_storage.py", VB_LOCAL_STORAGE_PY);
      pyodide.FS.writeFile("/utils/azure_file_storage.py", VB_AZURE_REEXPORT_PY);
      pyodide.FS.writeFile("/utils/dynamics_storage.py", VB_DYNAMICS_REEXPORT_PY);
      pyodide.FS.writeFile("/utils/storage_factory.py", VB_FACTORY_PY);
      await pyodide.runPythonAsync(`import sys; sys.path.insert(0, '/')`);

      // Load each agent .py — same source as a local brainstem.
      // Write to /agents/<file>.py and import its class via runPython.
      const token = getToken();
      for (const cfg of PYODIDE_AGENTS) {
        if (cfg.tier === "ascended" && !privateSoul) continue;
        try {
          const r = await fetch(SEED_AGENT_BASE + cfg.file, { cache: "no-cache" });
          if (!r.ok) {
            console.info("[doorman] couldn't fetch", cfg.file, r.status);
            continue;
          }
          const source = await r.text();
          // Drop into the FS so `import agents.<name>` works
          pyodide.FS.writeFile("/agents/" + cfg.file, source);
          const moduleName = cfg.file.replace(/\.py$/, "");
          // Import the module + grab the class + instantiate, all in one runPython
          await pyodide.runPythonAsync(
            `from agents.${moduleName} import ${cfg.className} as _Cls\n` +
            `_inst = _Cls()\n` +
            `_agent_${cfg.className.replace(/Agent$/, "")} = _inst\n`
          );
          const instance = pyodide.globals.get("_agent_" + cfg.className.replace(/Agent$/, ""));
          if (!instance) {
            console.info("[doorman] couldn't capture instance for", cfg.className);
            continue;
          }
          const metadataPy = instance.metadata;
          const metadata = metadataPy && metadataPy.toJs
            ? metadataPy.toJs({ dict_converter: Object.fromEntries })
            : metadataPy;
          const agentName = (instance.name && String(instance.name)) || cfg.className.replace(/Agent$/, "");
          pyAgents[agentName] = { instance, metadata, source };
          console.info("[doorman] loaded agent", agentName, "from", cfg.file);
        } catch (e) {
          console.info("[doorman] agent load failed for", cfg.file, ":", e && (e.message || e));
        }
      }

      const loaded = Object.keys(pyAgents);
      if (loaded.length) {
        renderMsg("system", "loaded " + loaded.length + " agent" + (loaded.length === 1 ? "" : "s") + " (Pyodide): " + loaded.join(", "));
      } else {
        renderMsg("system", "Pyodide ready (no agents loaded — using JS tool impls)");
      }
      refreshIndicator();
      return pyodide;
    } catch (e) {
      console.info("[doorman] Pyodide init failed:", e && (e.message || e));
      pyodide = null;
      return null;
    }
  })();
  return pyodideLoadingPromise;
}

// Dispatch a tool call to a Pyodide-loaded agent. Returns a string result
// (per the tool API). Falls back to JS handlers if the Pyodide agent
// isn't available (e.g. Pyodide still loading or load failed).
async function dispatchPyodideToolCall(tc, args) {
  const info = pyAgents[tc.function.name];
  if (!info) return null;  // signal: not handled here, caller should fall back
  try {
    pyodide.globals.set("_call_args", pyodide.toPy(args));
    const result = await pyodide.runPythonAsync(`
import json
_a = _call_args.to_py() if hasattr(_call_args, 'to_py') else dict(_call_args)
_r = _agent_${tc.function.name}.perform(**_a)
_r if isinstance(_r, str) else json.dumps(_r)
`);
    return typeof result === "string" ? result : String(result);
  } catch (e) {
    return "agent error: " + (e && e.message ? e.message : String(e));
  }
}

// Tool dispatchers — JS implementations of the agents' perform() methods
// adapted for the vbrainstem's storage tiers. Same return shape as the
// LLM expects. Three tiers, picked silently:
//   1. authed + has private access + user_guid matches viewerLogin
//      → GitHub Issue in private_companion repo (per-user, durable, syncs)
//   2. anyone else (anon, or authed without private access)
//      → localStorage on this device (per-front-door-per-browser)
// No public-memory.json writes here — that surface is read-only at the
// vbrainstem; the operator's local brainstem is the writer for that
// tier (it git-commits to .brainstem_data/memory.json directly).
async function toolManageMemory(args) {
  const content = (args.content || "").trim();
  if (!content) return "no content provided";
  const hasPrivateAccess = !!privateSoul || !!privateContext || privateAgents.length > 0 || privateFactsCount > 0;
  const wantPerUser = args.user_guid && viewerLogin && args.user_guid === viewerLogin;
  if (hasPrivateAccess && wantPerUser) {
    const r = await saveUserPrivateMemory(content);
    if (r.ok) return `saved as @${viewerLogin}'s private memory (Issue #${r.number})`;
    // fall through to device save on any failure — never leak access reasons
  }
  saveDeviceMemory(content);
  return "saved to this device's memory";
}

async function toolContextMemory(args) {
  let facts = (memory.facts || []).slice();
  if (args.user_guid && viewerLogin && args.user_guid === viewerLogin) {
    facts = facts.filter(f => f.startsWith("[@" + viewerLogin + "]"));
  }
  if (Array.isArray(args.keywords) && args.keywords.length && !args.full_recall) {
    const kws = args.keywords.map(k => String(k).toLowerCase());
    facts = facts.filter(f => kws.some(k => f.toLowerCase().includes(k)));
  }
  return facts.length ? facts.join("\n") : "(no matching memories)";
}

async function toolLearnNew(args) {
  // Vbrainstem stub: returns the generated code so the operator can apply
  // it via their local brainstem. The actual agent file lands in <seed>/
  // agents/<snake>_agent.py when committed locally + git-pushed. (Pyodide
  // execution path is a future upgrade — for now the operator confirms.)
  const code = (args.agent_code || "").trim();
  const name = (args.agent_name || "NewAgent").trim();
  if (!code) return "no agent_code supplied — generate the source and call again";
  // Cache the draft in localStorage so the operator can review/copy later
  try {
    const drafts = JSON.parse(localStorage.getItem("rapp_doorman_agent_drafts") || "[]");
    drafts.push({ kind: "learn_new", name, query: args.query || "", code, drafted_at: new Date().toISOString() });
    localStorage.setItem("rapp_doorman_agent_drafts", JSON.stringify(drafts));
  } catch (_) { /* best-effort */ }
  return `drafted agent "${name}" (${code.length} chars). Saved as a draft in this browser. To make it live, drop it into <seed>/agents/${name.replace(/([A-Z])/g, "_$1").replace(/^_/, "").toLowerCase()}_agent.py and git push from the local brainstem.`;
}

async function toolSwarmFactory(args) {
  const code = (args.agent_code || "").trim();
  const name = (args.swarm_name || "NewSwarm").trim();
  if (!code) return "no agent_code supplied — generate the swarm source and call again";
  try {
    const drafts = JSON.parse(localStorage.getItem("rapp_doorman_agent_drafts") || "[]");
    drafts.push({ kind: "swarm_factory", name, query: args.query || "", code, drafted_at: new Date().toISOString() });
    localStorage.setItem("rapp_doorman_agent_drafts", JSON.stringify(drafts));
  } catch (_) { /* best-effort */ }
  return `drafted swarm "${name}" (${code.length} chars). Saved as a draft in this browser. To make it live, drop into <seed>/agents/${name.replace(/([A-Z])/g, "_$1").replace(/^_/, "").toLowerCase()}_swarm.py and git push from the local brainstem.`;
}

async function dispatchToolCall(tc) {
  let args = {};
  try { args = JSON.parse(tc.function.arguments || "{}"); } catch (_) { /* keep default */ }
  // Try Pyodide-loaded agents first (real .py running in-browser)
  if (pyodide && pyAgents[tc.function.name]) {
    const result = await dispatchPyodideToolCall(tc, args);
    if (result !== null) return result;
  }
  // Fallback: JS-impl tools (used while Pyodide loads, or if loading failed)
  if (tc.function.name === "ManageMemory")  return toolManageMemory(args);
  if (tc.function.name === "ContextMemory") return toolContextMemory(args);
  if (tc.function.name === "LearnNew")      return toolLearnNew(args);
  if (tc.function.name === "SwarmFactory")  return toolSwarmFactory(args);
  return "unknown tool: " + tc.function.name;
}

// ── chat ───────────────────────────────────────────────────────────
function escapeHtml(s) {
  return String(s ?? "")
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}
function renderMsg(role, text) {
  const log = document.getElementById("chat-log");
  const div = document.createElement("div");
  div.className = "msg " + role;
  if (role === "user") {
    // Plaintext for what the visitor typed — no markdown surprises.
    div.textContent = text;
  } else if (window.marked && text) {
    // marked.parse handles bold, lists, code, links, paragraphs.
    let html = window.marked.parse(text);
    // Force every link in assistant/system bubbles to open in a new tab.
    html = html.replace(/<a\s+href=/g, '<a target="_blank" rel="noopener noreferrer" href=');
    div.innerHTML = html;
  } else {
    // Fallback if marked failed to load — keep newlines visible at least.
    div.innerHTML = escapeHtml(text || "").replace(/\n/g, "<br>");
  }
  log.appendChild(div);
  log.scrollTop = log.scrollHeight;
  return div;
}

// Pending-reply bubble: an assistant-styled bubble with three bouncing
// dots, dropped into the chat where the LLM's reply will eventually
// land. The visitor sees the doorman is "thinking" instead of staring
// at silence. Replaced (or removed) once the reply / error arrives.
function renderPending(label) {
  const log = document.getElementById("chat-log");
  const div = document.createElement("div");
  div.className = "msg assistant pending";
  div.innerHTML =
    `<div class="typing"><span></span><span></span><span></span></div>` +
    (label ? `<div class="pending-label">${escapeHtml(label)}</div>` : "");
  log.appendChild(div);
  log.scrollTop = log.scrollHeight;
  return div;
}
function setPendingLabel(div, label) {
  if (!div) return;
  let el = div.querySelector(".pending-label");
  if (!el) {
    el = document.createElement("div");
    el.className = "pending-label";
    div.appendChild(el);
  }
  el.textContent = label || "";
}

async function sendMessage() {
  const input = document.getElementById("chat-input");
  const userMsg = input.value.trim();
  if (!userMsg) return;
  const token = getToken();
  if (!token) return;

  input.value = "";
  input.style.height = "auto";
  renderMsg("user", userMsg);
  history.push({ role: "user", content: userMsg });

  const pending = renderPending();
  const sendBtn = document.getElementById("btn-send");
  sendBtn.disabled = true;

  try {
    // Tool-call loop: identical pattern to the local brainstem's tool
    // dispatch — LLM emits tool_calls, we dispatch to the JS-implemented
    // agent (same metadata schema as the .py agent), append the result
    // as a 'tool' message, and re-call. Loop until LLM stops calling
    // tools (capped at 4 rounds, matching the local brainstem's cap).
    let rounds = 0;
    while (rounds++ < 4) {
      // Get a fresh Copilot session token (auto-refreshed if expired)
      let copilotToken;
      try {
        copilotToken = await ensureCopilotToken();
      } catch (e) {
        pending.remove();
        clearAuthState();
        document.getElementById("auth-pane").hidden = false;
        document.getElementById("chat-log").hidden = true;
        document.getElementById("input-bar").hidden = true;
        document.getElementById("chat-actions").hidden = true;
        document.getElementById("memory-pane").hidden = true;
        renderMsg("error", "Couldn't refresh Copilot token: " + e.message + ". Sign in again.");
        return;
      }
      const r = await fetch(activeChatUrl(), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": "Bearer " + copilotToken,
        },
        body: JSON.stringify({
          model: loadSettings().model || MODEL,
          messages: [
            { role: "system", content: buildSystemPrompt() },
            ...history,
          ],
          tools: chatToolDefs(),
          max_tokens: 800,
        }),
      });
      if (!r.ok) {
        const err = await r.text();
        if (r.status === 401) {
          // Copilot token expired or rejected — clear and re-auth.
          clearAuthState();
          history.length = 0;
          pending.remove();
          document.getElementById("auth-pane").hidden = false;
          document.getElementById("chat-log").hidden = true;
          document.getElementById("input-bar").hidden = true;
          document.getElementById("chat-actions").hidden = true;
          document.getElementById("memory-pane").hidden = true;
          renderMsg("error", "Sign-in expired. Sign in again to continue.");
          return;
        }
        throw new Error("HTTP " + r.status + ": " + err.slice(0, 250));
      }
      const data = await r.json();
      const msg = data.choices && data.choices[0] && data.choices[0].message;
      if (!msg) break;

      if (msg.tool_calls && msg.tool_calls.length) {
        // Record assistant's tool-call message in history (required by the API
        // for subsequent 'tool' role messages to be valid replies).
        history.push({
          role: "assistant",
          content: msg.content || null,
          tool_calls: msg.tool_calls,
        });
        // Execute every tool call in this turn, append results
        for (const tc of msg.tool_calls) {
          // Surface what the LLM is doing in the pending bubble so the
          // visitor isn't staring at silent dots while a tool runs.
          const pretty = String(tc.function.name || "tool")
            .replace(/([a-z])([A-Z])/g, "$1 $2");
          setPendingLabel(pending, "calling " + pretty + "…");
          const result = await dispatchToolCall(tc);
          history.push({
            role: "tool",
            tool_call_id: tc.id,
            content: typeof result === "string" ? result : JSON.stringify(result),
          });
          // Quiet system note so the visitor sees tool activity (matches
          // the agent_logs surface on a local brainstem).
          if (tc.function.name === "ManageMemory" && result.startsWith("saved")) {
            renderMsg("system", "memory saved");
          }
        }
        // Tools done → back to thinking while the LLM composes the reply.
        setPendingLabel(pending, "");
        refreshIndicator();
        continue; // call again — let LLM produce its final reply
      }

      // No tool calls — render the final assistant reply
      const reply = msg.content || "(empty response)";
      pending.remove();
      renderMsg("assistant", reply);
      history.push({ role: "assistant", content: reply });
      return;
    }
    pending.remove();
    renderMsg("error", "Tool-call loop exceeded 4 rounds — stopping.");
  } catch (e) {
    pending.remove();
    renderMsg("error", "Couldn't reach GitHub Models: " + e.message);
  } finally {
    sendBtn.disabled = false;
    input.focus();
  }
}

// ── enter the chat (token already saved or just-saved) ─────────────
async function enterChat() {
  document.getElementById("auth-pane").hidden = true;
  document.getElementById("chat-log").hidden = false;
  document.getElementById("input-bar").hidden = false;
  document.getElementById("chat-actions").hidden = false;

  const token = getToken();
  // Public soul (every visitor — overrides kind-aware default if present)
  await loadPublicSoul();
  // Memory: load before private context so the prompt assembly already has it
  await loadMemory();
  // Device-local memory: every visitor gets their on-device tier
  loadDeviceMemory();
  // Best effort: refresh from GH API (gives us the sha for write + freshest content)
  refreshMemorySha(token);  // fire-and-forget — doorman can chat without it
  await loadPrivateContext(token);
  await loadAgents(token);  // agent inventory (public always, private if authed-with-access)
  // Capture viewer identity for per-user private memory keying
  const cached = getCachedUser();
  if (cached && cached.login) viewerLogin = cached.login;
  if (!viewerLogin) {
    const u = await fetchAndCacheUser(token);
    if (u && u.login) viewerLogin = u.login;
  }
  if (viewerLogin) await loadUserPrivateIssues(token);
  refreshIndicator();        // badge reflects soul + memory + agents + per-user mem
  // Reveal the ascended-egg export button only when the visitor qualifies
  // for the private layer (operator fallback OR private-companion access).
  const ascBtn = document.getElementById("btn-export-ascended");
  if (ascBtn) ascBtn.hidden = !privateLayerCoords;
  // Render the model dropdown with the static fallback right away so the
  // visitor sees something selectable, then refresh asynchronously when
  // the Copilot catalog lands.
  renderModelOptions();
  fetchCopilotModels().catch(() => { /* dropdown keeps its fallback */ });
  // Lazy-load Pyodide + agents (non-blocking — chat works against JS
  // tool impls in the meantime; once Pyodide finishes loading, future
  // tool calls hit the real .py implementations).
  initPyodide().catch(() => { /* silent — JS fallbacks remain available */ });
  const place = identity.display_name || identity.name || "this place";
  const memCount = (memory.facts || []).length;
  const memNote = memCount ? ` I'm carrying ${memCount} memor${memCount === 1 ? "y" : "ies"} from past visits.` : "";
  if (isOperator) {
    const me = viewerLogin ? `@${viewerLogin}` : "the operator";
    renderMsg("system", `Hi — I'm ${place}. You're signed in as ${me}, my operator. Ascended tools loaded.${memNote}`);
  } else if (privateSoul) {
    renderMsg("system", `Hi — I'm ${place}. You've authenticated with access to my private brain — I'm in full voice.${memNote}`);
  } else if (publicSoul) {
    renderMsg("system", `Hi — I'm ${place}, here at my front door.${memNote}`);
  } else {
    renderMsg("system", `Hi — I'm ${place}, here at my front door.${memNote} Ask me anything.`);
  }
}

// ── init ───────────────────────────────────────────────────────────
(async function init() {
  await loadIdentity();
  if (getToken()) {
    enterChat();
  }
})();

// ── wire ───────────────────────────────────────────────────────────
function openSigninModal() {
  document.getElementById("cpsignin-modal").style.display = "flex";
  document.getElementById("cpsignin-step1").style.display = "block";
  document.getElementById("cpsignin-step2").style.display = "none";
  document.getElementById("cpsignin-step3").style.display = "none";
  document.getElementById("cpsignin-error").style.display = "none";
}
function closeSigninModal() {
  document.getElementById("cpsignin-modal").style.display = "none";
}
function showSigninError(msg) {
  const e = document.getElementById("cpsignin-error");
  e.textContent = msg;
  e.style.display = "block";
}

async function runCopilotSignin() {
  document.getElementById("cpsignin-step1").style.display = "none";
  document.getElementById("cpsignin-error").style.display = "none";
  try {
    const { user_code, verification_uri } = await copilotStartDeviceLogin();
    document.getElementById("cpsignin-code").textContent = user_code;
    const link = document.getElementById("cpsignin-link");
    link.href = verification_uri;
    document.getElementById("cpsignin-step2").style.display = "block";
    // No auto-open — visitor copies the code first, then clicks "Open GitHub →"
    // themselves. Auto-opening yanked focus before they could read/copy.
    const interval = (pendingDeviceLogin?.interval || 5) * 1000;
    const expires  = pendingDeviceLogin?.expires_at || (Date.now() + 900000);
    while (Date.now() < expires && pendingDeviceLogin) {
      await new Promise(r => setTimeout(r, interval));
      try {
        const tok = await copilotPollDeviceLogin();
        if (tok) break;
      } catch (e) { throw e; }
    }
    if (!getToken()) throw new Error("Login timed out — try again.");
    await copilotExchange();
    document.getElementById("cpsignin-step2").style.display = "none";
    document.getElementById("cpsignin-step3").style.display = "block";
    fetchAndCacheUser(getToken()).catch(() => {});
    setTimeout(async () => {
      closeSigninModal();
      await enterChat();
    }, 1000);
  } catch (e) {
    showSigninError(e.message || String(e));
    document.getElementById("cpsignin-step1").style.display = "block";
    document.getElementById("cpsignin-step2").style.display = "none";
  }
}

document.getElementById("btn-signin-github").addEventListener("click", openSigninModal);
document.getElementById("cpsignin-go").addEventListener("click", runCopilotSignin);
document.getElementById("cpsignin-close").addEventListener("click", closeSigninModal);

async function copyDeviceCode() {
  const code = document.getElementById("cpsignin-code").textContent.trim();
  if (!code || code === "XXXX-XXXX") return;
  let ok = false;
  try {
    await navigator.clipboard.writeText(code);
    ok = true;
  } catch (_) {
    // Fallback for older / non-secure-context browsers
    try {
      const ta = document.createElement("textarea");
      ta.value = code;
      ta.style.position = "fixed"; ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      ok = document.execCommand("copy");
      document.body.removeChild(ta);
    } catch (__) {}
  }
  const btn = document.getElementById("cpsignin-copy-code");
  const orig = btn.textContent;
  btn.textContent = ok ? "✓ Copied" : "Press & hold to copy";
  btn.style.background = ok ? "#238636" : "#21262d";
  btn.style.borderColor = ok ? "#2ea043" : "#30363d";
  btn.style.color = "#fff";
  setTimeout(() => {
    btn.textContent = orig;
    btn.style.background = "#21262d";
    btn.style.borderColor = "#30363d";
    btn.style.color = "#c9d1d9";
  }, 1600);
}
document.getElementById("cpsignin-copy-code").addEventListener("click", (e) => {
  e.stopPropagation();
  copyDeviceCode();
});
document.getElementById("cpsignin-code-box").addEventListener("click", copyDeviceCode);

document.getElementById("btn-save-pat").addEventListener("click", async () => {
  const tok = document.getElementById("pat-input").value.trim();
  if (!tok) return;
  saveSettings({ ghuToken: tok });
  document.getElementById("pat-input").value = "";
  // Try to exchange right away so we know the token's valid
  try { await copilotExchange(); } catch (_) { /* will surface on first chat */ }
  fetchAndCacheUser(tok).catch(() => {});
  await enterChat();
});
document.getElementById("btn-send").addEventListener("click", sendMessage);
document.getElementById("btn-clear").addEventListener("click", () => {
  history = [];
  document.getElementById("chat-log").innerHTML = "";
  const place = identity.display_name || identity.name || "this place";
  renderMsg("system", `Cleared. — ${place}`);
});
document.getElementById("btn-logout").addEventListener("click", () => {
  clearToken();
  location.reload();
});
document.getElementById("model-sel").addEventListener("change", (e) => {
  const id = e.target.value;
  if (!id) return;
  saveSettings({ model: id });
  renderMsg("system", "model → " + id);
});
const ascBtnEl = document.getElementById("btn-export-ascended");
if (ascBtnEl) ascBtnEl.addEventListener("click", exportAscendedEgg);
// Memory UI: open / cancel / commit
document.getElementById("btn-add-memory").addEventListener("click", () => {
  document.getElementById("memory-pane").hidden = false;
  document.getElementById("memory-input").focus();
});
document.getElementById("btn-cancel-memory").addEventListener("click", () => {
  document.getElementById("memory-pane").hidden = true;
  document.getElementById("memory-input").value = "";
  document.getElementById("memory-status").textContent = "";
});
document.getElementById("btn-save-device-memory").addEventListener("click", async () => {
  const input = document.getElementById("memory-input");
  const status = document.getElementById("memory-status");
  const fact = input.value.trim();
  if (!fact) return;
  if (saveDeviceMemory(fact)) {
    status.textContent = "saved on this device.";
    input.value = "";
    renderMsg("system", "Saved on-device memory: \"" + fact + "\"");
    setTimeout(() => {
      document.getElementById("memory-pane").hidden = true;
      status.textContent = "";
      refreshIndicator();
    }, 1500);
  } else {
    status.textContent = "couldn't save (browser storage unavailable).";
  }
});

document.getElementById("btn-save-private-memory").addEventListener("click", async () => {
  const input = document.getElementById("memory-input");
  const status = document.getElementById("memory-status");
  const fact = input.value.trim();
  if (!fact) return;
  status.textContent = "saving…";
  document.getElementById("btn-save-private-memory").disabled = true;
  const result = await saveUserPrivateMemory(fact);
  document.getElementById("btn-save-private-memory").disabled = false;
  if (result.ok) {
    const tag = viewerLogin ? "@" + viewerLogin : "you";
    status.textContent = `saved as ${tag}'s private memory.`;
    input.value = "";
    renderMsg("system", `Saved private memory (${tag}): "${fact}"`);
    setTimeout(() => {
      document.getElementById("memory-pane").hidden = true;
      status.textContent = "";
      refreshIndicator();
    }, 1500);
  } else {
    // Silent fallback to device — no access reveals
    if (saveDeviceMemory(fact)) {
      status.textContent = "saved on this device.";
      input.value = "";
      renderMsg("system", "Saved on-device memory: \"" + fact + "\"");
      setTimeout(() => {
        document.getElementById("memory-pane").hidden = true;
        status.textContent = "";
        refreshIndicator();
      }, 1500);
    } else {
      status.textContent = "couldn't save.";
    }
  }
});
document.getElementById("chat-input").addEventListener("keydown", e => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});
// Auto-grow textarea
document.getElementById("chat-input").addEventListener("input", e => {
  e.target.style.height = "auto";
  e.target.style.height = Math.min(e.target.scrollHeight, 200) + "px";
});
</script>
</body>
</html>
TEMPLATE_EOF

    # Substitute placeholders via Python (env vars for safety)
    PLANT_DOORMAN_PATH="$target_dir/doorman/index.html" \
    PLANT_DISPLAY_NAME="$MIRROR_DISPLAY_NAME" \
    PLANT_LOCATION="${MIRROR_LOCATION:-}" \
    PLANT_KIND="${MIRROR_KIND:-mirror}" \
    python3 - <<'PYEOF'
import os, pathlib
path = pathlib.Path(os.environ["PLANT_DOORMAN_PATH"])
text = path.read_text()
subs = [
    ("__DISPLAY_NAME__", os.environ["PLANT_DISPLAY_NAME"]),
    ("__LOCATION__",     os.environ.get("PLANT_LOCATION", "")),
    ("__KIND__",         os.environ.get("PLANT_KIND", "mirror")),
]
for k, v in subs:
    text = text.replace(k, v)
path.write_text(text)
PYEOF
}

# ── banner ────────────────────────────────────────────────────────────
print_banner() {
    cat << EOF

  ${CYAN}🚪 RAPP front door planter${NC}

  Plant your AI's front door on the public internet.
  Kernel-compliant by structural fact. Yours forever.

EOF
}

# ── main ──────────────────────────────────────────────────────────────
main() {
    print_banner
    check_prereqs
    prompt_inputs

    local rappid now gh_user workspace
    rappid="$(mint_rappid)"
    now="$(now_iso)"

    if [[ "${PLANT_DRY_RUN:-0}" == "1" ]]; then
        gh_user="${PLANT_GH_USER:-test-user}"
    else
        gh_user="$(gh api user -q .login)"
    fi

    if [[ "${PLANT_DRY_RUN:-0}" == "1" ]]; then
        workspace="${PLANT_DRY_RUN_DIR:-$(mktemp -d)}"
        mkdir -p "$workspace"
        info "Dry run — building in $workspace"
    else
        workspace=$(mktemp -d)
    fi

    fetch_kernel       "$workspace"
    fetch_seed_agents  "$workspace"
    write_install_sh   "$workspace"
    write_rappid_json  "$workspace" "$gh_user" "$rappid" "$now"
    write_soul_md      "$workspace"
    write_gitignore    "$workspace"
    write_nojekyll     "$workspace"
    write_memory_json  "$workspace" "$gh_user" "$now"
    write_readme       "$workspace" "$gh_user" "$rappid"
    write_index_html   "$workspace" "$gh_user" "$rappid"
    write_doorman_html "$workspace" "$gh_user" "$rappid"

    if [[ "${PLANT_DRY_RUN:-0}" == "1" ]]; then
        echo ""
        ok "Dry run complete. Files written:"
        ( cd "$workspace" && find . -type f | sort | sed 's|^\./|  |' )
        echo ""
        echo "Path: $workspace"
        return 0
    fi

    info "Initializing git repo..."
    cd "$workspace"
    git init -q -b main
    git add .
    git -c user.email="${gh_user}@users.noreply.github.com" \
        -c user.name="$gh_user" \
        commit -q -m "plant: ${MIRROR_REPO_NAME} (rappid ${rappid:0:8}…)"
    ok "Initial commit"

    info "Creating GitHub repo: $gh_user/$MIRROR_REPO_NAME"
    gh repo create "$MIRROR_REPO_NAME" --public --source=. --push \
        --description "$MIRROR_DISPLAY_NAME — RAPP front door" \
        || err "gh repo create failed (does the repo already exist?)"
    ok "Repo created and pushed"

    info "Enabling GitHub Pages..."
    if gh api -X POST "/repos/$gh_user/$MIRROR_REPO_NAME/pages" \
        -f "source[branch]=main" -f "source[path]=/" >/dev/null 2>&1; then
        ok "Pages enabled"
    else
        warn "Pages may already be enabled, or hit a transient error — check repo Settings → Pages"
    fi

    cat << EOF

═══════════════════════════════════════════════════════════════════
  ${GREEN}✓ Front door planted!${NC}
═══════════════════════════════════════════════════════════════════

  Repo:    https://github.com/$gh_user/$MIRROR_REPO_NAME
  URL:     https://$gh_user.github.io/$MIRROR_REPO_NAME
  Rappid:  $rappid

  Pages takes 1–3 minutes to deploy. Once live:

  ${CYAN}Visit your front door:${NC}
    https://$gh_user.github.io/$MIRROR_REPO_NAME

  ${CYAN}Anyone can install your kernel locally with:${NC}
    curl -fsSL https://$gh_user.github.io/$MIRROR_REPO_NAME/installer/install.sh | bash

  ${CYAN}Generate a QR for sharing:${NC}
    https://kody-w.github.io/RAPP/installer/plant_qr.html?to=https://$gh_user.github.io/$MIRROR_REPO_NAME

  ${CYAN}Verify your kernel still matches grail (drift check):${NC}
    for f in rapp_brainstem/brainstem.py rapp_brainstem/VERSION rapp_brainstem/agents/basic_agent.py; do
      diff <(curl -fsSL "https://raw.githubusercontent.com/kody-w/rapp-installer/main/\$f") \\
           <(curl -fsSL "https://raw.githubusercontent.com/$gh_user/$MIRROR_REPO_NAME/main/\$f") \\
        || echo "DRIFT: \$f"
    done
    # Three empty diffs = compliant. Anything else = drift.

EOF
}

main "$@"
