# Full-Stack Code Generation Test Protocol

> **Origin:** [Regen AI Builders Standup - 2026-01-06](https://www.notion.so/regennetwork/Regen-AI-Builders-Standup-2e025b77eda180e1b7eaf58a28035e1b)

This protocol is designed so team members (technical or non-technical) can run repeatable tests and produce feedback that's actionable for engineering. It focuses on **code generation capability** — one of several testing tracks.

## Testing tracks overview

This document covers **Track A: Code Generation**. Other testing tracks exist for different goals:

| Track | Focus | Primary tester(s) | See also |
|-------|-------|-------------------|----------|
| **A: Code Generation** | Can KOI + coding agent produce working code? | Marie, engineers | This document |
| **B: Web2 User Onboarding** | Is the journey from "one link" to value frictionless? | Dave | Document journey in Notion |
| **C: Technical Questions** | Can it answer the hardest domain questions accurately? | Becca | Post results to Notion |
| **D: Multi-model/CLI** | Does it work across different models and interfaces? | Gregory | Test with Gemini CLI, etc. |

All tracks feed into the same learning goals and eventually the automated eval framework (`docs/eval-framework-design.md`).

## Phased rollout

Per the Jan 6 meeting decision:

1. **Phase 1 (now):** 3-4 focused testers (Marie, Dave, Becca, Gregory) run structured tests
2. **Phase 2:** Broader team orientation + testing (after "feature complete" checkpoint)
3. **Phase 3:** Ripple out to partners with specific asks (after internal validation)

This phased approach ensures we find and fix issues before external exposure.

## What we're trying to learn (learning goals framing)

Per Zach's suggestion, frame each testing sprint around learning goals:

> 1. **What's the most important thing to learn this sprint?**
> 2. **What tests support that learning?**
> 3. **What do we build to support those tests?**

For Track A (this protocol), our current learning goals are:

1. Can the system go from natural language → working code changes (not just advice)?
2. Can it safely navigate Regen's real codebases (regen-ledger + MCP stack) using the indexed code/knowledge?
3. Can it handle "full-stack" workflows that involve planning + implementation + verification (tests/builds) + clear handoff?
4. Where are the current capability boundaries (what reliably breaks)?

Update these learning goals each sprint based on what you discover.

## Manual vs Automated

This document describes the **manual test protocol** for Track A (Code Generation) testers.

For **automated regression testing**, see `docs/eval-framework-design.md`:
- Suite A/B/C run via HTTP in CI (implemented)
- Suite D scenarios are automated using the [Claude Agent SDK](https://docs.anthropic.com/en/docs/claude-code/sdk), which provides programmatic access to the same agent capabilities
- Suite D Delta runs paired A/B scenarios (baseline vs KOI-grounded) and reports a `koi_value_add_delta` signal
- Hallucination detection runs automatically on test results (`scripts/verify-citations.py`)
- Triage: `docs/runbooks/eval-triage.md`.

If you only want to check “is the system healthy today?”, look at the latest GitHub Actions run + the **KOI Eval Dashboard** issue. The manual protocol is for discovering new failure modes and capability boundaries.

## 0) Setup (15–30 min, once)

### Required
- A coding agent environment that can:
  - Read/write local repos
  - Run terminal commands
  - Use the KOI MCP tools (at minimum `search`, `query_code_graph`, `get_mcp_metrics`)
- **Installation:** See the [regen-koi-mcp README](https://github.com/gaiaaiagent/regen-koi-mcp) for setup instructions (Claude Code, Cursor, VS Code, etc.)
- If you're testing private/internal docs: authenticate with `regen_koi_authenticate` (you can just ask "can you authenticate me?").

### Recommended (for best signal)
- Start each test in a clean git working tree (no uncommitted changes).
- Create a new branch per test (e.g., `test/VC-01`).
- Keep a timer (phone is fine).

### Tooling prerequisites (Tier 1 vs Tier 2)

This protocol intentionally tests two different things:
- **Tier 1 (Portable):** generation + KOI grounding on any machine (Python + MCP access). Recommended for non-technical testers.
- **Tier 2 (Dev environment):** domain-specific coding with verification (Go/Rust toolchains, local repos, tests).

If a Tier 2 test is blocked by missing tooling, that’s still valuable data — mark it as “Blocked: Tooling” (see scoring).

If you want a consistent Tier 2 environment without installing local toolchains, use the devcontainer described in `.devcontainer/README.md` (VS Code “Reopen in Container” or Codespaces).

### Tooling check prompt (copy/paste)
Run this once before starting Tier 2 tests:
```text
Tooling check:
1) Run: python3 --version (and python --version if python3 is missing)
2) Run: git --version
3) Run (Tier 2 only): go version
4) Run (Tier 2 only): cargo --version

For each command: paste the exact output (or error). If go/cargo are missing, say “missing”.
```

### Tool naming note (important)
Depending on the client, tool names may show up with prefixes (e.g., `mcp__regen-koi__search` or `mcp__plugin_koi_regen-koi__search`). That’s OK — in this doc we refer to logical names like `search` / `query_code_graph`.

### Where to submit results (after you run tests)
Pick the simplest option available to you:
- **Option A (preferred):** Paste each completed “Test Result” block into a single Notion page titled `Full-Stack Codegen Test Results — <YYYY-MM-DD>` and share the link in the Gaia AI team channel, tagging Darren.
- **Option B (if you’re comfortable with git):** Create `koi-research/docs/test-results/` (if needed), then add `koi-research/docs/test-results/<YYYY-MM-DD>-track-a.md` with all results blocks and open a PR. Share the PR link in the Gaia AI team channel.

### Preflight prompt (copy/paste)
Use this once at the beginning of a testing session to confirm the stack is working:

```text
Preflight check:
0) If you can’t find these tools by name, list the available tools first, then run the closest equivalent.
1) Call search for "Registry Agent" (limit 3) and paste the results.
2) Call query_code_graph list_repos and paste the results.
3) If available: Call get_mcp_metrics and paste the results.

For steps 1-2: If either fails, stop and tell me exactly what failed and any error messages.
For step 3: If it fails with "authentication required", that's OK for public data testing - note it and continue.
```

**Note:** Some environments may require authentication for `get_mcp_metrics`. If it fails, note the error and continue with steps 1–2.

## How to run each test (important for consistency)

For each test below:
1. Start a new chat/thread for the test.
2. Copy/paste the exact prompt block (don’t paraphrase).
3. Do not provide extra hints unless the protocol says to (see “Allowed nudges”).
4. Record:
   - Start/end time
   - Whether it produced a concrete change (patch / files changed)
   - Whether it ran verification (tests/build) and showed output
   - Any tool errors (especially MCP tool calls)

### Allowed nudges (only if stuck for 5+ minutes)
Use exactly one of these, once per test:
- Nudge A: `Pick the smallest viable implementation and ship it with tests.`
- Nudge B: `Stop and ask me up to 3 clarifying questions.`
- Nudge C: `If a tool call fails, adapt and continue; don’t keep retrying the same thing.`

## Scoring rubric (quick + consistent)

### Outcome (pick one)
- **Worked (2 points):** Delivered a complete solution that matches the prompt, with verification evidence (tests/build/run output) or an explicit reason verification cannot be run.
- **Partially worked (1 point):** Meaningful progress, but missing a required element (e.g., no verification, incomplete wiring, wrong repo touched, unclear instructions).
- **Failed (0 points):** Didn’t produce a usable result, hallucinated, or got stuck without a viable next step.

### Blockers (record separately from score)
If something external prevented success, mark it here so engineering can triage correctly:
- **None**
- **Tooling:** missing Go/Rust/node/etc needed to run verification
- **Auth:** couldn’t access private docs that the prompt depended on
- **Repo missing:** required repo not present locally
- **Tool failure:** MCP/tool call failed repeatedly or returned hard errors
- **Other:** describe

### Verification status (helps distinguish “code wrong” vs “env blocked”)
- **Verified:** tests/builds were run and outputs recorded
- **Not verified (env blocked):** tooling missing or environment prevented running verification, but the agent provided exact commands for an engineer to run
- **Not verified (agent gap):** verification was possible but the agent didn’t run it / didn’t provide commands

### Quality checkboxes (for notes; not a numeric score)
Mark **Y/N** for each:
- **Used indexed knowledge:** referenced specific files/symbols/docs it discovered (not generic advice).
- **Tool reliability:** MCP tool calls succeeded without repeated errors.
- **Safe behavior:** avoided destructive actions; asked before risky steps; no secrets in output.
- **Good handoff:** end-state is clear (what changed, how to run, what to do next).

## Test suite overview

Run Tier 1 first. Tier 2 and the Delta tests are optional.

- **Total time estimate**
  - Tier 1 (recommended): ~2h of test time (plan ~2h30 including setup + breaks)
  - Tier 2 add-ons: +~1h15 (requires Go/Rust toolchains)
  - Delta (A/B KOI value-add): +~45 min

- **Tier 1 (Portable):** VC-01, VC-02, NU-02, CA-01, CA-02
- **Tier 2 (Dev environment):** NU-01, SC-01 (optional SC-02)
- **Delta (KOI value-add A/B):** KV-01, KV-02, KV-03

---

# Vibe Coding

## VC-01 (Tier 1): “Small feature + unit tests” in a new folder

**Goal:** Natural language → working code + tests with minimal dependencies.

**Timebox:** 20 minutes

**Prompt (copy/paste):**
```text
Create a small, self-contained Python CLI tool in a new folder `scratch/track-a-vc-01/` (create the folder if needed).

Requirements:
1) The CLI reads a JSON file containing a list of ecocredit “batches” with fields:
   - batch_denom (string)
   - project_id (string)
   - tradable_amount (number)
   - retired_amount (number)
2) It prints:
   - total_tradable_amount
   - total_retired_amount
   - top 3 projects by total retired_amount
3) Include unit tests using ONLY Python’s built-in `unittest` (no external dependencies).
4) Provide the exact commands to run the tool and run the tests, and actually run the tests.

Deliverable: code + tests + terminal output from running tests.
```

**Success looks like**
- Creates files under `scratch/track-a-vc-01/`
- `python -m unittest` passes
- Output matches requirements

**Common failure modes to note**
- Uses external libs despite instruction
- No tests, or tests don’t run
- CLI can’t parse JSON / crashes

---

## VC-02 (Tier 1): `query_code_graph` contract sanity (schema drift regression check)

**Goal:** Catch regressions where the MCP tool schema drifts from the backend `/graph` API (either advertising unsupported query types or hiding supported ones).

**Timebox:** 20 minutes

**Prompt (copy/paste):**
```text
This is a contract sanity check for query_code_graph.

Task:
1) Call query_code_graph list_repos (should succeed) and paste the result.
2) Call query_code_graph find_call_graph with entity_name="CreateBatch" (it may return 0 results, but should not error). Paste the result or error.
3) Try calling query_code_graph with query_type="list_keepers" (expected: tool rejects it as an invalid query_type). Paste the error.
4) Explain what this tells you about schema drift and how to prevent it (suggest an automated contract test).
```

**Success looks like**
- list_repos works
- find_call_graph is an accepted query_type (even if results are empty)
- list_keepers is NOT accepted (tool blocks unsupported query types)
- Provides a concrete automated contract test idea

**Common failure modes to note**
- Tool accepts unsupported query types (drift)
- Tool rejects supported query types (drift)
- Hand-wavy explanation without a prevention strategy

---

# Network Upgrade (regen-ledger style work)

## NU-02 (Tier 1): Upgrade planning from real upgrade docs (no code)

**Goal:** Can it turn retrieved upgrade docs into a reliable runbook (useful for humans)?

**Timebox:** 20 minutes

**Prompt (copy/paste):**
```text
Using KOI search only, find the most relevant regen-ledger documentation about validator/software upgrades and upgrade handlers.

Then produce a one-page runbook for a hypothetical “Regen Ledger vX.Y” upgrade that includes:
- prerequisites
- upgrade height coordination checklist
- binary build steps
- what to verify before/after
- rollback plan

Keep it specific to Regen Ledger conventions (cite the docs you found by file path or URL).
```

**Success looks like**
- Finds real regen-ledger upgrade docs via `search`
- Produces a concrete checklist/runbook grounded in those docs

**Common failure modes to note**
- Generic upgrade guidance with no Regen Ledger specifics
- No citations (can’t trace where claims came from)

---

## NU-01 (Tier 2): Add a “next upgrade handler” scaffold (local, minimal)

**Goal:** Test whether it can follow established patterns in regen-ledger and wire a small change end-to-end.

**Timebox:** 30–45 minutes

**Prereq:** You have a local clone of `regen-ledger` available to edit.

If you do not have it locally, ask the agent to run:
```bash
cd <where you keep repos>
git clone https://github.com/regen-network/regen-ledger.git
cd regen-ledger
go version
```

**Prompt (copy/paste):**
```text
In the local regen-ledger repo:
1) Find the existing upgrade handler pattern (search for existing upgrade handler folders/files).
2) Add a new placeholder upgrade handler named `vNEXT` that performs NO state migrations but is correctly wired so it can be invoked.
3) Add or update a minimal test that asserts the upgrade handler is registered (choose the smallest existing test pattern you can follow).
4) Run the smallest relevant `go test` command(s) and paste the output.

Constraints:
- Keep the change minimal and consistent with existing patterns.
- If you can’t run tests locally, explain exactly why and what command should be run by an engineer.
```

**Success looks like**
- New `vNEXT` handler exists, wired into the app’s upgrade map/registry
- A test exists and passes (or a precise explanation why tests can’t be run)

**Common failure modes to note**
- Adds files but doesn’t wire them
- No test and no clear verification plan
- Overly large refactor

---

# Smart Contract

## SC-01 (Tier 2): Generate a minimal CosmWasm contract + tests

**Goal:** Can it scaffold a contract and provide runnable tests (even if deployment is skipped)?

**Timebox:** 30 minutes

**Prompt (copy/paste):**
```text
Create a new folder `scratch/track-a-sc-01/` containing a minimal CosmWasm smart contract called `greeter`:
- Instantiate stores a greeting string
- Execute can update the greeting
- Query returns the current greeting

Requirements:
1) Include unit tests (Rust) that cover instantiate, execute, and query.
2) Provide the exact commands to run the tests.
3) If Rust tooling is missing, detect that and give the exact install commands (but don’t install without asking).

Deliverable: contract code + tests + the test command(s) to run.
```

**Success looks like**
- Contract skeleton + tests exist
- Commands are accurate for CosmWasm projects

**Common failure modes to note**
- Incorrect CosmWasm project structure
- Tests missing or not meaningful
- Vague commands

---

## SC-02 (Tier 2 / Stretch): Deploy to a local chain (optional, only if you already have a chain env)

**Goal:** End-to-end deployment workflow (compile → store → instantiate → execute → query).

**Timebox:** 60–90 minutes

**Prompt (copy/paste):**
```text
If (and only if) a local CosmWasm-enabled chain environment is available on this machine:
1) Build the greeter contract to a .wasm artifact.
2) Deploy (store) it on the chain.
3) Instantiate it with an initial greeting.
4) Execute an update.
5) Query and show the updated greeting.

I want the exact commands used and the resulting tx hashes / outputs.
If the environment is NOT available, stop early and tell me exactly what is missing and the minimum setup steps.
```

---

# Custom App (using indexed code knowledge)

## CA-01 (Tier 1): “Basket token helper” mini-app (docs + code-grounded)

**Goal:** Build something small but domain-specific using retrieved docs + code references.

**Timebox:** 30–45 minutes

**Prompt (copy/paste):**
```text
Build a small “basket token helper” in `scratch/track-a-ca-01/` as a single Python script + README.

The tool should:
1) Use KOI search to find authoritative docs about Regen ecocredit baskets and “basket tokens” (limit 5).
2) Summarize (in the README) what basket tokens are, and list the relevant on-chain messages/tx types by referencing regen-ledger code (use query_code_graph search_entities for key symbols like Basket, MsgCreate, MsgPut, etc.).
3) Provide a “user flow” section: how a user would create a basket token and what steps are missing today (UI, permissioning, etc.).

Deliverable: the script (even if it just prints the summary) + a README grounded in retrieved sources and code symbols.
```

**Success looks like**
- Uses `search` and `query_code_graph` in a grounded way (not hallucinated)
- Produces a README that a product person can understand

**Common failure modes to note**
- Makes up tx/message names without checking regen-ledger
- Provides generic web3 guidance with no Regen specifics

---

## CA-02 (Tier 1): Registry Agent “report template generator”

**Goal:** Can it produce structured, auditable outputs for a core internal workflow?

**Timebox:** 30 minutes

**Prompt (copy/paste):**
```text
Using KOI search only, find the most relevant internal/public documentation about:
- Registry Agent responsibilities
- project review / monitoring documentation for Regen Registry

Then generate a “Registry Review Report” markdown template with:
- required sections
- checklists
- evidence fields
- a scoring section

The template must be grounded in what you retrieved (cite URLs or doc titles you found).
```

**Success looks like**
- Template is structured and auditable (not just prose)
- Clearly derived from retrieved registry documentation

---

# KOI Value-Add (Delta) Tests (Optional)

These tests are designed to measure KOI’s incremental value over a baseline coding agent by running a quick A/B:
- **A (Baseline):** no KOI/MCP tools
- **B (KOI-grounded):** use KOI tools and include citations + code pointers

Run A and B in separate fresh threads so the answers don’t contaminate each other.

## KV-01 (Delta, public): Basket tokens — baseline vs KOI-grounded

**Goal:** Does KOI materially improve correctness + traceability (citations, real symbols) for a domain-specific technical explanation?

**Timebox:** 15 minutes total (A: 5, B: 10)

**A) Baseline prompt (copy/paste):**
```text
Timebox: 5 minutes.

Do NOT use any KOI/MCP tools.

Explain what “basket tokens” are in Regen ecocredits and outline a user flow for creating one. If you don’t know exact on-chain message names, say so.

At the end, list which parts of your answer are guesses or uncertain.
```

**B) KOI-grounded prompt (copy/paste):**
```text
Timebox: 10 minutes.

Use KOI tools to ground the answer. Do not rely on guesswork.

1) Use search with query="basketing tokens C06 basket token" limit=5.
2) Cite at least 3 sources from the results (RID or URL).
3) Use query_code_graph search_entities for: MsgCreate, MsgPut, MsgTake, Basket, Keeper.
   - If there are multiple matches, choose the ones whose file_path includes x/ecocredit/basket.
4) Rewrite the explanation + user flow, now including:
   - a Sources section (3+ citations)
   - a Code pointers section (symbol → file path)
5) Include a “Tools used” section listing which tool calls you ran.
```

**Success looks like**
- KOI version includes real citations and real code pointers (no invented symbols).
- Baseline version is noticeably less precise or explicitly uncertain (that’s expected).

---

## KV-02 (Delta, public): Regen Ledger upgrades — baseline vs KOI-grounded

**Goal:** Does KOI produce a Regen-specific runbook (not generic Cosmos advice) and point to the right docs/code?

**Timebox:** 15 minutes total (A: 5, B: 10)

**A) Baseline prompt (copy/paste):**
```text
Timebox: 5 minutes.

Do NOT use any KOI/MCP tools.

Write a one-page runbook for a hypothetical “Regen Ledger vX.Y” software upgrade:
- prerequisites
- upgrade height coordination checklist
- binary build steps
- what to verify before/after
- rollback plan

If you can’t make it Regen-specific (because you don’t have the docs), say so.
```

