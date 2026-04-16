#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# startup.sh -- JARVIS startup initialization
# Runs once per JARVIS session startup cycle
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

log()   { echo -e "[startup] $1"; }
warn()  { echo -e "[startup] WARNING: $1"; }
err()   { echo -e "[startup] ERROR: $1"; }

# ============================================================
# 1. Environment checks
# ============================================================
log "Initializing JARVIS..."

# Verify Python is available
if ! command -v python3 &>/dev/null; then
    err "python3 not found. Cannot run curiosity loop."
    exit 1
fi

# ============================================================
# 2. Curiosity Loop (JAR-119)
# Auto-create tasks from curiosity gaps for HOMER
# ============================================================
log "Running curiosity loop..."

CURIO_SCRIPT="${SCRIPT_DIR}/curiosity_loop.py"
if [[ -f "$CURIO_SCRIPT" ]]; then
    python3 "$CURIO_SCRIPT" || warn "Curiosity loop returned non-zero"
else
    warn "curiosity_loop.py not found at ${CURIO_SCRIPT}"
fi

# ============================================================
# 3. Future startup hooks (extend here)
# ============================================================
# - Session health checks
# - Memory rotation triggers
# - State consistency verification

log "Startup complete."
