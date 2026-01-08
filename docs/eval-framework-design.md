# MCP Stack Eval Framework (Regression Testing) — Design v0.1

> **Origin:** Zach's input on automated evals from [Regen AI Builders Standup - 2026-01-06](https://www.notion.so/regennetwork/Regen-AI-Builders-Standup-2e025b77eda180e1b7eaf58a28035e1b)

This document proposes an automated eval framework to catch regressions as:
- LLM models change
- agent behavior/prompts change
- MCP servers/tools change
- KOI indexing + backend APIs evolve

Target: concrete enough to implement in ~1–2 weeks.

## Goals (what “good” looks like)

1. **Catch hard breaks fast** (tool schema mismatch, auth broken, API errors, timeouts).
2. **Detect retrieval quality drift** (golden queries stop surfacing the right docs/entities).
3. **Track performance/health** (latency, error rate, circuit breaker, cache).
4. **Separate deterministic tests from LLM-nondeterministic tests** so CI signal stays high.
5. **Produce actionable reports** (which tool, which query, what changed, how to reproduce).

## Non-goals (v0)

- Proving overall “answer quality” across all possible prompts.
- Training/fine-tuning.
- Replacing product usability testing (that’s the Marie protocol in `koi-research/docs/test-protocol-full-stack.md:1`).

## System under test (SUT)

At minimum:
- **regen-koi-mcp (TS MCP server)**: tools like `search`, `query_code_graph`, `get_stats`, `get_mcp_metrics`, auth.
- **koi-processor / KOI Query API**: hybrid retrieval (vector + entity + keyword) and graph endpoints.
- **Code graph service** + its API surface as exposed via `query_code_graph`.

Optionally (recommended as Phase 2):
- **regen-python-mcp** (tools that must not regress)
- **Ledger MCP** (on-chain queries)
- **Registry MCP / Registry Agent path** (workflow regression tests)

## Key observation from current baseline

The stack already benefits from:
- A hybrid scoring pipeline (vector/entity/keyword fusion + boost).
- Tool-level metrics (`get_mcp_metrics`) that can be used as a health signal.
- Existing retrieval eval scaffolding in `regen-koi-mcp/evals/` (gold set + recall@k runner).

The main missing piece is a **single, versioned, automated test suite** that runs routinely and fails loudly on regressions.

---

# Test suite structure

Organize tests into suites with different “flakiness budgets” and run cadences.

## Suite A — Tool Contract Tests (deterministic, CI-blocking)

**Purpose:** Ensure MCP tool schemas and backend behavior match. Catch breaking changes immediately.

**What it tests**
- Tool list is obtainable (`tools/list`) and includes required tools.
- Each tool validates inputs as expected (required params, enum values).
- Each tool returns responses in an expected shape (ideally JSON; otherwise parseable raw JSON blocks).
- “Supported query types” mismatches are caught (e.g., `query_code_graph` accepts `list_keepers` but backend rejects it).

**Example cases**
- `query_code_graph` contract:
  - For each `query_type` enum in the MCP schema, run a minimal valid call and assert:
    - no `INVALID_QUERY_TYPE` backend error
    - response includes `metadata.query_type` (or an equivalent marker)
- `search` contract:
  - Minimal query `{"query":"Registry Agent","limit":1}` returns 1+ results and includes `rid`/`url`.
- Security checks:
  - Inputs containing obvious injection patterns are rejected (expected “validation error”, not 500).

**Pass/fail rule:** any failure fails the suite.

## Suite B — Retrieval Quality (mostly deterministic, threshold-based)

**Purpose:** Detect regressions in “does the right thing show up?” as corpuses/models/ranking change.

**What it tests**
- Golden queries: expected documents/entities appear in top-k.
- Stability metrics: average confidence/weighted score doesn’t collapse.
- Diversity sanity: results aren’t suddenly dominated by a single source (optional).

**Primary metrics**
- Recall@5 / Recall@10
- MRR@10 (optional)
- “Confidence” averages (if exposed consistently)

**Pass/fail rule (suggested v0)**
- Per-query: Recall@10 must be ≥ 0.6 (or “≥ baseline - 0.1” once baseline exists).
- Aggregate: Mean Recall@10 must not drop more than 0.05 vs baseline.

