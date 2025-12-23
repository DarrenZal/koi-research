# KOI Protocol Alignment Reference (Synthesized)

This document is the authoritative reference for RegenAI's KOI pipeline alignment with BlockScience's KOI-net protocol. It synthesizes findings from:
- `koi-research/reports/KOI_SYSTEM_IMPROVEMENT_RESEARCH.md`
- `koi-research/reports/KOI_PROTOCOL_ALIGNMENT_COMPREHENSIVE_REPORT.md`
- `koi-research/reports/KOI_ALIGNMENT_AND_IMPROVEMENT_STRATEGY_2025_12.md`
- `koi-research/reports/KOI_PREIMPLEMENTATION_RESEARCH.md` *(Dec 2025 — spike results + decision recommendations)*

---

## Status Summary (Dec 2025)

**Operational reliability track**: ✅ All services operational, KOI audit issues resolved.
**Strict KOI-net interoperability track**: ✅ Level 3 (SignedEnvelope) complete as of Dec 2025.

### Operational health (current pipeline)

| Area | Status |
|------|--------|
| POST polling endpoints | ✅ Done — All forwarders and docs use POST |
| Delivery confirmation | ✅ Done — Ack only on `success: true` |
| HTTP error semantics | ✅ Done — Bridges return 500 on failure |
| SignedEnvelope support (local) | ✅ Done — Optional, env-configurable |
| Queue persistence | ✅ Done — JSON file (coordinator + sensors) |
| Pending/processed state | ✅ Done — Sensors track before/after emit |

### Interop readiness (KOI-net reference nodes)

| Interop level | Meaning | Status |
|---|---|---|
| Level 1 | Wire shapes (unsigned) | ✅ Complete — All 5 `/koi-net/*` endpoints |
| Level 2 | Wire + **rid-lib hashing + RID parsing** | ✅ Complete — P0/P1a (rid-lib JCS, Z timestamps) |
| Level 3 | Level 2 + **SignedEnvelope strict schema** | ✅ Complete — P1b (Pydantic exclude_none, ErrorResponse) |
| Level 3+ | Level 3 + **durable state transfer** | ✅ Complete — P2a/P2b (persistent cache, retention) |
| Level 4 | Reference-node substitution (`koi-net` NodeInterface/server) | 🔴 Not planned (maintain custom reliability features) |

### Completed phases

**P0 — Foundation (Dec 2025):** ✅ Complete
- `rid-lib==3.2.12` pinned, JCS hashing for sha256_hash
- Dual-hash support for backward compatibility

**P1a — Level 2 Interop (Dec 2025):** ✅ Complete
- `/koi-net/events/poll` with JCS hash recompute, Z timestamps
- Schema-exact wire models

**P1b — Level 3 Interop (Dec 2025):** ✅ Complete
- `koi_envelope.py` consolidated (Pydantic models, exclude_none=True)
- All 5 `/koi-net/*` endpoints with SignedEnvelope support
- ErrorResponse for KOI-net error semantics
- 14 cross-verification tests passing

### Completed phases (continued)

**P2a — Durable State Transfer (Dec 2025):** ✅ Complete
- Persistent bundle cache using `rid_lib.ext.Cache`
- Write-through caching (memory + disk)
- FORGET event deletes from cache
- UPDATE event overwrites same RID
- Bundles survive coordinator restarts
- 47 tests passing (26 P2a + 21 P2b)

**P2b — Retention + Monitoring (Dec 2025):** ✅ Complete
- Max-size/max-age pruning policy
- Protected bundles (NodeProfile, identity, config) never pruned
- Metrics: bundle count, disk usage, alerts
- Systemd timer for scheduled daily pruning (3 AM)
- Environment configuration via `KOI_CACHE_*` variables

### Next priorities

**P3 — Optional future work:**
1. Formalize proxy-node boundary patterns + provenance/CATs.
2. KOI-net secure parity (NodeProfile trust chain) — only if accepting signed traffic from arbitrary nodes.
3. Propose upstream improvements (optional ack/confirm, persistence hooks, reliability modes).

---

## KOI Protocol Source of Truth

**Authoritative sources** (BlockScience contracts):

| Package | GitHub | PyPI | What it provides |
|---------|--------|------|------------------|
| **rid-lib** | https://github.com/BlockScience/rid-lib | `pip install rid-lib` | RID v3 parsing, Manifest/Bundle/Cache, hashing contract |
| **koi-net** | https://github.com/BlockScience/koi-net | `pip install koi-net` | NodeInterface, protocol endpoints, SignedEnvelope + secure mode |

**Local copies (offline reference):**
- `koi-research/sources/blockscience/rid-lib` (version 3.2.8)
- `koi-research/sources/blockscience/koi-net`

**Current dependency status (Dec 2025):**
- ✅ `rid-lib==3.2.12` pinned in `koi-sensors/requirements.txt` and `koi-processor/requirements.txt` (P0.1 hygiene)
- Sensor venvs fall back to legacy hashing if rid-lib not installed (ImportError caught in `bundle_system.py`)

### rid-lib defines the data contracts

- `RID.from_string()` is the canonical RID parser (RID v3; "all URIs can be valid RIDs").
- `Manifest` schema is **strict**: `{rid, timestamp, sha256_hash}`.
- Hashing is **JCS canonicalization** → `rid_lib.ext.utils.sha256_hash_json()` / `Manifest.generate(...)`.
- `Bundle` schema is **strict**: `{manifest, contents}` (RID is derived from `manifest.rid`).
- `Cache` is the reference filesystem persistence mechanism for bundles/manifests.

### koi-net defines the wire protocol contracts

**Endpoints (POST + JSON):**
- `/events/broadcast`
- `/events/poll`
- `/bundles/fetch`
- `/manifests/fetch`
- `/rids/fetch`

**KOI-net NodeServer default base path:** reference server mounts endpoints under `/koi-net/*` (see `koi-research/sources/blockscience/koi-net/src/koi_net/server.py`).

**Events are FUN ("Forget/Update/New") signals:** they are **signals** about cache state changes; reconciliation happens via fetch endpoints.

**SignedEnvelope contract (critical for interop):**
- Model: `{payload, source_node, target_node, signature}`
- Signature bytes are derived from Pydantic model serialization (`model_dump_json(exclude_none=True)`) of the **unsigned envelope**.
- KOI-net parses JSON into strict models first; **unknown fields are discarded before signature verification**.

**Implication:** our crypto implementation can be compatible, but any **extra keys** inside a signed payload will cause KOI-net verification to fail.

### KOI-net secure identity + trust (reference behavior)

KOI-net secure mode couples identity to keys:
- Node IDs are `KoiNetNode` ORNs: `orn:koi-net.node:<name>+<hash>`.
- The `<hash>` is derived from the node's public key.
- Trust distribution is via **NodeProfile bundles** stored in the network cache/dereference layer (see `koi-research/sources/blockscience/koi-net/src/koi_net/secure.py`).

This differs from RegenAI's current out-of-band key map approach (env-provided `node_id -> PEM`).

### Practical adoption note (runtime constraint)

The local KOI-net sources include Python 3.12+ syntax (e.g., `type X = ...`), which can block library adoption in Python 3.11 runtimes. Treat "full koi-net as a library" as a deliberate runtime decision.

