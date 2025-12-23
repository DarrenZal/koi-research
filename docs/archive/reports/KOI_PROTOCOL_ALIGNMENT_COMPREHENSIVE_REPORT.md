# KOI Protocol Alignment & RegenAI KOI System Improvement — Comprehensive Report

**Date:** December 22, 2025  
**Scope:** RegenAI KOI pipeline (`koi-sensors`, `koi-processor`, `koi-research`)  
**Primary reference:** `koi-research/docs/KOI_PROTOCOL_ALIGNMENT_REFERENCE.md`  
**Reference implementations (local copies):** `koi-research/sources/blockscience/rid-lib`, `koi-research/sources/blockscience/koi-net`

This report complements (and does not replace) `koi-research/reports/KOI_SYSTEM_IMPROVEMENT_RESEARCH.md` by adding a stricter KOI-net interoperability lens: **what is required for a BlockScience reference node to interoperate with our coordinator using SignedEnvelopes and strict Pydantic schemas**, without sacrificing our current reliability guarantees.

---

## 1. Executive Summary

RegenAI’s KOI pipeline is operational and “KOI-shaped”, but it is not yet **strictly interoperable** with KOI-net reference nodes under SignedEnvelope validation. The main blockers are not “endpoint availability” (we already expose the core paths), but **cryptographic + schema contracts** defined by BlockScience:

1. **RID v3 compliance:** our local RID implementation cannot parse ORNs or general URIs (it rejects `:` in the reference), so it cannot act as a correct RID v3 implementation.
2. **Hashing contract:** our Manifest content hashing does not match `rid-lib` (we use `json.dumps(sort_keys=True)`, while `rid-lib` hashes JCS canonicalized JSON).
3. **SignedEnvelope + strict schema:** our envelope signature algorithm is compatible with KOI-net, but **any extra fields** not in KOI-net schemas cause KOI-net signature verification to fail (because Pydantic drops unknown fields before reconstructing the signed bytes).
4. **Wire payload shapes:** our current “event”/“bundle”/“manifest” objects contain helpful operational fields (timestamps, source_node, size_bytes, metadata, etc.) that are **not part of KOI-net’s signed payload models**.

**High-level recommendation:** pursue a **two-surface strategy**:

- Keep the current robust internal interface (our “operational KOI”) to preserve reliability (`/events/confirm`, queue persistence, forwarder confirm-on-success).
- Add a **strict KOI-net interop surface** (recommended at `/koi-net/*`) that uses `rid-lib` structures + hashing and emits/accepts KOI-net-compliant payloads with no schema extras when SignedEnvelope mode is enabled.

This lets us be “protocol-first” *and* reliability-first without fragmenting the ecosystem.

---

## 2. Source of Truth (What We Must Align To)

### 2.1 `rid-lib` (RID v3 + core knowledge types)
`rid-lib` defines:
- **RID parsing/typing** (`RID.from_string`, `RIDType`)
- **Manifest**: `{rid, timestamp, sha256_hash}` and `Manifest.generate(rid, data)` hashing via JCS canonicalization (`rid_lib.ext.utils.sha256_hash_json`)
- **Bundle**: `{manifest, contents}` (RID is derived from the manifest)
- **Cache**: filesystem storage keyed by base64-encoded RID strings

### 2.2 `koi-net` (protocol endpoints + SignedEnvelope)
`koi-net` defines:
- **Endpoints (POST + JSON):** `/events/broadcast`, `/events/poll`, `/bundles/fetch`, `/manifests/fetch`, `/rids/fetch`
- **Event model:** `{rid, event_type, manifest?, contents?}` (notably no `timestamp` or `source_node` fields inside the event itself)
- **SignedEnvelope model:** `{payload, source_node, target_node, signature}` with ECDSA P-256 and base64 raw `r||s` signatures
- **Strict Pydantic schema validation**: payloads are parsed into Pydantic models (unknown fields are dropped) and signature verification is performed on the canonical serialized model, not on the raw incoming JSON text.

### 2.3 BlockScience blog synthesis (conceptual + governance)

