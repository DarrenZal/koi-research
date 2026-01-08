# Networked Knowledge Agents via KOI

> **Origin**: Gregory Landua brainstorm (January 2026) on lowering barriers to adding knowledge agents to KOI with permissioned access.
>
> **Status**: Idea / Early exploration
>
> **Related**: KOI-net proxy node spec, "A Language for Knowledge Networks" (BlockScience)

---

## Core Idea

Commercial AI platforms (OpenAI GPTs, Google Gems, Claude projects) have made it easy for anyone to create specialized knowledge agents. What's missing is infrastructure to **network these agents together** with appropriate access controls.

KOI could fill this gap by serving as the **networking and permissioning layer** for heterogeneous knowledge agents—regardless of how they're built internally. The value proposition:

- **Create** knowledge agent using GPT/Gem/whatever tool works for you
- **Register** with KOI network + set permissions (public/protected/private/hidden)
- **KOI handles** discovery, networking, and access control

This is "KOI-net as a service" for knowledge agents—lowering the barrier from "build a KOI node from scratch" to "create a GPT and register it."

---

## The Market Gap

| Layer | Status | Examples |
|-------|--------|----------|
| **Agent creation** | Solved (easy) | OpenAI (GPTs/Assistants), Google (Gems/Vertex), Anthropic (Claude), custom RAG |
| **Agent-to-agent interop (tasks/messages)** | Emerging | Google Agent-to-Agent (A2A), other emerging protocols |
| **Tool/context interop (LLM ↔ tools/data)** | Emerging | Anthropic Model Context Protocol (MCP), other tool-calling standards |
| **Permissioned cross-org knowledge networks** | Unsolved | This is KOI's focus |

Commercial providers commoditized agent creation, and interoperability standards are emerging. But there's still no good way to:
- Have agents discover each other across organizations
- Share knowledge between agents with verifiable provenance (RIDs/evidence) and appropriate access controls
- Query across multiple specialized agents in a coordinated way (routing + synthesis)

**KOI could fill this gap**—not by competing on agent creation, but by providing the connective tissue.

---

## GPT/Gem Reality Check

**Important architectural clarification**: Custom GPTs (ChatGPT UI) and Google Gems aren't reliably callable or embeddable via API. The "wrapper" we build should target **API-accessible agent definitions**, not the consumer UIs.

### What's Actually Wrappable

| Platform | Consumer UI | API-Accessible | Wrap This |
|----------|-------------|----------------|-----------|
| OpenAI | Custom GPTs | Assistants API | ✅ Assistants API |
| Google | Gems | Vertex AI Agents | ✅ Vertex AI |
| Anthropic | Claude Projects | Claude API + system prompts | ✅ API |
| Custom | — | RAG pipelines, LangChain, etc. | ✅ Direct integration |

### Design Implication

The wrapper SDK should target:
1. **Agent definitions** (system prompt + tools + retrieval config)
2. **API endpoints** (Assistants API, Vertex AI, direct LLM APIs)
3. **NOT** consumer UIs (GPT Builder, Gems UI)

GPTs and Gems can be thought of as **one possible front-end** for interacting with an agent—users might build there for convenience, then export/replicate the config to an API-accessible form for KOI integration.

---

## Mapping to KOI-net Primitives

To avoid semantic collisions with existing KOI-net/RID terminology, this section explicitly maps agent concepts to protocol primitives.

### Terminology Clarification

In RID-lib, **Manifest** has a specific meaning:

```python
class Manifest(BaseModel):
    rid: RID
    timestamp: datetime
    sha256_hash: str
```

A **Bundle** is a Manifest + contents:

```python
class Bundle(BaseModel):
    manifest: Manifest
    contents: dict
```

What we previously called "Capability Manifest" is actually the **contents** of an Agent Profile Bundle.

### Agent RID Type Definition

Agents use the `orn:koi-net.agent` namespace with a specific reference format:

```
orn:koi-net.agent:<name>+<pubkey-hash>
```

**Reference format**:
- `<name>`: Human-readable identifier (lowercase, hyphens allowed)
- `+`: Separator
- `<pubkey-hash>`: SHA-256 hex hash of the owning node's public key (64 hex chars, like KOI-net node RIDs)