**Current v0 implementation (HTTP runner)**
- Gold set: `koi-research/evals/suite_b_gold_set.json`
- Runner: `koi-research/scripts/run_suite_b.py`
- Baseline: `koi-research/reports/baselines/prod/suite_b.json`

Refresh the baseline (only when the new behavior is expected):
```bash
cd koi-research
python3 scripts/run_suite_b.py --env prod --write-baseline reports/baselines/prod/suite_b.json
```

## Suite C — Performance & Health (deterministic, threshold-based)

**Purpose:** Detect degradations that make the system unusable even if it’s “correct”.

**Signals**
- `get_mcp_metrics`:
  - tool success rates
  - p95 latency per tool
  - API error rate
  - circuit breaker trips
  - cache hit rate (contextual; not always high in CI)
- Backend “freshness”:
  - corpus `indexed_at` age (where exposed)

**Pass/fail rule (suggested v0)**
- `search` p95 latency ≤ 5s
- `query_code_graph` p95 latency ≤ 2s
- MCP API error rate ≤ 2%
- circuit breaker trips = 0 (warning if >0, fail if persistent)
- corpus indexed within last 48h (warning) / 7d (fail) depending on environment

## Suite D — End-to-End Agent Scenarios (LLM-dependent, non-blocking at first)

**Purpose:** Catch “weird, non-deterministic” regressions Zach flagged: small changes break workflows.

**Approach**
- Run a small number of scripted scenarios with a pinned model and low temperature.
- Score with **structural checks**, not judge models:
  - Did it call required tools?
  - Did it produce a patch/diff?
  - Did it run verification commands?
  - Did it output required sections in a template?

**Cadence:** nightly or weekly; non-blocking initially; promote to blocking once stable.

**Pinned model (v0 recommendation)**
- Nightly: **Claude Sonnet** (lower cost + faster, good stability) with low temperature.
- Weekly: **Claude Opus** (capability check) with the same scenario set.
- Always record: model name/version, temperature, agent version/prompt hash, MCP server version, and corpus `indexed_at` so failures are reproducible.

**Standardized environment (strongly recommended)**
- Run Suite D in a consistent devcontainer/Docker image with required toolchains (python/go/rust) so failures represent regressions, not missing local tooling.
- Starter option: reuse the devcontainer in `koi-research/.devcontainer/` (or mirror it into the eval runner repo once the harness is implemented).

**Where scenarios come from**
- Seed initial Suite D scenarios from the manual protocol: `koi-research/docs/test-protocol-full-stack.md:1`.
- Promote only when the acceptance criteria can be checked structurally (files changed, tests run, tool calls made), not by subjective grading.

---

# Golden dataset design

## Principles
- Prefer **stable targets**: repo docs, canonical specs, stable file paths, known message names.
- Avoid queries whose “correct” answer changes daily (market data, latest proposals) unless anchored to a height/date.
- Store **expected hits as patterns**, not exact text.

## Data model (YAML or JSON)

Recommended test case shape:
```yaml
id: retrieval_registry_agent_001
suite: retrieval
tool: regen-koi.search
input:
  query: "Registry Agent"
  limit: 10
assert:
  expected_any:
    - type: rid_contains
      values:
        - "regen-registry-handbook"
        - "handbook.regen.network"
  min_results: 3
  min_recall_10: 0.6
notes: "Should surface handbook + internal notion pages when authenticated."
```

For `query_code_graph`:
```yaml
id: codegraph_msg_create_batch
suite: retrieval
tool: regen-koi.query_code_graph
input:
  query_type: search_entities
  entity_name: "MsgCreateBatch"
  limit: 10
assert:
  expected_any:
    - type: file_path_contains
      values: ["x/ecocredit", "tx.pb.go"]
  min_results: 1
```

## Seeding the first gold set (v0)

Start with ~20–30 cases split across:
- ecocredit (Msgs, basket, retirement)
- upgrades (validator upgrade docs, upgrade handlers)
- MCP/tooling (auth, metrics, troubleshooting)
- registry agent (handbook + internal docs)

Leverage and update the existing gold set:
- `regen-koi-mcp/evals/gold_set.json`

Note: some query types referenced there (e.g., `docs_mentioning`, `list_keepers`, `list_messages`) should be treated as **contract tests** first, because mismatches currently occur.

