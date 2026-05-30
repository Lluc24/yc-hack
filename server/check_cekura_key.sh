#!/usr/bin/env bash
# Verify the CEKURA_API_KEY in the environment actually authenticates.
# Usage:  bash check_cekura_key.sh
set -euo pipefail

API="https://api.cekura.ai/mcp"
ACCEPT="Accept: application/json, text/event-stream"
CT="Content-Type: application/json"

if [ -z "${CEKURA_API_KEY:-}" ]; then
  echo "❌ CEKURA_API_KEY is not set in this shell."
  echo "   Run:  source ~/.zshrc   then try again."
  exit 1
fi

echo "Key length: ${#CEKURA_API_KEY}  prefix: ${CEKURA_API_KEY:0:4}..."

INIT='{"jsonrpc":"2.0","method":"initialize","id":1,"params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"t","version":"1"}}}'
CALL='{"jsonrpc":"2.0","method":"tools/call","id":2,"params":{"name":"user_organizations_list","arguments":{}}}'

# 1. initialize → grab session id
SID=$(curl -s -D - -o /dev/null -X POST "$API" \
  -H "$CT" -H "$ACCEPT" -H "X-CEKURA-API-KEY: $CEKURA_API_KEY" \
  -d "$INIT" | grep -i "mcp-session-id" | tr -d '\r' | awk '{print $2}')

if [ -z "$SID" ]; then
  echo "❌ Could not get a session id (network issue?)."
  exit 1
fi

# 2. authenticated tool call
RESP=$(curl -s -X POST "$API" \
  -H "$CT" -H "$ACCEPT" -H "X-CEKURA-API-KEY: $CEKURA_API_KEY" -H "mcp-session-id: $SID" \
  -d "$CALL")

echo ""
if echo "$RESP" | grep -q "401"; then
  echo "❌ KEY REJECTED (401). This is not a valid Cekura API key."
  echo "   → dashboard.cekura.ai → Settings → API Keys → copy the real key."
else
  echo "✅ KEY WORKS. Response:"
  echo "$RESP" | sed 's/^data: //' | tail -1
fi
