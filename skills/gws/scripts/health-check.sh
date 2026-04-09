#!/usr/bin/env bash
set -euo pipefail

# GWS health check -- verify Google Workspace access
# Usage: bash health-check.sh

echo "=== GWS Health Check ==="

# 1. Check gws binary
if ! command -v gws &>/dev/null; then
    echo "FAIL: gws not found in PATH"
    echo "Install: pip install google-workspace-cli"
    exit 1
fi
echo "OK: gws found"

# 2. Check config files
GWS_CONFIG="$HOME/.config/gws"
for f in client_secret.json credentials.json; do
    if [ -f "$GWS_CONFIG/$f" ]; then
        echo "OK: $f exists"
    else
        echo "FAIL: $f missing in $GWS_CONFIG/"
        exit 1
    fi
done

# 3. Check auth status
AUTH=$(gws auth status 2>/dev/null || echo '{}')
echo "$AUTH" | python3 -c "
import json, sys
s = json.load(sys.stdin)
user = s.get('user', 'unknown')
valid = s.get('token_valid', False)
scopes = s.get('scope_count', 0)
print(f'User: {user}')
print(f'Token valid: {valid}')
print(f'Scopes: {scopes}')
if not valid:
    print('WARN: token expired, will auto-refresh on next call')
"

# 4. Live test -- Gmail
echo ""
echo "Testing Gmail API..."
RESULT=$(gws gmail users messages list --params '{"userId":"me","maxResults":1}' 2>&1)
if echo "$RESULT" | python3 -c "
import json, sys
d = json.load(sys.stdin)
if 'messages' in d:
    print('OK: Gmail accessible')
else:
    print('WARN: no messages or unexpected response')
    sys.exit(1)
" 2>/dev/null; then
    echo "PASS: GWS fully operational"
else
    echo "FAIL: Gmail API error"
    echo "$RESULT" | head -5
    exit 1
fi