**Examples**:
```
orn:koi-net.agent:soil-carbon-expert+0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
orn:koi-net.agent:regen-registry-qa+fedcba9876543210fedcba9876543210fedcba9876543210fedcba9876543210
```

**Stability rules**:
- The pubkey-hash ties agent identity to its owning node's cryptographic identity
- If a node's keys rotate, the agent RID changes (requires FORGET + NEW)
- Name collisions are prevented by the pubkey-hash suffix
- Agents cannot be transferred between nodes without re-registration

**Why pubkey-hash?** This mirrors KOI-net node RIDs (`orn:koi-net.node:name+<hash>`) and ensures:
1. Agent identity is cryptographically bound to a node
2. No central registry needed to prevent collisions
3. Ownership is verifiable from the RID itself

### Agent as RIDed Bundle

Each agent in the network is represented as a RIDed knowledge object:

| Concept | KOI-net Primitive | Example |
|---------|-------------------|---------|
| Agent identity | RID | `orn:koi-net.agent:soil-carbon-expert+0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef` |
| Agent profile | Bundle | Manifest (rid + timestamp + hash) + Contents (profile JSON) |
| Profile schema | Bundle contents | The "Agent Profile" schema defined below |

### Lifecycle Events

Agent state changes map to KOI-net FUN events:

| Action | Event Type | What Happens |
|--------|------------|--------------|
| Agent joins network | `NEW` | Node broadcasts NEW event with agent RID + bundle |
| Agent updates profile/capabilities | `UPDATE` | Node broadcasts UPDATE event with new bundle |
| Agent leaves network | `FORGET` | Node broadcasts FORGET event for agent RID |

### Agent Profile Bundle Schema

The **contents** of an agent's bundle (not called "manifest" to avoid collision):

```yaml
# Agent Profile Bundle Contents (draft schema)
# This is the `contents` field of a Bundle, NOT a Manifest

profile_version: "1.0.0"

# Identity (matches the Bundle's RID)
identity:
  name: "Soil Carbon Methodology Expert"
  description: "Specialized in soil carbon measurement, MRV protocols, and regenerative agriculture practices"
  owner: "Land Trust XYZ"

# What this agent knows about
capabilities:
  topics:
    - soil_carbon
    - mrv_methodology
    - regenerative_agriculture
    - grassland_ecosystems

  # Input/output contract
  interface:
    input_types:
      - natural_language_query
      - structured_query  # optional
    output_format: "koi_agent_response"  # see response schema below
    max_context_length: 8000
    supports_streaming: false

# Operational characteristics
operational:
  avg_latency_ms: 2000
  cost_tier: "medium"  # low/medium/high/premium
  rate_limit: 100  # queries per hour
  availability: "best_effort"  # or "sla_99" etc.

# Access requirements (for human callers - see Auth Layering below)
access:
  visibility: "protected"  # public/protected/private/hidden
  human_auth_methods: ["oidc", "api_key"]

# Knowledge provenance
provenance:
  created: "2026-01-07"
  last_updated: "2026-01-07"
  knowledge_sources:
    - rid: "orn:regen.collection:land-trust-methodology-docs"
      type: "document_collection"
      description: "Internal methodology docs and research papers"
    - rid: "orn:regen.dataset:monitoring-data-2020-2024"
      type: "structured_data"
      description: "5 years of monitoring data"
```

### Response Format

Responses must include RIDs/evidence, not just prose:

```yaml
# KOI Agent Response Schema (draft)
response:
  query_id: "uuid"
  agent_rid: "orn:koi-net.agent:soil-carbon-expert+0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
  timestamp: "2026-01-07T12:00:00Z"

  # The actual answer
  content:
    text: "Based on the monitoring data from similar grassland projects..."
    confidence: 0.85  # optional

  # Evidence/citations - REQUIRED
  evidence:
    - rid: "orn:regen.document:methodology-doc-123"
      relevance: 0.92
      excerpt: "Section 3.2 specifies that soil samples should be taken at 0-30cm depth..."
    - rid: "orn:regen.data:monitoring-batch-456"
      relevance: 0.78
      excerpt: null  # structured data, no excerpt

  # What the agent doesn't know
  limitations:
    - "No data for East African grasslands specifically; extrapolating from Southern African projects"
    - "Monitoring data is from 2020-2024; recent climate shifts may affect applicability"

  # Processing metadata
  metadata:
    tokens_used: 1500
    latency_ms: 1823
    model: "claude-3-opus"
```