The KOI-net/rid-lib packages define the **physical** wire contracts. BlockScience’s blog posts clarify intended KOI design principles (governance, boundaries, interoperability, provenance) that help interpret what should (and should not) be part of the protocol surface.

- **Architecting KOI (Zargham, 2024)** — `koi-research/sources/blockscience/blog-architecting-koi.md`
  - **Institutions vs infrastructure:** governance is ongoing expectation alignment between narratives, specs, implementations, and user/operator experience (feedback loop).
  - **Four architecture levels:** conceptual/functional/logical/physical. KOI-net/rid-lib are primarily **physical-level** contracts; we should keep our higher-level architecture docs explicit to avoid fragmentation.
  - **Closed-loop knowledge processing:** outcomes/quality matter; knowledge processing is circular and non-idempotent (compose/decompose/decorate/mutate/curate/search/generate) → reinforces versioning + provenance + reconciliation.
  - **Requirements lens:** “From where / From whom / For whom / For what” → motivates explicit consent + bounded-use metadata as part of KOI governance, not an afterthought.

- **Objects as Reference (Reed, 2023/2024)** — `koi-research/sources/blockscience/blog-objects-as-reference.md`
  - **Digital objects are references to referents**; distinguishing reference vs referent is the foundation for organization and interop across system boundaries.
  - **Discriminators + perspectives:** multiple agents can refer to the “same thing” differently; coordination requires alignment mechanisms rather than assuming a single universal identifier.
  - **Endogenous vs exogenous identifiers:** content-addressed IDs are derived from referents (endogenous) → makes canonical hashing a core interop primitive, not an implementation detail.

- **A Language for Knowledge Networks (Zargham & Ben‑Meir, 2023)** — `koi-research/sources/blockscience/blog-language-for-knowledge-networks.md`
  - **“Dialect” model:** local cyberinfrastructure is purpose-fit and should not be flattened; interop should provide a common language without forcing uniform internal structure.
  - **Share knowledge, not rules:** coordination improves by increasing interoperability of organizational knowledge; merging “rules” across distinct orgs harms local autonomy.
  - **Map vs territory / beliefs vs facts:** RIDs enable communication about beliefs/knowledge while preserving boundaries and avoiding mistaking internal updates for external changes.
  - **LLMs as Calm Technology interface:** LLMs are valuable as interfaces to organizational internality; access control and governance decisions become first-class requirements.

- **KOI-net Protocol Preview (BlockScience, 2025)** — `koi-research/sources/blockscience/blog-koi-net-protocol-preview.md`
  - **RIDs preserve access control:** communicate about proprietary resources without sharing referents; boundary preservation is a design goal.
  - **Event vs state communication:** “FUN” events signal cache changes; state fetch supports reconciliation.
  - **Boundary-aware node roles:** sensors/actuators/processors can be understood by how they cross an org/network boundary; KOI-nets can be fractal (a network can present as a node).
  - **Protocol layering:** KOI-nets can incorporate MCP/A2A adapters as boundary interfaces without making those protocols requirements of KOI-net itself.

- **KOI Network Protocol x Project Interlay (BlockScience, 2025)** — `koi-research/sources/blockscience/blog-koi-network-protocol-interlay.md`
  - **Network configuration as knowledge objects:** nodes/edges are themselves RID-addressed knowledge objects; nodes can maintain internal perspectives of network state and share selectively via access-controlled proxy nodes.
  - **Handshake + node norms:** establishing mutual awareness and optional “normative agreements” metadata is a path to stability without enforcing uniform internal behavior.
  - **Layered protocols + “OSI B”:** avoid rigid processing-layer assumptions; keep protocols minimal/local, allow emergent global behavior (manifold analogy).
  - **FUN vs CRUD planes:** FUN events are signaling primitives; CRUD is an oversight/administration plane. This maps well to “strict KOI-net surface” vs “ops/admin extensions”.
  - **Provenance and trust:** CATs (Content‑Addressable Transformers) are framed as essential for attribution across hops — important for production networks.

