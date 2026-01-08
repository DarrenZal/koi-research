# Test Framework Review Report

**Date:** 2026-01-08
**Reviewer:** Gemini Agent
**Documents Reviewed:**
- `koi-research/docs/test-protocol-full-stack.md` (Marie's Manual Protocol)
- `koi-research/docs/eval-framework-design.md` (Automated Eval Design)

## 1. Review Criteria Assessment

### Test Protocol (Manual)
| Criterion | Status | Notes |
|-----------|--------|-------|
| Non-technical PM usability | **FAIL** | Preflight check fails immediately if unauthenticated (see Blocking Issues). |
| Copy-pasteable prompts | **PASS** | Prompts are clear and well-formatted. |
| Success criteria clarity | **PASS** | Distinctions between "Worked" and "Partially worked" are actionable. |
| Results template completeness | **PASS** | captures necessary fields (time, outcome, quality). |
| "Full-stack" coverage | **PASS** | Planning (VC-02), Implementation (VC-01), Verification (VC-01/NU-01) covered. |
| Realistic timeboxes | **PASS** | 20-45 mins per task seems appropriate. |

### Eval Framework (Automated)
| Criterion | Status | Notes |
|-----------|--------|-------|
| Implementable in 1-2 weeks | **PASS** | Existing `regen-koi-mcp/evals` infrastructure makes this feasible. |
| Suite A coverage | **PASS** | Explicitly catches the `query_code_graph` contract mismatch. |
| Golden dataset format | **PASS** | Proposed `yaml`/`json` schema is an improvement over existing but migration is clear. |
| Alert thresholds | **PASS** | Reasonable starting points (e.g., p95 < 5s). |
| Automation approach | **PASS** | Hybrid MCP client + HTTP runner is a pragmatic choice. |

### Cross-Document Consistency
- **PASS**: The `query_code_graph` mismatch identified in the manual test (VC-02) is explicitly handled in the automated Eval Framework (Suite A).

## 2. Blocking Issues

### 🚨 Preflight Prompt Fails Without Auth
**Location:** `test-protocol-full-stack.md` -> "Preflight prompt"
**Issue:** The prompt instructions say: "If any of these fail, stop and tell me exactly what failed".
**Observation:** Running the preflight prompt as an unauthenticated user causes `get_mcp_metrics` to fail with:
> "Authentication required. Please run regen_koi_authenticate first..."
**Impact:** A PM running this who hasn't set up auth (which is marked as "If you're testing private/internal docs") will hit a hard stop immediately and may abandon the test.
**Fix:** either:
1.  Make `regen_koi_authenticate` a **Required** step for all testers.
2.  Update the Preflight prompt to say "If get_mcp_metrics fails due to auth, that is acceptable if you are only testing public data."

## 3. Suggested Improvements

### Test Protocol
- **Refine VC-01 Success Criteria:** Add explicit instruction to check that `python -m unittest` output is actually visible.
- **Clarify Auth Requirements:** The "Setup" section lists auth as conditional, but the tools used in Preflight enforce it.

### Eval Framework
- **Sync Gold Set Schema:** The existing `regen-koi-mcp/evals/gold_set.json` uses a simpler format (`expected_rids`, `expected_entities`) than the proposed "assert block" design. The implementation plan should explicitly include a migration script or step to convert the existing 11 test cases to the new format.

## 4. Validation Results

I performed the validation steps as requested:

1.  **Preflight Prompt**:
    - `get_mcp_metrics`: **FAILED** (Auth required).
    - `search` ("Registry Agent"): **PASSED** (Found 3 docs, including handbook).
    - `query_code_graph` (`list_repos`): **PASSED** (Listed 8 repos).

2.  **Manual Test Spot-Check (VC-02 Integration Mismatch)**:
    - **Action:** Ran `query_code_graph` with `query_type: "list_keepers"`.
    - **Result:** Successfully reproduced the error: `Invalid query_type: list_keepers`.
    - **Conclusion:** The test case accurately reflects the current system state and is valid.

3.  **Golden Dataset Verification**:
    - **Action:** Ran `search` for "Registry Agent" and `query_code_graph` for "MsgCreateBatch".
    - **Result:** Both returned relevant results (`MsgCreateBatch` returned 8 entity hits).
    - **Conclusion:** The examples in the design doc are grounded in reality.
