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
<meta name="description" content="A RAPP front door — __DISPLAY_NAME__ on the public internet.">

<script src="https://unpkg.com/peerjs@1.5.4/dist/peerjs.min.js"></script>

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
</style>
</head>
<body>

<header>
  <h1>__DISPLAY_NAME__</h1>
  <div class="sub">A RAPP front door · planted by <a href="https://github.com/__GH_USER__" style="color:#58a6ff;text-decoration:none;">@__GH_USER__</a></div>
</header>

<main>
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
      <span class="chip">kind: <code>mirror</code></span>
      __LINEAGE_HTML__
    </div>
  </section>

  <div class="actions">
    <a class="action" href="./doorman/" style="text-decoration:none;text-align:center;">💬 Step in &amp; chat</a>
    <button class="action secondary" id="btn-tether">Tether (cross-device chat)</button>
    <button class="action secondary" id="btn-qr">Show QR</button>
    <button class="action secondary" id="btn-install">Install Brainstem</button>
  </div>

  <section class="pane" id="pane-tether" hidden>
    <h2>Tether — cross-device chat</h2>
    <p>Two devices, one channel. Open this page on another device, copy that one's ID, paste here, connect. WebRTC end-to-end encrypted (DTLS). Signaling via PeerJS public broker; once connected, the broker drops out.</p>

    <div>
      <span class="identity-key">My peer ID:</span>
      <div class="my-id" id="my-id"><span class="status-dot" id="peer-status"></span><span id="my-id-text">(connecting to broker...)</span></div>
      <button class="small" id="btn-copy-id">Copy ID</button>
      <button class="small" id="btn-show-tether-qr">Show QR for this ID</button>
    </div>

    <div class="input-row" style="margin-top:16px;">
      <input type="text" id="peer-id-input" placeholder="Paste peer's ID here">
      <button class="small primary" id="btn-connect">Connect</button>
    </div>

    <div class="chat-log" id="chat-log">
      <div class="msg system">Tether will appear here once connected.</div>
    </div>

    <div class="input-row">
      <input type="text" id="chat-input" placeholder="Type a message and hit Enter" disabled>
      <button class="small primary" id="btn-send" disabled>Send</button>
    </div>

    <div id="tether-qr-pane" hidden style="margin-top:16px;">
      <p>Scan to land on this front door + this peer ID:</p>
      <img class="qr-img" id="tether-qr-img" alt="Peer ID QR">
      <div class="qr-url" id="tether-qr-url"></div>
    </div>
  </section>

  <section class="pane" id="pane-qr" hidden>
    <h2>QR for this front door</h2>
    <p>Scan to land at <code>__URL__</code>.</p>
    <img class="qr-img" id="qr-img" alt="Front door QR">
    <div class="qr-url" id="qr-url"></div>
  </section>

  <section class="pane" id="pane-install" hidden>
    <h2>Install this front door's brainstem locally</h2>
    <p>Runs the canonical kernel under <code>~/.brainstem/</code> on your machine. Per the Mirror Spec, the installer re-fetches the canonical install logic from the grail, so it cannot drift.</p>
    <pre class="cmd" id="install-cmd">curl -fsSL __URL__/installer/install.sh | bash</pre>
    <button class="small primary" id="btn-copy-install">Copy command</button>
  </section>
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

function showTetherQR() {
  const myId = document.getElementById("my-id-text").textContent;
  if (!myId || myId.includes("...") || myId.includes("timeout") || myId.includes("failed")) {
    appendMsg("No peer ID yet — wait for the broker handshake to finish.", "system");
    return;
  }
  const tetherPane = document.getElementById("tether-qr-pane");
  tetherPane.hidden = false;
  const url = location.origin + location.pathname + "?peer=" + encodeURIComponent(myId);
  document.getElementById("tether-qr-img").src =
    "https://api.qrserver.com/v1/create-qr-code/?size=300x300&margin=0&data=" +
    encodeURIComponent(url);
  document.getElementById("tether-qr-url").textContent = url;
}

function showInstall() { showPane("pane-install"); }

async function copy(text) {
  try { await navigator.clipboard.writeText(text); } catch (_) { /* silent */ }
}

// Wire up buttons
document.getElementById("btn-tether").onclick = openTether;
document.getElementById("btn-qr").onclick = showFrontDoorQR;
document.getElementById("btn-install").onclick = showInstall;
document.getElementById("btn-connect").onclick = connectToPeer;
document.getElementById("btn-show-tether-qr").onclick = showTetherQR;
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
    python3 - <<'PYEOF'