- **KOI Nodes as Neurons (Sisson, 2025)** — `koi-research/sources/blockscience/blog-koi-nodes-as-neurons.md`
  - **Observed → conceived mapping:** sensors and decoders transform observed space into conceived space; calibration/validation is part of the loop (often human-in-the-loop).
  - **Sensor fusion → perception/coordination:** multi-modal sensing and downstream coordination suggests emphasizing decoders, schemas, and evaluation tooling over hardcoding one-off pipelines.
  - **Operational implication:** node templates should be configurable and composable; closed-loop behavior motivates explicit feedback, metrics, and provenance for transformations.

---

## 3. RegenAI Current KOI System (What We Have Today)

### 3.1 Current dataflow (operational)

1. Sensors broadcast events to the coordinator:
   - `koi-sensors/koi_protocol/coordinator/koi_coordinator.py` → `POST /events/broadcast`
2. Coordinator queues events for polling:
   - `koi-sensors/koi_protocol/nodes/koi_node.py` (delivery tracking + JSON persistence)
3. Forwarders poll and forward to downstream processing:
   - `koi-processor/scripts/coordinator_to_eventbridge_forwarder.py` (poll → forward → confirm-on-success)
4. Event bridges process content, generate embeddings/knowledge graph:
   - `koi-processor/src/core/koi_event_bridge_v2.py`
   - `koi-processor/src/core/koi_event_bridge_semantic.py`

### 3.2 Alignment wins already implemented (per reference doc)

From `koi-research/docs/KOI_PROTOCOL_ALIGNMENT_REFERENCE.md`, these are already in place:
- POST polling endpoints used by forwarders and docs
- Confirm only on downstream `success: true`
- Bridges return HTTP 500 on failure
- Optional SignedEnvelope support (env-configurable)
- Queue persistence (JSON)
- Pending/processed state tracking in sensors

These are meaningful production-hardening improvements over KOI-net’s default best-effort queueing model.

---

## 4. Gap Analysis vs KOI-net / rid-lib Contracts

### 4.1 RID v3 compliance (Critical)

**Observed:** `koi-sensors/koi_protocol/core/rid_system.py` implements a `RID.parse()` that rejects `:` in the reference component.

**Impact:**
- Cannot parse *any* ORN (`orn:<namespace>:<reference>`) because ORNs necessarily contain multiple `:` characters.
- Cannot parse many valid URIs (e.g., `https://example.com:8080/path`) because the reference contains `:`.
- This is incompatible with `rid-lib`’s foundational claim: **all URIs can be valid RIDs**.

**Recommendation:**
- Treat `rid-lib` as the canonical RID implementation and remove “homegrown parsing” from the protocol surface.
- If we keep local RID helpers for convenience, ensure they are *thin wrappers* over `rid_lib.RID`/`RIDType`.

### 4.2 Hashing contract (Critical)

**Observed:** `koi-sensors/koi_protocol/core/bundle_system.py` hashes JSON using `json.dumps(sort_keys=True)`; `rid-lib` hashes **JCS canonicalized JSON**.

**Impact:** Our `content_hash` / `sha256_hash` will not match other KOI nodes for identical contents, breaking:
- cross-node integrity checks,
- deduplication consistency,
- and any “CID-like” derivations (`cid:sha256:...`).

**Recommendation:**
- Switch hashing for manifests/bundles to `rid_lib.ext.utils.sha256_hash_json` (or `Manifest.generate`).
- Plan a migration strategy for existing stored hashes (expect hash changes).

### 4.3 Bundle/Manifest schema mismatch (High)

**Observed:**
- Our manifest extends the schema with `size_bytes`, `content_type`, `version`, `metadata`, and uses `content_hash` instead of `sha256_hash`.
- Our bundle includes a top-level `rid` field; `rid-lib` bundles derive RID from `manifest.rid`.

**Impact for SignedEnvelope interop:** KOI-net parses payloads into strict models; schema extras are discarded before signature verification. If a signed payload includes extras, signature verification fails.

**Recommendation:**
- Define two representations:
  - **Wire model (strict):** exact `rid-lib` `Manifest`/`Bundle`.
  - **Internal model (extended):** keep operational metadata, but move it into `contents` (or a namespaced subobject like `contents.meta`), not into the manifest.

