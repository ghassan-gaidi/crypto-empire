#!/usr/bin/env bash
set -euo pipefail

: "${POLAR_TOKEN:?Set POLAR_TOKEN in the environment (never commit tokens)}"
TOKEN="$POLAR_TOKEN"
BASE="https://api.polar.sh"
ORG_ID=""  # will be set after first org lookup

echo "=== Polar: Checking org ==="
ORG_RESP=$(curl -sL --max-time 15 -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" "$BASE/v1/organizations/?limit=1")
echo "$ORG_RESP" | python3 -m json.tool 2>/dev/null || echo "$ORG_RESP"