**B) KOI-grounded prompt (copy/paste):**
```text
Timebox: 10 minutes.

Use KOI tools to ground the runbook.

1) Use search to find Regen Ledger upgrade documentation (limit 5).
2) Cite at least 2 Regen-ledger sources (RID or URL).
3) Optional but preferred: use query_code_graph search_entities for UpgradeHandler / upgrade / SetUpgradeHandler and include any relevant file paths you find.
4) Write the runbook grounded in the sources, and include a Sources section.
5) Include a “Tools used” section listing which tool calls you ran.
```

**Success looks like**
- KOI version has concrete Regen-ledger citations and fewer assumptions.
- If code pointers can’t be found, it says so and still provides a useful cited runbook.

---

## KV-03 (Delta, private): Registry Agent — baseline vs KOI-grounded (auth recommended)

**Goal:** Demonstrate KOI’s “org memory” value (internal docs) for technical workflows.

**Timebox:** 15 minutes total (A: 5, B: 10)

**A) Baseline prompt (copy/paste):**
```text
Timebox: 5 minutes.

Do NOT use any KOI/MCP tools.

Describe what the “Registry Agent” does at Regen and produce a “Registry Review Report” markdown template with:
- required sections
- checklists
- evidence fields
- scoring section

If you’re unsure, say what you’re unsure about.
```