---

## Protocol architecture overview (what KOI "is", in layers)

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

Core concepts:
- **RIDs (Reference Identifiers):** can be ORNs or URIs; used to communicate about resources without necessarily sharing the referent.
- **RID examples:** `https://github.com/BlockScience/koi-net`, `orn:slack.message:TA2E6KPK3/C07BKQX0EVC/1721669683.087619`
- **FUN events:** *Forget/Update/New* signals about cache state changes.
- **Full vs partial nodes:** servers implement endpoints; clients poll.
- **Node roles (conceptual):** sensors observe; processors transform; actuators act; proxy nodes provide boundary interfaces between organizations/systems.

---

## Conceptual + governance synthesis (why KOI is shaped this way)

The KOI-net/rid-lib packages define the **physical wire contracts**. BlockScience's blog posts clarify intended KOI design principles (governance, boundaries, interoperability, provenance) that help interpret what should (and should not) be part of the protocol surface.

### "Architecting KOI" (Zargham, 2024)
*Source: `koi-research/sources/blockscience/blog-architecting-koi.md`*

- Governance is ongoing expectation alignment between narratives, specs, implementations, and operator/user experience (feedback loop).
- Architecture spans **conceptual / functional / logical / physical** levels; KOI-net/rid-lib are primarily physical-level contracts.
- Knowledge processing is a **closed loop** (compose/decompose/decorate/mutate/curate/search/generate); outcomes and non-idempotence motivate versioning, provenance, and reconciliation.
- Requirements lens: **"From where / From whom / For whom / For what"** → motivates explicit policy/consent metadata and bounded exposure at boundaries.

### "Objects as Reference" (Reed, 2023/2024)
*Source: `koi-research/sources/blockscience/blog-objects-as-reference.md`*

- Digital objects are **references to referents**; separating reference vs referent is foundational for interop across system boundaries.
- Endogenous vs exogenous identifiers: content-addressed IDs (endogenous) elevate canonical hashing from "implementation detail" to "interop primitive".
- Multiple agents can hold different "perspectives" on "the same thing"; coordination is about alignment mechanisms, not one universal internal identifier.

**Application to RegenAI:** Our extended manifest metadata conflates "Reference" with "Referent's Description." Move all metadata (URL, author, source) into `contents` (the referent); keep manifest as pure "shipping label" (RID + Hash + Timestamp only).

### "A Language for Knowledge Networks" (Zargham & Ben-Meir, 2023)
*Source: `koi-research/sources/blockscience/blog-language-for-knowledge-networks.md`*

- "Dialect" model: local systems should remain purpose-fit; interop provides a **common language** without forcing uniform internal structure.
- "Share knowledge, not rules": merging rules across orgs harms autonomy; interop should increase communicability of organizational knowledge.
- Map vs territory / beliefs vs facts: RIDs help communicate knowledge while preserving boundaries (avoid mistaking internal updates for external changes).
- LLMs as "calm technology" interfaces: access control + governance become first-class requirements when LLMs mediate internality/externality.
- Learning vs reflex agents ("cyborganizations"): treat higher-order verification (e.g., confirmation/reconciliation) as a learning layer around a reflexive signaling core.

### "KOI-net Protocol Preview" (BlockScience, 2025)
*Source: `koi-research/sources/blockscience/blog-koi-net-protocol-preview.md`*

- RIDs preserve access control: communicate about proprietary resources without necessarily sharing referents.
- Event vs state communication: FUN events signal cache change; fetch endpoints enable reconciliation.
- Boundary-aware roles and fractal networks: a KOI-net can present as a node; proxy nodes matter.
- Protocol layering: MCP/A2A adapters can exist as boundary interfaces without becoming KOI-net requirements.

### "KOI Network Protocol x Project Interlay" (BlockScience, 2025)
*Source: `koi-research/sources/blockscience/blog-koi-network-protocol-interlay.md`*

- Network configuration as knowledge objects: nodes/edges can themselves be RID-addressed objects; nodes may share perspectives selectively via access-controlled proxy nodes.
- Handshake + node norms: establishing mutual awareness and optional "normative agreements" is a path to stability without enforcing uniform internals.
- Layered protocols ("OSI B"): keep protocol surfaces minimal and local; allow emergent global behavior from local interactions.
- FUN vs CRUD: FUN signals are primitives; CRUD is oversight/admin plane (maps cleanly to "strict interop surface" vs "ops plane").
- Provenance/trust: CATs (Content‑Addressable Transformers) matter for multi-hop attribution and verification.

### "KOI Nodes as Neurons" (Sisson, 2025)
*Source: `koi-research/sources/blockscience/blog-koi-nodes-as-neurons.md`*

- Reflexive signaling: fast reactions to stimuli ("patellar tendon reflex" analogy) help explain KOI-net's best-effort/event-first orientation.
- Observed → conceived mapping: sensors/decoders transform observed space into conceived space; calibration/validation often includes humans.
- Operational implication: emphasize configurable templates, feedback, metrics, and provenance for transformations rather than hardcoding one-off pipelines.

**Key insight:** The reference koi-net's async "fire-and-forget" model is **intentional**, not a limitation. Nodes operate reflexively like biological neurons. Our "confirm-on-success" model is a "learning agent" wrapper — a valid node-specific behavior, not a protocol requirement.

---

## Protocol alignment principles (expanded)

Baseline principles (still valid):
1. **Protocol-first**: Follow KOI-net request/response semantics and payload shapes.
2. **Minimal extensions**: Add what is necessary for reliability/observability; keep extensions optional.
3. **Backwards compatibility**: Maintain interop with reference implementations; deprecate deviations gradually.
4. **Upstream first**: If a change is broadly useful (ack/confirm, persistence hooks), propose it upstream.
5. **No fragmentation**: Avoid forking the protocol; keep changes compatible or explicitly optional.

Additional principles synthesized from the reports + blog framing:
- **Dialect model (common language, not uniform internals):** expose strict KOI-net wire models while allowing richer internal models ("share knowledge, not rules").
- **FUN vs CRUD plane separation:** keep the strict KOI-net surface minimal (FUN/event+state plane); keep ops/admin/reliability features on a separate surface.
- **Wire vs internal model separation:** anything that may be signed must be schema-exact; put operational metadata into `contents` under a stable namespace.
- **Reliability is a node behavior:** treat "confirm-on-success" as a local learning/verification layer, not a protocol requirement.

---

## Background Reading

**KOI research overview** (history and context):
- Local: `koi-research/sources/blockscience/koi/README.md` — Inventory of KOI repos (v1–v3)
- GitHub: https://github.com/BlockScience/koi — Project index and version history

**BlockScience blog posts** (conceptual foundations; local copies preferred):
- [Architecting Knowledge Organization Infrastructure](../sources/blockscience/blog-architecting-koi.md)
- [A Preview of the KOI-net Protocol](../sources/blockscience/blog-koi-net-protocol-preview.md)
- [KOI Nodes as Neurons](../sources/blockscience/blog-koi-nodes-as-neurons.md)
- [KOI Network Protocol x Project Interlay](../sources/blockscience/blog-koi-network-protocol-interlay.md)
- [A Language for Knowledge Networks](../sources/blockscience/blog-language-for-knowledge-networks.md)
- [Objects as Reference](../sources/blockscience/blog-objects-as-reference.md)

