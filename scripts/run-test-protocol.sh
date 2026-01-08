#!/bin/bash
#
# Run Full-Stack Test Protocol
#
# Usage:
#   ./scripts/run-test-protocol.sh [OPTIONS]
#
# Options:
#   --suite SUITE    Test suite to run: preflight, tier1, tier2, delta, all (default: tier1)
#   --output DIR     Output directory for results (default: docs/test-results)
#   --model MODEL    Model to use: sonnet, opus (default: sonnet)
#   --help           Show this help message
#
# Prerequisites:
#   - KOI MCP configured in your agent environment (Claude Code / Codex / etc)
#   - Python 3.x (Tier 1 + Delta)
#   - Go 1.22+ (Tier 2 / NU-01)
#   - Rust + wasm32 target (Tier 2 / SC-01)

set -e

# Defaults
SUITE="tier1"
OUTPUT_DIR="docs/test-results"
MODEL="sonnet"
TIMESTAMP=$(date +%Y-%m-%d-%H%M)
RESULTS_FILE=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --suite)
            SUITE="$2"
            shift 2
            ;;
        --output)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --model)
            MODEL="$2"
            shift 2
            ;;
        --help)
            head -25 "$0" | tail -20
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Create output directory
mkdir -p "$OUTPUT_DIR"
RESULTS_FILE="$OUTPUT_DIR/${TIMESTAMP}-manual.md"

echo "================================"
echo "Full-Stack Test Protocol Runner"
echo "================================"
echo "Suite: $SUITE"
echo "Model: $MODEL"
echo "Output: $RESULTS_FILE"
echo "================================"
echo ""

# Environment check
echo "=== Environment Check ==="
version_line() {
    local name=$1
    local cmd=$2
    local version_cmd=$3

    if command -v "$cmd" >/dev/null 2>&1; then
        echo "  [OK] $name: $($version_cmd 2>&1 | head -1)"
        return 0
    fi

    echo "  [MISSING] $name"
    return 1
}

ENV_OK=true
version_line "Git" "git" "git --version" || ENV_OK=false
version_line "Python" "python3" "python3 --version" || ENV_OK=false

if [ "$SUITE" == "tier2" ] || [ "$SUITE" == "all" ]; then
    version_line "Go" "go" "go version" || ENV_OK=false
    version_line "Rust" "rustc" "rustc --version" || ENV_OK=false
    version_line "Cargo" "cargo" "cargo --version" || ENV_OK=false
else
    if command -v go >/dev/null 2>&1; then
        echo "  [OK] Go (Tier 2 only): $(go version 2>&1 | head -1)"
    else
        echo "  [WARN] Go: missing (Tier 2 only)"
    fi

    if command -v rustc >/dev/null 2>&1; then
        echo "  [OK] Rust (Tier 2 only): $(rustc --version 2>&1 | head -1)"
    else
        echo "  [WARN] Rust: missing (Tier 2 only)"
    fi

    if command -v cargo >/dev/null 2>&1; then
        echo "  [OK] Cargo (Tier 2 only): $(cargo --version 2>&1 | head -1)"
    else
        echo "  [WARN] Cargo: missing (Tier 2 only)"
    fi
fi

if command -v node >/dev/null 2>&1; then
    echo "  [OK] Node.js (optional): $(node --version 2>&1 | head -1)"
else
    echo "  [WARN] Node.js: missing (optional)"
fi

if [ "$ENV_OK" == "false" ]; then
    echo ""
    echo "ERROR: Required tools missing. Cannot continue."
    exit 1
fi

echo ""

# Initialize results file
mkdir -p scratch
cat > "$RESULTS_FILE" << EOF
# Test Results - $TIMESTAMP

**Date:** $(date)
**Suite:** $SUITE
**Model:** $MODEL
**Runner:** Manual ($(whoami)@$(hostname))

---

## Environment

| Tool | Version | Status |
|------|---------|--------|
| Git | $(git --version 2>&1 | head -1) | OK |
| Python | $(python3 --version 2>&1 | head -1) | OK |
| Go | $(go version 2>&1 | head -1 || echo "N/A") | $(command -v go &>/dev/null && echo "OK" || echo "Missing") |
| Rust | $(rustc --version 2>&1 | head -1 || echo "N/A") | $(command -v rustc &>/dev/null && echo "OK" || echo "Missing") |
| Cargo | $(cargo --version 2>&1 | head -1 || echo "N/A") | $(command -v cargo &>/dev/null && echo "OK" || echo "Missing") |
| Node | $(node --version 2>&1 | head -1 || echo "N/A") | $(command -v node &>/dev/null && echo "OK" || echo "Missing") |