**B) KOI-grounded prompt (copy/paste):**
```text
Timebox: 10 minutes.

Use KOI search to ground the answer. If you are not authenticated for private Notion, say so up front and continue using public sources.

1) search query="Registry Agent" limit=5
2) Cite at least 3 sources (RID/URL/doc title).
3) Rewrite the description + report template grounded in those sources.
4) Include a “Tools used” section listing which tool calls you ran.
```

**Success looks like**
- KOI version cites internal or authoritative sources and produces a template aligned to those docs.
- If not authenticated, it records “Blocked: Auth” but still uses public sources.

---

# Results template (copy/paste per test)

```md
## Test Result: <TEST_ID> - <Test Name>

- Date:
- Runner:
- Environment (Claude Code / other):
- Tier (Tier 1 / Tier 2 / Delta):
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
<paste exact prompt here>

### What the agent did (high level)

### What worked

### What didn’t / issues

### Tool errors (paste raw)

### Verification evidence
<tests run, outputs, links, screenshots if any>
```

## How this connects to automated evals

These manual tests are the source material for automated regression tests. If a prompt reveals an important failure mode (or a critical success that must not regress), we should convert it into:
- **Suite A** (tool contract) when it’s a schema/API mismatch, or
- **Suite B/C** (retrieval/perf) when it’s measurable and deterministic, or
- **Suite D** (agent scenario) when it’s a workflow that needs end-to-end behavior.

