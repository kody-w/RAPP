#!/usr/bin/env bash
# Scenario 8 — Live Translation Mesh.
#
# Three contributors, each with a library in a different language. A
# query in any language federates across all of them; bibliography
# preserves source-language for each citation. Tests the "library_kinds"
# tagging extending to language locales, not just storage types.

source "$(dirname "$0")/_lib.sh"
scenario_parse_args "$@"

heading "Scenario 8 — Live Translation Mesh"
note "Pattern: braintrust with library_kinds extended to language tags"
note "Showcases: federation across language barriers without central translation service"

TMP=$(mktemp -d -t rapp-scenario-08-XXXXXX)
trap 'rm -rf "$TMP"' EXIT
WORKSEED="$TMP/translate"
cp -R "$SEEDS_DIR/braintrust-template" "$WORKSEED"

# Three libraries, three languages — all describing the same concept
mkdir -p "$TMP/lib-en/notes" "$TMP/lib-es/notes" "$TMP/lib-ja/notes"
cat > "$TMP/lib-en/notes/concept.md" <<'EOF'
# decentralized network
A network where authority is distributed across many nodes rather than
concentrated in one central server. The decentralized structure makes
the network resilient to single points of failure.
EOF
cat > "$TMP/lib-es/notes/concepto.md" <<'EOF'
# red descentralizada
Una red donde la autoridad esta distribuida entre muchos nodos en lugar
de concentrarse en un servidor central. La estructura descentralizada
hace que la red sea resistente a puntos unicos de fallo.
EOF
cat > "$TMP/lib-ja/notes/konseputo.md" <<'EOF'
# decentralized bunsangata network
Bunsangata network ha kenryoku ga ooku no nodo ni bunsan sare, chuou
server ni shuuchuu sarete inai. Bunsangata kouzou ha tan'ichi shougai
ten ni taishi kyoujin de aru.
EOF

# 1. Open request — library_kinds_requested signals language preferences
REQ_KW='{"topic":"decentralized network resilience","requester_login":"polyglot","deadline_hours":1,"min_quorum":2,"library_kinds_requested":["language:en","language:es","language:ja"]}'
REQ_OUT=$(run_agent_direct "$WORKSEED" "agents/braintrust_request_agent.py" "BraintrustRequestAgent" "$REQ_KW")
REQUEST_ID=$(echo "$REQ_OUT" | python3 -c "import json,sys; print(json.load(sys.stdin)['request']['request_id'])")
step_pass "multi-language request opened"

# 2. Each language contributor queries their library
declare -a CONTRIBS=()
for lang in en es ja; do
  case $lang in
    en) terms="decentralized network resilience" ;;
    es) terms="descentralizada red resistente" ;;
    ja) terms="decentralized bunsangata network" ;;
  esac
  KW=$(python3 -c "import json; print(json.dumps({'request_id':'$REQUEST_ID','topic':'$terms','contributor_login':'$lang-librarian','contributor_rappid':'fake-$lang'}))")
  C=$(LIBRARY_PATHS="$TMP/lib-$lang/notes" run_agent_direct "$WORKSEED" "agents/braintrust_contribute_agent.py" "BraintrustContributeAgent" "$KW")
  INNER=$(echo "$C" | python3 -c "import json,sys; print(json.dumps(json.load(sys.stdin)['contribution']))")
  CONTRIBS+=("$INNER")
  HAS=$(echo "$INNER" | python3 -c "import json,sys; print(len(json.loads(sys.stdin.read())['findings']))")
  if [ "$HAS" -ge 1 ]; then
    step_pass "@$lang-librarian found $HAS finding(s) in $lang library"
  else
    step_fail "@$lang-librarian had no findings"
  fi
done

# 3. Synthesize — each citation preserves its source language via the source.ref
CONTRIBS_JSON=$(printf '[%s]' "$(IFS=,; echo "${CONTRIBS[*]}")")
SYN_KW=$(python3 -c "import json,sys; print(json.dumps({'request_id':'$REQUEST_ID','topic':'decentralized network resilience','contributions':json.loads(sys.argv[1]),'synthesizer_login':'polyglot','min_quorum':2}))" "$CONTRIBS_JSON")
SYN_OUT=$(run_agent_direct "$WORKSEED" "agents/braintrust_synthesize_agent.py" "BraintrustSynthesizeAgent" "$SYN_KW")
if echo "$SYN_OUT" | grep -q '"status": "ok"'; then
  step_pass "translation-mesh synthesis ok with 3 contributors"
else
  step_fail "translation-mesh synthesis failed"
fi

SLUG=$(echo "$SYN_OUT" | python3 -c "import json,sys; r=json.load(sys.stdin); print(r['report']['report_path'].replace('reports/','').replace('/report.md',''))")
if grep -q "concepto.md\|konseputo.md\|concept.md" "$WORKSEED/reports/$SLUG/report.md"; then
  step_pass "bibliography preserves source-language file references"
else
  step_fail "bibliography did not preserve language source refs"
fi

heading "Why this matters"
cat <<'EOF'
  Translation mesh: federation across language barriers without a central
  translation service. Each contributor's library_query operates in its
  native language; provenance preserves which language a citation came
  from. The synthesizer (or downstream agents) can then translate as needed,
  but the source-of-truth never gets flattened into one language.
EOF

scenario_summary
