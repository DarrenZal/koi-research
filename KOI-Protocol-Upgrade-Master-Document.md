# KOI Protocol Upgrade: Master Reference Document

> **Purpose:** Authoritative reference for upgrading Regen KOI to full BlockScience koi-net protocol compliance.
> **Status:** Living document — update as phases complete.
> **Created:** 2026-02-14 | **Author:** Darren Zal, with research from BlockScience source analysis

---

## 1. Executive Summary

### Status Dashboard

| Phase | Description | Status | Tests | Remaining Work |
|-------|-------------|--------|-------|----------------|
| **Phase 0** | Protocol Shim Layer | **COMPLETE** | Covered by P0A | — |
| **Phase 0A** | Protocol Contract Hardening | **COMPLETE** | 17 tests | — |
| **Phase 1** | Node Identity & Peer Discovery | **COMPLETE** | 32 tests | — |
| **Phase 2** | rid-lib Full Adoption | **COMPLETE** | 59 tests | — |
| **Phase 3** | Handler Chain Architecture | **COMPLETE** | 78 tests | — |
| **Phase 4** | Federation Testing | **COMPLETE** | 20 tests | — |
| **Phase 5** | Production Deployment & Real Federation | **COMPLETE** | 13 tests | — |

### Key Finding

**Phases 0–3 are complete.** Regen's coordinator is now a discoverable peer with:
- All 5 `/koi-net/*` strict endpoints with signed-only mode
- BlockScience-compatible NodeProfile, EdgeProfile, handshake protocol, and peer persistence
- rid-lib as a first-class dependency — 7 custom RID types replaced with rid-lib subclasses
- `RID_LIB_AVAILABLE` guard pattern fully removed (5 files cleaned)
- NodeProvides populated with all 8 sensor event types + 2 state types
- **Phase 3: Handler chain pipeline** — monolithic broadcast endpoints replaced with 5-phase async pipeline (`koi_protocol/processor/`), matching BlockScience's handler chain architecture
- 351 tests across all phases (305 P0-P3 + 20 P4 federation + 13 P5 identity + 13 P5.1 regression) — P0-P3 committed `bfcb5cf` (2026-02-15), P4 added 2026-02-16, P5 deployed 2026-02-17

**Phases 0–4 complete.** 338 tests validate full protocol compliance including cross-node federation.
**Phase 5 complete (2026-02-17):** Key-derived identity, `/koi-net/health`, signed handshake — deployed to production and federated with Octo Salish Sea. Bidirectional event polling verified: Octo receiving 50+ events per poll cycle from Regen's 8 sensor types.
**Phase 5.1 hardening (2026-02-17):** 13 regression tests codifying production discoveries — handshake format interop, base_url normalization, node name resolution. Preflight script updated to match deployed format.

### Deployment Commits (koi-sensors tag: `phase5-deployed`)

| SHA | Description |
|-----|-------------|
| `bfcb5cf` | Phases 0-3: Handler chain architecture (2026-02-15) |
| `5ad6b4d` | Phase 4: Federation tests (2026-02-16) |
| `6b1fc10` | Phase 5: Key-derived identity, signed federation (2026-02-17) |
| `f9820fa` | Phase 5 fix: Handshake format for Octo interop |
| `f626f25` | Phase 5.1: Regression tests and preflight hardening |

### Production Federation Topology

| Node | RID | Base URL | Status |
|------|-----|----------|--------|
| **Regen** | `orn:koi-net.node:koi-coordinator-main+c5ca332d...` | `https://regen.gaiaai.xyz/api/koi/coordinator` | Live, federated |
| **Octo Salish Sea** | `orn:koi-net.node:octo-salish-sea+50a3c9ea...` | `http://45.132.245.30:8351` | Live, federated |
| **Greater Victoria** | `orn:koi-net.node:greater-victoria+81ec47d8...` | `http://127.0.0.1:8352` (Octo-local) | Leaf node |
| **Cowichan Valley** | `orn:koi-net.node:cowichan-valley+52ae5cd1...` | `http://202.61.242.194:8351` | Leaf node |

### What Regen Brings to the Ecosystem

Regen KOI isn't just catching up — it contributes capabilities BlockScience doesn't have:
- Ecological ontology with 7 platform-specific RID types
- MCP server pattern for AI agent integration
- Hybrid RAG search (semantic + SPARQL + vector)
- On-chain integration with Regen Ledger
- CAT provenance receipts through the processing pipeline
- 8 production data sensors (7 via `start_all.sh` + YouTube via systemd; 18 sensor types available)

---

## 2. Protocol Reference (BlockScience koi-net Spec)

### 2.1 Endpoints

All endpoints live under the `/koi-net` base path. Every request and response is wrapped in `SignedEnvelope[T]`.

| Endpoint | Method | Request Type | Response Type |
|----------|--------|-------------|---------------|
| `/koi-net/events/broadcast` | POST | `SignedEnvelope[EventsPayload]` | None (async void) ¹ |
| `/koi-net/events/poll` | POST | `SignedEnvelope[PollEvents]` | `SignedEnvelope[EventsPayload]` |
| `/koi-net/rids/fetch` | POST | `SignedEnvelope[FetchRids]` | `SignedEnvelope[RidsPayload]` |
| `/koi-net/manifests/fetch` | POST | `SignedEnvelope[FetchManifests]` | `SignedEnvelope[ManifestsPayload]` |
| `/koi-net/bundles/fetch` | POST | `SignedEnvelope[FetchBundles]` | `SignedEnvelope[BundlesPayload]` |

¹ **Protocol delta:** Regen returns `{"status":"ok","processed":N}` in a signed envelope. koi-net's `RequestHandler` has `response_envelope=None` and discards the body — verified non-breaking in Phase 4 test #2.

Path constants defined in `koi-net/src/koi_net/protocol/consts.py`:
```
BROADCAST_EVENTS_PATH = "/events/broadcast"
POLL_EVENTS_PATH      = "/events/poll"
FETCH_RIDS_PATH       = "/rids/fetch"
FETCH_MANIFESTS_PATH  = "/manifests/fetch"
FETCH_BUNDLES_PATH    = "/bundles/fetch"
```

