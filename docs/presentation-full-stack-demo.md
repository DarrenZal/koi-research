# KOI MCP Testing Infrastructure - Team Demo

> **Duration:** 5-10 minutes
> **Audience:** Sam, Marie, Alexander, Regen team
> **Deliverables from Jan 6 meeting:**
> 1. Design test protocol for code generation capability
> 2. Design ongoing eval testing framework for MCP stack
> **Presenter:** Darren
> **Format:** Screen sharing (no slides)

---

## Before You Start (Setup)

Have these browser tabs ready:
1. **CI Dashboard:** https://github.com/DarrenZal/koi-research/actions
2. **Test Protocol:** https://github.com/DarrenZal/koi-research/blob/regen-prod/docs/test-protocol-full-stack.md
3. **Eval Framework:** https://github.com/DarrenZal/koi-research/blob/regen-prod/docs/eval-framework-design.md
4. **User Guide:** https://github.com/gaiaaiagent/regen-koi-mcp/blob/main/docs/FULL_STACK_USER_GUIDE.md

Optional: Terminal with Claude Code ready for live demo

---

## DEMO 1: Context - What We're Testing (1 min)

### Say:
> "From the Jan 6 meeting, I had two deliverables: design a test protocol for code generation, and design an ongoing eval framework. Here's what we built."

### Context on KOI value-add:
> "Quick context on why this matters: Claude Code can read local repos. But KOI provides access to everything else - forum discussions, internal Notion, community channels, and on-chain state. It's organizational memory, not just code search."

### The question we're answering:
> "How do we know it actually works? And how do we catch it when it breaks?"

---

## DEMO 2: Deliverable 1 - Test Protocol (2 min)

### Say:
> "First deliverable: a structured test protocol for humans to run."

### Show on screen:
**Open:** https://github.com/DarrenZal/koi-research/blob/regen-prod/docs/test-protocol-full-stack.md

Scroll through the document as you explain:

### Structure:
| Tier | Tests | Who runs it | What it tests |
|------|-------|-------------|---------------|
| **Tier 1 (Portable)** | VC-01, VC-02, CA-01, CA-02, NU-02 | Anyone with Claude Code | Can it generate code + use KOI tools? |
| **Tier 2 (Dev env)** | NU-01, SC-01, SC-02 | Engineers with Go/Rust | Can it work in real regen-ledger? |
| **Delta (A/B)** | KV-01, KV-02, KV-03 | Anyone | Does KOI add value vs baseline Claude? |

### Key features:
- **Exact prompts to copy/paste** - no ambiguity
- **Scoring rubric** - Worked (2), Partial (1), Failed (0)
- **Hallucination awareness** - every test requires citations
- **Phased rollout** - 3-4 testers first (Marie, Dave, Becca, Gregory), then broader team

### Say:
> "The protocol is designed so non-engineers can run tests and produce actionable feedback. Just copy the prompt, run it, fill out the result template."

---

## DEMO 3: Deliverable 2 - Eval Framework (2 min)

### Say:
> "Second deliverable: automated testing that runs continuously. Because as Zach said, 'systems are weird and non-deterministic - small changes can break things.'"

### Show on screen:
**Open:** https://github.com/DarrenZal/koi-research/blob/regen-prod/docs/eval-framework-design.md

Scroll through as you explain:

### The suites:
| Suite | What it tests | How it runs | Cost |
|-------|---------------|-------------|------|
| **A: Contract** | MCP schema matches backend | HTTP calls | Free |
| **B: Retrieval** | Search returns correct docs | HTTP calls + golden queries | Free |
| **C: Health** | API is responding | HTTP preflight | Free |
| **D: Agent** | Claude can complete real tasks | Claude Agent SDK | ~$2/run |
| **D Delta** | KOI adds value vs baseline | A/B comparison | ~$1.65/run |

### Schedule:
- **Nightly (2am UTC):** Suites A/B/C (free health checks)
- **Weekly (Sunday 6am):** Full suite including D (LLM-based, ~$3.62)
- **On-demand:** Manual trigger anytime

### Say:
> "The expensive LLM tests run weekly to save costs - about $15/month instead of $109. But we can trigger manually anytime we push changes."

---

## DEMO 4: Hallucination Detection (1 min)

### Show on screen:
Stay on the eval-framework doc, scroll to the hallucination section, or show a terminal with a recent test output.

### Say:
> "A key part of the framework: we verify every citation the agent produces."

### How it works:
```
Agent output: "MsgRetire is at x/ecocredit/base/types/v1/tx.pb.go:1399"
                                    ↓
Verification: Does that file exist? Does line 1399 contain MsgRetire?
                                    ↓
Result: verified ✓ or hallucinated ✗
```

### Metrics from latest run:
| Metric | Result | Threshold |
|--------|--------|-----------|
| Hallucination rate | **< 5%** | 20% |
| Citations (KOI vs baseline) | **3x more** | - |
| Verified citations | **95%+** | - |

