#!/bin/bash
#
# Verify citations in Delta test results (KOI value-add tests)
#
# Delta tests specifically measure whether KOI-grounded responses
# cite real code/docs. This script validates those citations.
#
# Usage:
#   ./scripts/verify-delta-citations.sh docs/test-results/2026-01-08-delta.md
#   ./scripts/verify-delta-citations.sh docs/test-results/*.md  # All results
#
# Exit codes:
#   0 = All files pass (<20% hallucination rate)
#   1 = Some files fail (>20% hallucination rate)
#   2 = Error

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Default paths (adjust for CI vs local)
if [ -d "/workspaces/regen-ledger" ]; then
    # In devcontainer/Codespaces
    REPOS="/workspaces/regen-ledger,/workspaces/koi-research,/workspaces/regen-koi-mcp"
else
    # Local development (adjust as needed)
    REPOS="${REGEN_LEDGER_PATH:-$REPO_ROOT/../regen-ledger},${KOI_RESEARCH_PATH:-$REPO_ROOT},${REGEN_KOI_MCP_PATH:-$REPO_ROOT/../regen-koi-mcp}"
fi

SCRATCH="${REPO_ROOT}/scratch"
THRESHOLD="${HALLUCINATION_THRESHOLD:-0.20}"
USE_KOI_API="${USE_KOI_API:-false}"
KOI_API_ENDPOINT="${KOI_API_ENDPOINT:-https://regen.gaiaai.xyz/api/koi}"

# Check for input files
if [ $# -eq 0 ]; then
    echo "Usage: $0 <test-results-file.md> [...]"
    echo ""
    echo "Environment variables:"
    echo "  HALLUCINATION_THRESHOLD  Max allowed rate (default: 0.20)"
    echo "  USE_KOI_API              Use KOI API for symbol verification (default: false)"
    echo "  KOI_API_ENDPOINT         KOI API URL (default: https://regen.gaiaai.xyz/api/koi)"
    exit 2
fi

echo "=========================================="
echo "Delta Citation Verification"
echo "=========================================="
echo "Repos: $REPOS"
echo "Scratch: $SCRATCH"
echo "Threshold: $THRESHOLD"
echo "KOI API: $USE_KOI_API"
echo ""

OVERALL_EXIT=0
TOTAL_FILES=0
PASSED_FILES=0
FAILED_FILES=0

for FILE in "$@"; do
    if [ ! -f "$FILE" ]; then
        echo "SKIP: $FILE (not found)"
        continue
    fi

    ((TOTAL_FILES++)) || true

    echo "---"
    echo "Checking: $FILE"

    KOI_FLAG=""
    if [ "$USE_KOI_API" = "true" ]; then
        KOI_FLAG="--use-koi-api --koi-api-endpoint $KOI_API_ENDPOINT"
    fi

    if python3 "${SCRIPT_DIR}/verify-citations.py" "$FILE" \
        --repos "$REPOS" \
        --scratch "$SCRATCH" \
        --fail-threshold "$THRESHOLD" \
        --format brief \
        $KOI_FLAG; then
        ((PASSED_FILES++)) || true
    else
        EXIT_CODE=$?
        if [ $EXIT_CODE -eq 1 ]; then
            ((FAILED_FILES++)) || true
            OVERALL_EXIT=1
        else
            echo "ERROR: Verification script failed with code $EXIT_CODE"
            OVERALL_EXIT=2
        fi
    fi
done

echo ""
echo "=========================================="
echo "Summary: $PASSED_FILES/$TOTAL_FILES passed"
if [ $FAILED_FILES -gt 0 ]; then
    echo "FAILED: $FAILED_FILES file(s) exceeded hallucination threshold"
fi
echo "=========================================="

exit $OVERALL_EXIT