**Related projects:**
- Metagov KOI Pond (v2): https://metagov.org/projects/koi-pond
- RMIT Slack Telescope: https://github.com/metagov/slack-telescope
- KOI Obsidian Plugin: https://github.com/metagov/koi-obsidian-plugin

**Reference node implementations** (examples to learn from):
- https://github.com/BlockScience/koi-net-coordinator-node
- https://github.com/BlockScience/koi-net-slack-sensor-node
- https://github.com/BlockScience/koi-net-github-sensor-node
- https://github.com/BlockScience/koi-net-node-template

---

## Current RegenAI KOI system (what we have today)

### System dataflow (operational)

1. Sensors broadcast events to the coordinator:
   - `koi-sensors/koi_protocol/coordinator/koi_coordinator.py` → `POST /events/broadcast`
2. Coordinator queues events for polling:
   - `koi-sensors/koi_protocol/nodes/koi_node.py` (delivery tracking + JSON persistence)
3. Forwarders poll and forward to downstream processing:
   - `koi-processor/scripts/coordinator_to_eventbridge_forwarder.py` (poll → forward → confirm-on-success)
4. Event bridges process content and store outputs:
   - `koi-processor/src/core/koi_event_bridge_v2.py`
   - `koi-processor/src/core/koi_event_bridge_semantic.py`

### Reliability advantages (vs KOI-net reference defaults)

- Confirm-on-success semantics (downstream success gating).
- Queue persistence (JSON), and pending/processed tracking.
- HTTP 500 on failure from event bridges (clear failure semantics).

### Current local behavior (summary)

- Coordinator supports legacy `GET /events/poll` and KOI-net `POST /events/poll`; internal forwarders now use POST with `include_event_ids`.
- Forwarders confirm delivery only when downstream returns `success: true` in the response body.
- Coordinator exposes KOI-net-like POST endpoints (`/events/poll`, `/rids/fetch`, `/manifests/fetch`, `/bundles/fetch`) with optional SignedEnvelope handling.
- SignedEnvelope verification/signing is supported when keys are configured; GET endpoints remain for legacy clients.
- Event bridge expects KOI-like event payloads but does not enforce signed envelopes.

---

## Current Production Contract (Dec 2025)

This section documents the exact state of the KOI-net interop surface in production.

### `/koi-net/*` Endpoints

| Endpoint | Method | Request Model | Response Model | SignedEnvelope |
|----------|--------|---------------|----------------|----------------|
| `/koi-net/events/broadcast` | POST | `EventsPayload` | `BroadcastResponse` | Optional |
| `/koi-net/events/poll` | POST | `PollEvents` | `EventsPayload` | Optional |
| `/koi-net/rids/fetch` | POST | `FetchRids` | `RidsPayload` | Optional |
| `/koi-net/manifests/fetch` | POST | `FetchManifests` | `ManifestsPayload` | Optional |
| `/koi-net/bundles/fetch` | POST | `FetchBundles` | `BundlesPayload` | Optional |

**Wire format:** All `/koi-net/*` responses use strict KOI-net schemas:
- Manifest: `{rid, timestamp, sha256_hash}` only (no size_bytes, content_type, metadata)
- Bundle: `{manifest, contents}` only
- Timestamps: `Z` suffix (not `+00:00`)

**Note:** `/koi-net/events/poll` is read-only; use internal `/events/confirm` for delivery acknowledgment.

### Node Identity

**Format:** `orn:koi-net.node:<name>+<hash>`

**Hash derivation:** Full 64-character hex SHA-256 of the DER-encoded public key (base64):
```python
node_id_hash = sha256(base64.b64decode(public_key_der_b64)).hexdigest()
```

**Current approach:** Out-of-band key distribution via `KOI_PUBLIC_KEYS_JSON` environment variable.

### Persistent Bundle Cache (P2a)

**Directory:** Configured via `KOI_CACHE_DIR` environment variable.
- Default: `/opt/projects/koi-sensors/.rid_cache`
- Production: Set in coordinator `.env`

**What's persisted:** Strict rid-lib Bundle format `{manifest: {rid, timestamp, sha256_hash}, contents}`
- Internal extras (size_bytes, content_type, metadata) are **not** persisted
- Internal extras are reconstructed from contents on read

**Cache operations:**
- `cache.write(bundle)` — Write-through to memory + disk
- `cache.read(rid)` — Memory-first, then disk
- `cache.delete(rid)` — Remove from both memory and disk
- `cache.load_all()` — Load all bundles from disk on startup

### Retention Policy (P2b)

**Environment variables:**
| Variable | Default | Description |
|----------|---------|-------------|
| `KOI_CACHE_MAX_SIZE_MB` | 500 | Maximum cache size in MB |
| `KOI_CACHE_MAX_AGE_DAYS` | 30 | Maximum bundle age in days |
| `KOI_CACHE_DISK_ALERT_PERCENT` | 80 | Disk usage alert threshold |

**Protected RID patterns** (never pruned):
- `orn:koi.node_profile:*` — Node profile bundles
- `orn:koi.identity:*` — Node identity bundles
- `orn:koi.config:*` — Configuration bundles

**Pruning behavior:**
1. Age-based pruning runs first (removes bundles older than max_age_days)
2. Size-based pruning runs second (removes oldest bundles until under max_size_mb)
3. Protected bundles are skipped in both phases

**Systemd timer:** `koi-cache-prune.timer`
- Runs daily at 3:00 AM
- Executes `scripts/prune_bundle_cache.py`
- Logs to systemd journal

**Manual pruning:**
```bash
# Dry run
./venv/bin/python scripts/prune_bundle_cache.py --dry-run

# Metrics only
./venv/bin/python scripts/prune_bundle_cache.py --metrics-only

# Execute prune
./venv/bin/python scripts/prune_bundle_cache.py
```

### Known Gotchas

1. **`/koi-net/events/poll` is read-only**: It returns events but does NOT mark them as delivered. Use internal `/events/confirm` endpoint for acknowledgment.

2. **Timestamp format**: Wire format uses `Z` suffix, internal storage may use `+00:00`. The persistent cache normalizes to `Z` on read.

3. **Hash recomputation**: When returning bundles via `/koi-net/*`, the coordinator recomputes `sha256_hash` using rid-lib JCS canonicalization, even if the original event only had a legacy hash.

4. **Protected bundles**: If you create bundles with RIDs matching protected patterns, they will never be pruned. Use this intentionally for identity/config data.

5. **Seed script limitation**: `scripts/seed_bundle_cache.py` only seeds from `coordinator_event_queue.json`, which contains recent pending events. Historical events require a separate database backfill.

---

### Audit issue status (KOI-related) — resolved

| Issue | Status | Notes |
|-------|--------|-------|
| Forwarder confirms on HTTP 200 only | DONE | Forwarders now confirm only on `success: true`. |
| Bridges return HTTP 200 on failure | DONE | Bridges now return HTTP 500 on failure; forwarders handle both. |
| Events acked when processing failed | DONE | Acks only after downstream success. |
| Double-enqueue in coordinator | DONE | Broadcast no longer queues twice. |
| No SignedEnvelope handling | DONE | Optional SignedEnvelope support added. |
| Event queue is in-memory only | DONE | Queue persists to JSON. |
| No pending vs confirmed state | DONE | Pending tracking added in sensor state. |

