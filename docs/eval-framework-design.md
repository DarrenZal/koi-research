# MCP Stack Eval Framework (Regression Testing) — Design v0.1

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

## Implementation options (choose one for v0)

### Option 1 (recommended): TypeScript runner + MCP stdio client
Because `regen-koi-mcp/evals/run_eval.ts` already exists.

Build:
- A small MCP test client that:
  - spawns the MCP server process (local) OR connects to a deployed MCP entrypoint if available
  - calls `tools/list`
  - calls tool methods and captures structured outputs

Pros: tests the actual MCP interface; aligns with existing TS code.
Cons: requires solid MCP client harness, careful parsing.

### Option 2: HTTP-only runner (KOI API endpoints)
Test `/api/koi/query` and `/api/koi/graph` directly.

Pros: simplest; structured JSON.
Cons: does not directly test MCP schema/tool behavior.

Pragmatic path: do **both** — Suite A through MCP, Suite B through HTTP.

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

# Implementation plan (1–2 weeks)

## Week 1 — Build the reliable core
1. Choose runner approach (TS MCP client + optional HTTP).
2. Implement Suite A (tool discovery + schema/contract tests).
3. Port/update existing gold set into Suite B format (keep small at first).
4. Add reporting output (JSON + Markdown) and baseline compare.

## Week 2 — Expand coverage + automate alerts
1. Add Suite C health/perf checks using `get_mcp_metrics` and `get_stats`.
2. Add simple alerting (GitHub issue/comment).
3. Add first 2–3 Suite D agent scenarios (non-blocking).
4. Document “gold set maintenance” playbook (how to update expected results safely).

---

# Ownership (make it someone’s job)

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
