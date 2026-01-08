# Full-Stack Code Generation Test Protocol (Marie)

This protocol is designed so a non-technical PM can run repeatable tests and produce feedback that’s actionable for engineering.

## What we’re trying to learn (per Zach’s “learning goal” framing)

1. Can the system go from natural language → working code changes (not just advice)?
2. Can it safely navigate Regen’s real codebases (regen-ledger + MCP stack) using the indexed code/knowledge?
3. Can it handle “full-stack” workflows that involve planning + implementation + verification (tests/builds) + clear handoff?
4. Where are the current capability boundaries (what reliably breaks)?

## 0) Setup (15–30 min, once)

### Required
- A coding agent environment that can:
  - Read/write local repos
  - Run terminal commands
  - Use the KOI MCP tools (at minimum `search`, `query_code_graph`, `get_mcp_metrics`)
- If you’re testing private/internal docs: authenticate with `regen_koi_authenticate` (you can just ask “can you authenticate me?”).

### Recommended (for best signal)
- Start each test in a clean git working tree (no uncommitted changes).
- Create a new branch per test (e.g., `marie/test-VC-01`).
- Keep a timer (phone is fine).

### Where to submit results (after you run tests)
Pick the simplest option available to you:
- **Option A (preferred):** Paste each completed “Test Result” block into a single Notion page titled `Full-Stack Codegen Test Results — <YYYY-MM-DD>` and share the link in the Gaia AI team channel, tagging Darren.
- **Option B (if you’re comfortable with git):** Create a markdown file `koi-research/docs/test-results/<YYYY-MM-DD>-marie.md`, paste all results blocks, and open a PR. Share the PR link in the Gaia AI team channel.

### Preflight prompt (copy/paste)
Use this once at the beginning of a testing session to confirm the stack is working:

```text
Preflight check:
1) Call search for "Registry Agent" (limit 3) and paste the results.
2) Call query_code_graph list_repos and paste the results.
3) If authenticated: Call get_mcp_metrics and paste the results.

For steps 1-2: If either fails, stop and tell me exactly what failed and any error messages.
For step 3: If it fails with "authentication required", that's OK for public data testing - note it and continue.
```

**Note:** `get_mcp_metrics` requires authentication. If you're only testing public data, you can skip it. If you need internal docs or full metrics, authenticate first (ask "can you authenticate me?").

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

### Quality checkboxes (for notes; not a numeric score)
Mark **Y/N** for each:
- **Used indexed knowledge:** referenced specific files/symbols/docs it discovered (not generic advice).
- **Tool reliability:** MCP tool calls succeeded without repeated errors.
- **Safe behavior:** avoided destructive actions; asked before risky steps; no secrets in output.
- **Good handoff:** end-state is clear (what changed, how to run, what to do next).

## Test suite overview

Run the “Core” tests first. If time remains, run “Stretch” tests.

- **Total time estimate**
  - Core only: ~2h40 of test time (plan ~3 hours including setup + breaks)
  - Core + Stretch: add ~2–3 hours (SC-02 adds another 60–90 min if you have a local chain)

- **Vibe coding:** VC-01 to VC-02
- **Network upgrade:** NU-01 to NU-02
- **Smart contract:** SC-01 (optional SC-02)
- **Custom app (indexed code knowledge):** CA-01 to CA-02

---

# Vibe Coding

## VC-01 (Core): “Small feature + unit tests” in a new folder

**Goal:** Natural language → working code + tests with minimal dependencies.

**Timebox:** 20 minutes

**Prompt (copy/paste):**
```text
Create a small, self-contained Python CLI tool in a new folder `scratch/marie-vc-01/` (create the folder if needed).

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
- Creates files under `scratch/marie-vc-01/`
- `python -m unittest` passes
- Output matches requirements

**Common failure modes to note**
- Uses external libs despite instruction
- No tests, or tests don’t run
- CLI can’t parse JSON / crashes

---

## VC-02 (Core): “Fix a real integration mismatch” (MCP tool contract)

**Goal:** See if the agent can notice a real mismatch and propose a concrete fix + verification plan.

**Timebox:** 20 minutes

**Prompt (copy/paste):**
```text
I’m seeing errors where query_code_graph accepts some query types but the backend rejects them (e.g., list_keepers / list_messages / docs_mentioning).

Task:
1) Use get_mcp_metrics and query_code_graph to reproduce at least one failing query_type and capture the exact error.
2) Explain, in plain language, what is mismatched (client schema vs backend support).
3) Propose a concrete fix in the MCP server implementation (what file(s) to change, what to change).
4) Provide a minimal regression test idea that would catch this in CI.

Do NOT make the code change yet—this is an analysis + fix plan only.
```

**Success looks like**
- Reproduces error and quotes it
- Diagnoses mismatch clearly
- Suggests specific code-level fix and a test to prevent regression

**Common failure modes to note**
- Hand-wavy explanation (“something is wrong”) without specifics
- Recommends changing the backend without acknowledging MCP schema validation

---

# Network Upgrade (regen-ledger style work)

## NU-01 (Core): Add a “next upgrade handler” scaffold (local, minimal)

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

## NU-02 (Stretch): Upgrade planning from real upgrade docs (no code)

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

---

# Smart Contract

## SC-01 (Core): Generate a minimal CosmWasm contract + tests

**Goal:** Can it scaffold a contract and provide runnable tests (even if deployment is skipped)?

**Timebox:** 30 minutes

**Prompt (copy/paste):**
```text
Create a new folder `scratch/marie-sc-01/` containing a minimal CosmWasm smart contract called `greeter`:
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

## SC-02 (Stretch): Deploy to a local chain (optional, only if you already have a chain env)

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

## CA-01 (Core): “Basket token helper” mini-app (docs + code-grounded)

**Goal:** Build something small but domain-specific using retrieved docs + code references.

**Timebox:** 30–45 minutes

**Prompt (copy/paste):**
```text
Build a small “basket token helper” in `scratch/marie-ca-01/` as a single Python script + README.

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

## CA-02 (Stretch): Registry Agent “report template generator”

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

# Results template (copy/paste per test)

```md
## Test Result: <TEST_ID> - <Test Name>

- Date:
- Runner:
- Environment (Claude Code / other):
- Authenticated to KOI private docs? (Y/N):
- Start time:
- End time:
- Outcome (Worked=2 / Partial=1 / Failed=0):
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

See `koi-research/docs/eval-framework-design.md:1`.