### Key Principles

1. **Everything is RIDed**: Agents, knowledge sources, responses can all be referenced by RID
2. **Bundles for state**: Agent profiles are Bundles (manifest + contents)
3. **Events for coordination**: NEW/UPDATE/FORGET signal network state changes
4. **Evidence required**: Responses cite RIDs, not just generate prose

### Query Routing Model

**Important clarification**: KOI-net is primarily object/event-oriented (Bundles, NEW/UPDATE/FORGET). How do queries fit?

**Queries are RPC (out-of-band)**:
- Query requests use standard HTTP/RPC to agent endpoints
- Not modeled as RIDed bundles or events
- This is pragmatic: queries are ephemeral, high-volume, latency-sensitive

**Responses can be RIDed bundles (optional)**:
- For auditability: response can be stored as a Bundle with RID
- For caching: repeated queries can return cached response RID
- For attribution: multi-agent synthesis can reference source response RIDs

```
┌─────────────────────────────────────────────────────────────┐
│                    Query Flow                                │
│                                                              │
│   Query (RPC)           Response (RPC or RIDed Bundle)      │
│   ──────────►  Agent   ─────────────────────────────►       │
│                 Node                                         │
│                                                              │
│   - HTTP POST           - Inline JSON (fast, ephemeral)     │
│   - Not a Bundle        - OR Bundle RID (auditable, cached) │
│   - Not an event        - Response Bundle stored locally    │
└─────────────────────────────────────────────────────────────┘
```

**State changes still use events**:
- Agent registration: NEW event with profile Bundle
- Agent updates: UPDATE event
- Agent removal: FORGET event

This hybrid model balances KOI-net's object-oriented design with practical query latency requirements.

---

## How It Maps to KOI-net Architecture

### Proxy Nodes

KOI-net already supports this pattern. From the spec:

> "A proxy node represents a specific set of knowledge and exposes standardized endpoints that allow it to communicate within KOI-net, even if the underlying system is entirely bespoke."

A GPT or Gem wrapped in a KOI-compliant interface is a valid node. The protocol is agnostic to internal implementations—it only cares about the standardized endpoints.

### Fractal Architecture

KOI-net's fractal nature means:
- An individual's GPT can be a node
- An organization's constellation of agents can appear as a single node to outsiders
- Networks of networks can form organically

### Evidence: KOI-net Demo Data Flow

The KOI-net demo described in the BlockScience KOI-net preview already outlines an end-to-end pipeline for distributed knowledge processing:

1. Collection: Sensor nodes fetch external data
2. Discovery: Sensors register with a Coordinator
3. Exchange: RIDs facilitate standardized communication
4. Processing: Event handlers transform data
5. Storage: Processed data is indexed
6. Access: CLI/REST interfaces provide query capabilities
7. Monitoring: Continuous updates create a live stream

This proposal layers "networked knowledge agents" on top of that foundation: representing agents as RIDed Bundles, coordinating via FUN events, and serving permissioned query/synthesis workloads.

---

## Authentication Layering

KOI-net already has node-to-node authentication. Human authentication is a separate layer on top.

### Layer 1: Node-to-Node Auth (Already in KOI-net)

KOI-net uses **signed envelopes** for node-to-node communication:

```python
# From koi_net/secure.py
class Secure:
    def create_envelope(self, payload, target) -> SignedEnvelope:
        return UnsignedEnvelope(
            payload=payload,
            source_node=self.identity.rid,
            target_node=target
        ).sign_with(self.priv_key)

    def validate_envelope(self, envelope: SignedEnvelope):
        # 1. Resolve source node's bundle to get public key
        # 2. Verify public key hash matches node RID
        # 3. Verify envelope signature with public key
        # 4. Verify this node is the intended target
```

**How it works**:
- Each node has a private/public key pair
- Node RID includes hash of public key: `orn:koi-net.node:name+<hash>`
- Outgoing messages are signed with private key
- Receiving node validates signature against sender's public key
- **Trust**: If signature is valid and public key hash matches RID, message is authentic

This handles **machine-to-machine authentication**—proving one node is who it claims to be.

### Layer 2: Human-to-Node Auth (New Layer)