---

# Manual → Automated feedback loop (how the two docs connect)

Use the manual protocol to discover “high-signal” prompts, then convert them into automated coverage:
- **VC-02** (query_code_graph mismatch) → Suite A (contract test: schema enum ↔ backend support)
- **CA-01** (basket token helper) → Suite B (retrieval: expected docs in top-k) + optional Suite D (generate README structure)
- **NU-01** (upgrade handler scaffold) → Suite D (repo edit + `go test` executed)
- **VC-01** (tiny CLI + `unittest`) → Suite D (file creation + tests executed)
- **CA-02** (registry report template) → Suite D (required headings/checklists present)
- **KV-01 / KV-02** (public delta tests) → Suite B (citations + expected docs in top-k) + Suite D (required sections present)
- **KV-03** (private delta test) → Suite B (auth-gated retrieval) + Suite D (template generation), or keep manual-only if CI auth is not available

Promotion checklist:
1. Copy the exact manual prompt.
2. Write explicit acceptance checks (deterministic where possible).
3. Add to the suite with a baseline run and thresholds.

---

# Regression detection strategy

## Baselines
Store baselines per environment (staging vs prod), because:
- corpuses differ
- indexing freshness differs
- auth availability differs

Baseline artifact:
- `reports/baselines/<env>/<suite>.json`
- includes:
  - test run timestamp
  - corpus version + indexed_at (if available)
  - MCP server versions (commit SHA / package version)
  - per-test metrics

## Comparison rules

Use a “traffic-light” approach:
- **Red:** contract failures, tool crashes, auth broken, hard latency regression.
- **Yellow:** retrieval metrics drift beyond warning threshold, freshness lag, moderate latency regression.
- **Green:** within thresholds.

To reduce noise:
- For Suite B/C, run each test **N=3** and take median (or require 2/3 passes).
- Quarantine flaky tests explicitly (tracked list), don’t silently ignore.

---

# Automation approach (CI/CD + scheduled)

## Where tests run

**PR checks (fast, blocking)**
- Suite A (tool contract)
- Minimal Suite C (health/latency sanity)

**Nightly scheduled (non-blocking initially)**
- Full Suite B (retrieval)
- Full Suite C (performance)
- Optional Suite D (agent scenarios) with pinned model

**Weekly**
- Extended Suite D scenarios (bigger workflows)
- Report review + gold set maintenance

## Implementation options

### Suite A/B/C: HTTP runner (implemented)
Test `/api/koi/query` and `/api/koi/graph` directly via curl/Python requests.

- **Suite A** (contract): Validate query types against backend
- **Suite B** (retrieval): Golden queries via HTTP (`scripts/run_suite_b.py`)
- **Suite C** (health): Metrics via `get_mcp_metrics` endpoint

Pros: simple, structured JSON, no MCP client needed.
Implemented in: `.github/workflows/full-stack-tests.yml`

### Suite D: Claude Agent SDK (recommended)

