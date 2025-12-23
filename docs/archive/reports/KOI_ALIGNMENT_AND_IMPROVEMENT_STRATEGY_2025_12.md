# KOI Protocol Alignment & System Improvement Strategy

**Report Date:** December 22, 2025
**Prepared by:** Claude (AI Research Assistant)
**Scope:** RegenAI KOI pipeline alignment with BlockScience KOI-net protocol
**Reference:** `koi-research/docs/KOI_PROTOCOL_ALIGNMENT_REFERENCE.md`

---

## Executive Summary

RegenAI's KOI system is operationally healthy with all services running and audit issues resolved. However, deep analysis reveals that while we are "KOI-shaped," we are not yet fully interoperable with BlockScience's reference KOI-net nodes. This report provides a strategic roadmap for achieving true protocol alignment while preserving our reliability advantages.

**Key Findings:**
1. **Critical Gaps Identified:** RID v3 parsing, JCS hashing, and SignedEnvelope schema compliance block true interoperability
2. **Reliability Advantage:** Our confirm-on-success architecture exceeds reference implementation reliability
3. **Strategic Recommendation:** Adopt a dual-surface architecture that maintains internal reliability while presenting a strict KOI-net interface

**Priority Actions:**
- P0: Adopt `rid-lib` for hashing and data structures
- P1: Implement strict `/koi-net/*` endpoints for interoperability
- P2: Propose reliability extensions upstream to BlockScience

---

## 1. KOI Protocol Architecture Overview

### 1.1 Protocol Components

The KOI (Knowledge Organization Infrastructure) system comprises two core packages from BlockScience:

| Package | Version | Purpose |
|---------|---------|---------|
| `rid-lib` | v3.2.12 | RID parsing, Manifest, Bundle, Cache classes |
| `koi-net` | v1.2.4 | NodeInterface, protocol endpoints, knowledge handlers |

### 1.2 Protocol Layers

```
                    Application Layer
                          |
    +---------------------+---------------------+
    |                     |                     |
  Sensors             Processors           Actuators
    |                     |                     |
    +---------------------+---------------------+
                          |
                   KOI-net Protocol
            (5 endpoints, FUN events, SignedEnvelope)
                          |
                    RID v3 Layer
          (RID parsing, Manifest, Bundle, Cache)
                          |
                  Transport Layer
                     (HTTP/POST)
```

### 1.3 Core Concepts

**RIDs (Reference Identifiers):**
- Format: `<context>:<reference>` or `orn:<namespace>:<reference>`
- All URIs can be valid RIDs
- Examples: `https://github.com/BlockScience/koi-net`, `orn:slack.message:TA2E6KPK3/C07BKQX0EVC/1721669683.087619`

**FUN Events:**
- **F**orget: RID was deleted from cache
- **U**pdate: Previously known RID was updated
- **N**ew: Previously unknown RID was cached

**Node Types:**
- **Full Nodes:** Web servers implementing all KOI-net endpoints
- **Partial Nodes:** Web clients that poll for events

---

## 2. Current RegenAI KOI System Status

### 2.1 Operational Health

| Component | Status | Notes |
|-----------|--------|-------|
| POST polling endpoints | Done | All forwarders use POST |
| Delivery confirmation | Done | Ack only on `success: true` |
| HTTP error semantics | Done | Bridges return 500 on failure |
| SignedEnvelope support | Done | Optional, env-configurable |
| Queue persistence | Done | JSON file storage |
| Pending/processed state | Done | Sensors track before/after emit |

### 2.2 Architecture Components

```
koi-sensors/                    koi-processor/
    |                               |
    +-- Sensors (13 active)         +-- Event Bridges
    |   - Website, GitHub           |   - koi_event_bridge_v2.py
    |   - Discord, Telegram         |   - koi_event_bridge_semantic.py
    |   - Medium, Discourse         |
    |   - Podcast, YouTube          +-- Forwarders
    |   - Notion, Ledger            |   - coordinator_to_eventbridge_forwarder.py
    |                               |
    +-- Coordinator                 +-- Storage
        - koi_coordinator.py            - PostgreSQL, Qdrant
```

### 2.3 Reliability Advantages

RegenAI's implementation exceeds the reference KOI-net reliability:

| Feature | RegenAI | Reference KOI-net |
|---------|---------|-------------------|
| Delivery confirmation | Confirm-on-success | Fire-and-forget |
| Queue persistence | JSON file, survives restart | In-memory by default |
| Error handling | HTTP 500 on failure | HTTP 200 with error body |
| State tracking | Pending/processed per item | Best-effort |

---

## 3. Gap Analysis: Interoperability Blockers

### 3.1 Critical Gaps (P0)

#### 3.1.1 RID v3 Parsing Incompatibility

**Issue:** Our local RID parser in `koi_protocol/core/rid_system.py` rejects `:` in the reference component.

**Impact:**
- Cannot parse ORNs (`orn:namespace:reference`)
- Cannot parse URIs with ports (`https://example.com:8080/path`)
- Violates rid-lib's claim that "all URIs can be valid RIDs"

**Evidence:**
```python
# Current RegenAI implementation (incompatible)
def parse(rid_string):
    parts = rid_string.split(":", 1)  # Only splits on first ":"
    # Fails for: orn:slack.message:team/channel/ts
```

**Solution:** Replace with `rid_lib.RID.from_string()` or create thin wrapper.

#### 3.1.2 Hashing Algorithm Mismatch

**Issue:** RegenAI uses `json.dumps(sort_keys=True)` while rid-lib uses JCS (JSON Canonicalization Scheme).

**Impact:**
- Content hashes don't match across nodes
- Breaks integrity verification
- Breaks deduplication
- Prevents content-addressed identifiers (CIDs)

**Evidence:**
```python
# RegenAI (WRONG)
content_bytes = json.dumps(content, sort_keys=True).encode('utf-8')
hash = sha256(content_bytes).hexdigest()

# rid-lib (CORRECT)
from canonicaljson import canonicalize
canonicalized = canonicalize(data, utf8=False)
hash = sha256(canonicalized).hexdigest()
```

**Solution:** Switch to `rid_lib.Manifest.generate()` for all hash operations.

#### 3.1.3 Schema Field Mismatches

**Manifest Schema Divergence:**

| Field | RegenAI | rid-lib (Required) |
|-------|---------|-------------------|
| rid | Yes | Yes |
| timestamp | Yes | Yes |
| sha256_hash | Uses `content_hash` | Yes |
| size_bytes | Yes | **No** |
| content_type | Yes | **No** |
| version | Yes | **No** |
| metadata | Yes | **No** |

**Bundle Schema Divergence:**

| Field | RegenAI | rid-lib (Required) |
|-------|---------|-------------------|
| rid | Yes (root level) | Derived from manifest |
| manifest | Yes | Yes |
| contents | Yes | Yes |

**Solution:**
- Wire format: Use exact rid-lib schemas
- Internal format: Move extra fields into `contents` under a namespace (e.g., `contents._regen`)

### 3.2 High Priority Gaps (P1)

#### 3.2.1 SignedEnvelope Payload Compatibility

**Issue:** KOI-net signature verification parses payloads into strict Pydantic models before verification. Extra fields are discarded, causing signature mismatch.

**RegenAI Fields That Break Signatures:**
- `node_id` in poll requests
- `include_event_ids` in poll requests
- `event_ids` in responses
- `timestamp`, `source_node` in event payloads

**Solution:** Strip non-schema fields before signing; use envelope for identity (`source_node`, `target_node`).

#### 3.2.2 Node Identity Convention

**Issue:** KOI-net uses `KoiNetNode` ORNs derived from public keys: `orn:koi-net.node:<name>+<hash>`.

**RegenAI Current:** Arbitrary strings (often timestamp-suffixed).

**Solution:** Adopt KoiNetNode identity generation if full secure interop is required.

### 3.3 Medium Priority Gaps (P2)

#### 3.3.1 Endpoint Path Convention

- KOI-net often mounts at `/koi-net/*`
- RegenAI mounts at root (`/events/poll`)

**Solution:** Add `/koi-net/*` prefixed router for strict compatibility.

#### 3.3.2 Cache Persistence

- KOI-net uses `rid-lib` Cache (filesystem, base64 RID keys)
- RegenAI coordinator uses in-memory `Dict[str, Bundle]`

**Impact:** After restart, `/bundles/fetch` returns "not found" for previously processed content.

**Solution:** Adopt `rid-lib.Cache` or equivalent durable store.

---

## 4. Strategic Recommendations

### 4.1 Dual-Surface Architecture

Maintain two API surfaces:

```
                  External KOI-net Nodes
                          |
                          v
    +-----------------------------------------+
    |     /koi-net/* (Strict KOI-net API)    |
    |   - rid-lib schemas                     |
    |   - SignedEnvelope compatible           |
    |   - No custom extensions                |
    +-----------------------------------------+
                          |
                   [Adapter Layer]
                          |
    +-----------------------------------------+
    |      Internal API (Reliability-First)   |
    |   - /events/confirm (custom extension)  |
    |   - Extended schemas in contents        |
    |   - Queue persistence                   |
    |   - Confirm-on-success semantics        |
    +-----------------------------------------+
                          |
                          v
              Internal Services & Storage
```

### 4.2 Interoperability Levels

Define success criteria by level:

| Level | Description | Requires |
|-------|-------------|----------|
| 1 | Wire-compatible (unsigned) | Endpoint shapes match, hashes may differ |
| 2 | Wire + hash compatible | rid-lib hashing, correct RID parsing |
| 3 | SignedEnvelope interop | Strict schemas, envelope verification works |
| 4 | Reference-node substitution | Full koi-net adoption (reliability trade-offs) |

**Recommendation:** Target Level 3 (SignedEnvelope interop) while maintaining internal reliability.

### 4.3 FUN vs CRUD Plane Separation

BlockScience distinguishes:
- **FUN Plane:** Event signaling (forget/update/new) - minimal, reflexive
- **CRUD Plane:** Administration/oversight - operational extensions

**Application:**
- `/koi-net/*` = FUN plane (strict protocol)
- `/events/confirm`, dashboards, ops = CRUD plane (RegenAI extensions)

---

## 5. Implementation Roadmap

### Phase 1: Foundation (P0) - Weeks 1-2

**Goal:** Achieve hash and RID compatibility with rid-lib.

**Tasks:**
1. Install `rid-lib` in `koi-sensors` and `koi-processor`
   ```bash
   pip install rid-lib==3.2.12
   ```

2. Replace RID parsing:
   ```python
   # Before
   from koi_protocol.core.rid_system import RID

   # After
   from rid_lib import RID
   rid = RID.from_string("orn:slack.message:team/channel/ts")
   ```

3. Replace hashing:
   ```python
   # Before
   content_bytes = json.dumps(content, sort_keys=True).encode('utf-8')
   hash = sha256(content_bytes).hexdigest()

   # After
   from rid_lib.ext import Manifest
   manifest = Manifest.generate(rid, contents)
   hash = manifest.sha256_hash
   ```

4. Migrate existing data (plan for hash changes)

**Validation:**
- Hash comparison test: same content produces same hash as rid-lib
- RID parsing test: ORNs and URIs parse correctly

### Phase 2: Strict API Surface (P1) - Weeks 3-4

**Goal:** Add KOI-net compatible endpoints.

**Tasks:**
1. Create `/koi-net/*` FastAPI router:
   ```python
   from fastapi import APIRouter

   koi_net_router = APIRouter(prefix="/koi-net")

   @koi_net_router.post("/events/broadcast")
   def broadcast_events(req: EventsPayload) -> None:
       ...

   @koi_net_router.post("/events/poll")
   def poll_events(req: PollEvents) -> EventsPayload:
       ...
   ```

2. Implement wire ↔ internal model transformers:
   ```python
   def internal_to_wire(internal_event: InternalEvent) -> KoiNetEvent:
       # Strip non-schema fields, move extras to contents._regen
       ...

   def wire_to_internal(wire_event: KoiNetEvent) -> InternalEvent:
       # Restore internal fields from envelope and contents
       ...
   ```

3. SignedEnvelope handling with strict schemas

**Validation:**
- Integration test: reference KOI-net node can broadcast/poll/fetch
- Signature verification test: signed payloads verify correctly

### Phase 3: Durability & Upstream (P2) - Weeks 5-6

**Goal:** Enhance persistence and contribute upstream.

**Tasks:**
1. Adopt `rid-lib.Cache` for bundle storage:
   ```python
   from rid_lib.ext import Cache

   cache = Cache(".rid_cache")
   cache.write(bundle)
   bundle = cache.read(rid)
   ```

2. Prepare upstream proposals:
   - `/events/confirm` extension
   - Queue persistence hooks
   - Synchronous processor option

3. Document RegenAI extensions as optional protocol additions