Human users querying the network need a separate auth mechanism:

| Method | Use Case | Implementation |
|--------|----------|----------------|
| **OIDC** | Human users, org SSO | Standard OAuth2/OIDC flow |
| **API Keys** | Simple integrations, scripts | Scoped keys with rotation |
| **DID Auth** | Decentralized identity | For future P2P scenarios |

**How it layers**:
1. Human authenticates to a gateway/interface node (OIDC, API key, etc.)
2. Gateway node acts on human's behalf within the network
3. Node-to-node communication uses signed envelopes (Layer 1)
4. Target nodes enforce access policies based on human's identity/groups

### Gateway Trust Model

**Critical question**: When a gateway forwards "user@org.com, groups: [verified_partner]", how does the target node trust this claim?

**Option A: Trust the gateway node (simpler)**
- Target node trusts claims from known gateway nodes
- Gateway node's signed envelope proves *it* made the claim
- Target trusts gateway to have verified the human
- **Risk**: Compromised gateway can impersonate any user

**Option B: Signed attestation (more secure)**
- Gateway includes a signed attestation in the envelope payload:
  ```yaml
  user_attestation:
    identity: "user@org.com"
    groups: ["verified_partner"]
    oidc_issuer: "https://auth.regen.network"
    oidc_sub: "auth0|abc123"
    issued_at: "2026-01-07T12:00:00Z"
    expires_at: "2026-01-07T13:00:00Z"
    gateway_signature: "<sig over above fields>"
  ```
- Target node can verify:
  1. Gateway's signature on the attestation
  2. Attestation hasn't expired
  3. (Optionally) Validate against OIDC issuer's JWKS

**Recommendation**: Start with Option A for MVP (trust gateway nodes), evolve to Option B for production. The signed attestation provides defense-in-depth without requiring target nodes to integrate directly with OIDC.

### Auth Flow Example

```
Human (OIDC) → Gateway Node → [Signed Envelope + User Attestation] → Target Agent Node
                   ↓                                                        ↓
           Gateway verifies                                    Target verifies:
           OIDC token, issues                                  1. Envelope signature (gateway)
           signed attestation                                  2. Attestation signature (gateway)
                                                               3. Attestation not expired
                                                               4. ABAC policy check
                                                                        ↓
                                                               Returns permitted knowledge
```

### Summary

| Layer | Who | Mechanism | Already Exists? |
|-------|-----|-----------|-----------------|
| Node-to-Node | Machines | Signed envelopes, public key verification | ✅ Yes (KOI-net) |
| Human-to-Node | Users | OIDC, API keys, DIDs | ❌ Build on top |

---

## Access Control & Authorization

### Beyond Commons/Private/Public

The conceptual model (commons/private/public) needs concrete ABAC implementation:

```yaml
# Example ABAC Policy
policy:
  name: "land-trust-data-access"

  rules:
    # Public methodology - anyone can query
    - resource: "methodology/*"
      action: "query"
      effect: "allow"
      conditions: []

    # Monitoring data - only verified partners
    - resource: "monitoring-data/*"
      action: "query"
      effect: "allow"
      conditions:
        - attribute: "requester.org_type"
          operator: "in"
          value: ["verified_partner", "registry_admin"]
        - attribute: "requester.has_nda"
          operator: "equals"
          value: true

    # Raw data export - only internal
    - resource: "monitoring-data/*"
      action: "export"
      effect: "allow"
      conditions:
        - attribute: "requester.org_id"
          operator: "equals"
          value: "land-trust-xyz"
```

### Access Control Features

| Feature | Description | Priority |
|---------|-------------|----------|
| **Group-based access** | Define groups (partners, public, internal) | MVP |
| **Attribute-based (ABAC)** | Fine-grained rules on requester/resource attributes | V2 |
| **Rate limiting** | Per-requester, per-group, per-node | MVP |
| **Quota management** | Monthly query limits, cost caps | MVP |
| **Audit logging** | Who queried what, when, response summary | MVP |
| **Public metadata / private content** | Discoverable but not queryable without auth | MVP |

### Visibility Levels (Refined)