---

## Critical Interoperability Gaps (Research Findings)

While operationally stable and "KOI-shaped", we are **not wire-compatible** with reference KOI-net nodes. These gaps must be addressed for true interoperability.

### P0 — Foundation (Critical)

#### Gap 1: Hashing Algorithm Mismatch (CRITICAL) ✅ VERIFIED BY SPIKE

**Issue:** RegenAI uses `json.dumps(sort_keys=True)` while rid-lib uses JCS (JSON Canonicalization Scheme).

**Evidence:**
```python
# RegenAI (koi-sensors/koi_protocol/core/bundle_system.py) - WRONG
content_bytes = json.dumps(content, sort_keys=True).encode('utf-8')
hash = sha256(content_bytes).hexdigest()

# rid-lib (rid-lib/src/rid_lib/ext/utils.py) - CORRECT
# Uses vendored JCS canonicalizer, NOT PyPI canonicaljson
from rid_lib._vendor.org.webpki.json import Canonicalize
canonicalized_data = Canonicalize.canonicalize(data, utf8=True)
hash = sha256(canonicalized_data).hexdigest()
```

**Spike Results (9,588 real payloads tested):**
- **Legacy vs rid-lib JCS: 100% mismatch** (9,588/9,588 payloads)
- **"Compact JSON" vs rid-lib JCS: 8.79% mismatch** (843/9,588 payloads)
- Root cause: JCS **normalizes numbers** (e.g., `1.0` → `1`), not just whitespace

**Critical finding:** The PyPI `canonicaljson` package is **NOT sufficient** — it doesn't implement JCS number normalization, so it disagrees with rid-lib on ~8.8% of payloads.

**Concrete example from coordinator queue:**
- RID: `rid:test-fail:1`
- Stored/legacy hash: `24f6a8383c8f88ce8c39333fb7d3842bf29c8a2dc690e0288af3d91f829b3113`
- rid-lib JCS hash: `a8d1890cfdcfdca1b985ab7cc291fe4ec8597268922cb0d8529d85e2f621dd71`

**Impact:**
- Content hashes **will not match** other nodes for identical content
- Breaks integrity verification across the ecosystem
- Breaks deduplication consistency
- Prevents content-addressed identifiers (CIDs like `cid:sha256:...`)

**Existing data affected:**
- Coordinator dedup state: **3,873 `url_hashes` + 12 `content_hashes`** (`coordinator_dedup_state.json`)
- Database: ~**2,835 KOI memories** with legacy manifest hashes in `koi_memories.metadata.koi_manifest`
- ~**19,760+ CAT receipts** (Sep 2025 verification report)

**Solution:** Switch to `rid_lib.Manifest.generate()` — must use rid-lib's internal JCS implementation, not standalone `canonicaljson`.

**Migration strategy (recommended):** Dual-hash support during transition:
- Store both `legacy_content_hash` and `sha256_hash` (rid-lib JCS)
- Use `sha256_hash` on strict KOI-net surface
- Keep `legacy_content_hash` for backward compatibility until cutover

#### Gap 2: RID v3 Parsing Incompatibility (CRITICAL)

**Issue:** Our local RID parser in `koi_protocol/core/rid_system.py` rejects `:` in the reference component.

**Evidence:**
```python
# Current RegenAI implementation (incompatible)
def parse(rid_string):
    parts = rid_string.split(":", 1)  # Only splits on first ":"
    # Fails for: orn:slack.message:team/channel/ts
```

**Impact:**
- Cannot parse **any** ORN (`orn:<namespace>:<reference>`) because ORNs contain multiple `:` characters
- Cannot parse URIs with ports (`https://example.com:8080/path`)
- Violates rid-lib's foundation: "all URIs can be valid RIDs"

**Solution:** Replace with `rid_lib.RID.from_string()` or ensure local types are thin wrappers over rid-lib.

#### Gap 3: Manifest/Bundle Schema Mismatch (HIGH → CRITICAL under signing)

**Manifest divergence:**

| Field | RegenAI | rid-lib (Required) |
|-------|---------|-------------------|
| rid | Yes | Yes |
| timestamp | Yes | Yes |
| sha256_hash | Uses `content_hash` | Yes |
| size_bytes | Yes | **No** |
| content_type | Yes | **No** |
| version | Yes | **No** |
| metadata | Yes | **No** |

**Bundle divergence:**

| Field | RegenAI | rid-lib (Required) |
|-------|---------|-------------------|
| rid | Yes (root level) | Derived from manifest |
| manifest | Yes | Yes |
| contents | Yes | Yes |

**Solution:** Define two representations:
- **Wire (strict):** exact rid-lib + KOI-net schemas.
- **Internal (extended):** keep operational fields, but move them into `contents` (or `contents._regen`) rather than extending manifest/event schemas.

### P1 — SignedEnvelope interoperability (high priority)

#### Gap 4: SignedEnvelope Payload Incompatibility (CRITICAL NUANCE) ✅ VERIFIED BY SPIKE

**Issue:** Our crypto is compatible, but payloads are not. KOI-net verifies signatures **after** parsing into strict Pydantic models; unknown fields are discarded before reconstructing the signed bytes.

**Crypto compatibility verified:** Cross-verification tests confirmed:
- A KOI-net-signed `PollEvents` envelope verifies via RegenAI `verify_envelope()`
- A RegenAI-signed `PollEvents` envelope verifies via KOI-net `SignedEnvelope.verify_with()`

**Fields that break verification (confirmed):**
- `node_id` / `include_event_ids` in poll requests → `InvalidSignature`
- `event_ids` in poll responses
- `timestamp`, `source_node` inside event payloads → `InvalidSignature`
- `metadata` in manifest payloads → `InvalidSignature`

**NEW: Timestamp serialization mismatch (subtle but critical):**
- KOI-net Pydantic serializes UTC datetimes as `...Z` (Zulu)
- If we sign `manifest.timestamp` as `...+00:00`, KOI-net re-serializes as `...Z` → **signature mismatch**
- Must use identical serialization path (prefer rid-lib/koi-net Pydantic models)

**Solution:** If a payload is to be signed for KOI-net interop, it must be **schema-exact** (no extras). Identity belongs in the envelope (`source_node`, `target_node`), not in the payload. Timestamps must use `Z` suffix, not `+00:00`.

**Note:** Two separate `koi_envelope.py` implementations exist (`koi-sensors/shared/` and `koi-processor/scripts/`) — consolidate to avoid drift.

#### Gap 5: Node Identity + Trust Model Mismatch (HIGH)

**KOI-net secure parity expects:**
- `KoiNetNode` ORNs derived from public keys (`orn:koi-net.node:<name>+<hash>`),
- NodeProfile bundles used for key distribution/trust.

**RegenAI today:** env-configured key maps (`KOI_PUBLIC_KEYS_JSON`), arbitrary node_id strings.

**Decision point:**
1. **Fast interop (weaker trust):** accept SignedEnvelope with out-of-band key maps; interop requires partner nodes configured comparably.
2. **KOI-net secure parity (strong trust):** adopt KoiNetNode identity derivation + NodeProfile distribution so reference nodes can validate us.