### Say:
> "This is how we prove KOI produces grounded answers, not hallucinations. Every citation is checked against real files and the knowledge graph."

---

## DEMO 5: Results - It's Working (1 min)

### Show on screen:
**Open:** https://github.com/DarrenZal/koi-research/actions

Click into the latest successful run to show the green checkmarks.

### Say:
> "We ran the full suite. Here's what we found."

### Latest CI results:
| Test | Status |
|------|--------|
| Preflight (API health) | ✅ Pass |
| Suite B (Retrieval) | ✅ Pass |
| Suite D Delta KV-01 (Baskets A/B) | ✅ Green |
| Suite D Delta KV-02 (Upgrades A/B) | ✅ Green |
| Hallucination rate | ✅ < 5% |

### Live demo result:
> "I ran a manual test: 'Create a technical brief on ecocredit retirement with code pointers.' It produced 225 lines with 10+ verified file:line citations."

### Say:
> "The infrastructure is working. Now we need the team to run manual tests and find edge cases the automation misses."

---

## DEMO 6: How You Participate (1 min)

### Show on screen:
**Open:** https://github.com/gaiaaiagent/regen-koi-mcp/blob/main/docs/FULL_STACK_USER_GUIDE.md

Show the install command and test prompts.

### Say:
> "Here's how each of you can help validate this."

### For everyone:
1. **Install:** `claude mcp add regen-koi npx regen-koi-mcp@latest`
2. **Run one Tier 1 test** from the protocol (takes 20 min)
3. **Submit feedback directly:** Use the new `submit_feedback` tool in Claude Code
4. **Or report in Slack** or the Notion page

### Specific asks:
| Person | Ask |
|--------|-----|
| **Marie** | Run VC-01 and CA-01, focus on code generation quality |
| **Dave** | Test from Web2 user perspective - is the journey clear? |
| **Becca** | Ask hardest technical questions, document what breaks |
| **Gregory** | Already tested with Gemini CLI ✓ |

### Say:
> "The protocol has exact prompts and a scoring template. Just copy/paste and fill it out. I'll collect results and we'll iterate."

---

## DEMO 7: Next Steps (30 sec)

### Say:
> "Here's the plan."

| Timeline | Action |
|----------|--------|
| **This week** | Team runs manual tests, reports issues |
| **Next week** | Address feedback, fix gaps |
| **After validation** | Partner rollout with specific asks |

### Paste in chat/Slack:
```
Full Stack Guide: https://github.com/gaiaaiagent/regen-koi-mcp/blob/main/docs/FULL_STACK_USER_GUIDE.md
Test Protocol: https://github.com/DarrenZal/koi-research/blob/regen-prod/docs/test-protocol-full-stack.md
CI Dashboard: https://github.com/DarrenZal/koi-research/actions
```

### Close:
> "Questions?"

### Optional live demo:
If time permits, show Claude Code with KOI MCP:
```bash
# In terminal
claude
> What repositories are indexed in KOI?

# Show the new feedback tool (full stack demo)
> Submit feedback: rating 5, category success, notes "Demo went well!"
```

This demonstrates the full stack: MCP tool → Backend API → PostgreSQL → Confirmation.

---

## Backup: FAQ

### "What's the difference between manual tests and automated?"
- **Manual:** Humans discover new failure modes, test edge cases
- **Automated:** CI catches regressions, ensures known-good scenarios don't break
- Manual tests get "promoted" to automated once we know they're important

### "How much does this cost?"
- KOI MCP: Free to use (we run the backend)
- Automated testing: ~$15/month (weekly LLM runs)
- Manual testing: Uses your normal Claude Code credits

### "What if I find a bug?"
- **Easiest:** Use `submit_feedback` directly in Claude Code - it captures session context automatically
- Or post in Slack with the prompt you used and what happened
- Bonus: fill out the test result template from the protocol

### "What about the Regen App embedding Marie mentioned?"
- That's next phase, after we validate core functionality
- Created as feature request on the repo

---

## Links

| Resource | Location |
|----------|----------|
| **Full Stack Guide** | [regen-koi-mcp/docs/FULL_STACK_USER_GUIDE.md](https://github.com/gaiaaiagent/regen-koi-mcp/blob/main/docs/FULL_STACK_USER_GUIDE.md) |
| **Test Protocol** | [koi-research/docs/test-protocol-full-stack.md](https://github.com/DarrenZal/koi-research/blob/regen-prod/docs/test-protocol-full-stack.md) |
| **Eval Framework Design** | [koi-research/docs/eval-framework-design.md](https://github.com/DarrenZal/koi-research/blob/regen-prod/docs/eval-framework-design.md) |
| **CI Dashboard** | https://github.com/DarrenZal/koi-research/actions |
| **KOI MCP GitHub** | https://github.com/gaiaaiagent/regen-koi-mcp |