### 2.2 FUN Event Model

Three event types (Forget, Update, New):

```python
class EventType(StrEnum):
    NEW = "NEW"
    UPDATE = "UPDATE"
    FORGET = "FORGET"

class Event(BaseModel):
    rid: RID
    event_type: EventType
    manifest: Manifest | None = None    # None for FORGET
    contents: dict | None = None        # None for FORGET
```

### 2.3 Edge Protocol (Peer Relationships)

```python
class EdgeType(StrEnum):
    WEBHOOK = "WEBHOOK"    # Push-based delivery
    POLL = "POLL"          # Pull-based delivery

class EdgeStatus(StrEnum):
    PROPOSED = "PROPOSED"
    APPROVED = "APPROVED"

class EdgeProfile(BaseModel):
    source: KoiNetNode      # Proposing node
    target: KoiNetNode      # Target node
    edge_type: EdgeType
    status: EdgeStatus
    rid_types: list[RIDType] # Which RID types to subscribe to
```

Edges are negotiated through the event system: a node proposes an edge via a NEW event containing an `EdgeProfile`, and the target node approves/rejects it. This is how nodes subscribe to each other's content.

### 2.4 Handler Chain (5-Phase Pipeline)

The `KnowledgePipeline` processes events through five handler phases:

| Phase | Input | Purpose | Key Decision |
|-------|-------|---------|-------------|
| **RID** | RID only | Filter/route | Fetch manifest or handle FORGET? |
| **Manifest** | RID + manifest | Validate | Fetch bundle or skip? |
| **Bundle** | RID + manifest + contents | Store | Write to cache, set NEW vs UPDATE |
| **Network** | Full bundle | Distribute | Which peers to broadcast to? |
| **Final** | Full bundle | App logic | Custom application behavior |

Handlers return `STOP_CHAIN` sentinel to halt processing at any phase.

### 2.5 Node Identity & Configuration

```python
class NodeConfig(BaseModel):
    server: ServerConfig          # host, port, path ("/koi-net")
    koi_net: KoiNetConfig         # node_name, node_rid, profile, keys, polling

class KoiNetConfig(BaseModel):
    node_name: str
    node_rid: KoiNetNode | None = None
    node_profile: NodeProfile
    cache_directory_path: str = ".rid_cache"
    event_queues_path: str = "event_queues.json"
    private_key_pem_path: str = "priv_key.pem"
    polling_interval: int = 5
    first_contact: NodeContact     # Bootstrap node to connect to
```

### 2.6 Cryptographic Signing

- **Curve:** SECP256R1 (P-256)
- **Hash:** SHA-256
- **Algorithm:** ECDSA
- **Signature encoding:** Base64-encoded raw r||s (32 bytes each, not DER)
- **Key storage:** PKCS8 PEM with password encryption
- **Public key exchange:** Base64-encoded DER format

### 2.7 RID Type System

RID-lib uses a metaclass (`RIDType`) with automatic type registration:

```python
class RID(metaclass=RIDType):
    # Abstract: from_reference(), reference property
    # Concrete: from_string(), __str__(), __eq__(), __hash__()

class ORN(RID):    # Open Resource Name (scheme="orn")
class URN(RID):    # Uniform Resource Name (scheme="urn")
```

Built-in types: `KoiNetNode`, `KoiNetEdge`, `HTTP`, `HTTPS`, `SlackWorkspace`, `SlackChannel`, `SlackMessage`.

Content addressing via `Manifest`:
- JCS (JSON Canonicalization Scheme) → SHA-256
- Base64-encoded filenames in filesystem cache

---

## 3. Current State Assessment (Regen KOI)

### 3.1 Protocol Endpoints — IMPLEMENTED

The coordinator (`koi-sensors/koi_protocol/coordinator/koi_coordinator.py`) implements **both** endpoint surfaces:

**Strict /koi-net/* surface (lines 896–1230):**
- `POST /koi-net/events/poll` — Schema-exact wire format, Z-suffix timestamps, JCS hash recomputation
- `POST /koi-net/events/broadcast` — Accepts `{type: "events_payload", events: [...]}`
- `POST /koi-net/rids/fetch` — Returns `{type: "rids_payload", rids: [...]}`
- `POST /koi-net/manifests/fetch` — Returns strict wire manifests
- `POST /koi-net/bundles/fetch` — Returns bundles with strict manifests

> **~~Interop Caveat — Manifest Field Mismatch~~** — RESOLVED (Phase 0A). `Manifest.from_dict()` accepts 3-field manifests.

> **~~Interop Caveat — Poll Queue Semantics~~** — RESOLVED (Phase 0A). Strict endpoint uses per-node delivery tracking.

**Legacy surface (lines 443–717):** 12 endpoints for backward compatibility with existing sensors.

### 3.2 SignedEnvelope — IMPLEMENTED

`koi-sensors/shared/koi_envelope.py` + coordinator handler (lines 756–894):
- ECDSA P-256 with SHA-256 (matching BlockScience exactly)
- Raw r||s signature format (32 bytes each), base64-encoded
- `exclude_none=True` serialization (critical for FORGET events with `manifest=None`)
- Public key registry loaded from environment
- Target node validation
- Signed responses when requests are signed

> **~~Interop Caveat — Unsigned Requests Accepted~~** — RESOLVED (Phase 0A). Signed-only mode toggle (`KOI_NET_REQUIRE_SIGNED`) implemented.

### 3.3 Wire Format Transformation — IMPLEMENTED

The `_to_koi_net_wire_event()` function (coordinator) converts internal events to BlockScience-compatible format:
- Timestamps converted to Z-suffix (not +00:00)
- Wire events contain exactly 4 fields: `{rid, event_type, manifest, contents}`
- Wire manifests contain exactly 3 fields: `{rid, timestamp, sha256_hash}`
- JCS hash recomputed via rid-lib when available

### 3.4 RID System — COMPLETE (Phase 2)

`koi-sensors/koi_protocol/core/rid_system.py`:
- rid-lib imported unconditionally (no fallback)
- 7 custom ORN classes replaced with re-exports from `shared/rid_types/`
- Backward-compatible aliases (e.g. `TwitterTweetRID = TwitterTweet`) for existing consumers
- New types added: `GitHubFile`, `GmailMessage`, `GmailAttachment` in `shared/rid_types/`
- `YouTubeVideo` updated to `(channel_id, video_id)` format matching sensor usage
- `ORN` re-exported from `rid_lib.core` for consumers importing from `rid_system`
- `NodeProvides` populated with all 8 event types + 2 state types

### 3.5 Bundle System — IMPLEMENTED (Dual-Hash)

`koi-sensors/koi_protocol/core/bundle_system.py`:
- JCS canonical hashing when rid-lib available (`sha256_hash`)
- Legacy `json.dumps(sort_keys=True)` fallback (`legacy_content_hash`)
- Both hashes stored in manifests for migration safety
- `verify_content()` checks JCS hash; `verify_legacy_content()` checks legacy
- **This dual-hash strategy is production-proven** — no data loss during migration

### 3.6 Content Deduplication — IMPLEMENTED

Three persistent state files:
- `coordinator_dedup_state.json` — Content hashes by RID and URL
- `coordinator_sensor_registry.json` — Broadcast sensor tracking
- `coordinator_event_queue.json` — Reliable event delivery across restarts

### 3.7 Semantic Processing Pipeline — IMPLEMENTED (v2 bridge)

`koi-processor/src/core/koi_event_bridge_semantic.py` — 5-stage pipeline (note: production startup launches the **v2 event bridge** on port 8100 at `/process-koi-event`, not the older semantic bridge directly):
1. **Sensor Receipt** → CAT provenance receipt
2. **LLM Extraction** → GPT-4o-mini entity/relationship extraction
3. **Metadata Resolution** → Sensor vs LLM conflict resolution with confidence scores
4. **Knowledge Graph Integration** → Apache Jena Fuseki SPARQL store
5. **Smart Chunking** → Entity-aware text chunking

Each stage generates a CAT receipt establishing provenance chain.

### 3.8 Interop Testing — IMPLEMENTED

Three test files validate protocol compliance:
- `tests/test_koi_net_strict_surface.py` — Wire format, Z timestamps, JCS hashing
- `tests/test_koi_net_signed_envelope.py` — Cross-verification with koi-net signatures
- `scripts/koi_net_interop_test.py` — End-to-end Level 3 test (poll → manifests → bundles)

---

## 3.9 Production Contract: Two Communication Planes

The coordinator serves two distinct communication surfaces that must not be confused:

### Legacy Internal Plane (Sensor ↔ Coordinator)

| Aspect | Value |
|--------|-------|
| **Endpoints** | `/events/*` (poll, confirm, broadcast), `/bundles/*`, `/rids/*`, `/manifests/*` |
| **Ports** | 8005 (coordinator); forwarder is a client (no listen port) |
| **Authentication** | None — internal trust boundary |
| **Event delivery** | Per-node delivery tracking with confirm flow (`koi_node.py:311,341`) |
| **Clients** | 8 active sensors, event forwarder, health monitor |

### Federation Plane (Node ↔ Node)

| Aspect | Value |
|--------|-------|
| **Endpoints** | `/koi-net/events/*`, `/koi-net/rids/*`, `/koi-net/manifests/*`, `/koi-net/bundles/*` |
| **Ports** | 8005 (same coordinator, `/koi-net` prefix) |
| **Authentication** | `SignedEnvelope` required (`KOI_NET_REQUIRE_SIGNED=true` enforced) |
| **Event delivery** | Must implement per-node destructive flush for compliance |
| **Clients** | External koi-net nodes (BlockScience coordinator, future federation partners) |

### Service Routing

| Service | Port | Env Var | Default |
|---------|------|---------|---------|
| Event Forwarder | — (no listen port) | `COORDINATOR_URL`, `EVENT_BRIDGE_URL` | Polls coordinator:8005, POSTs to v2 bridge:8100 |
| Coordinator | 8005 | — | Both legacy and `/koi-net/*` surfaces |
| V2 Event Bridge | 8100 | `EVENT_BRIDGE_URL`, `EVENT_BRIDGE_ENDPOINT` | `/process-koi-event` |
| Semantic Bridge | 8100 | — | Same process as v2 bridge |

> **Federation Access:** Signed-only mode enforced (Phase 0A). The `/koi-net/*` endpoints reject unsigned requests when `KOI_NET_REQUIRE_SIGNED=true`. Verified end-to-end in Phase 4 federation tests (20 tests, all signed).

---

## 4. Gap Analysis

### Gap Analysis (all phases complete)

| Gap | Severity | Phase | Status |
|-----|----------|-------|--------|
| Manifest field compatibility | Critical | Phase 0A | **RESOLVED** — `Manifest.from_dict()` accepts 3-field wire manifests |
| Per-node poll queue semantics | High | Phase 0A | **RESOLVED** — Per-node destructive flush implemented |
| Signed-only enforcement | High | Phase 0A | **RESOLVED** — `KOI_NET_REQUIRE_SIGNED` toggle implemented |
| Stable node identity | High | Phase 0A | **RESOLVED** — `KoiNetNode` RID persisted across restarts |
| Error type mismatch | Medium | Phase 0A | **RESOLVED** — Aligned to BlockScience's 4 error types |
| Edge Negotiation | High | Phase 1 | **RESOLVED** — `EdgeProfile` proposal/approval via `/koi-net/handshake` + `/koi-net/edges/approve` |
| NodeProfile Announcement | High | Phase 1 | **RESOLVED** — `to_koi_net_profile()` + handshake response |
| Peer Discovery via `first_contact` | High | Phase 1 | **RESOLVED** — `handshake_with()` + config-based bootstrap |
| NetworkGraph topology | Medium | Phase 1 | **DEFERRED** — Flat peer list sufficient for current federation; NetworkX graph is a future optimization |
| rid-lib as primary dependency | Medium | Phase 2 | **RESOLVED** — Unconditional imports, all fallback guards removed |
| Custom RID types as rid-lib subclasses | Medium | Phase 2 | **RESOLVED** — 7 types in `shared/rid_types/` + 3 new types |
| Handler Chain architecture | Medium | Phase 3 | **RESOLVED** — 5-phase async pipeline in `koi_protocol/processor/` |
| ProcessorInterface queue | Low | Phase 3 | **DEFERRED** — Current async pipeline handles concurrency; thread-safe queue not needed |
| Polling interval configuration | Low | Phase 1 | **RESOLVED** — Configurable via `NodeConfig` |
| YAML-based NodeConfig | Low | Phase 1 | **RESOLVED** — `NodeConfig` with YAML + env var loading |

### What's NOT Missing (Contrary to Greg's Analysis)

Greg's analysis understated these areas that are already done:
- ~~Protocol endpoints~~ → All 5 implemented with strict wire format
- ~~SignedEnvelope~~ → Full ECDSA P-256 with correct serialization
- ~~Content hashing~~ → JCS canonical hashing operational
- ~~Bundle format~~ → Dual-hash manifests with integrity verification
- ~~Interop testing~~ → Level 3 end-to-end test exists

---

## 5. Implementation Phases

### Phase 0: Protocol Shim — COMPLETE

**Completed:**
- [x] 5 strict `/koi-net/*` endpoints
- [x] SignedEnvelope with ECDSA P-256
- [x] Wire format transformation (Z timestamps, 4-field events, 3-field manifests)
- [x] JCS hash recomputation
- [x] Dual-hash bundle system
- [x] Content deduplication with persistent state
- [x] Level 3 interop test
- [x] `ErrorResponse` model matches BlockScience's 4 error types (folded into Phase 0A)
- [x] `/koi-net/events/broadcast` async void return (folded into Phase 0A)
- [x] FORGET event handling with manifest=None, contents=None (folded into Phase 0A)

### Phase 0A: Protocol Contract Hardening — COMPLETE (17 tests)

**Goal:** Fix the 4 interop-blocking issues (1 Critical + 3 High), 1 Medium runtime error-type mismatch, and 1 validation task identified by code review. The 4 interop-blockers are non-optional — federation will crash or silently misbehave without them. The error-type mismatch requires code changes in the coordinator (lines 818–882 emit wrong types) and the validation task confirms the fixes end-to-end.

**Tasks (~2 days):**

1. **Fix `Manifest.from_dict()` to accept 3-field wire manifests** (Critical):
   - `bundle_system.py:163-164` — `size_bytes` and `content_type` are required but absent in BlockScience manifests
   - Make these fields optional with defaults (`size_bytes=None`, `content_type="application/json"`)
   - Add test: parse `{"rid": "...", "timestamp": "...", "sha256_hash": "..."}` without crash

2. **Migrate strict `/koi-net/events/poll` to per-node destructive flush** (High):
   - Current strict behavior: global read-only queue (`get_queued_events()` at coordinator line 923)
   - Legacy already has per-node semantics: `get_queued_events_for_delivery()` at `koi_node.py:311` + `confirm_delivery()` at `koi_node.py:341`
   - Required: model strict endpoint on legacy's existing per-node tracking, adding destructive flush (`flush_poll_queue(source_node)`)
   - Reference: `koi-net/network/event_queue.py:158` — `NetworkEventQueue.flush_poll_queue()`
   - Legacy sensor behavior preserved as-is

3. **Add signed-only mode toggle for `/koi-net/*` endpoints** (High):
   - Currently: unsigned requests accepted on `/koi-net/*` (coordinator line 783)
   - Required: configurable toggle — `KOI_NET_REQUIRE_SIGNED=true` for federation
   - Internal sensors continue using unsigned legacy endpoints

4. **Correct error types in `ErrorResponse`** (Medium):
   - Wrong: `UNKNOWN_RID`, `INVALID_SIGNATURE`, `UNAUTHORIZED`, `INTERNAL_ERROR`
   - Correct: `unknown_node`, `invalid_key`, `invalid_signature`, `invalid_target`
   - Source: `koi-net/src/koi_net/protocol/errors.py` (lines 4-8)

5. **Generate stable `KoiNetNode` RID, persist across restarts** (High):
   - Current: `f"{node_name}-{datetime.now().timestamp()}"` in `koi_node.py:67` — changes every restart
   - Required: `orn:koi-net.node:<name>+<hash>` format, generated once and persisted to file/env
   - Reference: `rid-lib/src/rid_lib/types/koi_net_node.py`

6. **Add strict interop test with BlockScience-shaped payloads** (Validation):
   - Post a broadcast with 3-field manifest (no `size_bytes`/`content_type`)
   - Poll with `source_node` and verify destructive flush
   - Send unsigned request to `/koi-net/*` with signed-only mode enabled — expect rejection
   - Send a **signed** `POST SignedEnvelope[PollEvents]` to `/koi-net/events/poll` — expect 200 with valid `SignedEnvelope[EventsPayload]` response (confirms federation path works end-to-end, not just rejection)

**Validation:** All 6 tasks pass. A real BlockScience coordinator can POST a broadcast and Regen processes it without crash.

### Phase 1: Node Identity & Peer Discovery — COMPLETE (32 tests)

**Goal:** Regen coordinator can join a koi-net network by connecting to a bootstrap node.

**Delivered:**
- `koi_protocol/protocol/node.py` — `NodeType`, `NodeProvides`, `NodeProfile`
- `koi_protocol/protocol/edge.py` — `EdgeType`, `EdgeStatus`, `EdgeProfile`, `generate_edge_bundle`, `generate_edge_rid`
- `koi_protocol/protocol/config.py` — `NodeConfig`, YAML + env var loading
- `koi_node.py` — `LegacyNodeProfile` rename, `to_koi_net_profile()`
- `koi_coordinator.py` — `/koi-net/handshake`, `/koi-net/edges/approve`, `/koi-net/peers`, `handshake_with()`, peer persistence, first-contact bootstrap
- `tests/test_koi_net_phase1_peer_discovery.py` — 32 tests, 0 regressions

### Phase 2: rid-lib Full Adoption — COMPLETE (59 tests)

**Goal:** Replace custom RID types with rid-lib subclasses. Remove all fallback patterns.

**Delivered (4 sessions):**

**Session 2.1 — Consolidate RID Types (35 tests):**
- Created `shared/rid_types/dev_tools.py` — `GitHubFile(ORN)` with `github.file` namespace
- Created `shared/rid_types/communication.py` — `GmailMessage(ORN)`, `GmailAttachment(ORN)`
- Fixed `shared/rid_types/social_media.py` — `YouTubeVideo` now takes `(channel_id, video_id)`
- Replaced 7 custom classes in `rid_system.py` with re-exports + backward-compatible aliases
- Created `tests/test_rid_lib_migration.py` — string format parity verified for all types

**Session 2.2 — Remove Fallback Guards (5 files cleaned):**
- `rid_system.py` — Unconditional `from rid_lib import RID`
- `bundle_system.py` — Unconditional `from rid_lib.ext.utils import sha256_hash_json`
- `koi_coordinator.py` — Unconditional `from rid_lib.ext import Manifest`
- `persistent_cache.py` — Unconditional rid-lib imports
- `koi_net_interop_test.py` — Unconditional `from rid_lib.ext import Manifest`

**Session 2.3 — Sensor Imports + NodeProvides (24 tests):**
- YouTube sensor imports `YouTubeVideo` from `shared/rid_types/`
- Email sensor imports `GmailMessage`/`GmailAttachment` from `shared/rid_types/`
- `to_koi_net_profile()` now declares 8 event types + 2 state types in `NodeProvides`
- Created `tests/test_rid_lib_phase2_integration.py`

**Session 2.4 — Cleanup + Verification:**
- Removed unused imports, verified `rid-lib==3.2.12` in requirements.txt
- Full regression: **203 tests passed, 1 skipped, 0 failures** across P0–P2

### Phase 3: Handler Chain Architecture — COMPLETE (78 tests)

**Goal:** Replace monolithic coordinator with 5-phase handler pipeline.

**Delivered:**
- `koi_protocol/processor/` — New package with 4 modules:
  - `handler.py` — Handler type system with `STOP_CHAIN` sentinel
  - `knowledge_object.py` — Internal processing state (RID, manifest, contents, event type)
  - `knowledge_pipeline.py` — 5-phase async pipeline: RID → Manifest → Bundle → Network → Final
  - `default_handlers.py` — 6 handlers extracted from monolithic coordinator:
    heartbeat, bundle_normalization, sensor_tracking, dedup, cat_receipt, event_emission
- `koi_coordinator.py` — Both broadcast endpoints now route through unified `_ingest_events()` → `pipeline.process()`
- Strict `/koi-net/events/broadcast` and legacy `/events/broadcast` share the same pipeline
- Regen semantic processing integrable as Final handlers (CAT receipts preserved)
- 78 tests: 14 baseline + 30 pipeline core + 18 handler + 16 integration

### Phase 4: Federation Testing — COMPLETE

**Goal:** Verified interoperability with BlockScience koi-net nodes.

**Approach:** Dedicated Python 3.12+ test environment (`venv-federation/`) with `koi-net==1.2.4` installed, testing against Regen coordinator via ASGI TestClient. Two test tiers:

**Tier 1 — Wire Compatibility (11 tests):** Use koi-net models to craft payloads, post to Regen endpoints, verify responses parse back into koi-net models.

| # | Test | Validates |
|---|------|-----------|
| 1 | `test_broadcast_accepted_with_koi_net_models` | EventsPayload → Regen accepts |
| 2 | `test_broadcast_response_is_discardable` | Protocol delta: Regen returns body, koi-net ignores it |
| 3 | `test_poll_returns_valid_events_payload` | PollEvents → EventsPayload response |
| 4 | `test_fetch_rids_response` | FetchRids → RidsPayload |
| 5 | `test_fetch_manifests_3field` | Manifests have exactly {rid, timestamp, sha256_hash} |
| 6 | `test_fetch_bundles_schema` | Bundles match rid-lib schema |
| 7 | `test_signed_broadcast_roundtrip` | Cross-node signed broadcast + processing |
| 8 | `test_signed_poll_roundtrip` | Signed poll → signed response validates |
| 9 | `test_regen_signed_validates_in_koi_net` | Regen signature → koi-net verification |
| 10 | `test_3field_manifest_roundtrip` | Broadcast → fetch manifest → hash preserved |
| 11 | `test_forget_event_with_none_manifest` | FORGET with manifest=None via exclude_none |

**Tier 2 — Federation Flow (9 tests):** Full federation scenarios with handshake, edge negotiation, and event lifecycle.

| # | Test | Validates |
|---|------|-----------|
| 12 | `test_handshake_with_koi_net_payload` | FORGET+NEW handshake accepted |
| 13 | `test_edge_proposal_from_handshake` | EdgeProfile (PROPOSED) in response |
| 14 | `test_edge_approval_flow` | Edge approval → peer stored |
| 15 | `test_bidirectional_event_flow` | Broadcast → poll queue |
| 16 | `test_rid_type_filtering` | Edge with rid_types (documents current behavior) |
| 17 | `test_peer_persistence_across_restart` | Peer state survives coordinator recreation |
| 18 | `test_concurrent_sensor_broadcasts` | 10 simultaneous broadcasts → all polled |
| 19 | `test_nodeinterface_broadcast_path` | koi-net RequestHandler wire format accepted |
| 20 | `test_full_federation_cycle` | Handshake → broadcast → poll → fetch manifests → fetch bundles |

**Known Protocol Deltas (documented, not breaking):**
1. **Broadcast response body:** Regen returns `{"status":"ok","processed":N}` in a signed envelope; BlockScience expects async void (`response_envelope=None`). koi-net discards the response — not breaking.
2. **rid-lib version:** Federation tests use rid-lib 3.2.12 (not 3.2.14) to avoid RIDType metaclass collision with Regen's custom types in `shared/rid_types/`.

**Validation:** All 20 federation tests pass under `venv-federation/` (Python 3.14 + koi-net 1.2.4). All 305 P0-P3 tests still pass under `venv/` (Python 3.11).

### Phase 5: Production Deployment & Real Federation — IN PROGRESS (13 tests)

**Goal:** Deploy Regen to production with cryptographic identity and establish bidirectional federation with Octo (Salish Sea Knowledge Commons) at `45.132.245.30:8351`.

**Delivered (Step 1–6 complete, Steps 7–10 pending deploy):**

**Step 1 — Key-Derived Identity:**
- `shared/koi_envelope.py`: Added `generate_and_save_keypair()`, `derive_node_rid()`, `node_rid_matches_public_key()`, `public_key_to_b64der()`, `public_key_from_b64der()` — single source of truth for hash derivation
- `koi_protocol/nodes/koi_node.py`: `_resolve_node_id()` now generates/loads ECDSA P-256 keypair from `{cache_dir}/node_private_key.pem`, derives 64-char RID via `sha256(base64(DER(pubkey)))` matching BlockScience canonical pattern
- `koi_protocol/protocol/config.py`: Updated `_generate_missing_identity()` to use `derive_node_rid()` for full 64-char hash (was truncated to 16)
- `koi_protocol/coordinator/koi_coordinator.py`: Coordinator uses `self.koi_node.private_key` instead of separate env var loading; auto-registers own public key
- Identity migration: old `.node_id` backed up to `.node_id.legacy`, peer state updated atomically

**Step 2 — Hash-Length Aliasing (16/64-char):**
- `_lookup_public_key()`: Exact match first, then 16→64 char truncated hash aliasing for legacy peers (Octo uses 16-char)
- `AmbiguousNodeError`: Rejects ambiguous collisions when multiple 64-char peers collide at 16-char truncation
- `_try_learn_public_key_from_handshake()`: TOFU — learns public key from first-contact handshake payload, validates key matches source_node RID

**Step 3 — `/koi-net/health` Endpoint:**
- GET `/koi-net/health` returns nested response matching Octo's contract: `response["node"]["public_key"]`, `response["node"]["node_rid"]`, `peers`, `protocol`, `timestamp`
- Enables automatic public key discovery during handshake

**Step 4 — Signed Edge Approval & Response Verification:**
- `handshake_with()`: Signs `/edges/approve` payload when `envelope_sign=True`
- Verifies response signature when peer key is known (TOFU for first contact)
- Validates envelope↔payload identity binding (anti-spoofing)
- `_try_learn_key_from_health()`: Auto-discovers peer public key from `/koi-net/health` before handshake

**Step 5 — Phase 5 Tests (13 tests):**

| # | Test | Validates |
|---|------|-----------|
| 21 | `test_key_derived_node_rid_format` | RID = `orn:koi-net.node:{name}+{64char}` |
| 22 | `test_node_rid_derives_from_keypair` | Deterministic: same key → same RID |
| 23 | `test_node_rid_different_keys_different_rids` | Different keys → different RIDs |
| 24 | `test_derive_node_rid_matches_blockscience_pattern` | `sha256(b64(DER))` matches manual computation |
| 25 | `test_config_and_koi_node_derive_same_rid` | Both code paths use `derive_node_rid()` |
| 26 | `test_node_rid_matches_64char` | 64-char hash matches public key |
| 27 | `test_node_rid_matches_16char_legacy` | 16-char legacy hash matches public key |
| 28 | `test_node_rid_mismatch` | Wrong key doesn't match |
| 29 | `test_public_key_b64der_roundtrip` | Encode → decode preserves key |
| 30 | `test_generate_and_save_keypair_persists` | Same key loaded across calls |
| 31 | `test_koi_net_health_endpoint` | Returns node_rid, public_key, protocol |
| 32 | `test_signed_handshake_with_signed_approval` | Full handshake + signed approval roundtrip |
| 33 | `test_identity_migration` | Old .node_id backed up, new 64-char RID generated |

**Step 6 — Preflight Script:**
- `scripts/federation_preflight.py`: Automated hard-gate checks (outbound to Octo, inbound reachability, identity consistency, signed handshake dry-run, signed poll roundtrip)
- Exit 0 required before deploy proceeds

**Remaining Steps:**
- Step 7: Production deploy (pull code, auto-generate keypair, set env vars, restart)
- Step 8: Public key exchange with Octo (handshake on startup)
- Step 9: Verify bidirectional event flow
- Step 10: Push commits, update this document

**Validation:** All 338 tests pass (305 P0-P3 on Python 3.11 + 33 P4-P5 federation on Python 3.14).

---

## 6. Regen's Unique Contributions to koi-net

These capabilities position Regen as a valuable node in the koi-net ecosystem, not just a consumer:

### 6.1 Ecological Ontology (8+ Platform-Specific RID Types)
- `orn:twitter.tweet`, `orn:discourse.post`, `orn:notion.page`, `orn:web.page`, `orn:github.file`, `orn:gmail.message`, `orn:gmail.attachment`, `orn:youtube.video`
- All implemented as rid-lib `ORN` subclasses in `shared/rid_types/` (Phase 2 complete)
- Declared in `NodeProvides` — any koi-net peer can filter on these types

### 6.2 Semantic Processing Pipeline
- LLM-powered entity/relationship extraction (GPT-4o-mini)
- Metadata conflict resolution with confidence scoring
- Apache Jena Fuseki SPARQL integration
- Entity-aware smart chunking
- **This is processing depth BlockScience doesn't have** — their handler chain is structural, ours adds intelligence

### 6.3 MCP Server Pattern
- `regen-koi-mcp` exposes KOI knowledge to AI agents (Claude, etc.)
- Entity resolution, SPARQL queries, code graph analysis
- **Novel integration pattern** — AI agents as first-class koi-net consumers

### 6.4 CAT Provenance Chain
- Every processing stage generates a Content Authenticity Token
- Establishes verifiable provenance from sensor → extraction → graph → chunks
- Ties into on-chain Regen Ledger for ecological credit verification

### 6.5 Hybrid RAG Search
- Vector similarity (pgvector) + SPARQL graph queries + full-text search
- Enables semantic questions over the knowledge graph
- Available to any koi-net node via MCP or API

### 6.6 Production Sensor Fleet
- 7 sensors in `start_all.sh` default array (Websites, GitHub, GitHub Activity, Discourse, Notion, Telegram, Twitter) + YouTube managed via systemd = 8 active in production
- 18 sensor types available (including disabled: GitLab, Medium, Podcast, and personal sensors like Gmail)
- Continuous monitoring with deduplication
- Each sensor becomes a koi-net data source post-migration

---

## 7. File Reference

### BlockScience Codebase (Reference Implementation)

| File | Role |
|------|------|
| `koi-net/src/koi_net/server.py` | 5 endpoint definitions |
| `koi-net/src/koi_net/core.py` | `NodeInterface` with dependency injection |
| `koi-net/src/koi_net/config.py` | YAML-based `NodeConfig` |
| `koi-net/src/koi_net/identity.py` | `NodeIdentity` wrapper |
| `koi-net/src/koi_net/protocol/event.py` | FUN event model |
| `koi-net/src/koi_net/protocol/edge.py` | Edge negotiation models |
| `koi-net/src/koi_net/protocol/envelope.py` | `SignedEnvelope` generic wrapper |
| `koi-net/src/koi_net/protocol/secure.py` | ECDSA signing (SECP256R1) |
| `koi-net/src/koi_net/protocol/errors.py` | 4 error types |
| `koi-net/src/koi_net/protocol/consts.py` | Path constants |
| `koi-net/src/koi_net/processor/knowledge_pipeline.py` | 5-phase handler chain |
| `koi-net/src/koi_net/processor/handler.py` | Handler type system, STOP_CHAIN |
| `koi-net/src/koi_net/processor/default_handlers.py` | Reference handler implementations |
| `koi-net/src/koi_net/processor/knowledge_object.py` | Internal processing state |
| `koi-net/src/koi_net/processor/interface.py` | Thread-safe queue |
| `koi-net/src/koi_net/network/graph.py` | NetworkX topology |
| `koi-net/src/koi_net/network/request_handler.py` | Inter-node HTTP client |
| `koi-net/src/koi_net/network/event_queue.py` | Poll/webhook queues |
| `koi-net/src/koi_net/effector.py` | 3-level action dereferencing |
| `koi-net/src/koi_net/context.py` | Dependency bundles for handlers |
| `rid-lib/src/rid_lib/core.py` | RID metaclass type system |
| `rid-lib/src/rid_lib/ext/cache.py` | Filesystem cache |
| `rid-lib/src/rid_lib/ext/bundle.py` | Bundle with manifest |
| `rid-lib/src/rid_lib/ext/manifest.py` | Content-addressed hashing |
| `rid-lib/src/rid_lib/ext/utils.py` | JCS canonical hashing |
| `rid-lib/src/rid_lib/utils.py` | RID string parsing |
| `koi-net/examples/coordinator.py` | Reference coordinator |
| `koi-net/examples/partial.py` | Reference partial node |

### Regen Codebase (Production)

| File | Role |
|------|------|
| `koi-sensors/koi_protocol/coordinator/koi_coordinator.py` | Main coordinator (2057 lines) |
| `koi-sensors/shared/koi_envelope.py` | SignedEnvelope implementation |
| `koi-sensors/koi_protocol/core/rid_system.py` | RID base classes + re-exports from shared/rid_types/ |
| `koi-sensors/shared/rid_types/` | rid-lib ORN subclasses (social_media, web_content, productivity, dev_tools, communication) |
| `koi-sensors/koi_protocol/protocol/` | NodeProfile, EdgeProfile, NodeConfig (Phase 1) |
| `koi-sensors/koi_protocol/core/bundle_system.py` | Dual-hash bundle system |
| `koi-sensors/sensors/discourse/discourse_sensor_koi.py` | Example sensor (KOI pattern) |
| `koi-processor/src/core/koi_event_bridge_v2.py` | Production event bridge (launched by `start_all.sh:169`, imports from semantic bridge) |
| `koi-processor/src/core/koi_event_bridge_semantic.py` | Semantic pipeline module (imported by v2 bridge) |
| `koi-sensors/tests/test_koi_protocol_alignment_p0.py` | P0 alignment tests (33 tests) |
| `koi-sensors/tests/test_koi_net_signed_envelope.py` | Envelope cross-verification (18 tests) |
| `koi-sensors/tests/test_koi_net_strict_surface.py` | Wire format tests (28 tests) |
| `koi-sensors/tests/test_koi_net_phase1_peer_discovery.py` | P1 peer discovery tests (32 tests) |
| `koi-sensors/tests/test_persistent_cache_p2a.py` | Persistent cache tests (33 tests) |
| `koi-sensors/tests/test_rid_lib_migration.py` | P2 RID type migration parity tests (35 tests) |
| `koi-sensors/tests/test_rid_lib_phase2_integration.py` | P2 integration tests (24 tests) |
| `koi-sensors/tests/federation/conftest.py` | P4 federation fixtures (signed-only, keypairs, ASGI client) |
| `koi-sensors/tests/federation/test_wire_compat.py` | P4 Tier 1: wire compatibility (11 tests) |
| `koi-sensors/tests/federation/test_federation_flow.py` | P4 Tier 2: federation flow (9 tests) |
| `koi-sensors/scripts/koi_net_interop_test.py` | Level 3 interop test (manual) |

### Source Documentation (BlockScience Blog Posts)

| File | Topic |
|------|-------|
| `koi-research/sources/blockscience/blog-architecting-koi.md` | Architecture overview |
| `koi-research/sources/blockscience/blog-koi-net-protocol-preview.md` | Protocol design |
| `koi-research/sources/blockscience/blog-koi-network-protocol-interlay.md` | Network interlay concepts |
| `koi-research/sources/blockscience/blog-koi-nodes-as-neurons.md` | Node philosophy |
| `koi-research/sources/blockscience/blog-language-for-knowledge-networks.md` | Knowledge network theory |
| `koi-research/sources/blockscience/blog-objects-as-reference.md` | RID design philosophy |

---

## 8. Validation Criteria

### Phase 0 Complete When: **DONE**
- [x] `ErrorResponse` matches BlockScience's 4 error types exactly
- [x] Broadcast endpoint returns async void (no response body)
- [x] FORGET events propagate with `manifest=None, contents=None`
- [x] All existing interop tests pass

### Phase 0A Complete When: **DONE** (17 tests)
- [x] `Manifest.from_dict()` accepts 3-field BlockScience manifests without crash
- [x] Per-node poll queues with destructive flush operational
- [x] Signed-only mode toggle exists and rejects unsigned `/koi-net/*` requests when enabled
- [x] Node identity persisted as stable `KoiNetNode` RID across restarts
- [x] Interop test posts BlockScience-shaped payload end-to-end without error
- [x] Signed POST with valid `SignedEnvelope[PollEvents]` returns 200 with `SignedEnvelope[EventsPayload]`

### Phase 1 Complete When: **DONE** (32 tests)
- [x] Regen node generates `KoiNetNode` RID on startup
- [x] `NodeProfile`, `EdgeProfile` with BlockScience-compatible models
- [x] `NodeConfig` with YAML + env var loading
- [x] Handshake protocol (`/koi-net/handshake`, `/koi-net/edges/approve`, `/koi-net/peers`)
- [x] `handshake_with()` for peer discovery
- [x] Peer persistence across restarts
- [x] First-contact bootstrap from config

### Phase 2 Complete When: **DONE** (59 tests: 35 migration + 24 integration)
- [x] `rid-lib` is a required dependency (no optional imports)
- [x] All 7 custom RID types replaced with rid-lib `ORN` subclasses from `shared/rid_types/`
- [x] 2 new types added: `GitHubFile`, `GmailMessage`, `GmailAttachment`
- [x] `YouTubeVideo` updated to match sensor `(channel_id, video_id)` format
- [x] Backward-compatible aliases preserve all existing imports
- [x] No `RID_LIB_AVAILABLE` checks in codebase (5 files cleaned)
- [x] `NodeProvides` populated with all 8 sensor event types + 2 state types
- [x] All 8 active sensors work with rid-lib types
- [x] Full regression: 203 tests across P0–P2, 0 failures

### Phase 3 Complete When: **DONE** (78 tests)
- [x] `KnowledgePipeline` processes events through 5 phases
- [x] Default handlers (RID, Manifest, Bundle, Network) operational
- [x] Regen semantic processing integrable as Final handlers
- [x] CAT receipt handler in pipeline (heartbeat, bundle_normalization, sensor_tracking, dedup, cat_receipt, event_emission)
- [x] Async pipeline handles concurrent events via `_ingest_events()`
- [x] All existing interop tests still pass (305 total, 0 failures)

### Phase 4 Complete When:
- [x] koi-net model payloads accepted by all Regen /koi-net/* endpoints (tests 1-6)
- [x] SignedEnvelope verified cross-node (tests 7-9)
- [x] 3-field manifest hash preserved through broadcast→fetch roundtrip (test 10)
- [x] FORGET events with manifest=None serialize correctly (test 11)
- [x] Handshake with FORGET+NEW pattern accepted (test 12)
- [x] Edge negotiation works: PROPOSED → APPROVED (tests 13-14)
- [x] Events flow bidirectionally: broadcast → poll queue (test 15)
- [x] Peer persistence survives coordinator restart (test 17)
- [x] Load test with 10 concurrent sensor broadcasts passes (test 18)
- [x] koi-net RequestHandler wire format accepted by Regen (test 19)
- [x] Full federation cycle: handshake → broadcast → poll → fetch manifests → fetch bundles (test 20)

---

## Appendix A: Timeline

| Phase | Status | Tests | Completed |
|-------|--------|-------|-----------|
| Phase 0 | **COMPLETE** | Covered by P0A | 2026-02-14 |
| Phase 0A | **COMPLETE** | 17 | 2026-02-14 |
| Phase 1 | **COMPLETE** | 32 | 2026-02-14 |
| Phase 2 | **COMPLETE** | 59 | 2026-02-14 |
| Phase 3 | **COMPLETE** | 78 tests (14 baseline + 30 pipeline core + 18 handler + 16 integration) | 2026-02-15 |
| Phase 4 | **COMPLETE** | 20 tests (11 wire compat + 9 federation flow) | 2026-02-16 |
| **Total tests** | | **325 passed** | (305 P0-P3 + 20 P4) |

## Appendix B: Architecture Diagram

```
                    ┌─────────────────────────────────┐
                    │     BlockScience Coordinator     │
                    │    (koi-net reference impl)      │
                    └──────────┬──────────────────────┘
                               │ /koi-net/* endpoints
                               │ SignedEnvelope
                    ┌──────────▼──────────────────────┐
                    │      Regen KOI Coordinator       │
                    │  (koi_coordinator.py - 2057 LOC) │
                    │                                  │
                    │  ┌──────────┐  ┌──────────────┐  │
                    │  │ /koi-net │  │   Legacy      │  │
                    │  │ strict   │  │   endpoints   │  │
                    │  └────┬─────┘  └──────┬───────┘  │
                    │       │               │          │
                    │  ┌────▼───────────────▼───────┐  │
                    │  │   SignedEnvelope Handler    │  │
                    │  │   (ECDSA P-256 / SHA-256)  │  │
                    │  └────────────┬───────────────┘  │
                    │               │                  │
                    │  ┌────────────▼───────────────┐  │
                    │  │  Bundle System (Dual-Hash) │  │
                    │  │  JCS primary + legacy      │  │
                    │  └────────────┬───────────────┘  │
                    │               │                  │
                    │  ┌────────────▼───────────────┐  │
                    │  │  Content Deduplication     │  │
                    │  │  (3 persistent state files)│  │
                    │  └───────────────────────────┘  │
                    └──────────┬───────────────────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
    ┌─────────▼──┐   ┌────────▼───┐   ┌────────▼───┐
    │  8 Sensors  │   │  Event     │   │  MCP       │
    │  (Discourse,│   │  Bridge    │   │  Server    │
    │  GitHub,    │   │  Semantic  │   │  (AI agent │
    │  Notion...) │   │  Pipeline  │   │  access)   │
    └─────────────┘   └────┬───────┘   └────────────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
        ┌─────▼────┐ ┌────▼─────┐ ┌────▼─────┐
        │ LLM      │ │ Jena     │ │ Smart    │
        │ Extract  │ │ Fuseki   │ │ Chunker  │
        │ (GPT-4o) │ │ (SPARQL) │ │ + pgvec  │
        └──────────┘ └──────────┘ └──────────┘
```
