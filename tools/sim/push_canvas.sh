#!/usr/bin/env bash
# push_canvas.sh — publish the local neighborhood's canvas to the public repo.
#
# Idempotent: no-op if no local changes since the last push. Additive:
# only adds new submissions / votes / members entries — never removes.
# After this runs, vbrainstem (and any other public observer) sees Bill +
# Alice's autonomous tick contributions.
#
# Usage:
#   ./push_canvas.sh [<neighborhood-dir>]
#
# Default neighborhood: ~/RAPP-sim/local-art-collective
# Exit codes:
#   0 — pushed cleanly OR no changes (idempotent success)
#   1 — git/gh failure (auth, network, etc.)
#   2 — neighborhood dir invalid (not a git repo)

# Historical source provenance (fullest known implementation).
# commit: 8d089dc459f156fb214316db3383e2d95355261d
# blob: 31f09a46735aa0d058bd55fab22dc6a55d921698
# sha256: 734670eaa877b78e3f913d2abc3235baab17ddb358d94181abc89c8ca367e88e
historical_push_canvas() (
set -uo pipefail
NB=${1:-$HOME/RAPP-sim/local-art-collective}

if [ ! -d "$NB" ]; then
  echo "ERROR: neighborhood dir not found: $NB" >&2
  exit 2
fi
if [ ! -d "$NB/.git" ]; then
  echo "ERROR: $NB is not a git repo (run the publish step first)" >&2
  exit 2
fi

cd "$NB"

# Stage the canonical canvas files (additive — git add never removes from index).
# Add each path individually; if the path doesn't exist, skip it.
# (`git add a/ b/ missing.json` aborts the WHOLE add when one pathspec is bad —
# we sidestep that by adding paths one at a time.)
for path in submissions/ votes/ members.json card.json holo.md holo.svg holo-qr.svg \
            specs/ neighborhood.json soul.md rappid.json; do
  [ -e "$path" ] && git add "$path" 2>/dev/null || true
done

if git diff --cached --quiet; then
  echo "[push] no changes since last push (canvas already up-to-date)"
  exit 0
fi

UTC=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
NEW_SUBS=$(git diff --cached --name-only -- submissions/ 2>/dev/null | grep -c "meta\.json$" || true)
NEW_VOTES=$(git diff --cached --name-only -- votes/ 2>/dev/null | grep -c "\.json$" || true)
OTHER=$(git diff --cached --name-only 2>/dev/null | grep -v "^submissions/.*meta\.json$\|^votes/" | wc -l | tr -d ' ')

if ! git -c commit.gpgsign=false commit -q -m "canvas tick @ $UTC: +${NEW_SUBS}sub +${NEW_VOTES}vote +${OTHER}other (autonomous local→public push)"; then
  echo "[push] commit failed" >&2
  exit 1
fi

if ! git push -q origin main 2>&1; then
  echo "[push] git push failed (auth or network — try \`cd $NB && git pull --rebase && git push\`)" >&2
  exit 1
fi

echo "[push] OK @ $UTC: +${NEW_SUBS}sub +${NEW_VOTES}vote +${OTHER}other → $(git remote get-url origin)"
)

print_plan() {
  printf '%s\n' \
    '{"schema":"rapp-canvas-publication-plan/1.0","mode":"plan","staged_paths":["submissions/","votes/","members.json","card.json","holo.md","holo.svg","holo-qr.svg","specs/","neighborhood.json","soul.md","rappid.json"],"commit":false,"push":false,"historical_source_commit":"8d089dc459f156fb214316db3383e2d95355261d","effects":[]}' \
    'No directory validation, git command, staging, commit, credential access, network request, or publication occurs in plan mode.'
}

refuse_apply() {
  printf '%s\n' \
    '{"schema":"rapp-effect-refusal/1.0","operation":"canvas-publication","code":"authenticated-registry-unavailable","effects_started":false,"requirements":["reviewed-dependency-injection","exact-target-receipt","authenticated-fresh-section-13-evidence"]}' \
    'Current authority cannot authenticate the publication target; refusal occurs before git add, commit, remote inspection, or push.' >&2
  return 78
}

case "${1:-plan}" in
  plan|--plan|inspect|--inspect|check|--check)
    print_plan
    ;;
  apply|--apply|run|--run|publish|--publish)
    refuse_apply
    ;;
  help|-h|--help)
    printf '%s\n' \
      'Usage: push_canvas.sh [--plan|--inspect|--check|--apply]' \
      'Default: deterministic publication plan.' \
      '--apply requires reviewed dependency injection, an exact target receipt,' \
      'and authenticated fresh RAPP/1 section-13 evidence; unavailable here.'
    ;;
  *)
    printf 'Unknown mode: %s\n' "$1" >&2
    exit 2
    ;;
esac