import os, pathlib
path = pathlib.Path(os.environ["PLANT_INDEX_PATH"])
text = path.read_text()
subs = [
    ("__DISPLAY_NAME__", os.environ["PLANT_DISPLAY_NAME"]),
    ("__REPO_NAME__",    os.environ["PLANT_REPO_NAME"]),
    ("__GH_USER__",      os.environ["PLANT_GH_USER"]),
    ("__RAPPID__",       os.environ["PLANT_RAPPID"]),
    ("__URL__",          os.environ["PLANT_URL"]),
    ("__LINEAGE_HTML__", os.environ["PLANT_LINEAGE_HTML"]),
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
  footer {
    padding: 8px 20px;
    border-top: 1px solid #21262d;
    font-size: 11px; color: #6e7681; text-align: center;
  }
  footer a { color: #58a6ff; text-decoration: none; }
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
    <h2>To start chatting</h2>
    <p>This page is a vbrainstem — runs in your browser, calls GitHub Models with your own token. Same auth pattern as the egg hub's summon page; if you've signed in there, you can paste the same token.</p>
    <ol>
      <li>Visit <a href="https://github.com/settings/tokens?type=beta" target="_blank" rel="noopener">github.com/settings/tokens</a> → <strong>Generate new token (fine-grained)</strong>.</li>
      <li>Default permissions are fine — GitHub Models is included for any authenticated token.</li>
      <li>Paste it below. Stored locally in your browser only (never sent anywhere except GitHub Models + the private companion repo, if any).</li>
    </ol>
    <div class="row">
      <input type="password" id="pat-input" placeholder="github_pat_…  or  ghp_…" autocomplete="off">
      <button id="btn-save-pat">Save</button>
    </div>
  </section>

  <div class="chat-log" id="chat-log" hidden></div>

  <div class="input-bar" id="input-bar" hidden>
    <textarea id="chat-input" placeholder="Talk to the doorman…" rows="1"></textarea>
    <button id="btn-send">Send</button>
  </div>

  <div class="actions" id="chat-actions" hidden>
    <button id="btn-add-memory">+ Save a memory</button>
    <button id="btn-clear">Clear chat</button>
    <button id="btn-logout">Sign out</button>
  </div>

  <section class="auth-pane" id="memory-pane" hidden style="margin-top:12px;">
    <h2>Save a memory to this front door</h2>
    <p>Adds a fact to <code>.brainstem_data/memory.json</code> in this seed's repo via GitHub API. The fact is then context for every future doorman conversation. Requires write access to the repo.</p>
    <textarea id="memory-input" placeholder="One thing future visitors should know about this place…" rows="3"></textarea>
    <div class="row">
      <button id="btn-save-memory">Commit memory</button>
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
const GH_MODELS_URL   = "https://models.github.ai/inference/chat/completions";
const MODEL           = "openai/gpt-4o-mini";
const STORAGE_KEY     = "rapp_settings";  // mirrors vbrainstem (per-origin)

let identity = null;
let privateContext = "";
let privateFactsCount = 0;
let memory = { schema: "rapp-memory/1.0", facts: [], preserved_by: "", preserved_at: "" };
let memorySha = null;  // GitHub blob sha for the current memory.json (needed for PUT)
let history = [];

// ── token storage (vbrainstem-shape) ────────────────────────────────
function getToken() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const s = JSON.parse(raw);
    return s.ghToken || s.copilotToken || null;
  } catch { return null; }
}
function setToken(t) {
  let s = {};
  try { s = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}"); } catch {}
  s.ghToken = t;
  s.provider = "github";
  localStorage.setItem(STORAGE_KEY, JSON.stringify(s));
}
function clearToken() {
  let s = {};
  try { s = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}"); } catch {}
  delete s.ghToken;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(s));
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
  // The doorman IS the planted AI — not a separate persona. Speak as
  // <name> directly. Frame "front door" as where this AI lives publicly,
  // not a separate hosted role. Kind-aware first-person voice.
  const lines = [];
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
  // Inject persistent memory (facts saved by past visitors with write access)
  const memBlock = memoryFactsForPrompt();
  if (memBlock) lines.push(memBlock);
  if (privateContext) {
    lines.push("");
    lines.push("=== Private brain context (visible to authenticated collaborators only) ===");
    lines.push(privateContext);
    lines.push("=== End private context ===");
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
      // Also fetch via GH API once we have a token, so we know the blob sha.
    }
  } catch (_) { /* missing file is fine, doorman still works */ }
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

