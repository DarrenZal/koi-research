# MCP vs. Skills: Architecture Analysis for Regen AI

> **Origin**: Investigation into Agent Skills (agentskills.io) as an alternative/complement to MCP (Model Context Protocol), prompted by industry criticism that "MCP is broken" and Anthropic's introduction of Skills.
>
> **Status**: Analysis / Architecture Recommendation
>
> **Related**: regen-koi-mcp, regen-python-mcp, networked-knowledge-agents-via-koi.md

---

## Executive Summary

Our current MCP implementation provides powerful capabilities but suffers from the core architectural problem affecting most MCP deployments: **context bloat**. With 61+ tools across two servers, every interaction loads metadata for all tools regardless of relevance.

**Recommendation**: Adopt a **Skills-as-orchestration-layer** pattern where Skills sit in front of MCP. This preserves our MCP infrastructure investment while gaining progressive disclosure and better token efficiency.

**Critical caveat**: This recommendation depends on assumptions about how Claude Code handles MCP tool loading when Skills are active. See [Assumptions & Risks](#11-assumptions--risks) for details.

---

## 1. Why We Use MCP

### Our Goals

The Regen AI ecosystem aims to:

1. **Democratize access to ecological data**: Make Regen Network's blockchain state, credit markets, and governance queryable by AI agents
2. **Surface organizational knowledge**: Expose the KOI knowledge graph (165K+ triples, 48K+ documents) to AI assistants
3. **Enable cross-platform interoperability**: Support Claude, VSCode, Cursor, and any MCP-compatible client
4. **Maintain data sovereignty**: Keep sensitive data in our infrastructure while exposing controlled interfaces

### Why MCP Made Sense

MCP (Model Context Protocol) was the right choice because:

| Requirement | MCP Solution |
|-------------|--------------|
| Cross-platform support | Standard protocol supported by Claude, Cursor, VSCode, etc. |
| Tool-based interface | Natural fit for blockchain queries and search operations |
| Local execution | Stdio transport keeps data flow under our control |
| Extensibility | Easy to add new tools as capabilities grow |

### The Client-Server Model

Our MCP servers act as **clients to backend services**, not as passive tool repositories:

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Claude / AI Agent                            │
│                    (MCP Client - Tool Consumer)                      │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   │ MCP Protocol (stdio)
                                   │ JSON-RPC 2.0
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        MCP Server Layer                              │
│  ┌─────────────────────────┐   ┌─────────────────────────┐         │
│  │     regen-koi-mcp       │   │   regen-python-mcp      │         │
│  │     (TypeScript)        │   │      (Python)           │         │
│  │                         │   │                         │         │
│  │  - 16 tools             │   │  - 45+ tools            │         │
│  │  - Knowledge search     │   │  - Blockchain queries   │         │
│  │  - Code graph           │   │  - Governance           │         │
│  │  - Entity resolution    │   │  - Marketplace          │         │
│  │  - SPARQL queries       │   │  - Analytics            │         │
│  └─────────────────────────┘   └─────────────────────────┘         │
└─────────────────────────────────────────────────────────────────────┘
          │                                    │
          │ HTTP (axios)                       │ HTTP (httpx async)
          ▼                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       Backend Services                               │
│  ┌─────────────────────────┐   ┌─────────────────────────┐         │
│  │     KOI API Server      │   │   Regen LCD/RPC Nodes   │         │
│  │  (regen.gaiaai.xyz)     │   │   (Polkachu, Cosmos)    │         │
│  │                         │   │                         │         │
│  │  - PostgreSQL + pgvector│   │  - Cosmos SDK REST      │         │
│  │  - Apache Jena Fuseki   │   │  - Tendermint RPC       │         │
│  │  - Apache AGE (graphs)  │   │  - gRPC endpoints       │         │
│  │  - BGE embeddings       │   │                         │         │
│  └─────────────────────────┘   └─────────────────────────┘         │
└─────────────────────────────────────────────────────────────────────┘
```

**Key insight**: Our MCP servers are not simple tool wrappers. They are sophisticated clients with:

- **Retry logic**: Exponential backoff with jitter for transient failures
- **Circuit breakers**: Prevent cascading failures after N consecutive errors
- **Caching**: LRU (koi-mcp) and Redis-compatible (python-mcp) caching
- **Validation**: Zod schemas (TypeScript) and Pydantic models (Python)
- **Multi-endpoint failover**: Automatic fallback across RPC/REST endpoints
- **Pagination helpers**: `fetch_all_pages()` to eliminate agent loops

This is why simply replacing MCP with Skills would lose significant engineering investment.

---

## 2. Current MCP Architecture

### regen-koi-mcp (TypeScript/Node.js)

**Focus**: Knowledge discovery - semantic search, code graphs, entity resolution

```
regen-koi-mcp/
├── src/
│   ├── index.ts              # MCP server entry point (stdio transport)
│   ├── tools.ts              # 16 tool definitions (schemas + descriptions)
│   ├── graph_tool.ts         # Code knowledge graph query handler
│   ├── graph_client.ts       # Apache AGE abstraction layer
│   ├── sparql-client-enhanced.ts  # SPARQL query handler
│   ├── cache.ts              # LRU caching with configurable TTL
│   ├── validation.ts         # Zod input validation schemas
│   ├── auth.ts               # OAuth token management
│   ├── metrics.ts            # Performance monitoring
│   ├── resilience.ts         # Retry logic, timeouts, circuit breakers
│   └── logger.ts             # Pino structured logging
├── package.json              # npm metadata + dependencies
└── .mcp.json                 # MCP server configuration
```

**16 Tools**:
- Knowledge Base: `search`, `get_stats`, `generate_weekly_digest`
- Code Graph: `query_code_graph` (17 query types)
- Entity Resolution: `resolve_entity`, `get_entity_neighborhood`, `get_entity_documents`
- GitHub Docs: `search_github_docs`, `get_repo_overview`, `get_tech_stack`
- SPARQL/RDF: `sparql_query`, `resolve_metadata_iri`, `derive_offchain_hectares`
- RID Tools: `parse_rid`, `kb_rid_lookup`, `kb_list_rids`
- Utility: `get_mcp_metrics`, `regen_koi_authenticate`

### regen-python-mcp (Python/FastMCP)

**Focus**: Blockchain queries - on-chain state, governance, credits, marketplace

```
regen-python-mcp/
├── main.py                              # Entry point
├── src/mcp_server/
│   ├── server.py                        # FastMCP server (45+ tools)
│   ├── client/
│   │   └── regen_client.py              # HTTP client with retry/failover
│   ├── tools/
│   │   ├── bank_tools.py                # 11 tools (accounts, balances)
│   │   ├── distribution_tools.py        # 9 tools (validator rewards)
│   │   ├── governance_tools.py          # 8 tools (proposals, votes)
│   │   ├── marketplace_tools.py         # 5 tools (sell orders)
│   │   ├── credit_tools.py              # 4 tools (credit types, classes)
│   │   ├── basket_tools.py              # 5 tools (basket operations)
│   │   └── analytics_tools.py           # 3 tools (portfolio, trends)
│   └── prompts/                         # 8 interactive workflows
├── pyproject.toml                       # Python packaging
└── .mcp.json                            # MCP server configuration
```

**45+ Tools** organized by Cosmos SDK module:
- Bank: Account balances, token supplies, metadata
- Distribution: Validator rewards, delegator info, community pool
- Governance: Proposals, votes, deposits, tallies
- Marketplace: Sell orders, pricing, allowed denominations
- Ecocredits: Credit types, classes, projects, batches
- Baskets: Basket creation, balances, fees
- Analytics: Portfolio impact, market trends, methodology comparison

### Combined Tool Surface

| Server | Tools | Prompts | Total Context Load |
|--------|-------|---------|-------------------|
| regen-koi-mcp | 16 | 0 | ~2,400 tokens |
| regen-python-mcp | 45+ | 8 | ~6,800 tokens |
| **Total** | **61+** | **8** | **~9,200 tokens** |

Every interaction pays this context cost upfront, regardless of task relevance.

---

## 3. The MCP Problem

### Industry Criticism

Multiple sources have identified fundamental issues with MCP as commonly implemented:

#### "MCP Is Broken" (Cordero Core, Medium)

> "MCP works beautifully in demos and breaks the moment you try to scale it... The clean interface turns into a firehose—every tool schema gets stuffed into the context window up front."

#### "98% of MCP Servers Got This Wrong" (HackerNoon)

> "Production systems work only with extremely limited toolsets of 3-5 tools maximum. Anything beyond that creates immediate context problems."

Key problems identified:
- **Context efficiency crisis**: LLMs are pattern-matching machines, not databases. More tools = more noise
- **Poor implementation standards**: Only ~2% of MCP servers include OAuth, state management, observability
- **Scalability limits**: Beyond 3-5 tools, context overhead overwhelms useful signal

#### What Anthropic "Admitted"

When Anthropic introduced Skills, Cordero Core observed:

> "Instead of saying 'MCP is broken,' Anthropic changed how the model meets MCP. **Skills sit in front, MCP sits behind.** This pattern is RAG applied to tool access—progressive disclosure rather than upfront loading."

### How This Applies to Us

With **61+ tools**, we are well beyond the "3-5 tools maximum" recommended for production systems. Our MCP implementation is technically excellent (retry logic, caching, validation) but architecturally vulnerable to context bloat.

---

## 4. What Are Agent Skills?

### Definition

**Agent Skills** are a lightweight, open format for extending AI agent capabilities. At their core:

- A folder containing a `SKILL.md` file with metadata and instructions
- Optional scripts, templates, and reference materials
- Progressive disclosure: metadata loaded at startup, full content on demand

### SKILL.md Format (Claude Code)

**Important**: Claude Code has specific YAML fields that control tool access and context isolation. The `allowed-tools` field is **configuration**, not just documentation—it actually restricts which tools the skill can use.

**Portability note**: `allowed-tools` and `context: fork` are **Claude Code-specific extensions**. Other clients (Cursor, VSCode, generic MCP clients) may ignore these fields. If cross-client portability is critical, rely on the alternatives in Section 12 rather than Claude Code-specific features.

```yaml
---
name: blockchain-explorer
description: Query Regen blockchain for accounts, balances, governance proposals,
  credit batches, and marketplace data. Use when user asks about on-chain state,
  validators, staking, or ecological credits.
allowed-tools:
  - mcp__plugin_ledger_regen-network__get_balance
  - mcp__plugin_ledger_regen-network__get_all_balances
  - mcp__plugin_ledger_regen-network__list_governance_proposals
  - mcp__plugin_ledger_regen-network__get_governance_vote
  - mcp__plugin_ledger_regen-network__list_credit_batches
  - mcp__plugin_ledger_regen-network__list_projects
  - mcp__plugin_ledger_regen-network__list_sell_orders
context: fork  # Run in isolated sub-agent to keep main conversation clean
license: Apache-2.0
metadata:
  author: regen-network
  version: "1.0"
---

# Blockchain Explorer

## When to use
- User asks about account balances or token holdings
- User wants governance proposal status or voting info
- User needs credit batch, project, or marketplace data

## Workflow
1. Identify what blockchain data is needed
2. Call the specific MCP tool(s) from allowed-tools
3. Synthesize results for the user

## Notes
- Tools are restricted via `allowed-tools` frontmatter
- Runs in forked context to avoid polluting main conversation
```

**Key YAML fields**:

| Field | Purpose | Required |
|-------|---------|----------|
| `name` | Skill identifier (lowercase, hyphens only, max 64 chars) | Yes |
| `description` | When to use this skill (max 1024 chars, include keywords) | Yes |
| `allowed-tools` | **Restricts** which tools the skill can use without permission | No (but recommended) |
| `context: fork` | Run skill in isolated sub-agent context | No (but recommended for heavy skills) |
| `license` | License for the skill | No |
| `metadata` | Arbitrary key-value pairs | No |

### Progressive Disclosure (Three-Stage Loading)

| Stage | What Loads | When | Token Cost |
|-------|------------|------|------------|
| **Discovery** | `name` + `description` only | Startup | ~50-100 per skill |
| **Activation** | Full `SKILL.md` body | Task matches skill | ~500-2000 |
| **Execution** | Scripts, references, assets | On demand | Variable |

**Key benefit**: 7 skills at ~100 tokens each = 700 tokens at startup vs. 9,200 tokens for 61 tools.

### Industry Adoption

Skills are supported by:
- Claude Code, Claude Desktop
- Cursor, VSCode
- OpenAI Codex
- Goose, Amp, Letta
- GitHub Copilot
- Factory

---

## 5. Skills vs. MCP: Technical Comparison

| Aspect | MCP | Skills |
|--------|-----|--------|
| **Purpose** | Access external tools/data | Encode procedural knowledge + workflows |
| **Activation** | Explicit invocation by agent | Automatic detection by relevance |
| **Token cost** | High (all schemas upfront) | Low (progressive disclosure) |
| **Setup** | Server configuration | Markdown + optional code |
| **Best for** | Real-time data, external APIs | Internal workflows, domain expertise |
| **Context management** | None (all or nothing) | Tiered (metadata → instructions → resources) |

### Complementary, Not Competitive

The consensus from [IntuitionLabs comparison](https://intuitionlabs.ai/articles/claude-skills-vs-mcp):

> "Use MCP to connect to GitHub/CI, then create Skills for analyzing build trends and generating reports. MCP servers fetch live data; Skills interpret and process that data according to domain logic."

This is exactly our situation:
- **MCP**: Fetch blockchain state, query knowledge graph
- **Skills**: Interpret results, guide workflows, manage context

---

## 6. Recommended Architecture

### Skills as Orchestration Layer

```
User Request
    │
    ▼
┌───────────────────────────────────────────────────────────────────┐
│          Skills Layer (Progressive Disclosure)                     │
│                                                                    │
│  At startup: Only skill metadata loaded (~700 tokens)              │
│                                                                    │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ │
│  │ blockchain- │ │ knowledge-  │ │ ecocredit-  │ │ marketplace-│ │
│  │ explorer    │ │ search      │ │ analyst     │ │ investigator│ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘ │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐                  │
│  │ code-       │ │ knowledge-  │ │ cleanup-    │                  │
│  │ explorer    │ │ graph-expert│ │ and-push    │                  │
│  └─────────────┘ └─────────────┘ └─────────────┘                  │
│                                                                    │
│  When task matches: Full skill instructions loaded (~1500 tokens)  │
└───────────────────────────────────────────────────────────────────┘
    │
    │ Skill determines which MCP tools to invoke
    ▼
┌───────────────────────────────────────────────────────────────────┐
│          MCP Servers (Backend Infrastructure)                      │
│                                                                    │
│  Tools loaded on-demand, not all at once                          │
│                                                                    │
│  ┌─────────────────────────┐   ┌─────────────────────────┐       │
│  │     regen-koi-mcp       │   │   regen-python-mcp      │       │
│  │     (16 tools)          │   │     (45+ tools)         │       │
│  │                         │   │                         │       │
│  │  Invoked by skills:     │   │  Invoked by skills:     │       │
│  │  - knowledge-search     │   │  - blockchain-explorer  │       │
│  │  - code-explorer        │   │  - ecocredit-analyst    │       │
│  │  - knowledge-graph-expert│   │  - marketplace-invest.  │       │
│  └─────────────────────────┘   └─────────────────────────┘       │
└───────────────────────────────────────────────────────────────────┘
    │
    ▼
Backend Services (KOI API, Regen Blockchain)
```

### Proposed Skill Portfolio

Based on our MCP capabilities, we should create 7 domain-specific skills:

| Skill | Purpose | MCP Tools Used | Context |
|-------|---------|----------------|---------|
| `blockchain-explorer` | On-chain state queries | bank_*, distribution_*, get_account | fork |
| `ecocredit-analyst` | Credit ecosystem analysis | credit_*, basket_*, analyze_portfolio_impact | fork |
| `marketplace-investigator` | Market dynamics | marketplace_*, list_sell_orders, analyze_market_trends | fork |
| `knowledge-search` | Semantic search, entity resolution | search, resolve_entity, get_entity_* | normal |
| `code-explorer` | Code graph, repo structure | query_code_graph, get_repo_overview, get_tech_stack | normal |
| `knowledge-graph-expert` | SPARQL queries, RDF triples, entity relationships, RIDs | sparql_query, resolve_metadata_iri, parse_rid, kb_* | fork |
| `cleanup-and-push` | Cross-repo maintenance | Bash, Read, Edit, Glob, Grep | normal |

**Naming rationale**: Skills use noun-based domain names (not action words) to help the LLM semantic matcher trigger correctly. "Knowledge Graph Expert" triggers on "entities," "relationships," "graph data," "triples" better than "Regen Research."

### Context Efficiency Comparison

| Approach | Startup Cost | Per-Task Cost | Main Context Impact | Notes |
|----------|--------------|---------------|---------------------|-------|
| Current (pure MCP) | ~9,200 tokens | ~0 | ~9,200 tokens | All tool schemas loaded |
| Skills + MCP (normal context) | ~700 tokens | ~1,500-2,000 | ~2,200-2,700 tokens | Skill instructions in main context |
| Skills + MCP (context: fork) | ~700 tokens | ~0 (isolated) | ~700 tokens + summary | Heavy skills run in sub-agent |

**Token measurement methodology**: Estimates based on tool schema character counts converted to tokens (~4 chars/token). Actual values vary by client implementation. Measure empirically in your environment.

**With `context: fork`**: Heavy skills (blockchain-explorer, ecocredit-analyst, knowledge-graph-expert) run in isolated sub-agents. The main conversation only sees the returned summary, not the full skill execution context. This can reduce main context impact to near-zero for complex operations.

---

## 7. Implementation Plan

### Phase 1: Create Skill Directory Structure

**Critical**: Skills must be in `.claude/skills/` for automatic discovery by Claude Code.

```
.claude/skills/
├── blockchain-explorer/
│   └── SKILL.md
├── ecocredit-analyst/
│   └── SKILL.md
├── marketplace-investigator/
│   └── SKILL.md
├── knowledge-search/
│   └── SKILL.md
├── code-explorer/
│   └── SKILL.md
├── knowledge-graph-expert/
│   └── SKILL.md
└── cleanup-and-push/
    └── SKILL.md    # (convert existing .claude/commands/ version)
```

**Note**: No additional configuration needed in `.claude/settings.json` for skill discovery—Claude Code automatically discovers skills in `.claude/skills/`.

### Phase 2: Create Tool Index for Sync

To prevent drift (skills listing tools that have changed), create a tool index.

**Tool name caveat**: Tool names vary by client context. The MCP server exposes short names (e.g., `get_balance`), but Claude Code may namespace them (e.g., `mcp__plugin_ledger_regen-network__get_balance`). Always verify the exact names visible in your client session before populating `allowed-tools`.

**Option A: Query from running Claude Code session**
```bash
# In Claude Code, check available tools
# Use whatever debug/inspection mechanism is current (CLI flags, /debug command, etc.)
# Look for the exact tool name format used in your environment
```

**Option B: Export from MCP servers directly** (requires build/venv setup)
```bash
# regen-koi-mcp (after running: npm run build)
cd regen-koi-mcp && node -e "require('./dist/tools.js').TOOLS.forEach(t => console.log(t.name))"

# regen-python-mcp (from activated venv with PYTHONPATH set)
cd regen-python-mcp && python -c "from src.mcp_server.server import mcp; [print(t.name) for t in mcp.list_tools()]"
```

**Option C: Use MCP protocol introspection**
```bash
# If your MCP server supports stdio, query tools/list directly
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | npx regen-koi-mcp@latest
```

Update skill `allowed-tools` when tool indexes change. Consider automating via pre-commit hook or CI check.

### Phase 3: Test MCP Tool Loading Behavior

**This is the critical unknown.** Before full rollout, verify:

1. Does enabling Skills change how MCP tool schemas are loaded?
2. Does `allowed-tools` in a skill reduce the tool schemas sent to the model?
3. Or does `enableAllProjectMcpServers: true` still load all 61 tools regardless?

**Test method**: Use whatever Claude Code debug/prompt-inspection mechanism is current (environment variables, CLI flags, `/debug` command, or prompt logging). The specific mechanism may change—check current documentation.

**Concrete success criteria (pass/fail)**:

| Metric | Baseline (no Skills) | Target (with Skills) | Pass Threshold |
|--------|---------------------|----------------------|----------------|
| Tool schemas in context | ~61 tools (~9,200 tokens) | ≤10 relevant tools | ≤15 tools on typical task |
| Startup context tokens | ~9,200 | ~700 (skill metadata only) | ≤1,500 tokens |
| Tool-call accuracy | Measure baseline | No regression | ≥95% of baseline |
| Skill match rate | N/A | Correct skill activates | ≥90% on test queries |

**Test queries** (should each activate different skills):
- "What's the REGEN balance for regen1xyz..." → blockchain-explorer
- "Search for documents about carbon credits" → knowledge-search
- "Show me the entity relationships for Gregory Landua" → knowledge-graph-expert
- "List active sell orders" → marketplace-investigator

If Skills do NOT reduce tool schema loading (first two metrics fail), proceed to Phase 4 alternatives.

### Phase 4: Optimize or Restructure

Based on Phase 3 results:

**If Skills DO gate MCP tools**: Proceed with skill refinement:
- Add `references/` directories for detailed documentation
- Add `scripts/` for complex workflows
- Tune skill descriptions for better semantic matching

**If Skills do NOT gate MCP tools**: Implement one of the alternatives from Section 12.

---

## 8. What to Keep, What to Change

### Keep (MCP Infrastructure)

- Both MCP servers as backend infrastructure
- All 61+ tools (they're the capability layer)
- Retry logic, caching, validation, circuit breakers
- Multi-endpoint failover
- Current deployment model (npx for koi-mcp, uv for python-mcp)

### Add (Skills Layer)

- 7 domain-specific skills wrapping MCP tool groups
- Progressive disclosure for context efficiency
- Better discoverability via skill descriptions
- Cross-agent compatibility (works in Claude, Cursor, VSCode, etc.)

### Migrate (Commands to Skills)

- Convert `.claude/commands/cleanup-and-push.md` to formal `SKILL.md` format
- Convert other commands as appropriate

---

## 9. MCP Prompts vs. Skills

Our `regen-python-mcp` server already has 8 MCP prompts. These are **different mechanisms** from Skills:

| Aspect | MCP Prompts | Skills |
|--------|-------------|--------|
| **Location** | Defined in MCP server code | `.claude/skills/SKILL.md` files |
| **Invocation** | Explicit slash command (`/mcp__servername__promptname`) | Automatic (Claude matches task to skill description) |
| **Discovery** | Dynamic from connected MCP servers | Static from filesystem |
| **Arguments** | Can accept runtime arguments | Fixed instructions |
| **Control** | Server-side | Client-side |

### Current MCP Prompts (regen-python-mcp)

```
/mcp__plugin_ledger_regen-network__chain_exploration
/mcp__plugin_ledger_regen-network__ecocredit_query_workshop
/mcp__plugin_ledger_regen-network__marketplace_investigation
/mcp__plugin_ledger_regen-network__project_discovery
/mcp__plugin_ledger_regen-network__credit_batch_analysis
/mcp__plugin_ledger_regen-network__list_regen_capabilities
/mcp__plugin_ledger_regen-network__query_builder_assistant
/mcp__plugin_ledger_regen-network__methodology_comparison
```

### Consolidation vs. Layering

**Option A: Consolidation** - Replace MCP prompts with Skills
- Simpler mental model (one mechanism)
- Skills offer `context: fork` isolation
- But loses dynamic server-side control

**Option B: Layering** - Keep both, use for different purposes
- MCP prompts = quick interactive workflows (user explicitly invokes)
- Skills = automatic domain expertise (Claude decides when to use)
- More complex, but more flexible

**Recommendation**: Start with layering. Keep MCP prompts for explicit user-driven workflows. Use Skills for automatic domain matching. Consolidate later if redundancy becomes confusing.

---

## 10. Relationship to KOI-net Architecture

This Skills + MCP pattern aligns with the KOI-net architecture described in `networked-knowledge-agents-via-koi.md`:

```
┌─────────────────────────────────────────────────────────────────┐
│                        KOI Network                               │
│                                                                  │
│  Skills define the "how" of knowledge access                     │
│  MCP provides the "what" (tools/data)                           │
│  KOI-net handles the "where" (discovery, routing, permissions)  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    Skills Layer                           │   │
│  │   (Domain expertise, workflow orchestration)              │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              │                                   │
│                              ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    MCP Servers                            │   │
│  │   (Tool execution, data access)                           │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              │                                   │
│                              ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                 KOI-net Protocol                          │   │
│  │   (Node coordination, RIDs, events, permissions)          │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

From the KOI-net interoperability section:

> "MCP is the LLM interface: Human users interact via MCP-enabled interfaces (Claude Code, ChatGPT, etc.)"

Adding Skills to this picture:

> "Skills are the orchestration layer: They determine which MCP tools to invoke and how to interpret results, encoding domain expertise that sits between user intent and tool execution."

---

## 11. Assumptions & Risks

This analysis depends on several assumptions that should be validated:

### Critical Assumptions

| Assumption | Risk if Wrong | Mitigation |
|------------|---------------|------------|
| Skills reduce MCP tool context loading | Skills add overhead without solving bloat | Test in Phase 3; have fallback plan |
| `allowed-tools` restricts tool schemas sent to model | Model still sees all 61 tools | Implement alternative (split servers, aggregators) |
| `context: fork` provides true isolation | Fork still inherits full tool context | Measure actual token usage in forked context |
| Claude Code semantic matching works reliably | Skills don't trigger when expected | Tune descriptions, add explicit keywords |

### Known Unknowns

1. **MCP tool loading precedence**: Documentation doesn't specify whether `allowed-tools` affects which MCP tool *schemas* are loaded, or only which tools Claude can *use*. These are different:
   - Schema loading = affects context tokens
   - Usage restriction = affects behavior, not tokens

2. **Client variance**: Skills behavior may differ across Claude Code, Cursor, VSCode. Test in each environment you support.

3. **Skill-match failures**: When semantic matching fails, Claude may not use any skill, or may use the wrong one. No graceful fallback mechanism documented.

### Security & Trust Boundaries

**Skills are orchestration instructions, not access control.**

- Skills cannot enforce permissions—they're client-side text
- Auth/permissions must remain in MCP servers and backends
- Prompt injection via skill instructions is a concern for complex skills
- Skills should not contain secrets or credentials

---

## 12. Alternatives Considered

If Skills do not adequately address MCP tool bloat, consider these alternatives:

### Alternative A: Split MCP Servers

Break `regen-python-mcp` (45+ tools) into smaller domain-specific servers:

```
regen-bank-mcp        (11 tools)
regen-governance-mcp  (8 tools)
regen-ecocredit-mcp   (13 tools)  # credits + baskets + analytics
regen-marketplace-mcp (5 tools)
```

**Pros**: Even naive clients load fewer tools; cleaner separation
**Cons**: More servers to maintain; cross-domain queries harder

### Alternative B: Aggregator "Front-Door" Tools

Add 7 high-level tools that internally dispatch to granular functions:

```python
@server.tool()
async def explore_blockchain(query: str, domain: str = "auto") -> Dict:
    """Natural language blockchain exploration. Domains: bank, governance, ecocredit, marketplace."""
    # Internally routes to specific tools based on query + domain
    ...
```

Hide the 45 granular tools by default (advanced mode only).

**Pros**: Reduces visible tool count; preserves granular access
**Cons**: Complex routing logic; may reduce precision

### Alternative C: Tool Retrieval (If Client Supports)

Index tool schemas locally. Per-turn, retrieve only top-k relevant tools:

```
Turn 1: "What's my REGEN balance?"
  → Inject: get_balance, get_all_balances (2 tools, not 61)

Turn 2: "Show governance proposals"
  → Inject: list_governance_proposals, get_governance_vote (2 tools)
```

**Pros**: Optimal context efficiency; scales to any tool count
**Cons**: Requires client support; not available in Claude Code today

### Alternative D: Schema Compression

Shorten tool descriptions and parameter schemas:

```yaml
# Before (verbose)
description: "Get the balance of a specific token denomination for a given account address on the Regen Network blockchain"

# After (compressed)
description: "Get token balance for account"
```

**Pros**: Quick win; no architectural changes
**Cons**: May reduce model accuracy; limited gains (~20-30%)

### Recommended Path

1. **First**: Implement Skills (low effort, tests the hypothesis)
2. **If Skills insufficient**: Implement Alternative B (aggregator tools)
3. **If still insufficient**: Implement Alternative A (split servers)

---

## 13. Conclusion

**Should we use Skills with integrated MCP functionality?**

**Yes, but as a layer, not a replacement.**

The pattern is:
1. **Skills** = Front door (progressive disclosure, domain expertise, workflow orchestration)
2. **MCP** = Backend infrastructure (tool execution, data access, resilience)
3. **KOI-net** = Network layer (discovery, routing, permissions)

This preserves our significant MCP investment while addressing the context efficiency problem that affects all large MCP deployments.

---

## Sources

- [Agent Skills Home](https://agentskills.io/home)
- [Agent Skills Specification](https://agentskills.io/specification)
- [Agent Skills Integration Guide](https://agentskills.io/integrate-skills)
- [Claude Skills vs. MCP: A Technical Comparison](https://intuitionlabs.ai/articles/claude-skills-vs-mcp)
- [98% of MCP Servers Got This Wrong](https://hackernoon.com/98percent-of-mcp-servers-got-this-wrong-the-reason-why-the-protocol-never-worked)
- [MCP Is Broken and Anthropic Just Admitted It](https://medium.com/@cdcore/mcp-is-broken-and-anthropic-just-admitted-it-7eeb8ee41933)
- [MCP One Year Anniversary Spec Release](https://blog.modelcontextprotocol.io/posts/2025-11-25-first-mcp-anniversary/)
- [A Preview of the KOI-net Protocol](https://blog.block.science/a-preview-of-the-koi-net-protocol/)

---

## Changelog

- **2026-01-08 v3**: Final refinements based on review
  - Added portability note: `allowed-tools` and `context: fork` are Claude Code-specific
  - Added tool name caveat: short names vs namespaced names vary by client
  - Expanded Phase 2 with three tool discovery options (session query, direct export, MCP introspection)
  - Added concrete success criteria table for Phase 3 pass/fail
  - Added test queries for skill match validation
  - Softened debug instructions to be version-agnostic
- **2026-01-08 v2**: Major revision based on technical review feedback
  - Fixed directory path: `skills/` → `.claude/skills/` (Claude Code standard)
  - Added `allowed-tools` YAML field for tool binding (configuration, not just documentation)
  - Added `context: fork` for isolated sub-agent execution
  - Renamed `regen-research` → `knowledge-graph-expert` (better semantic matching)
  - Added Section 9: MCP Prompts vs. Skills (clarify different mechanisms)
  - Added Section 11: Assumptions & Risks (critical unknowns, security boundaries)
  - Added Section 12: Alternatives Considered (split servers, aggregators, tool retrieval, schema compression)
  - Updated token methodology with measurement guidance
  - Added tool index sync mechanism to prevent drift
  - Removed incorrect `.claude/settings.json` configuration
- **2026-01-08 v1**: Initial analysis from MCP vs Skills investigation (Darren/Claude synthesis)
