#!/usr/bin/env bash
# Verify the four new marketing/docs pages parse cleanly, contain the
# expected messaging anchors, and cross-link to each other correctly.
# No brainstem needed; pure file checks.
set -euo pipefail
cd "$(dirname "$0")/../.."

PAGES=(one-pager.html release-notes.html roadmap.html faq.html)

for f in "${PAGES[@]}"; do
    [ -f "$f" ] || { echo "FAIL: $f does not exist"; exit 1; }
    BYTES=$(wc -c < "$f")
    LINES=$(wc -l < "$f")
    if [ "$BYTES" -lt 4000 ]; then
        echo "FAIL: $f suspiciously small ($BYTES bytes)"
        exit 1
    fi
    echo "PASS: $f exists ($BYTES bytes, $LINES lines)"
done

# Parse sanity for each
for f in "${PAGES[@]}"; do
    python3 - <<EOF || { echo "FAIL: $f parse error"; exit 1; }
from html.parser import HTMLParser
import sys
class P(HTMLParser):
    def __init__(self):
        super().__init__(); self.err = None
    def error(self, msg): self.err = msg
p = P()
with open("$f") as fh: p.feed(fh.read())
if p.err:
    print(p.err); sys.exit(1)
EOF
    echo "PASS: $f parses"
done

# ── Content anchors — the specific messaging that MUST be in each ──

check() {
    local file="$1"; local label="$2"; local pattern="$3"
    if grep -qE "$pattern" "$file"; then
        echo "PASS: [$file] $label"
    else
        echo "FAIL: [$file] missing — $label"
        echo "  expected pattern: $pattern"
        exit 1
    fi
}

# one-pager.html — the boss's ask
echo "▶ one-pager content anchors..."
check one-pager.html "headline uses 'goal' + 'swarm'"             'Give it a.*goal.*swarm'
check one-pager.html "contrasts GPTs/Skills/Plugins"              'GPTs.*Skills.*Plugins|GPTs / Skills / Plugins'
check one-pager.html "contrasts Copilot Studio"                   'Copilot Studio'
check one-pager.html "claims portable single file"                'Single Python file|single Python file|Single .*file|single .*file'
check one-pager.html "claims deterministic"                       'eterministic'
check one-pager.html "claims local-first / offline"               'Local-first|offline|Offline'
check one-pager.html "pull-quote distills the pitch"              'swarm around your goal'
check one-pager.html "cross-links to FAQ"                         'faq\.html'
check one-pager.html "cross-links to roadmap"                     'roadmap\.html'

# release-notes.html
echo "▶ release-notes content anchors..."
check release-notes.html "v0.12.1 listed"                         'v0.12.1|brainstem-v0\.12\.1'
check release-notes.html "v0.12.0 listed"                         'v0.12.0|brainstem-v0\.12\.0'
check release-notes.html "Three Tiers One Model reference"        'Three Tiers|One Model|tier-2'
check release-notes.html "install pin example"                    'BRAINSTEM_VERSION='
check release-notes.html "cross-links to roadmap"                 'roadmap\.html'
check release-notes.html "cross-links to FAQ"                     'faq\.html'

# roadmap.html
echo "▶ roadmap content anchors..."
check roadmap.html "three horizons columns"                       'Now|Next|Later'
check roadmap.html "Tier 2 cloud item"                            'Tier 2.*[cC]loud|provision-twin-lite'
check roadmap.html "swarm factory distribution item"              'swarm factory|Swarm factory|workshop'
check roadmap.html "on-device / offline item"                     'on-device|offline|IoT'
check roadmap.html "one-pager linked"                             'one-pager\.html'
check roadmap.html "Article references"                           'Article I-A|Article II|Article V'

# faq.html
echo "▶ faq content anchors..."
check faq.html "Q about GPT/Claude/Copilot"                       'GPT.*Claude.*Copilot|using GPT'
check faq.html "Q about real scenario"                            'real scenario|forestry'
check faq.html "Q about offline"                                  '[oO]ffline'
check faq.html "Q about Copilot Studio"                           'Copilot Studio directly|Copilot Studio'
check faq.html "Q about portable meaning"                         'portable.*actually|portable.*mean'
check faq.html "Q about install one-liner"                        'curl -fsSL'
check faq.html "one-sentence version at end"                      'one-sentence|one sentence|one.*line version'
check faq.html "cross-links to one-pager"                         'one-pager\.html'

echo "✅ HTML pages smoke test passed"