#### Gap 6: Endpoint Base Path Convention (Medium)

**KOI-net reference server:** mounts endpoints under `/koi-net/*`.

**Recommendation:** add a strict `/koi-net/*` surface that mirrors KOI-net models exactly, while keeping internal endpoints stable for existing RegenAI components.

### P2 — Durability + scaling alignment (medium → high as networks grow)

#### Gap 7: Bundle/Manifests Cache Persistence (Medium)

**Issue:** rid-lib provides durable `Cache`; RegenAI coordinator caches bundles in memory (`Dict[str, Bundle]`).

**Impact:** After restart, fetch endpoints may not reflect prior knowledge, undermining reconciliation.

**Solution:** Adopt `rid-lib.Cache` (or equivalent) for bundle/manifest persistence.

#### Gap 8: Python Version Skew (Medium)

**Issue:** koi-net uses Python 3.12+ syntax (`type X = ...`).

**RegenAI:** Services describe Python 3.8+/3.11-compatible environments.

**Solution options:**
- Upgrade service runtimes to Python 3.12+
- Vendor/wrap only protocol models in 3.11-compatible way

---

## Recommended Alignment Strategy (Dual-Surface Architecture)

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

This implements the "dialect/common language" model: strict common language at the boundary, richer internals inside the organization.

### FUN vs CRUD plane separation

- **FUN plane (KOI-net):** strict `/koi-net/*` endpoints + rid-lib hashing + schema-exact signed payloads.
- **CRUD/admin plane (RegenAI):** delivery confirmation, dashboards, sensor control, ops endpoints, reliability and reconciliation tooling.

### Interoperability levels (success criteria)

| Level | Description | Requires |
|-------|-------------|----------|
| 1 | Wire-compatible (unsigned) | Endpoint shapes match |
| 2 | Wire + hash compatible | rid-lib hashing + RID parsing authoritative |
| 3 | SignedEnvelope interop | Strict schemas; signature verification works with reference nodes |
| 4 | Reference-node substitution | Full koi-net adoption without reliability regression |

**Recommended target:** Level 3 (SignedEnvelope interop) while preserving internal reliability.

---

## Implementation Roadmap (Updated Dec 2025)

Based on pre-implementation research findings.

### Phase 1 (P0) — Foundation ✅ COMPLETE (Dec 2025)