| Level | Discovery | Query | Use Case |
|-------|-----------|-------|----------|
| **Public** | ✅ Anyone | ✅ Anyone | Open knowledge goods |
| **Protected** | ✅ Anyone | 🔐 Authenticated | Discoverable but gated |
| **Private** | 🔐 Group only | 🔐 Group only | Internal org knowledge |
| **Hidden** | ❌ None | 🔐 Direct invite | Sensitive, unlisted |

---

## Interoperability: MCP & A2A

The KOI-net protocol is designed to complement—not replace—other agent communication standards.

### Model Context Protocol (MCP)

From the [KOI-net Preview](https://blog.block.science/a-preview-of-the-koi-net-protocol/):

> "MCP standardizes how models receive context and invoke external functionality, eliminating the need for custom integrations for each data source."

**Role in this architecture**:
- MCP connects KOI nodes to **non-KOI data/tools within a network's boundaries**
- An "MCP adapter" node could unify datastreams into a searchable registry
- Example: KOI-net + MCP server → LLM can query sensors, answer questions about HackMD specs vs GitHub repos

**We're already using MCP**: The Regen KOI MCP server is an example of this pattern—exposing KOI knowledge to Claude Code and other MCP-compatible interfaces.

### Agent-to-Agent Protocol (A2A)

From the same source:

> "A2A uses a task-based model with capability discovery, asynchronous management, and standardized message formats to allow agents to work together seamlessly."

**Role in this architecture**:
- A2A enables KOI-net to **present a controlled interface to outside systems**
- Secure, standardized communication **across network boundaries**
- Could allow external agents to interact with KOI-net without full node integration

### How They Fit Together

| Protocol | Scope | Function |
|----------|-------|----------|
| **KOI-net** | Core network | Node coordination, knowledge events, state sync |
| **MCP** | Within boundaries | Connect nodes to non-KOI tools/data (LLMs, databases, APIs) |
| **A2A** | Across boundaries | External agent interop, controlled access for non-KOI agents |

```
┌─────────────────────────────────────────────────────────┐
│                     KOI Network                         │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐          │
│  │  Sensor  │───▶│Coordinator│◀───│ Processor│          │
│  │   Node   │    │   Node   │    │   Node   │          │
│  └──────────┘    └──────────┘    └──────────┘          │
│       │                               │                 │
│       │         KOI-net protocol      │                 │
│       │         (signed envelopes,    │                 │
│       │          RIDs, events)        │                 │
│       ▼                               ▼                 │
│  ┌──────────┐                   ┌──────────┐           │
│  │   MCP    │                   │   MCP    │           │
│  │ Adapter  │                   │ Adapter  │           │
│  └──────────┘                   └──────────┘           │
│       │                               │                 │
└───────│───────────────────────────────│─────────────────┘
        │ MCP                           │ MCP
        ▼                               ▼
   ┌─────────┐                    ┌─────────┐
   │  Claude │                    │  Other  │
   │  Code   │                    │   LLM   │
   └─────────┘                    └─────────┘

                    ┌─────────┐
                    │   A2A   │◀── External agents
                    │ Gateway │    (not KOI nodes)
                    └─────────┘
                         │
                         ▼
                   KOI Network
```

### Implications for This Design

1. **MCP is the LLM interface**: Human users interact via MCP-enabled interfaces (Claude Code, ChatGPT, etc.)
2. **A2A is the external agent interface**: Non-KOI agents can interact via A2A gateway
3. **KOI-net is the knowledge backbone**: Coordinates knowledge objects, handles permissions
4. **Agent wrappers speak KOI-net**: GPT/Gem wrappers implement KOI-net protocol, optionally expose MCP

---

## Trust Model

Different layers require different trust considerations:

### Protocol Trust
**KOI-net as a protocol doesn't require trusting Regen.** The spec is open—anyone can implement nodes, run coordinators, or connect peer-to-peer.

### Infrastructure Trust
**If Regen runs shared infrastructure** (coordinator nodes, discovery services), participants trust Regen as infrastructure provider. Comparable to trusting AWS or Cloudflare.

### Knowledge Location Trust
**Knowledge stays in nodes.** KOI passes:
- RIDs (references to knowledge objects)
- Events (notifications about changes)
- Manifests (metadata about bundles)

Actual knowledge content can stay local. When you query a node, *that node* decides what to return.

### Commercial AI Trust
**Already a given.** Using a GPT means trusting OpenAI. Using a Gem means trusting Google. KOI doesn't change existing trust relationships—it networks agents that already exist.

### The Trust Spectrum

| Architecture | Trust Requirement | Trade-off |
|--------------|-------------------|-----------|
| **Centralized** (single hub) | Trust hub operator | Easy setup, single point of failure |
| **Federated** (multiple coordinators) | Trust chosen coordinator(s) | Resilient, choose trust relationships |
| **Peer-to-peer** (direct connections) | Trust only direct peers | Maximum sovereignty, harder discovery |

KOI-net supports all three. Choice depends on use case.

### Trust Minimization Strategies

1. **Open protocol**: No lock-in—can fork or reimplement
2. **Self-hosting**: Organizations run their own nodes
3. **Edge permissioning**: Each node controls what it shares locally
4. **Federation**: Multiple coordinators (Regen, partners, universities)
5. **Cryptographic verification**: Signed envelopes + content hashes in manifests
6. **Audit trails**: Event system creates logs of knowledge flows

---

## Security & Threat Model

### Threat Categories

| Threat | Description | Risk Level |
|--------|-------------|------------|
| **Prompt injection** | Malicious queries try to manipulate agent behavior | High |
| **Data exfiltration** | Queries designed to extract private knowledge | High |
| **Spam nodes** | Low-quality agents flooding the network | Medium |
| **Knowledge poisoning** | Agents returning false/misleading information | High |
| **Denial of service** | Overwhelming nodes with queries | Medium |
| **Identity spoofing** | Pretending to be a trusted node/user | Medium |

### Mitigations

#### Prompt Injection Defense
- **Least-privilege outputs**: Agents only return what's explicitly in their knowledge base
- **Structured response format**: Enforce schema compliance, reject free-form outputs
- **Input sanitization**: Filter/escape potentially malicious query patterns
- **Allowlisted tools**: Agents can only call pre-approved external tools

#### Data Exfiltration Prevention
- **Query logging + anomaly detection**: Flag unusual query patterns
- **Rate limiting**: Prevent bulk extraction
- **Response size limits**: Cap amount of data per response
- **Differential privacy**: For aggregate queries over sensitive data (advanced)

#### Spam/Quality Control
- **Node registration review**: Manual or automated vetting before joining network
- **Signed envelopes**: Cryptographic proof of node identity via KOI-net envelope signatures
- **Reputation signals**: Track query success rates, user feedback
- **Stake/deposit**: Economic skin-in-the-game for node operators (optional)

#### Knowledge Poisoning Defense
- **Evidence requirements**: Responses must cite RIDs—no unsourced claims
- **Source verification**: RIDs link to verifiable source material
- **Cross-validation**: Route queries to multiple agents, flag disagreements
- **Human oversight**: Flag low-confidence or high-stakes responses for review

#### Infrastructure Protection
- **DDoS protection**: Standard CDN/WAF for public endpoints
- **Signed envelopes**: Node-to-node auth via KOI-net Secure layer
- **Circuit breakers**: Nodes can disconnect from misbehaving peers

### Security Principles

1. **Defense in depth**: Multiple layers, no single point of failure
2. **Least privilege**: Nodes/users get minimum necessary access
3. **Audit everything**: Comprehensive logging for forensics
4. **Fail secure**: Default deny, explicit allow
5. **Assume breach**: Design for detection and containment, not just prevention

---

## Economics Model

### Cost Components

| Component | Who Pays Today | Options |
|-----------|----------------|---------|
| **LLM inference** | Node operator | BYO API key, network subsidy, query fees |
| **Infrastructure** | Regen (coordinator) | Node fees, grants, freemium |
| **Bandwidth** | Node operator | Included in node fee, or metered |
| **Storage** | Node operator | Local responsibility |

### Economic Models

#### Model A: BYO API Key (Decentralized Costs)
- Each node operator pays their own LLM costs
- No money flows through the network
- **Pro**: Simple, no financial infrastructure needed
- **Con**: No incentive to serve others' queries

#### Model B: Query Fees (Marketplace)
- Requesters pay per query (or per token)
- Node operators earn for serving queries
- **Pro**: Incentivizes participation, quality
- **Con**: Complex payment infrastructure, friction

#### Model C: Subscription/Quota (Network Membership)
- Organizations pay membership fee
- Get quota of queries across network
- **Pro**: Predictable costs, simple UX
- **Con**: Requires central treasury management

#### Model D: Hybrid
- Free tier for public/commons knowledge
- Paid tier for premium/private access
- Credits/tokens for heavy users
- **Pro**: Balances accessibility and sustainability
- **Con**: Complexity

### Cost Visibility

Regardless of model, costs should be **transparent**:

```yaml
# Query cost breakdown (example)
query_cost:
  total: 0.02  # USD
  breakdown:
    routing: 0.001
    agent_inference: 0.015
    synthesis: 0.004
  paid_by: "requester_org"
  charged_to: "monthly_quota"
```

### MVP Approach

Start with **Model A (BYO API Key)** for simplicity:
- Node operators bring their own API keys
- No payments infrastructure needed
- Track usage metrics for future monetization
- Iterate based on actual usage patterns

---

## MVP Roadmap

### Phase 1: Foundation (Wrapper SDK + Discovery)

**Goal**: Enable agents to join the network and be discovered.

**Deliverables**:
- [ ] Wrapper SDK for common platforms (Assistants API, Vertex AI, direct LLM)
- [ ] Agent Profile Bundle schema (aligned with RID-lib Bundle)
- [ ] Registration flow (CLI or simple UI)
- [ ] Discovery index (searchable directory of registered agents)
- [ ] Basic human auth (API keys)

**Success criteria**: 5+ agents registered and discoverable.

### Phase 2: Basic Routing

**Goal**: Enable queries to find relevant agents.

**Deliverables**:
- [ ] Query router (profile search → dispatch)
- [ ] Single-agent query flow (query → route → respond)
- [ ] Response format enforcement (evidence/RIDs required)
- [ ] Rate limiting + basic abuse prevention
- [ ] Audit logging

**Success criteria**: End-to-end query flow working, <3s latency.

### Phase 3: Multi-Agent Synthesis

**Goal**: Queries can draw on multiple agents with attribution.

**Deliverables**:
- [ ] Multi-agent dispatch (parallel queries)
- [ ] Response synthesis (combine answers with attribution)
- [ ] Conflict detection (flag disagreements)
- [ ] Confidence scoring
- [ ] ABAC policy engine

**Success criteria**: Cross-organizational query working (e.g., Scenario 3).

### Phase 4: Production Hardening

**Goal**: Ready for real-world deployment.

**Deliverables**:
- [ ] Full OIDC integration
- [ ] KOI-net Secure layer for all node-to-node
- [ ] Comprehensive security audit
- [ ] Economics/billing infrastructure (if needed)
- [ ] SLA monitoring and alerting
- [ ] Federation support (multiple coordinators)

**Success criteria**: Partner organizations running production workloads.

---

## Practical Scenarios

### Scenario 1: Partner Organization

A land trust wants to share their monitoring methodologies but protect proprietary data.

1. They prototype an agent using ChatGPT's GPT Builder (easy UI, quick iteration)
2. They export/replicate the config to an **OpenAI Assistants API** agent (API-accessible)
3. They (or we help them) wrap the Assistants API agent as a KOI proxy node
4. They set permissions:
   - "Public": General methodology questions
   - "Protected": Detailed monitoring protocols (authenticated partners only)
   - "Private": Raw monitoring data, internal assessments
5. Other network agents can discover and query their public expertise

### Scenario 2: Individual Expert

A soil scientist wants to contribute their knowledge to the network.

1. They prototype using Google's Gems UI for quick setup with their research papers
2. They replicate the agent config to **Vertex AI Agents** (API-accessible)
3. They register the Vertex AI agent with KOI, set to "Public" (anyone can query)
4. When network queries touch soil carbon topics, their agent can be invoked
5. They maintain control—can update, restrict, or remove at any time

### Scenario 3: Cross-Organizational Query

Query: "What regenerative practices are most effective for degraded grasslands in East Africa?"

The network could route to:
- **Regen Registry**: Credit batch data for the region
- **Partner land trust**: Monitoring outcomes from similar projects
- **Soil scientist node**: Methodology and research context
- **Savory Institute node**: Holistic management expertise

Response synthesizes across these specialized sources with appropriate attribution.

---

## The "Mycelial Network" Metaphor

Gregory's intuition about connective infrastructure maps to how mycelial networks function in forests:

| Mycelial Networks | KOI Agent Network |
|-------------------|-------------------|
| Connect different organisms | Connect different knowledge agents |
| Enable nutrient sharing | Enable knowledge sharing |
| No centralized control required | Protocol supports P2P |
| Selective resource allocation | Permissioned access |
| Resilient to node failure | Distributed, no single point of failure |

The value is in the connections, not the individual nodes.

---

## Implementation Considerations

### What We'd Need to Build

1. **Agent wrapper SDK**: Standardized way to expose API-accessible agents as KOI proxy nodes
2. **Registration flow**: User-friendly onboarding (vs. current "build a node from scratch")
3. **Permissions UI**: Set and manage access controls without touching code
4. **Discovery service**: How do agents find each other?
5. **Query router**: How do network-level queries get distributed to relevant agents?

### What Already Exists

- KOI-net protocol and reference implementation
- RID-lib with Manifest/Bundle primitives
- Signed envelope authentication (Secure layer)
- Proxy node concept in the spec
- Event system (NEW/UPDATE/FORGET) for network coordination
- MCP server implementation (Regen KOI MCP)

### Gap: The Onramp

The protocol exists. What's missing is the user-facing layer that makes participation easy for non-technical users or organizations without dedicated engineering resources.

---

## Open Questions

1. **Discovery mechanics**: How do agents advertise their capabilities? How do queries find relevant agents? (Addressed in MVP Phase 1-2)

2. **Query routing**: Does a central router dispatch queries, or is it emergent/P2P? (Start centralized, evolve to federated)

3. **Response synthesis**: When multiple agents contribute to an answer, how is it combined? Who does the synthesis? (Addressed in MVP Phase 3)

4. **Economics**: Is there a fee/incentive structure for contributing knowledge to the network? (Start with BYO API key, iterate)

5. **Quality/trust signals**: How do you know if an agent's knowledge is reliable? Reputation system? (Evidence requirements + future reputation layer)

6. **Versioning**: How do you handle agents whose knowledge becomes outdated? (Bundle versioning via manifest timestamps)

7. **Commercial terms**: If someone's GPT is queried 10,000 times via the network, who pays the OpenAI API costs? (See Economics Model section)

---

## Relationship to Services Offering

This vision could inform a services offering to partners:

- Help partners set up custom GPTs/Gems with their domain knowledge
- Wrap those agents as KOI nodes
- Connect them to the broader network
- Ongoing support for permissions, updates, monitoring

This is infrastructure we're building for ourselves anyway. Offering it to partners could:
- Expand the network (more agents = more valuable)
- Create revenue/sustainability path
- Deepen partner relationships

*(Note: This is a separate strategic conversation from the architectural vision above.)*

---

## Related Resources

- [KOI-net Protocol README](https://github.com/BlockScience/koi-net)
- [RID-lib Protocol](https://github.com/BlockScience/rid-lib) - Manifest/Bundle primitives
- [A Preview of the KOI-net Protocol](https://blog.block.science/a-preview-of-the-koi-net-protocol/) - MCP/A2A discussion
- [A Language for Knowledge Networks](https://blog.block.science/a-language-for-knowledge-networks/) - Zargham & Ben-Meir
- [KOI Network Protocol x Project Interlay](https://blog.block.science/koi-network-protocol-project-interlay/)
- [KOI Nodes as Neurons](https://blog.block.science/koi-nodes-as-neurons/) - David Sisson

---

## Changelog

- **2026-01-07**: Initial capture from Gregory brainstorm + Darren/Claude synthesis
- **2026-01-07**: Incorporated feedback: added agent node contract, GPT/Gem reality check, expanded permissions/auth, MVP roadmap, security/threat model, economics model
- **2026-01-07**: Aligned with KOI-net/RID semantics: renamed "Capability Manifest" to Agent Profile Bundle, added explicit primitive mapping, clarified auth layering (node-to-node vs human-to-node), added MCP/A2A interop section
- **2026-01-07**: Refinements: defined `orn:koi-net.agent` RID type format (name+pubkey-hash), clarified query routing model (RPC vs events), tightened gateway trust model (signed attestations), updated intro visibility levels, aligned scenarios with GPT/Gem reality check, fixed "signed bundles" → "signed envelopes"
