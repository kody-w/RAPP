#!/usr/bin/env bash
# tests/osi/run.sh — master runner for the RAPP OSI conformance suite.
#
# Runs every L<n> + X<n> script in order; collects pass/fail; prints a
# matrix at the end. Exits non-zero if any layer or cross-cutting concern
# fails.
#
# Usage:
#   bash tests/osi/run.sh              # full suite, network on
#   bash tests/osi/run.sh --offline    # skip network checks
#   bash tests/osi/run.sh --layer=L1   # single layer

set -uo pipefail
RUN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$RUN_DIR/../.." && pwd)"

OFFLINE=0
ONLY=""
WITH_BROWSER=0
for arg in "$@"; do
  case "$arg" in
    --offline) OFFLINE=1 ;;
    --layer=*) ONLY="${arg#*=}" ;;
    --with-browser) WITH_BROWSER=1 ;;
    --help|-h)
      echo "Usage: $0 [--offline] [--layer=L1|L2|...|X1|X2|...] [--with-browser]"
      echo "  --with-browser  Also run tests/osi/L4a-tether-browser.sh (Playwright; ~150MB on first run)."
      exit 0
      ;;
  esac
done

if [ -t 1 ]; then
  GREEN=$'\033[32m'; RED=$'\033[31m'; YELLOW=$'\033[33m'; BLUE=$'\033[34m'; BOLD=$'\033[1m'; RESET=$'\033[0m'
else
  GREEN=""; RED=""; YELLOW=""; BLUE=""; BOLD=""; RESET=""
fi

LAYERS=(
  "L1-substrate"
  "L2-identity"
  "L3-discovery"
  "L4-channels"
  "L5-trust-scope"
  "L6-envelope"
  "L7-application"
)
CROSS=(
  "X1-tier-portability"
  "X2-survival"
  "X3-egg-lifecycle"
  "X4-federation"
)

ALL=("${LAYERS[@]}" "${CROSS[@]}")
if [ "$WITH_BROWSER" -eq 1 ] && [ -z "$ONLY" ]; then
  ALL+=("L4a-tether-browser")
  ALL+=("L6a-frame-chain-browser")
fi

if [ -n "$ONLY" ]; then
  ALL=()
  for s in "${LAYERS[@]}" "${CROSS[@]}"; do
    case "$s" in "${ONLY}-"*) ALL+=("$s") ;; esac
  done
  if [ "${#ALL[@]}" -eq 0 ]; then
    echo "${RED}no test matches --layer=$ONLY${RESET}"
    exit 1
  fi
fi

EXTRA_FLAGS=()
[ "$OFFLINE" -eq 1 ] && EXTRA_FLAGS+=("--offline")

declare -a STATUS
declare -a NAMES
TOTAL_PASS=0
TOTAL_FAIL=0
START=$(date +%s)

printf "\n${BOLD}${BLUE}━━━ RAPP OSI Conformance Suite ━━━${RESET}\n"
[ "$OFFLINE" -eq 1 ] && printf "${YELLOW}offline mode — network checks skipped${RESET}\n"

for s in "${ALL[@]}"; do
  TEST_FILE="$RUN_DIR/$s.sh"
  if [ ! -f "$TEST_FILE" ]; then
    printf "${RED}MISSING: $TEST_FILE${RESET}\n"
    NAMES+=("$s")
    STATUS+=("✗")
    TOTAL_FAIL=$((TOTAL_FAIL+1))
    continue
  fi
  printf "\n${BOLD}▶ Running $s${RESET}\n"
  if bash "$TEST_FILE" ${EXTRA_FLAGS[@]+"${EXTRA_FLAGS[@]}"}; then
    NAMES+=("$s")
    STATUS+=("✓")
    TOTAL_PASS=$((TOTAL_PASS+1))
  else
    NAMES+=("$s")
    STATUS+=("✗")
    TOTAL_FAIL=$((TOTAL_FAIL+1))
  fi
done

ELAPSED=$(($(date +%s) - START))

# Matrix output
printf "\n\n${BOLD}━━━ Conformance Matrix ━━━${RESET}\n\n"
printf "  ${BOLD}%-22s %s${RESET}\n" "Layer / CC" "Status"
printf "  ${BLUE}%s${RESET}\n" "──────────────────────  ──────"
for i in "${!NAMES[@]}"; do
  name="${NAMES[$i]}"
  status="${STATUS[$i]}"
  if [ "$status" = "✓" ]; then
    printf "  %-22s ${GREEN}%s pass${RESET}\n" "$name" "$status"
  else
    printf "  %-22s ${RED}%s FAIL${RESET}\n" "$name" "$status"
  fi
done
printf "\n  ${BOLD}%d passing, %d failing${RESET} (of ${#ALL[@]} suites, ${ELAPSED}s)\n\n" "$TOTAL_PASS" "$TOTAL_FAIL"

if [ "$TOTAL_FAIL" -gt 0 ]; then
  exit 1
fi
exit 0