### 4.4 Events schema mismatch (High)

**Observed:**
- Our events often include `timestamp` and `source_node` fields (and sometimes embed a “bundle” object).
- KOI-net `Event` payload is `{rid, event_type, manifest?, contents?}` (no `timestamp`, no `source_node`, no nested `bundle` field).

**Impact for SignedEnvelope interop:** Same as above — extra fields invalidate signed envelopes when KOI-net verifies.

**Recommendation:**
- For strict KOI-net mode, transform internal events to KOI-net events by:
  - using envelope `source_node` as the sender identity,
  - using manifest timestamp as the time anchor,
  - encoding any extra operational details into `contents` under a stable namespace (e.g., `contents._regen`).

### 4.5 SignedEnvelope interop: crypto is compatible, payloads are not (Critical nuance)

**Observed (tested):**
- Our envelope signing/verification algorithm in `koi-sensors/shared/koi_envelope.py` is compatible with KOI-net’s signature scheme **when the payload matches KOI-net’s schema exactly**.
- If the payload includes *any* extra keys not in KOI-net models (e.g., `node_id`, `include_event_ids`, `event_ids`), KOI-net signature verification fails.

**Why:** KOI-net verifies signatures after parsing into strict Pydantic models; unknown fields are discarded before reconstructing the signed bytes.

**Implication:** Our current SignedEnvelope “optional support” is **not sufficient for KOI-net interop** unless we:
- remove schema extras from signed payloads, and
- adopt KOI-net identity conventions (KoiNetNode ORNs) for `source_node`/`target_node`.

### 4.6 Endpoint pathing and defaults (Medium)

**Observed:**
- We expose KOI endpoints at root paths (e.g., `/events/poll`), while KOI-net’s server example often mounts under `/koi-net/*`.

**Impact:** KOI-net nodes may default to `/koi-net` base paths in configs, so out-of-the-box interop may fail without reconfiguration.

**Recommendation:**
- Add a `/koi-net` prefixed router that mirrors the strict KOI-net API surface (without breaking existing internal clients).

### 4.7 Reliability semantics (Strategic divergence; likely desirable)

**Observed:**
- We implemented a confirm-on-success pipeline with `/events/confirm` and persistent queues.
- KOI-net’s reference network queue flush is best-effort and (currently) not durably persisted by default.

**Impact:** Full replacement with KOI-net defaults would reduce reliability.

**Recommendation:**
- Keep reliability features as **optional extensions** and document them as such.
- Propose upstream options:
  - persistence hooks wired into KOI-net lifecycle,
  - optional ack/confirm extension for stronger delivery semantics.

### 4.8 Node identity + trust model mismatch (High, for secure interop)

**Observed:**
- KOI-net’s “secure mode” ties node identity to cryptographic keys:
  - `source_node`/`target_node` are `rid-lib` `KoiNetNode` ORNs (`orn:koi-net.node:<name>+<hash>`).
  - `<hash>` is derived from the node’s public key (see `koi-research/sources/blockscience/koi-net/src/koi_net/config.py`).
  - Node public keys are distributed via **NodeProfile bundles** in the network cache/dereference layer (see `koi-research/sources/blockscience/koi-net/src/koi_net/secure.py`).
- RegenAI’s current envelope verification uses an out-of-band env-provided mapping:
  - `KOI_PUBLIC_KEYS_JSON` / `KOI_PUBLIC_KEYS_PATH` → `{node_id -> PEM}` (see `koi-sensors/shared/koi_envelope.py`).
- RegenAI node identifiers are currently arbitrary strings (often timestamp-suffixed) rather than `KoiNetNode` RIDs (see `koi-sensors/koi_protocol/nodes/koi_node.py`).

**Impact:** even if we make payload schemas strict, **full KOI-net secure validation will still fail** unless we align identity and public key distribution.

**Recommendation:**
- Decide which “security posture” we want for interop:
  1. **Insecure interop mode:** accept SignedEnvelope but do not enforce KOI-net’s NodeProfile-based trust chain (fastest to interop, weaker trust).
  2. **KOI-net secure parity:** adopt `KoiNetNode` identity generation + NodeProfile bundles + dereference-based trust validation (strongest, more work).