**Validation:**
- Restart test: bundles survive coordinator restart
- State transfer test: `/bundles/fetch` returns previously processed content

---

## 6. Validation Criteria

### 6.1 Definition of Done for Level 3 Interop

| Test | Expected Result |
|------|-----------------|
| Reference node broadcasts to RegenAI | Events processed successfully |
| Reference node polls from RegenAI | Events returned in KOI-net format |
| Reference node fetches bundle | Bundle returned with correct rid-lib schema |
| SignedEnvelope verification | All signed responses verify correctly |
| Hash comparison | `sha256_hash` matches for identical content |
| Internal reliability preserved | Confirm-on-success still works |

### 6.2 Automated Test Suite

Recommended tests to add:

```python
def test_rid_parsing_orn():
    """ORNs with multiple colons parse correctly."""
    rid = RID.from_string("orn:slack.message:T123/C456/1234.5678")
    assert rid.namespace == "slack.message"

def test_hash_parity_with_ridlib():
    """Content hashes match rid-lib output."""
    from rid_lib.ext import Manifest
    content = {"key": "value", "nested": {"a": 1}}
    manifest = Manifest.generate(rid, content)
    assert our_hash(content) == manifest.sha256_hash

def test_signed_envelope_interop():
    """KOI-net node can verify our signed responses."""
    from koi_net.protocol.secure import verify_envelope
    response = our_signed_response()
    assert verify_envelope(response) is True
```

---

## 7. Risk Assessment

### 7.1 Migration Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Hash changes break existing data | High | Version RIDs; maintain migration map |
| Schema changes break internal clients | Medium | Use adapter pattern; gradual rollout |
| Python version skew (koi-net needs 3.12+) | Medium | Upgrade services or vendor models |
| Performance impact from canonicalization | Low | Benchmark; optimize hot paths |

### 7.2 Operational Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Reliability regression | High | Maintain internal API; don't adopt koi-net server wholesale |
| Interop issues with reference nodes | Medium | Comprehensive integration tests |
| Upstream API changes | Low | Pin versions; monitor releases |

---

## 8. Conceptual Alignment with BlockScience Vision

### 8.1 "Objects as Reference" (Orion Reed, 2023)

**Key Principle:** Digital objects are references to referents; the means of reference (locator, name, content-hash) determines stability and interoperability.

**Application to RegenAI:**
- Our extended manifest metadata conflates "reference" with "referent description"
- Move metadata (URLs, authors, sources) into `contents` (the referent)
- Keep manifest as pure "shipping label" (RID + hash + timestamp)

### 8.2 "KOI Nodes as Neurons" (Sisson, 2025)

**Key Principle:** Nodes operate reflexively (fast, fire-and-forget signaling) like biological neurons.

**Application to RegenAI:**
- Reference koi-net's async model is intentional (reflexive behavior)
- Our confirm-on-success model is a "learning agent" wrapper
- Solution: Keep core node reflexive; add reliability as higher-order layer

### 8.3 "Architecting KOI" (Zargham, 2024)

**Key Principle:** Middle-out design; avoid top-down rigidity; prioritize interoperability.

**Application to RegenAI:**
- Don't enforce reliability at protocol level (that's top-down rigidity)
- Implement reliability as node-specific behavior
- Interoperability is primary; extensions are optional

### 8.4 Proxy Node Pattern

**Key Principle:** Sensors/actuators/processors cross organizational boundaries; proxy nodes provide controlled access.

**Application to RegenAI:**
- MCP servers, dashboards, forwarders are boundary interfaces
- Formalize as "proxy nodes" with explicit allowlists and policy metadata
- Enable "From where / From whom / For whom / For what" governance

---

## 9. Research Recommendations for Future Work

### 9.1 Short-Term Research Spikes

1. **Hash Parity Spike**
   - Script comparing `json.dumps` vs JCS hashes for representative payloads
   - Quantify blast radius for existing data

2. **SignedEnvelope Interop Spike**
   - Minimal integration test with reference node
   - Verify signatures work end-to-end

3. **Bundle Cache Persistence Spike**
   - Implement `rid-lib.Cache` in coordinator
   - Test state transfer after restart

### 9.2 Medium-Term Research

1. **Provenance and CATs (Content-Addressable Transformers)**
   - Make transformations verifiable across hops
   - Link input/output manifests with transform metadata

2. **Proxy Node Architecture**
   - Explicit allowlists for external exposure
   - Policy metadata integration

