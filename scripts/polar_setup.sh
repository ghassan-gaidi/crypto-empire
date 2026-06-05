#!/usr/bin/env bash
set -euo pipefail

TOKEN="polar_oat_00S6NNHKDy9X6EBunIzyJKMAz9JhuBiHFAXfX2fMa1y"
BASE="https://api.polar.sh"
ORG_ID=""  # will be set after first org lookup

echo "=== Polar: Checking org ==="
ORG_RESP=$(curl -sL --max-time 15 -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" "$BASE/v1/organizations/?limit=1")
echo "$ORG_RESP" | python3 -m json.tool 2>/dev/null || echo "$ORG_RESP"
