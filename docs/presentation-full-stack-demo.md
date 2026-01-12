# Full Stack KOI MCP - Team Presentation Script

> **Duration:** 5-10 minutes
> **Audience:** Sam, Marie, Alexander, Regen team
> **Goal:** Demonstrate "AI assistant with full awareness of Regen tech systems"
> **Presenter:** Darren

---

## Before You Start (Setup)

Have these ready:
1. Terminal with the demo output from `scratch/full-stack-demo/`
2. This script open for reference
3. Team quick-start link ready to share: `koi-research/docs/team-quick-start.md`

---

## SLIDE 1: The Goal (1 min)

### Say:
> "Sam, Marie, and Alexander all mentioned the same goal: an AI assistant with full awareness of Regen tech systems. Today I'll show you what we built and how you can start using it."

### Key points:
- This is the "Full Stack" functionality on the KOI MCP
- Two MCPs working together:
  - **KOI MCP** → Knowledge (48K docs, 31K code entities, internal Notion)
  - **Ledger MCP** → On-chain state (balances, proposals, credits)

### Show install command:
```bash
claude mcp add regen-koi npx regen-koi-mcp@latest
```

> "One line to install. Works in Claude Code, VS Code, Cursor, Warp, and 15+ other tools."

---

## SLIDE 2: Live Demo - The Value-Add (3-4 min)

### Say:
> "Let me show you what this looks like in practice. I asked Claude with KOI to create a technical brief on ecocredit retirement."

### Show the output files:
1. Open `scratch/full-stack-demo/retirement_flow.md`
2. Scroll to the **Code pointers** section
3. Highlight a specific line like:
   > `MsgRetire` → `x/ecocredit/base/types/v1/tx.pb.go:1399`

### Say:
> "This file path and line number came from KOI's code graph - not Claude's training data. Without KOI, Claude would have to guess."

### Show the contrast:
| Without KOI | With KOI |
|-------------|----------|
| Guesses field names like `amount`, `recipient` | Finds actual fields: `owner`, `credits`, `jurisdiction`, `reason` |
| Generic Cosmos advice | Regen-specific code paths |
| No citations | 10+ verifiable file:line references |

### Say:
> "The key insight: every claim is backed by a tool result. We can verify it. That's the difference between helpful advice and grounded engineering documentation."

---

## SLIDE 3: What's Available Now (1 min)

### Say:
> "Here's what you can do with it today."

### Show table:
| Capability | Tool | Try this prompt |
|------------|------|-----------------|
| Search docs/forum/Notion | `search` | "What is the Registry Agent?" |
| Navigate codebase | `query_code_graph` | "Find MsgRetire implementation" |
| On-chain queries | Ledger MCP | "What's in the community pool?" |
| Private docs | `regen_koi_authenticate` | "Authenticate me" then ask about internal docs |

### Say:
> "The search covers forum posts, GitHub docs, Medium articles, Telegram, Discord, and if you authenticate, internal Notion."

---

## SLIDE 4: Quality Assurance (1 min)

### Say:
> "We built automated testing to make sure this keeps working as models and code change."

### Key points:
- **Nightly:** Health checks (is the API up? do searches return correct docs?)
- **Weekly:** Full agent scenarios (can it complete real coding tasks?)
- **Hallucination detection:** Verifies every citation is real

### Show metrics:
| Metric | Result |
|--------|--------|
| KOI vs baseline citations | **3x more** |
| Hallucination rate | **< 5%** (threshold: 20%) |
| Repositories indexed | 8 |
| Code entities | 31,728 |

### Say:
> "We ran A/B tests - same prompt with and without KOI. KOI produces 3x more citations with less than 5% hallucination."

---

## SLIDE 5: Try It Yourself (1 min)

### Say:
> "I want you all to try this. Here's how to get started."

### Share the quick-start:
> "I'll drop a link in chat to `team-quick-start.md` with install instructions and sample prompts."

### Three things to try:
1. **Install:** `claude mcp add regen-koi npx regen-koi-mcp@latest`
2. **Basic test:** "What repositories are indexed in KOI?"
3. **Real task:** "Explain how ecocredit baskets work, with code pointers to x/ecocredit/basket"

### Say:
> "If it can tell you that `MsgPut` is at `x/ecocredit/basket/types/v1/tx.pb.go:1052`, it's working."

---

## SLIDE 6: Next Steps (30 sec)

### Say:
> "Here's the plan from here."

1. **This week:** You try it, report issues in Slack
2. **Next week:** We address feedback
3. **After validation:** Partner rollout

### For Marie specifically:
> "Marie, you mentioned embedding in the Regen App - that's the next phase after we validate the core functionality works well."

### Close:
> "Questions?"

---

## Backup Materials

### If asked "How much does this cost?"
- KOI MCP: Free (we run the backend)
- Ledger MCP: Free (queries public RPC)
- Automated testing: ~$15/month (weekly LLM runs)

### If asked "What models does it work with?"
- Any MCP-compatible client
- Tested with: Claude (all versions), works with Gemini CLI too (Gregory tested)

### If asked "What about private/sensitive data?"
- Public data: Available to everyone
- Private Notion: Requires @regen.network OAuth
- No secrets are exposed through the tools

### Architecture diagram (if needed):
```
┌─────────────────────────────────────────────────────────────┐
│  AI Agent (Claude Code / Claude Desktop / Cursor / etc.)    │
└─────────────────────────┬───────────────────────────────────┘
                          │ MCP (stdio)
          ┌───────────────┴───────────────┐
          ▼                               ▼
┌─────────────────────┐         ┌─────────────────────┐
│  regen-koi MCP      │         │  regen-ledger MCP   │
│  (Knowledge + Code) │         │  (On-chain State)   │
└─────────┬───────────┘         └─────────┬───────────┘
          │                               │
          ▼                               ▼
┌─────────────────────┐         ┌─────────────────────┐
│  KOI API Backend    │         │  Regen Ledger RPC   │
│  48K docs, 31K code │         │  (Cosmos SDK)       │
└─────────────────────┘         └─────────────────────┘
```

---

## Links to Share

- **Quick Start:** `koi-research/docs/team-quick-start.md`
- **Full User Guide:** `regen-koi-mcp/docs/USER_GUIDE.md`
- **Test Protocol (for deeper testing):** `koi-research/docs/test-protocol-full-stack.md`
- **GitHub:** https://github.com/gaiaaiagent/regen-koi-mcp
