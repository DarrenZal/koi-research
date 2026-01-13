# KOI MCP Testing Infrastructure - Demo Script

> **Duration:** 3-5 minutes
> **Format:** Screen share, no slides

---

## Setup (before call)

Open these tabs:
1. https://github.com/DarrenZal/koi-research/actions (CI Dashboard)
2. https://github.com/gaiaaiagent/regen-koi-mcp (KOI MCP repo)

---

## Script

### Step 1: Context (30 sec)

**Say:**
> "From the Jan 6 meeting, I had two deliverables: a test protocol and an eval framework. Quick context - KOI gives Claude access to forum discussions, internal Notion, and on-chain state. The question is: how do we know it works?"

---

### Step 2: Show CI Dashboard (30 sec)

**Do:** Show https://github.com/DarrenZal/koi-research/actions

**Say:**
> "We have automated tests running nightly. Green means the system is healthy - search works, code graph works, no regressions."

**Point out:** Latest run status (green/red)

---

### Step 3: Test Protocol (1 min)

**Do:** Open https://github.com/DarrenZal/koi-research/blob/regen-prod/docs/test-protocol-full-stack.md

**Say:**
> "For manual testing, we have a structured protocol. Two tiers - Tier 1 anyone can run, Tier 2 needs dev environment. Each test has an exact prompt to copy/paste and a scoring rubric."

**Scroll to show:** A test example (e.g., VC-01), the scoring section

**Say:**
> "The ask: run one test, submit feedback using the `submit_feedback` tool or paste results in Slack."

---

### Step 4: How to Install (30 sec)

**Do:** Open https://github.com/gaiaaiagent/regen-koi-mcp

**Say:**
> "Installation is one command."

**Point to README:**
```
claude mcp add regen-koi npx regen-koi-mcp@latest
```

---

### Step 5: Next Steps (30 sec)

**Say:**
> "This week: team runs manual tests. Next week: we fix what breaks. After that: partner rollout."

**Paste in chat:**
```
Install: claude mcp add regen-koi npx regen-koi-mcp@latest
Guide: https://github.com/gaiaaiagent/regen-koi-mcp/blob/main/docs/FULL_STACK_USER_GUIDE.md
Test Protocol: https://github.com/DarrenZal/koi-research/blob/regen-prod/docs/test-protocol-full-stack.md
```

**Say:**
> "Questions?"

---

## If Asked

**"What does KOI add vs plain Claude?"**
> Forum discussions, internal Notion, on-chain state, cross-repo code search. It's organizational memory.

**"How do I report bugs?"**
> Easiest: use `submit_feedback` in Claude Code. Or post in Slack.

**"What's the cost?"**
> Free to use. Automated testing is ~$15/month.

**"What got fixed recently?"**
> Call graph queries now work. `keeper_for_msg` returns results. 11K+ CALLS edges in the graph.

---

## Links

| Resource | URL |
|----------|-----|
| KOI MCP Repo | https://github.com/gaiaaiagent/regen-koi-mcp |
| User Guide | https://github.com/gaiaaiagent/regen-koi-mcp/blob/main/docs/FULL_STACK_USER_GUIDE.md |
| Test Protocol | https://github.com/DarrenZal/koi-research/blob/regen-prod/docs/test-protocol-full-stack.md |
| CI Dashboard | https://github.com/DarrenZal/koi-research/actions |