**PRs merged:**
- [koi-sensors#4](https://github.com/gaiaaiagent/koi-sensors/pull/4) — Merged 2025-12-23
- [koi-processor#5](https://github.com/gaiaaiagent/koi-processor/pull/5) — Merged 2025-12-23

**Completed:**
1. ✅ **Add `rid-lib` dependency** to `koi-sensors` and `koi-processor` requirements
2. ✅ **Adopt rid-lib for hashing and RID parsing:**
   - `Manifest.generate()` now uses rid-lib's JCS canonicalization
   - RID parsing handles ORNs (`orn:namespace:reference`) and URIs with ports
   - ImportError fallback to legacy hashing if rid-lib not available
3. ✅ **Implement dual-hash support:**
   - `sha256_hash` (rid-lib JCS) + `legacy_content_hash` (json.dumps)
   - `content_hash` property aliases `sha256_hash`
   - Internal endpoints continue accepting legacy format
4. ✅ **Backward compatibility verification:**
   - 24 tests in koi-sensors, 11 tests in koi-processor — all passing
   - `test_koi_flow_integration.py` passes
   - Internal forwarders work unchanged

**Deferred to P1:**
- [ ] Timestamp Z serialization (still uses `+00:00`, not `Z`)
- [ ] `koi_envelope.py` consolidation (two implementations still exist)

**Rollout note:** Low-risk Option A deployed — rid-lib installed in coordinator/processor venvs but NOT in sensor venvs. Sensors fall back to legacy hashing until rid-lib is explicitly installed in their venvs.

### Phase 2 (P1) — Strict interop surface ← NEXT

**Carries over from P0:**
- [ ] Timestamp Z serialization (replace `+00:00` with `Z` for wire format)
- [ ] `koi_envelope.py` consolidation (use koi-sensors version as canonical)

**P1 scope:**
1. **Add `/koi-net/*` router** that matches KOI-net request/response models exactly:
   - `POST /koi-net/events/broadcast`
   - `POST /koi-net/events/poll`
   - `POST /koi-net/bundles/fetch`
   - `POST /koi-net/manifests/fetch`
   - `POST /koi-net/rids/fetch`
2. **Implement wire ↔ internal transformers:**
   - Strip non-schema fields before signing
   - Move extras into `contents._regen`
   - Use envelope `source_node`/`target_node` for identity
   - Ensure timestamp `Z` format on all signed payloads
3. **Update downstream consumers:**
   - Coordinate with daily curator on metadata location change (`koi_manifest.metadata.url` → `contents._regen.url`)
4. **Create SignedEnvelope interop tests** against a reference node template
5. **Consider Python 3.12 upgrade** if using koi-net models directly

**Critical constraint:** Keep internal `/events/*` endpoints unchanged. Appendix F clients must continue working.

#### P1 Acceptance Criteria (Definition of Done)

**P1a — Level 2 Interop (strict wire, unsigned OK):**

| Criterion | Category |
|-----------|----------|
| [ ] `/koi-net/*` endpoints implemented with schema-exact KOI-net models | Endpoints |
| [ ] Coordinator recomputes `sha256_hash` via rid-lib JCS on `/koi-net/*` output (sensors can stay legacy) | Hashing |
| [ ] Wire `Manifest` = strict `{rid, timestamp, sha256_hash}` only (no `size_bytes`, `content_type`, `metadata`) | Schema |
| [ ] Timestamp serialization uses `Z` suffix on `/koi-net/*` wire output (internal storage unchanged) | Serialization |
| [ ] Internal `/events/*` endpoints unchanged (`+00:00` timestamps, dual hashes accepted) | Compatibility |
| [ ] Test: event broadcast with `legacy_content_hash` only → `/koi-net/events/poll` returns correct JCS `sha256_hash` | Verification |
| [ ] Test: wire timestamps use `Z`, internal use `+00:00` | Verification |
| [ ] Decision documented: koi-net Pydantic models (Python 3.12+) vs hand-rolled (drift risk) | Architecture |

**P1b — Level 3 Interop (SignedEnvelope): ✅ COMPLETE (Dec 2025)**

| Criterion | Category | Status |
|-----------|----------|--------|
| `koi_envelope.py` consolidated (koi-sensors version canonical, koi-processor symlinks) | Consolidation | ✅ |
| Signing uses `UnsignedEnvelope.model_dump_json(exclude_none=True)` | Signing | ✅ |
| `source_node` and `target_node` are required KoiNetNode ORNs | Signing | ✅ |
| `ErrorResponse` returned on invalid signature/target/key (not FastAPI default) | Errors | ✅ |
| All 5 `/koi-net/*` endpoints implemented with SignedEnvelope support | Endpoints | ✅ |
| Signed request → signed response (or ErrorResponse if no key) | Signing | ✅ |
| Test: RegenAI-signed envelope verifies with koi-net bytes | Verification | ✅ |
| Test: koi-net-signed envelope verifies with RegenAI | Verification | ✅ |
| Test: extra fields break verification | Verification | ✅ |
| Test: FORGET event with None manifest (exclude_none behavior) | Verification | ✅ |
| Metadata migration decision documented (Option A: no `_regen` on wire for P1b) | Migration | ✅ |

**Implemented in:**
- `koi-sensors/shared/koi_envelope.py` (Pydantic models + exclude_none=True)
- `koi-processor/scripts/koi_envelope.py` → symlink to koi-sensors
- `koi-sensors/koi_protocol/coordinator/koi_coordinator.py` (/koi-net/* endpoints)
- `koi-sensors/tests/test_koi_net_signed_envelope.py` (14 tests)

**Metadata Migration Decision (Option A):**
For P1b, we do NOT emit `_regen` metadata on wire. External nodes get strict `{manifest, contents}` bundles.
- Rationale: Adding `_regen` to contents changes the JCS hash, breaking dedup and hash verification
- Internal metadata stays in internal endpoints only
- Future P2: Consider separate knowledge object for operational metadata if needed

### Phase 3 (P2) — Durability + retention ✅ COMPLETE (Dec 2025)

**P2a — Durable State Transfer:** ✅ Complete
- `rid-lib.ext.Cache` integration for persistent bundle storage
- Write-through caching (memory + disk)
- Bundles survive coordinator restarts
- `/koi-net/bundles/fetch` returns persisted bundles
- 26 tests covering persistence, event semantics, signed persistence

**P2b — Retention + Monitoring:** ✅ Complete
- Environment-configurable retention policy (`KOI_CACHE_MAX_SIZE_MB`, `KOI_CACHE_MAX_AGE_DAYS`)
- Protected bundle patterns for NodeProfile/identity bundles
- Pruning script with dry-run and metrics modes
- Systemd timer for scheduled daily pruning
- 21 tests covering pruning, metrics, protection

**Implemented in:**
- `koi-sensors/koi_protocol/core/persistent_cache.py`
- `koi-sensors/scripts/prune_bundle_cache.py`
- `koi-sensors/scripts/seed_bundle_cache.py`
- `koi-sensors/systemd/koi-cache-prune.{service,timer}`
- `koi-sensors/tests/test_persistent_cache_p2a.py` (26 tests)
- `koi-sensors/tests/test_cache_retention_p2b.py` (21 tests)

**Deferred to P3 (optional):**
1. Backfill existing DB knowledge into rid-lib Cache (requires separate Postgres query script)
2. Formalize proxy node patterns for boundary exposure
3. Standardize provenance/CAT receipts as verifiable knowledge objects
4. Prepare upstream proposals:
   - optional ack/confirm extension,
   - persistence hooks in KOI-net node lifecycle,
   - reliability mode knobs (best-effort vs durable vs synchronous processor option)

### Suggested spikes (de-risk before big refactors)

1. ✅ **Hash parity spike** — compare rid-lib vs current hashing on real payloads. *COMPLETED: 100% mismatch confirmed, JCS numeric normalization identified*
   - Methodology: `koi-research/reports/KOI_PREIMPLEMENTATION_RESEARCH.md` Section 1
   - Artifacts: `koi-research/spikes/koi_hash_parity_spike.py`, `koi-research/spikes/koi_hash_parity_spike_output.md`
2. ✅ **Strict SignedEnvelope interop spike** — KOI-net node signs/validates end-to-end. *COMPLETED: crypto compatible, timestamp Z vs +00:00 issue found*
   - Methodology: `koi-research/reports/KOI_PREIMPLEMENTATION_RESEARCH.md` Section 4
3. ✅ **`/koi-net` router shim spike** — mirror strict paths without breaking internal clients. *COMPLETED: P1b*
4. ✅ **Bundle cache persistence spike** — restart durability + fetch correctness. *COMPLETED: P2a*
5. **Proxy-node "controlled subset" spike** — allowlists + policy metadata. *Deferred to P3*
6. **Provenance/CATs spike** — content-addressed transform records. *Deferred to P3*

---

## Validation: "Definition of Done" for Level 3 Interop

Interop is "real" when a KOI-net reference node (e.g., `koi-net-node-template`) can:
- broadcast events to our coordinator via `/koi-net/events/broadcast`,
- poll events from our coordinator via `/koi-net/events/poll`,
- fetch bundles/manifests/rids via `/koi-net/*`,
- validate SignedEnvelope signatures on all responses,
- and produce matching `sha256_hash` for identical contents (rid-lib hashing).

While still preserving RegenAI's internal reliability:
- confirm-on-success behavior to downstream processors,
- durable queueing semantics,
- and correct HTTP failure signaling.

---

## Risk Assessment

### Migration risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Hash changes break existing data | High | Dual-hash support during transition; 100% drift confirmed across 9,588 payloads |
| Schema changes break internal clients | Medium | Adapter layer; staged rollout; keep internal plane stable |
| Python version skew (koi-net 3.12+) | Medium | Use rid-lib only for P0 (3.11 compatible); upgrade to 3.12 for P1+ |
| Canonicalization performance overhead | Low | Benchmark; optimize hot paths; cache where appropriate |

### Technical risks (from pre-implementation spike)

| Risk | Impact | Mitigation |
|------|--------|------------|
| JCS numeric normalization (`1.0` → `1`) | High | Cannot use `canonicaljson` PyPI; must use rid-lib's internal JCS |
| Timestamp `+00:00` vs `Z` signature mismatch | High | Use rid-lib/koi-net Pydantic models for wire serialization |
| SignedEnvelope silent field stripping | Medium | Schema-exact payloads only; test with `InvalidSignature` assertions |
| Duplicate `koi_envelope.py` implementations | Medium | Consolidate into shared module before further changes |
| Metadata relocation breaks daily curator | Medium | Coordinated update; daily curator currently reads `koi_manifest.metadata.url` |

### Operational risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Reliability regression | High | Do not replace coordinator with koi-net server wholesale; keep confirm-on-success internal plane |
| Interop issues with reference nodes | Medium | Add integration tests using KOI-net models; pin versions |
| Upstream API changes | Low | Pin versions; track KOI-net/rid-lib releases |
| Coordinator durability gap | Medium | Bundle/manifest cache is in-memory; implement rid-lib Cache for P2 |

---

## Operational Defaults (RegenAI internal reliability plane)

These are RegenAI defaults for durability/ops. Keep them **out of the strict KOI-net signed payload surface** (CRUD/admin plane).

### Retry policy for pending items (recommended defaults)

Sensors mark items `pending` before emit and `processed` only on success. The following policy handles failures:

| Condition | Retry Behavior |
|-----------|----------------|
| Network timeout or 5xx from coordinator | Exponential backoff: 10s, 30s, 60s, 300s, then hourly up to 24h |
| 4xx from coordinator (bad request) | Log and drop; likely a data issue; manual review |
| Coordinator ack (HTTP 200) but downstream bridge fails | Event remains queued; forwarder re-polls automatically |
| Sensor restart while pending | Items re-emitted on next collection cycle (idempotent via content hash) |

Implementation notes:
- Sensors use `shared/persistent_state.py` for pending/processed tracking (JSON file).
- Forwarders poll with `include_event_ids=true` and call `/events/confirm` only after downstream success.
- Events unconfirmed for >24h should trigger an alert (future reconciliation job).

### Key distribution and target validation (RegenAI defaults)

SignedEnvelope support is optional. When enabled:

| Setting | Default | Description |
|---------|---------|-------------|
| `KOI_ENVELOPE_SIGN` | `auto` | Sign if a private key is available; can force on/off |
| `KOI_ENVELOPE_VERIFY` | `auto` | Verify if public keys are available; can force on/off |
| `KOI_PRIVATE_KEY_PEM` | unset | ECDSA P-256 private key PEM (inline) |
| `KOI_PRIVATE_KEY_PEM_PATH` | unset | Path to private key PEM |
| `KOI_PRIVATE_KEY_PASSWORD` | unset | Optional private key password |
| `KOI_PUBLIC_KEYS_JSON` | unset | JSON map of `node_id -> PEM` public keys |
| `KOI_PUBLIC_KEYS_PATH` | unset | Path to JSON map of public keys |
| `KOI_ENVELOPE_VERIFY_TARGET` | `false` | Enforce `target_node` matches local `node_id` |

Target validation (when `KOI_ENVELOPE_VERIFY=true`):
- Envelope `target_node` must match the local `node_id` when `KOI_ENVELOPE_VERIFY_TARGET=true`.
- Sender must have a public key in `KOI_PUBLIC_KEYS_JSON`/`KOI_PUBLIC_KEYS_PATH`.
- If validation fails, return HTTP 400 and log the rejection.

Key rotation guidance:
- Rotate keys quarterly or on suspected compromise.
- Keep previous public keys during overlap (e.g., 7 days).
- Announce new public keys out-of-band (shared config repo or manual distribution).

### Operational safeguards (non-protocol)

- systemd units for coordinator, forwarder, event bridge, and other critical services.
- Alerts on service failure and queue backlog thresholds.
- Reconciliation job to detect "scraped but not stored" and re-queue (future hardening).

---

## Proposed Upstream Contributions

If these patterns are broadly useful, propose them upstream rather than forking:
- Optional delivery confirmation extension (e.g., `/events/confirm`) for stronger delivery semantics.
- Lifecycle hooks for queue persistence and/or durable caches.
- Documented guidance on best-effort broadcast vs reconciliation via fetch.
- Compatibility guidance on schema-exact SignedEnvelope payloads and "wire vs internal" model separation.
- Optional reliability modes (best-effort vs durable vs synchronous processor option), if BlockScience wants to support it.

---

## Open Questions + Recommended Decisions

Based on the pre-implementation research spike (Dec 2025):

| Question | Recommendation | Rationale |
|----------|---------------|-----------|
| **Security posture** | Two-tier: P1 "insecure interop" (manual key maps), P2 KOI-net secure parity (NodeProfile) only if needed | Lower effort for initial interop; secure parity adds significant complexity |
| **Hash migration** | Dual-hash support during transition (`legacy_content_hash` + rid-lib `sha256_hash`) | 100% hash drift confirmed; versioning RIDs is unnecessary since RIDs aren't derived from content hash |
| **Metadata namespace** | Adopt `contents._regen` for wire-transmitted operational metadata | Keeps manifest/event schemas strict; note that `contents` fields affect the hash |
| **Base path convention** | Add `/koi-net/*` as strict interop surface; keep root endpoints as internal/legacy | Avoids breaking forwarders, GAIA monitoring, and sensors during transition |
| **Reliability semantics** | Keep `/events/confirm` as internal-only; implement "smart client" reconciliation for strict KOI-net surface | FUN plane should remain minimal per protocol philosophy |
| **Python runtime** | Python 3.11 sufficient for rid-lib only; Python 3.12+ required if using koi-net as a library | koi-net uses PEP 695 `type` aliases (3.12+ only) |

**Still open (requires stakeholder input):**
- When to execute the migration cutover (deprecate legacy hashes)
- Whether to backfill existing DB knowledge into rid-lib Cache
- Timeline for Python 3.12 upgrade across services

---

## Appendix A — Schema Mapping Cheat Sheet (Internal → KOI-net wire)

**Key constraint:** anything signed must match KOI-net schemas exactly.

### A.1 Poll request

- RegenAI internal polling commonly includes: `node_id`, `include_event_ids`.
- KOI-net wire model is:
  - `PollEvents = {"type": "poll_events", "limit": 0}`
  - identity comes from `SignedEnvelope.source_node`, not from payload fields.

### A.2 Event payload

- RegenAI common internal event shape:
  ```json
  {"event_type":"NEW","rid":"...","timestamp":"...","source_node":"...","bundle":{...}}
  ```
- KOI-net wire `Event` model:
  ```json
  {"rid":"...","event_type":"NEW","manifest":{...},"contents":{...}}
  ```

Mapping guidance:
- sender identity → envelope `source_node`
- "when" → `manifest.timestamp`
- operational extras → `contents._regen` (stable namespace)

### A.3 Manifest / bundle

- RegenAI internal manifests frequently include extras and use `content_hash`.
- rid-lib manifest is strictly:
  - `{"rid": "...", "timestamp": "...", "sha256_hash": "..."}`
- rid-lib bundle is strictly:
  - `{"manifest": {...}, "contents": {...}}`

Practical consequence: **do not extend manifests on the wire**; put extra fields into `contents` or separate knowledge objects.

---

## Appendix B — Code Migration Patterns

### B.1 RID Parsing

```python
# Before (incompatible with ORNs)
from koi_protocol.core.rid_system import RID
rid = RID.parse("context:reference")  # Fails for orn:namespace:reference

# After (rid-lib compatible)
from rid_lib import RID
rid = RID.from_string("orn:slack.message:T123/C456/1234.5678")
print(rid.context, rid.reference)
```

### B.2 Manifest Generation with Correct Hashing

```python
# Before (json.dumps — wrong hash)
import json
from hashlib import sha256
content_bytes = json.dumps(content, sort_keys=True).encode('utf-8')
hash = sha256(content_bytes).hexdigest()

# After (JCS canonicalization — correct hash)
from rid_lib.ext import Manifest
manifest = Manifest.generate(rid, contents)
hash = manifest.sha256_hash
```

### B.3 Bundle Creation

```python
# Before (custom Bundle class)
from koi_protocol.core.bundle_system import Bundle
bundle = Bundle(rid=rid, manifest=manifest, contents=contents)

# After (rid-lib Bundle)
from rid_lib.ext import Bundle
bundle = Bundle.generate(rid, contents)
# RID is derived from manifest, not stored separately
```

### B.4 Cache Usage

```python
# Before (in-memory dict)
self.cache: Dict[str, Bundle] = {}
self.cache[str(rid)] = bundle
bundle = self.cache.get(str(rid))

# After (rid-lib Cache — persistent)
from rid_lib.ext import Cache
cache = Cache(".rid_cache")
cache.write(bundle)
bundle = cache.read(rid)
```

### B.5 Wire/Internal Model Transformation

```python
def internal_to_wire(internal_event: InternalEvent) -> KoiNetEvent:
    """Transform internal event to strict KOI-net wire format."""
    return {
        "rid": internal_event.rid,
        "event_type": internal_event.event_type,
        "manifest": {
            "rid": internal_event.manifest.rid,
            "timestamp": internal_event.manifest.timestamp,
            "sha256_hash": internal_event.manifest.sha256_hash,
        },
        "contents": {
            **internal_event.contents,
            "_regen": {
                "source": internal_event.source_node,
                "original_timestamp": internal_event.timestamp,
                "size_bytes": internal_event.manifest.size_bytes,
            }
        }
    }

def wire_to_internal(wire_event: KoiNetEvent, envelope: SignedEnvelope) -> InternalEvent:
    """Transform KOI-net wire format to internal event."""
    regen_meta = wire_event.get("contents", {}).get("_regen", {})
    return InternalEvent(
        rid=wire_event["rid"],
        event_type=wire_event["event_type"],
        manifest=wire_event["manifest"],
        contents=wire_event["contents"],
        source_node=envelope.source_node,
        timestamp=regen_meta.get("original_timestamp", wire_event["manifest"]["timestamp"]),
    )
```

---

## Appendix C — Test Cases for Validation

```python
def test_rid_parsing_orn():
    """ORNs with multiple colons parse correctly."""
    from rid_lib import RID
    rid = RID.from_string("orn:slack.message:T123/C456/1234.5678")
    assert rid.context == "orn"
    # or depending on rid-lib API:
    # assert rid.namespace == "slack.message"

def test_hash_parity_with_ridlib():
    """Content hashes match rid-lib output."""
    from rid_lib.ext import Manifest
    content = {"key": "value", "nested": {"a": 1}}
    rid = RID.from_string("test:content")
    manifest = Manifest.generate(rid, content)
    assert our_hash(content) == manifest.sha256_hash

def test_signed_envelope_interop():
    """KOI-net node can verify our signed responses."""
    from koi_net.protocol.secure import verify_envelope
    response = our_signed_response()
    assert verify_envelope(response) is True

def test_strict_event_schema():
    """Wire events have no extra fields."""
    wire_event = internal_to_wire(sample_internal_event)
    allowed_keys = {"rid", "event_type", "manifest", "contents"}
    assert set(wire_event.keys()) <= allowed_keys
    manifest_keys = {"rid", "timestamp", "sha256_hash"}
    assert set(wire_event["manifest"].keys()) == manifest_keys

def test_reference_node_poll():
    """Reference KOI-net node can poll from our coordinator."""
    # Start coordinator with /koi-net/* endpoints
    # Use koi-net client to poll
    # Verify events returned in correct format
    # Verify SignedEnvelope signature validates
    pass

def test_state_transfer_after_restart():
    """Bundles survive coordinator restart."""
    # Store bundle via broadcast
    # Restart coordinator
    # Fetch bundle via /bundles/fetch
    # Verify contents match
    pass
```

---

## Appendix D — KOI-net Endpoint Reference (strict interop surface)

KOI-net reference NodeServer mounts endpoints under `/koi-net` and wraps them with an envelope handler:
- server code: `koi-research/sources/blockscience/koi-net/src/koi_net/server.py`
- envelope model: `koi-research/sources/blockscience/koi-net/src/koi_net/protocol/envelope.py`
- request/response models: `koi-research/sources/blockscience/koi-net/src/koi_net/protocol/api_models.py`

**Secure mode wire shape:** requests/responses are `SignedEnvelope[<model>]` in the HTTP JSON body.

| Endpoint | Method | Request payload model | Response payload model |
|----------|--------|-----------------------|------------------------|
| `/koi-net/events/broadcast` | POST | `EventsPayload` | (none on success) |
| `/koi-net/events/poll` | POST | `PollEvents` | `EventsPayload` |
| `/koi-net/rids/fetch` | POST | `FetchRids` | `RidsPayload` |
| `/koi-net/manifests/fetch` | POST | `FetchManifests` | `ManifestsPayload` |
| `/koi-net/bundles/fetch` | POST | `FetchBundles` | `BundlesPayload` |

---

## Appendix E — Common rid-lib Patterns (implementation reminder)

```python
from rid_lib import RID
from rid_lib.ext import Manifest, Bundle, Cache

rid = RID.from_string("orn:slack.message:T123/C456/1234.5678")
manifest = Manifest.generate(rid, {"hello": "world"})
bundle = Bundle(manifest=manifest, contents={"hello": "world"})

cache = Cache(".rid_cache")
cache.write(bundle)
bundle2 = cache.read(rid)
```

---

## Appendix F — Client Impact Matrix (from pre-implementation research)

This matrix identifies which internal clients will break under strict KOI-net SignedEnvelope verification and what changes are needed.

| Client / File | Coordinator Endpoints Used | Non-standard Fields | Breaks Strict Interop? | Change Needed |
|---------------|---------------------------|---------------------|------------------------|---------------|
| `koi-processor/scripts/coordinator_to_eventbridge_forwarder.py` | poll + confirm | `node_id`, `include_event_ids`, `event_ids` | Yes | Use internal endpoints OR migrate to strict `/koi-net/events/poll` |
| `koi-processor/scripts/coordinator_to_code_graph_forwarder.py` | poll + confirm | same as above | Yes | same |
| `koi-processor/src/core/coordinator_to_semantic_bridge.py` | poll + confirm | same as above | Yes | same |
| `koi-sensors/koi_protocol/nodes/koi_node.py` | broadcast + poll | event-level `timestamp`, `source_node`, `node_id` | Yes | Split internal vs wire models; identity in envelope |
| `koi-sensors/sensors/telegram/telegram_sensor.py` | broadcast | non-FUN `event_type=HEARTBEAT`, `data` field | Yes | Keep on internal ops-plane only |
| `GAIA/packages/server/src/api/koi/index.ts` | poll (monitoring) | `node_id` | Yes | Point to internal endpoint or sign strict PollEvents |
| `GAIA/packages/server/src/api/koi-proxy.ts` | poll (monitoring) | `node_id` | Yes | same |
| `koi-processor/tests/test_koi_flow_integration.py` | broadcast + poll + confirm | legacy hashing + event_ids | Yes | Update after wire/internal split |

**Key insight:** Internal clients should continue using root endpoints (`/events/*`); only external KOI-net interop uses strict `/koi-net/*` endpoints.

---

## Appendix G — Code Paths Generating Legacy Hashes

These code locations generate or assume the legacy manifest hash and will need updates:

**Primary legacy hashing:**
- `koi-sensors/koi_protocol/core/bundle_system.py` — `Manifest.generate()` and `Manifest.verify_content()`

**Places that recompute hash when missing:**
- `koi-sensors/koi_protocol/coordinator/koi_coordinator.py` — `_koi_net_event_to_koi_event_data()`
- `koi-processor/scripts/coordinator_to_eventbridge_forwarder.py`
- `koi-processor/scripts/coordinator_to_code_graph_forwarder.py`
- `koi-processor/src/core/coordinator_to_semantic_bridge.py`

**Tests encoding legacy assumptions:**
- `koi-processor/tests/test_koi_flow_integration.py`

**Downstream consumers of manifest metadata:**
- `koi-processor/src/content/daily_curator.py` — expects `koi_manifest.metadata.url`

---

*Document synthesized from RegenAI KOI system analysis and BlockScience protocol specifications. December 2025.*