### 4.9 Cache/state persistence mismatch (Medium, impacts durability + fetch semantics)

**Observed:**
- KOI-net uses `rid-lib` `Cache` to persist bundles on disk.
- RegenAI coordinator caches bundles in memory (`koi-sensors/koi_protocol/nodes/koi_node.py` uses `self.cache: Dict[str, Bundle] = {}`), with no durable store for bundles themselves.

**Impact:**
- After restarts, `/bundles/fetch` and `/manifests/fetch` may return “not found” for knowledge we previously processed, even though events were delivered.
- Interop nodes that rely on state transfer for reconciliation will not behave as expected.

**Recommendation:**
- Adopt `rid-lib` `Cache` (or an equivalent durable store) for bundles/manifests, at least for the coordinator’s full-node role.

### 4.10 Practical adoption constraint: Python version skew (Medium)

**Observed:**
- The local `koi-net` source uses Python 3.12+ syntax (e.g., `type RequestModels = ...` in `koi-research/sources/blockscience/koi-net/src/koi_net/protocol/api_models.py`), which fails under Python 3.11.
- Our services/docs currently describe Python 3.8+ / 3.11-compatible environments (`koi-processor/requirements.txt`).

**Impact:** “Adopt koi-net as a library” may require:
- upgrading service runtimes to Python 3.12+, or
- vendoring/wrapping only the protocol models in a 3.11-compatible way.

**Recommendation:**
- Treat Python runtime upgrade as an explicit decision point in any “full koi-net adoption” plan.

### 4.11 Boundary interfaces and proxy nodes (High, for inter-org deployments)

**Observed:**
- BlockScience framing emphasizes sensors/actuators/processors and **proxy nodes** as boundary interfaces between “inside the KOI-net” and “outside systems / other orgs”.
- RegenAI already has boundary-adjacent components (e.g., forwarders, MCP servers, dashboards), but we do not formalize them as **proxy nodes** with explicit “controlled subset” semantics or stable access-control policies.

**Impact:**
- Hard to safely expose a bounded subset of internal knowledge to external consumers or partner networks.
- Increased risk of accidental over-sharing, and difficulty aligning inter-org expectations (especially when SignedEnvelope is enabled).

**Recommendation:**
- Treat “proxy node” as a first-class role in our architecture and configuration:
  - explicit allowlists (RID types, sources, collections),
  - policy metadata (“From where / From whom / For whom / For what”),
  - and audited export surfaces (e.g., MCP adapter node at the boundary).

### 4.12 FUN vs CRUD plane separation (Medium, prevents protocol surface creep)

**Observed:**
- KOI-net frames FUN events (“forget/update/new”) as signaling primitives (event plane), and contrasts them with CRUD operations (oversight/administration plane).
- RegenAI currently mixes KOI-net endpoints with operational extensions like `/events/confirm` and other management endpoints.

**Impact:**
- Risk of protocol “surface creep” where operational concerns leak into signed payload schemas (which breaks strict KOI-net signature verification).
- Confusion for external nodes about what is protocol vs what is local admin behavior.

**Recommendation:**
- Treat strict KOI-net endpoints (ideally under `/koi-net/*`) as the FUN/event+state plane.
- Treat delivery confirmation, dashboards, sensor control, and other ops as a separate admin/CRUD plane (separate path prefix and documentation).

### 4.13 Provenance and CATs alignment (Medium → High as networks scale)

**Observed:**
- KOI-net roadmapping explicitly calls out provenance/trust as essential for multi-hop networks (CATs — Content‑Addressable Transformers).
- RegenAI already creates “CAT receipts” in places, but they are not yet clearly standardized as content-addressable transform records that can be exchanged/verified across a network.

**Impact:**
- Reduced ability to audit/verify knowledge transformations across hops and across organizational boundaries.
- Harder to align with BlockScience’s provenance/trust direction as networks grow and become less trusted.

