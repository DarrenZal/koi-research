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
- **Register** with KOI network + set permissions (commons/private/public)
- **KOI handles** discovery, networking, and access control

This is "KOI-net as a service" for knowledge agents—lowering the barrier from "build a KOI node from scratch" to "create a GPT and register it."

---

## The Market Gap

| Layer | Status | Providers |
|-------|--------|-----------|
| **Agent creation** | Solved (easy) | OpenAI (GPTs), Google (Gems), Anthropic (Claude), custom RAG |
| **Agent networking** | Unsolved | ??? |
| **Knowledge permissioning** | Unsolved | ??? |

Commercial providers commoditized agent creation. But there's no good way to:
- Have agents discover each other across organizations
- Share knowledge between agents with appropriate access controls
- Query across multiple specialized agents in a coordinated way

**KOI could fill this gap**—not by competing on agent creation, but by providing the connective tissue.

---

## How It Maps to KOI-net Architecture

### Proxy Nodes

KOI-net already supports this pattern. From the spec:

> "A proxy node represents a specific set of knowledge and exposes standardized endpoints that allow it to communicate within KOI-net, even if the underlying system is entirely bespoke."

A GPT or Gem wrapped in a KOI-compliant interface is a valid node. The protocol is agnostic to internal implementations—it only cares about the standardized endpoints.

### Permissions Model

Gregory's framing maps to existing KOI concepts:

| Permission Level | Description | KOI Concept |
|------------------|-------------|-------------|
| **Full Commons** | Open to all network participants | Public node, unrestricted queries |
| **Private Subgraph** | Visible only within a boundary | Access-controlled proxy node |
| **Public Access** | Discoverable but query-restricted | Public metadata, permissioned content |

### Fractal Architecture

KOI-net's fractal nature means:
- An individual's GPT can be a node
- An organization's constellation of agents can appear as a single node to outsiders
- Networks of networks can form organically

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
- Manifests (metadata)

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
5. **Cryptographic verification**: RIDs include content hashes
6. **Audit trails**: Event system creates logs of knowledge flows

---

## Practical Scenarios

### Scenario 1: Partner Organization

A land trust wants to share their monitoring methodologies but protect proprietary data.

1. They create a GPT loaded with their methodology docs and public reports
2. They (or we help them) wrap it as a KOI proxy node
3. They set permissions:
   - "Commons": General methodology questions
   - "Private": Raw monitoring data, internal assessments
4. Other network agents can discover and query their public expertise

### Scenario 2: Individual Expert

A soil scientist wants to contribute their knowledge to the network.

1. They create a Gem with their research papers and domain expertise
2. They register with KOI, set to "Public" (anyone can query)
3. When network queries touch soil carbon topics, their agent can be invoked
4. They maintain control—can update, restrict, or remove at any time

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

1. **GPT/Gem wrapper SDK**: Standardized way to expose commercial AI agents as KOI proxy nodes
2. **Registration flow**: User-friendly onboarding (vs. current "build a node from scratch")
3. **Permissions UI**: Set and manage access controls without touching code
4. **Discovery service**: How do agents find each other?
5. **Query routing**: How do network-level queries get distributed to relevant agents?

### What Already Exists

- KOI-net protocol and reference implementation
- Proxy node concept in the spec
- RID system for knowledge object references
- Event system (NEW/UPDATE/FORGET) for network coordination

### Gap: The Onramp

The protocol exists. What's missing is the user-facing layer that makes participation easy for non-technical users or organizations without dedicated engineering resources.

---

## Open Questions

1. **Discovery mechanics**: How do agents advertise their capabilities? How do queries find relevant agents?

2. **Query routing**: Does a central router dispatch queries, or is it emergent/P2P?

3. **Response synthesis**: When multiple agents contribute to an answer, how is it combined? Who does the synthesis?

4. **Economics**: Is there a fee/incentive structure for contributing knowledge to the network?

5. **Quality/trust signals**: How do you know if an agent's knowledge is reliable? Reputation system?

6. **Versioning**: How do you handle agents whose knowledge becomes outdated?

7. **Commercial terms**: If someone's GPT is queried 10,000 times via the network, who pays the OpenAI API costs?

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
- [A Language for Knowledge Networks](https://blog.block.science/a-language-for-knowledge-networks/) - Zargham & Ben-Meir
- [KOI Network Protocol x Project Interlay](https://blog.block.science/koi-network-protocol-project-interlay/)
- [KOI Nodes as Neurons](https://blog.block.science/koi-nodes-as-neurons/) - David Sisson

---

## Changelog

- **2026-01-07**: Initial capture from Gregory brainstorm + Darren/Claude synthesis