The Delta tests (KV-01/02/03) are especially useful to turn into Suite B (retrieval expectations) and Suite D (workflow structure) because they explicitly measure “KOI-grounded vs baseline”.

See `koi-research/docs/eval-framework-design.md:1`.

## Engineering note (optional): Suite B baseline refresh

The automated Suite B retrieval eval uses a committed “known good” baseline for prod:
- Gold set: `koi-research/evals/suite_b_gold_set.json`
- Baseline: `koi-research/reports/baselines/prod/suite_b.json`

Refresh the baseline only when you believe the current behavior is correct (even if results changed due to an intentional re-index / ranking change):
```bash
cd koi-research
python3 scripts/run_suite_b.py \
  --env prod \
  --koi-api-endpoint https://regen.gaiaai.xyz/api/koi \
  --gold evals/suite_b_gold_set.json \
  --write-baseline reports/baselines/prod/suite_b.json
```

Then open a PR with the baseline change so future runs diff against it.

## Engineering note (optional): Hallucination baseline refresh

Hallucination detection in CI produces `citation_verification.json`. Once CI runs real agent scenarios, we can also diff hallucination rate vs a committed baseline:
- Baseline: `koi-research/reports/baselines/prod/hallucination.json`
- Diff script: `koi-research/scripts/compare_hallucination_baseline.py`

Refresh the baseline from a known-good run:
```bash
cd koi-research
python3 scripts/verify-citations.py docs/test-results/<your-latest-run>.md --format json > /tmp/citation_verification.json
python3 scripts/compare_hallucination_baseline.py \
  --current /tmp/citation_verification.json \
  --baseline reports/baselines/prod/hallucination.json \
  --write-baseline
```