**Recommendation:**
- Align receipts with the CATs concept: treat each transformation as a first-class, content-addressed knowledge object that links input/output manifests and transformation metadata, and can be propagated and verified across nodes.

---

## 5. Recommended Alignment Strategy (No Fragmentation, No Downgrade)

### 5.1 Define “Interop Levels”

Use these levels to scope work and measure success:

1. **Level 1 — Wire-compatible (unsigned):** endpoints accept/emit KOI-net shapes, but do not require envelope verification; hashes may still diverge (not ideal).
2. **Level 2 — Wire + hash compatible:** `rid-lib` hashing and RID parsing are authoritative; state transfer is compatible.
3. **Level 3 — SignedEnvelope interop:** strict KOI-net payloads + working signature validation with reference nodes.
4. **Level 4 — Reference-node substitution:** adopt or wrap `koi-net` NodeInterface (only if reliability constraints can be preserved).

### 5.2 Preferred approach: “Selective + adapter”

1. **Adopt `rid-lib`** for RID parsing + JCS hashing (foundation).
2. Build a **strict KOI-net adapter surface** (`/koi-net/*`) that:
   - accepts SignedEnvelope requests with KOI-net payload models,
   - emits SignedEnvelope responses with KOI-net payload models,
   - converts between strict wire payloads and our internal extended models.
3. Keep our reliability semantics (`/events/confirm`, queue persistence) as RegenAI extensions, but do not require them for KOI-net compatibility.
   - Conceptually: keep the strict `/koi-net/*` surface as the **FUN plane**, and keep confirmations/ops as a separate **CRUD/admin plane**.

This minimizes rework and avoids operational regressions.

---

## 6. Concrete Actions (Prioritized)

### P0 (Foundation, unblock interop)
- Adopt `rid-lib` hashing (`sha256_hash_json`) for manifest generation and integrity checks.
- Replace local RID parsing/typing (`koi-sensors/koi_protocol/core/rid_system.py`) with `rid_lib.RID`/`RIDType` (or ensure local types are compatible wrappers).
- Introduce “wire vs internal” model separation:
  - wire: exact rid-lib/koi-net schemas (no extras),
  - internal: operational fields preserved inside `contents`.
- Add a minimal, stable **provenance + policy** shape in `contents` (not manifests) that can carry “From where / From whom / For whom / For what” + consent/agreements metadata without breaking wire schemas.

### P1 (Enable SignedEnvelope interop)
- Add `/koi-net/*` endpoints that follow KOI-net request/response models exactly:
  - `POST /koi-net/events/broadcast`
  - `POST /koi-net/events/poll`
  - `POST /koi-net/bundles/fetch`
  - `POST /koi-net/manifests/fetch`
  - `POST /koi-net/rids/fetch`
- Ensure signed payloads include **no non-schema fields**:
  - remove `node_id` from poll requests in KOI-net mode,
  - remove `event_ids` and similar extensions from KOI-net signed responses.
- Align node identity to KOI-net `KoiNetNode` ORNs and adopt the key→RID derivation convention if we want full secure validation compatibility.

### P2 (Durability + upstream collaboration)
- Decide on a persistence backend (JSON vs SQLite/Postgres) for coordinator queues and caches.
- Prepare upstream proposals:
  - optional ack/confirm extension,
  - persistence hooks wired into KOI-net node lifecycle,
  - guidance on best-effort vs durable operation modes.

---

## 7. Validation: “Definition of Done” for KOI-net Interop

Interop is real (not aspirational) when:

- A KOI-net reference node (e.g., `koi-net-node-template`) can:
  - broadcast events to our coordinator,
  - poll events from our coordinator,
  - fetch bundles/manifests/rids from our coordinator,
  - and validate SignedEnvelope signatures on all responses.
- Hashes (`sha256_hash`) match across nodes for the same contents using `rid-lib`.
- Our internal pipeline still preserves:
  - confirm-on-success behavior to downstream processors,
  - durable queueing,
  - and correct HTTP failure semantics.

---

## 8. Notes on Background Reading (for context and alignment)