The [Claude Agent SDK](https://docs.anthropic.com/en/docs/claude-code/sdk) provides programmatic access to the same agent capabilities that power Claude Code. This is the recommended approach for Suite D (agent scenarios) because:

1. **Battle-tested tooling** — Same file editing, bash, search tools used in production
2. **Native MCP support** — Configure KOI MCP server directly in the agent
3. **Structural verification** — Capture tool calls, outputs, and files created
4. **No abstraction tax** — Claude-native, no multi-provider overhead

**Example test harness:**

```python
from claude_agent_sdk import Agent

def run_scenario(prompt: str, expected_tools: list[str], expected_files: list[str]):
    agent = Agent(
        model="claude-sonnet-4-20250514",
        tools=["bash", "read", "edit", "glob", "grep"],
        mcp_servers=["regen-koi"],
        setting_sources=["project"]  # Enable skills, CLAUDE.md, etc.
    )

    result = agent.run(prompt)

    # Structural checks
    tools_called = [call.tool for call in result.tool_calls]
    files_created = [f for f in expected_files if Path(f).exists()]

    return {
        "passed": all(t in tools_called for t in expected_tools),
        "tools_called": tools_called,
        "files_created": files_created,
        "output": result.output
    }

# Run VC-01 scenario
result = run_scenario(
    prompt="Create a Python CLI that prints 'Hello, Regen!' with a --name flag...",
    expected_tools=["regen-koi.search", "edit"],
    expected_files=["scratch/hello_regen.py", "scratch/test_hello_regen.py"]
)
```

**Why Agent SDK over other frameworks:**

| Consideration | Agent SDK | LangChain/CrewAI/etc |
|---------------|-----------|----------------------|
| MCP support | Native | Requires custom integration |
| Tool execution | Production-proven | Framework-dependent |
| Claude optimization | Built-in (caching, context) | Generic abstractions |
| Maintenance | Anthropic-maintained | Community-maintained |

**When to use other frameworks:** If you need multi-model support or have existing LangChain investments.

**Prototype implementation (this repo)**
- Scenarios: `koi-research/evals/suite_d_scenarios.json`
- Runner: `koi-research/scripts/run_suite_d.py`
- CI: runs in `koi-research/.github/workflows/full-stack-tests.yml` (Tier 1 / `all`), and feeds into hallucination detection via the generated markdown results file.

Run locally (requires Claude Code CLI + API key):
```bash
cd koi-research
python3 -m pip install claude-agent-sdk==0.1.19
export ANTHROPIC_API_KEY=...   # required by Claude Code CLI
python3 scripts/run_suite_d.py --env prod --model sonnet --out-md /tmp/suite_d.md --out-json /tmp/suite_d.json
```

---

# Metrics to track (dashboards + alerts)

## Reliability
- Tool success rate by tool name
- API error rate
- Circuit breaker trips

## Retrieval
- Recall@5 / Recall@10 per query and averaged
- MRR@10
- Mean “confidence” (if exposed consistently)
- Result source distribution (optional)

## Performance
- p50/p95 latency per tool
- End-to-end eval run duration

## Freshness
- corpus `indexed_at` age
- total doc count + recent doc count deltas (from `get_stats`)

---

# Alert thresholds (initial suggestions)

Tune after 1–2 weeks of baseline data.

## Hard fail (page someone / block deploy)
- Any Suite A failure (schema mismatch, tool not found, 500s)
- `search` p95 > 8s sustained
- `query_code_graph` p95 > 3s sustained
- API error rate > 5%

## Soft fail (flag in report / open issue)
- Mean Recall@10 drop > 0.05 vs baseline
- More than 20% of retrieval queries drop below Recall@10 < 0.6
- corpus indexed_at > 48h old (staging) / > 7d (prod) depending on expectations

---

# Reporting (make it easy to act)

Each run produces:
1. `reports/evals/<env>/<timestamp>.json` (machine-readable)
2. `reports/evals/<env>/<timestamp>.md` (human summary)
3. A diff vs baseline highlighting:
   - which tests regressed
   - example “missing expected” items
   - last known good timestamp

Recommended workflow integration:
- Post nightly summary as a comment to the retrieval tracking issue (e.g. `regen-koi-mcp#3`), or create a dedicated “Eval Dashboard” issue.
- Open a new issue automatically only on **red** regressions.

---

# Concrete example test cases (starter set)

## Contract
- `query_code_graph` accepts all declared `query_type` values (no backend `INVALID_QUERY_TYPE` errors).
- `search` returns at least 1 result for “Registry Agent”.
- `get_mcp_metrics` returns JSON and includes `tools.search.p95_latency_ms`.

## Retrieval
- “basketing tokens C06 basket token” should surface:
  - `regen-ledger` basket types/proto docs OR docs.regen.network ecocredit basket module page within top 10.
- “upgrade handler regen-ledger” should surface:
  - regen-ledger upgrade docs (validators/upgrades) within top 10.

## Performance
- `search` median latency < 3s, p95 < 5s (staging)

---

# Implementation plan

## Phase 1 — HTTP-based suites (done)
- [x] Suite A: Contract tests via HTTP (`curl` in CI workflow)
- [x] Suite B: Retrieval gold set via HTTP (`scripts/run_suite_b.py`)
- [x] Suite C: Health/preflight via HTTP (CI workflow)
- [x] Hallucination detection (`scripts/verify-citations.py`)
- [x] CI workflow with artifacts and summary

## Phase 2 — Agent SDK for Suite D (next)
1. Install Claude Agent SDK in test environment
2. Create `scripts/run_suite_d.py` harness using Agent SDK
3. Port 2-3 scenarios from `test-protocol-full-stack.md`:
   - VC-01 (Python CLI + tests)
   - CA-01 (basket token helper)
   - NU-02 (upgrade planning)
4. Add structural checks: tools called, files created, sections present
5. Integrate with CI (nightly, non-blocking initially)

## Phase 3 — Alerts + baseline tracking
1. Baseline comparison for hallucination rate trends
2. GitHub issue creation on red regressions
3. Weekly summary comment to tracking issue

---

# Implemented: Hallucination Detection

> **Status:** Implemented and integrated into CI workflow.

Hallucination detection validates that agent-generated citations (file paths, line numbers, symbols, GitHub URLs) actually exist in the codebase. This is especially valuable for **Delta tests (KV-01/02/03)** where we compare KOI-grounded vs baseline responses.

## Scripts

- `scripts/verify-citations.py` — Main verification script
  - Extracts citations from markdown test results
  - Verifies file paths exist in configured repos
  - Verifies line numbers are in range
  - Verifies symbols via grep or KOI API
  - Reports hallucination rate (failed / verifiable)

- `scripts/verify-delta-citations.sh` — Wrapper for Delta tests
  - Runs verification with environment-aware repo paths
  - Configurable threshold via `HALLUCINATION_THRESHOLD` env var
  - Optional KOI API symbol verification via `USE_KOI_API=true`

## CI Integration

The GitHub Actions workflow (`.github/workflows/full-stack-tests.yml`) includes:
- `hallucination_threshold` input parameter (default: 0.20 = 20%)
- Automatic citation verification after test results are generated
- Results included in job summary with pass/warn status
- Artifacts include `citation_verification.json`

## Baseline + Regression

Once CI is running real agent scenarios (Suite D), track hallucination regressions by diffing the current run vs a committed baseline:
- Baseline file: `reports/baselines/prod/hallucination.json`
- Diff runner: `scripts/compare_hallucination_baseline.py`

Refresh the baseline (only when the new behavior is expected):
```bash
cd koi-research
python3 scripts/verify-citations.py docs/test-results/<your-latest-run>.md --format json > /tmp/citation_verification.json
python3 scripts/compare_hallucination_baseline.py \
  --current /tmp/citation_verification.json \
  --baseline reports/baselines/prod/hallucination.json \
  --write-baseline
```

## Usage

```bash
# Verify a test results file
python scripts/verify-citations.py docs/test-results/2026-01-08-delta.md \
  --repos /path/to/regen-ledger,/path/to/koi-research \
  --scratch scratch \
  --fail-threshold 0.20

# Use KOI API for symbol verification
python scripts/verify-citations.py results.md --use-koi-api

# Output JSON for CI
python scripts/verify-citations.py results.md --format json
```

## Interpretation Notes

False positives can occur when:
- Agent proposes new code (citations to files that will be created)
- Agent creates files in scratch/ (add `--scratch` path)
- Agent references example code blocks (not real files)

The 20% threshold accommodates some false positives while catching significant hallucination issues.

---

# Ownership (make it someone's job)

Suggested initial ownership (edit as needed):
- **Eval framework DRI (engineering):** Darren (build/maintain harness, CI wiring, thresholds, incident triage)
- **Gold set + scenario curator (product):** Marie (manual test intake → candidate prompts), with engineering support to convert into automated checks
- **Weekly review:** 15 minutes in Gaia AI standup to review the latest report and decide: fix / adjust thresholds / update gold set

---

# Open questions (prioritized)

## P0 (blocks Week 1)
1. **Where to run evals:** GitHub Actions vs a dedicated nightly runner VM (rate limiting, network access).
2. **Environment targets:** staging endpoint(s) vs prod (and which is the “baseline of record”).
3. **Tool output format:** standardize “raw JSON for eval harness” across tools (recommended).

## P1 (can land after harness works)
4. **Auth in CI:** do we provision a limited-scope token for private Notion retrieval tests, or keep those as manual-only?
5. **Model pinning details:** confirm exact model IDs for “Sonnet”/“Opus”, temperature, and any provider credentials for scheduled runs.