3. **Node Norms and Handshake Protocol**
   - Formalize mutual awareness establishment
   - Document optional normative agreements

### 9.3 Long-Term Research

1. **MCP/A2A Integration**
   - MCP adapter nodes for LLM integration
   - A2A for cross-boundary agent communication

2. **Federated KOI Networks**
   - Multi-org knowledge sharing with access control
   - Consent-based data propagation

---

## 10. Conclusion

RegenAI's KOI system has achieved operational stability with reliability features exceeding the reference implementation. However, true interoperability with BlockScience's KOI-net requires addressing critical gaps in RID parsing, content hashing, and schema compliance.

The recommended strategy is to adopt `rid-lib` as the authoritative source for data structures and hashing, while maintaining our reliability-first internal architecture through a dual-surface API design. This approach achieves protocol alignment without sacrificing operational guarantees.

**Next Steps:**
1. Begin Phase 1 (rid-lib adoption) immediately
2. Establish integration tests with reference nodes
3. Plan data migration for hash changes
4. Prepare upstream contribution proposals

---

## Appendix A: Quick Reference

### A.1 Package Installation

```bash
# Add to requirements.txt
rid-lib==3.2.12
koi-net==1.2.4  # Optional, for reference

# Install
pip install rid-lib koi-net
```

### A.2 Common Code Patterns

```python
# RID parsing
from rid_lib import RID
rid = RID.from_string("orn:koi-net.node:my-node+abc123")
print(rid.context, rid.reference)

# Manifest generation with correct hashing
from rid_lib.ext import Manifest, Bundle
manifest = Manifest.generate(rid, contents)
bundle = Bundle.generate(rid, contents)

# Cache usage
from rid_lib.ext import Cache
cache = Cache(".rid_cache")
cache.write(bundle)
bundle = cache.read(rid)
```

### A.3 Endpoint Reference

| Endpoint | Method | Request Body | Response Body |
|----------|--------|--------------|---------------|
| `/events/broadcast` | POST | `{events: [...]}` | None |
| `/events/poll` | POST | `{rid: "...", limit: N}` | `{events: [...]}` |
| `/bundles/fetch` | POST | `{rids: [...]}` | `{bundles: [...]}` |
| `/manifests/fetch` | POST | `{rids: [...]}` | `{manifests: [...]}` |
| `/rids/fetch` | POST | `{rid_types: [...]}` | `{rids: [...]}` |

### A.4 Event Structure

```json
{
  "rid": "orn:koi-net.node:sensor-1+abc",
  "event_type": "NEW",
  "manifest": {
    "rid": "...",
    "timestamp": "2025-12-22T00:00:00Z",
    "sha256_hash": "..."
  },
  "contents": {
    "title": "...",
    "body": "...",
    "_regen": {
      "source": "github",
      "url": "https://..."
    }
  }
}
```

---

## Appendix B: References

### B.1 Primary Sources

- BlockScience rid-lib: https://github.com/BlockScience/rid-lib
- BlockScience koi-net: https://github.com/BlockScience/koi-net
- KOI Project Index: https://github.com/BlockScience/koi

### B.2 Blog Posts

- "Objects as Reference" (2023): https://blog.block.science/objects-as-reference-toward-robust-first-principles-of-digital-organization/
- "KOI-net Protocol Preview" (2025): https://blog.block.science/a-preview-of-the-koi-net-protocol/
- "Architecting KOI" (2024): https://blog.block.science/architecting-knowledge-organization-infrastructure/
- "KOI Nodes as Neurons" (2025): Local copy in koi-research/sources/blockscience/

### B.3 Internal References

- `koi-research/docs/KOI_PROTOCOL_ALIGNMENT_REFERENCE.md`
- `koi-research/reports/KOI_PROTOCOL_ALIGNMENT_COMPREHENSIVE_REPORT.md`
- `koi-research/reports/KOI_SYSTEM_IMPROVEMENT_RESEARCH.md`

### B.4 Reference Node Implementations

- https://github.com/BlockScience/koi-net-coordinator-node
- https://github.com/BlockScience/koi-net-slack-sensor-node
- https://github.com/BlockScience/koi-net-github-sensor-node
- https://github.com/BlockScience/koi-net-node-template

---

*Report generated by Claude Code based on analysis of RegenAI KOI system and BlockScience protocol specifications.*