See the “Background Reading” section in `koi-research/docs/KOI_PROTOCOL_ALIGNMENT_REFERENCE.md` for:
- KOI v1–v3 repo inventory (`BlockScience/koi`)
- blog posts (“Objects as Reference”, KOI-net protocol preview, etc.)
- reference node implementations and related projects

Particularly relevant for architecture + governance framing:
- Local copies (preferred for this repo):
  - `koi-research/sources/blockscience/blog-architecting-koi.md`
  - `koi-research/sources/blockscience/blog-koi-net-protocol-preview.md`
  - `koi-research/sources/blockscience/blog-koi-network-protocol-interlay.md`
  - `koi-research/sources/blockscience/blog-koi-nodes-as-neurons.md`
  - `koi-research/sources/blockscience/blog-language-for-knowledge-networks.md`
  - `koi-research/sources/blockscience/blog-objects-as-reference.md`
- Original posts:
  - https://blog.block.science/architecting-knowledge-organization-infrastructure/

These sources are best used to align not only on payloads, but also on **intended norms** (minimal extensions, upstream-first, no fragmentation).

---

## 9. Suggested Spikes (to de-risk adoption)

These are lightweight, high-signal experiments that can be completed before any major refactor:

1. **Hash parity spike (rid-lib vs current)**
   - Goal: demonstrate hash mismatch on real bundle contents and quantify blast radius (dedup/versioning implications).
   - Deliverable: a small script that prints both hashes for representative payloads and confirms parity after switching to `sha256_hash_json`.

2. **Strict SignedEnvelope interop spike**
   - Goal: prove a KOI-net node can sign a request our coordinator accepts, and can verify our signed responses.
   - Deliverable: an integration test that uses KOI-net protocol models to sign `PollEvents` and verify an `EventsPayload` response.

3. **`/koi-net` router shim**
   - Goal: add KOI-net-compatible paths without breaking existing internal clients.
   - Deliverable: a FastAPI router mounted at `/koi-net` that proxies to existing handlers but emits strict KOI-net schemas.

4. **Bundle cache persistence spike**
   - Goal: demonstrate durable state transfer across coordinator restarts (`/bundles/fetch`, `/manifests/fetch`).
   - Deliverable: proof-of-concept storing bundles in `rid-lib` `Cache` and fetching after restart.

5. **Proxy-node “controlled subset” spike**
   - Goal: prove we can expose a bounded subset of knowledge across an org boundary (proxy node pattern).
   - Deliverable: minimal allowlist-based export via an adapter node (e.g., MCP adapter) with explicit policy metadata.

6. **Provenance/CATs spike**
   - Goal: make transformations verifiable across hops.
   - Deliverable: content-addressed receipts that bind input/output manifest hashes + transform metadata, stored/queried as knowledge objects.

## Appendix A. Schema Mapping Cheat Sheet (Internal → KOI-net wire)

This is the key practical constraint: **anything signed must match KOI-net schemas exactly**.

### A.1 Poll request

- **RegenAI today (internal):** includes `node_id`, `include_event_ids`.
- **KOI-net wire:** `PollEvents = {type: \"poll_events\", limit: int}` and identity comes from `SignedEnvelope.source_node`.

### A.2 Event payload

- **RegenAI today (common shape):**
  ```json
  {\"event_type\":\"NEW\",\"rid\":\"...\",\"timestamp\":\"...\",\"source_node\":\"...\",\"bundle\":{...}}
  ```
- **KOI-net wire (Event):**
  ```json
  {\"rid\":\"...\",\"event_type\":\"NEW\",\"manifest\":{...},\"contents\":{...}}
  ```
  - sender identity is the envelope `source_node`
  - “when” can be represented via `manifest.timestamp`
  - any extra operational fields should be moved into `contents` under a stable namespace (e.g., `contents._regen`)

### A.3 Manifest/bundle

- **RegenAI today (manifest):** includes `content_hash` plus operational fields (`size_bytes`, `content_type`, `metadata`, etc.).
- **KOI-net wire (rid-lib Manifest):** `{rid, timestamp, sha256_hash}` only.

Practical consequence: for strict interop, the “extra manifest fields” must become part of `contents` (or a separate bundle contents envelope), not the manifest itself.