// ── private companion: best-effort fetch ───────────────────────────
//
// Silent escalation pattern. Same raw.githubusercontent.com URL shape
// for public and private repos — private content resolves ONLY when the
// visitor's token has read access. No access? The fetches return 404 and
// we just skip them. No error surfaced; doorman keeps speaking from
// public memory only.
//
// Two layers we look for in the private companion:
//   1. Persona / vault content — README, soul.md, vault entrypoint —
//      added as raw text to the system prompt for richer voice.
//   2. Private memory — memory.json or .brainstem_data/memory.json
//      with a `.facts` array — parsed and surfaced as additional
//      "Known facts" alongside the public seed's memory. Exactly the
//      same data shape; just not visible to anonymous visitors.
async function loadPrivateContext(token) {
  privateContext = "";
  privateFactsCount = 0;
  if (!identity || !identity.private_companion) return;
  const pc = identity.private_companion;
  const tmpl = pc.raw_url_template;
  if (!tmpl) return;

  const PROSE_CANDIDATES = ["README.md", "soul.md", "vault/00 Index/Home.md"];
  const MEMORY_CANDIDATES = ["memory.json", ".brainstem_data/memory.json"];

  // Prose: append text directly, capped at 4KB total
  for (const path of PROSE_CANDIDATES) {
    if (privateContext.length >= 4000) break;
    try {
      const url = tmpl.replace("{path}", path);
      const r = await fetch(url, {
        headers: { "Authorization": "Bearer " + token, "Accept": "text/plain" }
      });
      if (r.ok) {
        const text = await r.text();
        privateContext = (privateContext + "\n\n" + text).trim().slice(0, 4000);
      }
    } catch (_) { /* silent — anonymous fall-through */ }
  }

  // Memory: parse .facts arrays from private memory.json files and merge
  // them into the running memory.facts list so the prompt assembly treats
  // them uniformly. They're tagged with a [private] prefix so the LLM
  // understands the access boundary.
  for (const path of MEMORY_CANDIDATES) {
    try {
      const url = tmpl.replace("{path}", path);
      const r = await fetch(url, {
        headers: { "Authorization": "Bearer " + token, "Accept": "application/json" }
      });
      if (r.ok) {
        const j = await r.json();
        if (Array.isArray(j.facts)) {
          for (const f of j.facts) {
            if (typeof f === "string" && f.trim()) {
              memory.facts.push("[private] " + f.trim());
              privateFactsCount++;
            }
          }
        }
      }
    } catch (_) { /* silent */ }
  }

  const ind = document.getElementById("private-indicator");
  if (privateContext || privateFactsCount > 0) {
    const bits = [];
    if (privateContext)        bits.push(`prose ${privateContext.length}c`);
    if (privateFactsCount > 0) bits.push(`+${privateFactsCount} private mem`);
    ind.innerHTML = `<span class="private-badge">✓ private brain loaded — ${bits.join(", ")}</span>`;
  }
}

// ── chat ───────────────────────────────────────────────────────────
function renderMsg(role, text) {
  const log = document.getElementById("chat-log");
  const div = document.createElement("div");
  div.className = "msg " + role;
  div.textContent = text;
  log.appendChild(div);
  log.scrollTop = log.scrollHeight;
  return div;
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

  const pending = renderMsg("system", "…");
  const sendBtn = document.getElementById("btn-send");
  sendBtn.disabled = true;

  try {
    const r = await fetch(GH_MODELS_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + token,
      },
      body: JSON.stringify({
        model: MODEL,
        messages: [
          { role: "system", content: buildSystemPrompt() },
          ...history,
        ],
        max_tokens: 600,
      }),
    });
    if (!r.ok) {
      const err = await r.text();
      throw new Error("HTTP " + r.status + ": " + err.slice(0, 250));
    }
    const data = await r.json();
    const reply = data.choices?.[0]?.message?.content || "(empty response)";
    pending.remove();
    renderMsg("assistant", reply);
    history.push({ role: "assistant", content: reply });
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
  // Memory: load before private context so the prompt assembly already has it
  await loadMemory();
  // Best effort: refresh from GH API (gives us the sha for write + freshest content)
  refreshMemorySha(token);  // fire-and-forget — doorman can chat without it
  await loadPrivateContext(token);
  const place = identity.display_name || identity.name || "this place";
  const memCount = (memory.facts || []).length;
  const memNote = memCount ? ` I'm carrying ${memCount} memor${memCount === 1 ? "y" : "ies"} from past visits.` : "";
  renderMsg("system", `Hi — I'm ${place}, here at my front door.${memNote} Ask me anything.`);
}

// ── init ───────────────────────────────────────────────────────────
(async function init() {
  await loadIdentity();
  if (getToken()) {
    enterChat();
  }
})();

// ── wire ───────────────────────────────────────────────────────────
document.getElementById("btn-save-pat").addEventListener("click", async () => {
  const tok = document.getElementById("pat-input").value.trim();
  if (!tok) return;
  setToken(tok);
  document.getElementById("pat-input").value = "";
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
document.getElementById("btn-save-memory").addEventListener("click", async () => {
  const input = document.getElementById("memory-input");
  const status = document.getElementById("memory-status");
  const fact = input.value.trim();
  if (!fact) { status.textContent = "Empty memory."; return; }
  status.textContent = "Committing to GitHub…";
  document.getElementById("btn-save-memory").disabled = true;
  const result = await commitMemory(fact);
  document.getElementById("btn-save-memory").disabled = false;
  if (result.ok) {
    status.textContent = "✓ Saved. " + (memory.facts.length) + " facts now live in this front door's memory.";
    input.value = "";
    renderMsg("system", "Saved memory: \"" + fact + "\"");
    setTimeout(() => {
      document.getElementById("memory-pane").hidden = true;
      status.textContent = "";
    }, 2000);
  } else {
    status.textContent = "✗ Failed: " + result.error + ". You probably don't have write access to this seed's repo (that's normal — only the operator/maintainers can write to public memory).";
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