---

EOF

append_result_block() {
    local test_id=$1
    local test_name=$2
    local tier=$3

    cat >> "$RESULTS_FILE" << EOF
## Test Result: ${test_id} - ${test_name}

- Date:
- Runner:
- Environment (Claude Code / other):
- Tier (${tier}):
- Authenticated to KOI private docs? (Y/N):
- Start time:
- End time:
- Outcome (Worked=2 / Partial=1 / Failed=0):
- Blockers (None / Tooling / Auth / Repo missing / Tool failure / Other):
- Verification status (Verified / Not verified (env blocked) / Not verified (agent gap)):
- For Delta tests only: KOI value-add vs baseline (Y/N) + 1 sentence why:
- Quality:
  - Used indexed knowledge (Y/N):
  - Tool reliability (Y/N):
  - Safe behavior (Y/N):
  - Good handoff (Y/N):

### Prompt Used
<paste exact prompt here from docs/test-protocol-full-stack.md>

### What the agent did (high level)

### What worked

### What didn’t / issues

### Tool errors (paste raw)

### Verification evidence
<tests run, outputs, links, screenshots if any>

---

EOF
}

# Preflight section (always included)
cat >> "$RESULTS_FILE" << EOF
## Preflight

Run the preflight prompt from:
- docs/test-protocol-full-stack.md

Paste outputs + any errors here.

---

EOF

# Add test blocks based on suite
case "$SUITE" in
    preflight)
        ;;
    tier1)
        append_result_block "VC-01" "Small feature + unit tests" "Tier 1"
        append_result_block "VC-02" "query_code_graph contract sanity" "Tier 1"
        append_result_block "NU-02" "Upgrade planning from real upgrade docs (no code)" "Tier 1"
        append_result_block "CA-01" "Basket token helper mini-app (docs + code-grounded)" "Tier 1"
        append_result_block "CA-02" "Registry Agent report template generator" "Tier 1"
        ;;
    tier2)
        append_result_block "NU-01" "Add a next upgrade handler scaffold" "Tier 2"
        append_result_block "SC-01" "Minimal CosmWasm greeter contract + tests" "Tier 2"
        append_result_block "SC-02" "Deploy to a local chain (optional)" "Tier 2"
        ;;
    delta)
        append_result_block "KV-01" "Basket tokens — baseline vs KOI-grounded" "Delta"
        append_result_block "KV-02" "Regen Ledger upgrades — baseline vs KOI-grounded" "Delta"
        append_result_block "KV-03" "Registry Agent — baseline vs KOI-grounded (auth recommended)" "Delta"
        ;;
    all)
        append_result_block "VC-01" "Small feature + unit tests" "Tier 1"
        append_result_block "VC-02" "query_code_graph contract sanity" "Tier 1"
        append_result_block "NU-02" "Upgrade planning from real upgrade docs (no code)" "Tier 1"
        append_result_block "CA-01" "Basket token helper mini-app (docs + code-grounded)" "Tier 1"
        append_result_block "CA-02" "Registry Agent report template generator" "Tier 1"
        append_result_block "NU-01" "Add a next upgrade handler scaffold" "Tier 2"
        append_result_block "SC-01" "Minimal CosmWasm greeter contract + tests" "Tier 2"
        append_result_block "SC-02" "Deploy to a local chain (optional)" "Tier 2"
        append_result_block "KV-01" "Basket tokens — baseline vs KOI-grounded" "Delta"
        append_result_block "KV-02" "Regen Ledger upgrades — baseline vs KOI-grounded" "Delta"
        append_result_block "KV-03" "Registry Agent — baseline vs KOI-grounded (auth recommended)" "Delta"
        ;;
    *)
        echo "ERROR: Unknown suite: $SUITE"
        echo "Valid suites: preflight, tier1, tier2, delta, all"
        exit 1
        ;;
esac

# Summary
cat >> "$RESULTS_FILE" << EOF

## Summary

Fill in scores directly in each Test Result block above.

---

*Generated by run-test-protocol.sh*
EOF

echo "================================"
echo "Results file created: $RESULTS_FILE"
echo ""
echo "Next steps:"
echo "1. Open Claude Code in this directory"
echo "2. Run each test prompt from docs/test-protocol-full-stack.md"
echo "3. Fill in results in $RESULTS_FILE"
echo "================================"
