#!/usr/bin/env bash
# One logged, headless Claude Code run against SolidCraft 0.16.2 (clean: no user CLAUDE.md, no user settings, no memory).
#   bash claude-run/run.sh plain|parametric RUN_ID
# plain: the plate and a resize, in plain words (no mention of parameters).
# parametric: the same, asking for a width parameter the holes follow, then resizing by that parameter only.
# Claude Code --stdio--> docker run -i ... [mcp_log_proxy.py --stdio--> solidcraft-cli mcp]; only the solidcraft tools.
set -euo pipefail
ARM=$1; RUN=$2
cd "$(dirname "$0")/.."
LAB="$(pwd -W 2>/dev/null || pwd)"
OUT=out/runs/$ARM-$RUN
mkdir -p "$OUT"; rm -f "$OUT"/*
MODEL="${MODEL:-claude-sonnet-5-5}"
BUDGET="${BUDGET:-1.50}"

cat > "$OUT/mcp-config.json" <<JSON
{"mcpServers": {"solidcraft": {"command": "docker", "args": ["run", "-i", "--rm", "-v", "$LAB/proxy:/proxy:ro", "-v", "$LAB/$OUT:/lab/out", "solidcraft-resize-lab:0.16.2", "python3", "/proxy/mcp_log_proxy.py", "--log", "/lab/out/transcript.jsonl", "--png-dir", "/lab/out", "--", "solidcraft-cli", "mcp", "--allow-path", "/lab/out"]}}}
JSON

PLATE="Use the solidcraft MCP tools to model a mounting plate in millimetres: 80 mm wide along X, 50 mm deep along Y and 5 mm thick (Z from 0 to 5), with one corner at the origin. Drill four 5 mm holes at the corners, each centred 8 mm in from both edges, and one 12 mm hole in the middle of the plate. Export it as STL to /lab/out/plate-80.stl."
if [ "$ARM" = plain ]; then
  PROMPT="$PLATE Then make the plate 60 mm wide, keeping the corner holes 8 mm from the edges and the big hole in the middle, and export /lab/out/plate-60.stl. Report what you did and any step that failed."
else
  PROMPT="$PLATE Make the width a parameter named width and build the plate so the holes follow it: the corner holes stay 8 mm from the edges and the 12 mm hole stays in the middle. Then change only the width parameter: to 120 mm, export /lab/out/plate-120.stl; then to 60 mm, export /lab/out/plate-60.stl. Report the bounding box after each export and any step that failed."
fi
printf '%s\n' "$PROMPT" > "$OUT/prompt.txt"

T0=$(date +%s)
set +e
MSYS_NO_PATHCONV=1 timeout 900 "${CLAUDE:-claude}" -p "$PROMPT" --model "$MODEL" \
  --mcp-config "$OUT/mcp-config.json" --strict-mcp-config \
  --tools "" --allowedTools "mcp__solidcraft__*" --permission-mode dontAsk \
  --max-budget-usd "$BUDGET" --no-session-persistence \
  --setting-sources project,local --settings '{"claudeMdExcludes":["**/.claude/CLAUDE.md"],"autoMemoryEnabled":false}' \
  --output-format json < /dev/null > "$OUT/claude-output.json"
RC=$?
set -e
# no host path in the saved config (the lab may be published)
sed -i "s#$LAB#\$LAB#g" "$OUT/mcp-config.json"
echo "{\"arm\": \"$ARM\", \"run\": \"$RUN\", \"model\": \"$MODEL\", \"budget_usd\": $BUDGET, \"exit\": $RC, \"wall_s\": $(( $(date +%s) - T0 )), \"claude_version\": \"$(${CLAUDE:-claude} --version | head -1)\"}" > "$OUT/run-meta.json"
cat "$OUT/run-meta.json"
