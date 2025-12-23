# KOI Protocol Alignment — Pre-Implementation Research (Dec 2025)

Scope: research + planning only (no production code changes). Primary reference: `koi-research/docs/KOI_PROTOCOL_ALIGNMENT_REFERENCE.md`.

---

## 1) Hash Parity Spike Results (RegenAI vs rid-lib)

### Goal
Quantify how often RegenAI’s current `Manifest.content_hash` (sha256 over `json.dumps(sort_keys=True)`) differs from rid-lib’s KOI-net hashing contract (sha256 over **JCS canonicalized JSON**).

### What was tested (real payloads)
We hashed **9,588** real JSON payloads already in this repo (not synthetic):
- Coordinator queue bundle contents: `koi-sensors/koi_protocol/coordinator/coordinator_event_queue.json` (3)
- Discourse sensor output docs: `koi-sensors/sensors/discourse/output/*.json` (9,463 docs across 159 files)
- Telegram sensor output items: `koi-sensors/sensors/telegram/output/*.json` (22 items across 11 files)
- Twitter output items: `koi-sensors/sensors/twitter/output/*.json` (22 tweets across 8 files)
- Podcast transcript JSONs: `koi-sensors/sensors/podcast/transcripts/*.json` (67 files)
- Medium test data: `koi-sensors/sensors/medium/medium_articles_test.json`

Script used (created in `/tmp`, not committed): `/tmp/koi_hash_parity_spike.py`
- It computes three hashes per payload:
  1) **legacy**: `sha256(json.dumps(sort_keys=True).encode("utf-8"))` (matches current RegenAI manifest hashing)
  2) **compact**: `sha256(json.dumps(sort_keys=True, separators=(",",":"), ensure_ascii=False))` (useful control)
  3) **rid-lib JCS**: `sha256(rid_lib._vendor.org.webpki.json.Canonicalize.canonicalize(obj, utf8=True))`

Raw output captured: `/tmp/koi_hash_parity_spike_output.md` (from a full run over all 9,588 payloads).

### Results (bottom line)
- **Legacy vs rid-lib JCS**: **9,588 / 9,588 mismatched (100%)**
  - This means **any existing RegenAI bundle/manifest hashed today will not match KOI-net/rid-lib hashes** for identical JSON content.
- **“Compact JSON” vs rid-lib JCS**: **843 / 9,588 mismatched (8.79%)**
  - Even if we “fix” RegenAI to use compact UTF-8 JSON (`separators=(",",":"), ensure_ascii=False`), we still won’t match rid-lib for a non-trivial subset because JCS **normalizes numbers**.

### Why the hashes differ (evidence)

#### A) RegenAI legacy uses non-canonical JSON bytes (whitespace + ASCII escaping)
Current code (`koi-sensors/koi_protocol/core/bundle_system.py`) uses:
- `json.dumps(content, sort_keys=True).encode("utf-8")`
Python’s default JSON formatting inserts whitespace and escapes non-ASCII, which changes the hash bytes relative to JCS.

#### B) JCS number normalization breaks even “compact JSON”
Example from a real Discourse payload (`koi-sensors/sensors/discourse/output/discourse_20250926_010205.json`, `documents[25]`):
- Regen-style compact JSON emits `"score":1.0`
- rid-lib JCS emits `"score":1` (trailing `.0` removed)

This alone changes the sha256 hash.

#### C) Concrete “real bundle” example from the coordinator queue
From `koi-sensors/koi_protocol/coordinator/coordinator_event_queue.json`:
- Stored manifest hash equals Regen legacy recomputation (expected)
- rid-lib JCS hash differs

Example (one of 3 events):
- RID: `rid:test-fail:1`
- Stored/legacy: `24f6a8383c8f88ce8c39333fb7d3842bf29c8a2dc690e0288af3d91f829b3113`
- rid-lib JCS: `a8d1890cfdcfdca1b985ab7cc291fe4ec8597268922cb0d8529d85e2f621dd71`

### Dependency checks (requested)
- `rid-lib` is **not** present in service requirements today:
  - `koi-sensors/requirements.txt` does not include it
  - `koi-processor/requirements.txt` does not include it
- Some in-repo code already imports `rid_lib` (e.g., `koi-sensors/shared/rid_types/*.py`), so adding the dependency is required even before full protocol alignment work can be considered “complete”.
- There is a local offline copy at `koi-research/sources/blockscience/rid-lib/` (version `3.2.8` in `pyproject.toml`).
- `canonicaljson` (PyPI) is **not sufficient** to match rid-lib JCS:
  - It does not normalize `1.0 -> 1`, so it disagrees with rid-lib on ~8.8% of tested payloads.
  - It also does not expose `canonicaljson.canonicalize()`; the API is `encode_canonical_json()`.

### Blast radius (hash parity)
Any system component that:
- persists `content_hash`/`sha256_hash` for later verification, or
- uses `content_hash` for dedup/version decisions, or
- expects hashes to match other KOI-net nodes,

…will be impacted.

Immediate impacted mechanisms in this repo:
- Coordinator deduplication state (URL/RID hash maps)
- Any stored manifests in DB metadata (`koi_manifest` currently stores the legacy hash)
- Any future interop with rid-lib / KOI-net reference nodes (hash mismatch blocks Level 2 interop)

---

## 2) Existing Data Assessment (storage + migration complexity)

### Where bundles/manifests live today
**Coordinator (koi-sensors)**
- Event queue persistence (contains full events + bundles):  
  `koi-sensors/koi_protocol/coordinator/coordinator_event_queue.json`
- Deduplication persistence (RID->hash and URL->hash maps):  
  `koi-sensors/koi_protocol/coordinator/coordinator_dedup_state.json`
  - Current contents:
    - `url_hashes`: **3,873** entries
    - `content_hashes`: **12** entries
- Bundle/manifest “cache” is **in-memory only** (`KOIFullNode.cache`) → **lost on restart**, so `/bundles/fetch` and `/manifests/fetch` are not durable.

**Sensors (koi-sensors)**
- Some sensors write raw collected items to `koi-sensors/sensors/**/output/*.json` (not KOI bundles).
- Base sensor framework supports caching KOI bundles to disk under `KoiNetConfig.cache_directory` (default `.sensor_cache`) via `koi-sensors/shared/handlers/base_sensor.py`, but no `.sensor_cache` directory is present in-repo (likely runtime-only).

**Processor (koi-processor)**
- KOI memory storage is in Postgres tables (not in this repo as data files). Evidence of production-scale volume exists in:
  - `koi-processor/docs/FINAL_VERIFICATION_REPORT.md` (Sep 30, 2025): **2,835 KOI memories**, **19,760+ CAT receipts**
- `koi_event_bridge_v2` persists a copy of the KOI manifest into DB metadata:
  - In `koi-processor/src/core/koi_event_bridge_v2.py`, `metadata` includes `"koi_manifest": event.bundle.manifest.dict()`
  - This means existing DB rows contain the **legacy manifest schema + legacy hash** today.

### Volume estimate of “legacy-hash” data
Hard numbers available from this repo:
- Coordinator dedup state: **3,885** hashes persisted (`coordinator_dedup_state.json`)
- Documentation evidence of DB volume (Sep 2025): **2,835** KOI memories and **19,760+** receipts
- Real sensor payload corpus in-repo: **9,588** documents/items (not all necessarily ingested, but representative of shape/entropy)

Recommended verification queries (run on the live DB where KOI is deployed):
- Total KOI rows: `SELECT COUNT(*) FROM koi_memories;`
- Rows with embedded KOI manifest metadata:  
  `SELECT COUNT(*) FROM koi_memories WHERE metadata ? 'koi_manifest';`
- Distinct legacy hashes stored:  
  `SELECT COUNT(DISTINCT (metadata->'koi_manifest'->>'content_hash')) FROM koi_memories WHERE metadata ? 'koi_manifest';`

### Code paths that generate/assume the legacy KOI manifest hash
**Primary legacy hashing implementation**
- `koi-sensors/koi_protocol/core/bundle_system.py`
  - `Manifest.generate()` and `Manifest.verify_content()`: `json.dumps(sort_keys=True)` → sha256

**Places that recompute the hash when missing**
- `koi-sensors/koi_protocol/coordinator/koi_coordinator.py`
  - `_koi_net_event_to_koi_event_data()` + legacy `"data"` → bundle conversion
- `koi-processor/scripts/coordinator_to_eventbridge_forwarder.py`
- `koi-processor/scripts/coordinator_to_code_graph_forwarder.py`
- `koi-processor/src/core/coordinator_to_semantic_bridge.py`

**Tests that encode legacy assumptions**
- `koi-processor/tests/test_koi_flow_integration.py` (constructs manifests with legacy hashing)

### Migration complexity (assessment)
Key factors:
1) **100% hash drift** when switching to rid-lib JCS hashing → everything “legacy-hashed” becomes interop-incompatible.
2) **Dedup side effects**:
   - Coordinator’s `url_hashes`/`content_hashes` will treat all content as changed if the hashing algorithm changes (unless migrated).
3) **DB schema coupling**:
   - KOI manifest metadata is stored in `koi_memories.metadata['koi_manifest']`, and downstream consumers read it (e.g., `koi-processor/src/content/daily_curator.py` expects `koi_manifest.metadata.url`).
4) **Durability gap**:
   - Coordinator does not persist bundles/manifests in a rid-lib cache; strict KOI-net semantics assume fetch endpoints are meaningful across restarts.

Net: migration is feasible but requires a deliberate strategy (see recommendations below) and a wire/internal model split to avoid breaking SignedEnvelope interop.

---

## 3) Decision Recommendations (open questions)

### 3.1 Security posture (insecure interop vs KOI-net secure parity)

**Recommendation**
- Implement **two tiers**:
  1) **P1: “Insecure interop” compatibility tier** for internal services: signed envelopes with manual key distribution (current `KOI_PUBLIC_KEYS_JSON`-style) and optional target enforcement.
  2) **P2: KOI-net secure parity** (NodeProfile trust chain + KoiNetNode identity derivation) only if/when we need to interoperate with unmodified KOI-net reference nodes in secure mode.

**Why**
- KOI-net reference `NodeServer` is wired to secure validation (`koi_net/secure.py`) and expects:
  - node IDs of type `KoiNetNode` (`orn:koi-net.node:<name>+<hash>`)
  - NodeProfile bundles resolvable in-cache (or bootstrapped via NEW events)
  - key hash checks (`source_node.hash == sha256_hash(node_profile.public_key)`)
  - strict signature verification on Pydantic-serialized models
- “Insecure interop” is significantly lower effort (fits current ops model) but cannot claim “secure parity” with reference nodes.

**What we lose with insecure**
- No on-network trust discovery / bootstrapping via NodeProfile bundles
- No key-bound identity derivation (stronger spoofing resistance)
- No drop-in secure-mode interop with KOI-net reference nodes

### 3.2 Hash migration strategy

**Recommendation**
- Adopt **dual-hash support** during migration:
  - Store/track both:
    - `legacy_content_hash` (current Regen hash)
    - `sha256_hash` (rid-lib JCS hash)
  - Use `sha256_hash` on the strict KOI-net surface and when generating rid-lib manifests.
  - Keep `legacy_content_hash` only for backward compatibility (internal dedup/state) until cutover completes.

**Why**
- The spike shows **100%** mismatch between legacy and rid-lib hashes across 9,588 real payloads.
- Even “canonical JSON” libraries that don’t implement JCS number rules will disagree with rid-lib on ~**8.8%** of payloads.
- RIDs are not derived from the content hash in our system today, so **versioning RIDs is unnecessary** and would create additional churn.

### 3.3 Metadata namespace (is `contents._regen` the right convention?)

**Recommendation**
- Yes: adopt `contents._regen` for Regen-specific operational metadata **that must travel on the wire** while keeping:
  - Event schema strict (no extra event-level keys)
  - Manifest schema strict (rid-lib `Manifest` only)

**Important nuance**
- Anything placed inside `contents` becomes part of the rid-lib `sha256_hash` (hash of contents).
- Avoid volatile/operational-only fields that would cause spurious hash churn (e.g., “collected_at”, “processed_at”) unless we *intend* them to version the object.

**Observed current patterns**
- Today we often store operational metadata in `manifest.metadata` and extra event keys (timestamp, source_node), which will break strict SignedEnvelope verification.
- Downstream code reads `metadata['koi_manifest']['metadata']` (e.g., daily curator URL extraction), so moving metadata requires a planned transition.

### 3.4 Python runtime (current versions + upgrade path to 3.12+)

**Findings**
- This workstation has both `python3` **3.11.13** and `python3.12` **3.12.3** installed.
- `koi-net` source in `koi-research/sources/blockscience/koi-net/src` uses Python 3.12-only syntax (`type RequestModels = ...`), so it **cannot be imported on Python 3.11**.
- `rid-lib` source does import on Python 3.11.

**Recommendation**
- If we plan to use `koi-net` as a library (even just protocol models), standardize KOI services involved in interop on **Python 3.12+**.
- If we only adopt `rid-lib` initially, Python 3.11 is sufficient for the hashing + RID parsing layer.

**Upgrade path**
- Add CI/runtime matrix for 3.11 + 3.12 initially, then converge on 3.12.
- Update Dockerfiles (where used) from `python:3.11-slim` to `python:3.12-slim`.
- Smoke-test critical deps (FastAPI, asyncpg/psycopg2, pgvector, cryptography).

### 3.5 Base path convention (`/koi-net/*`)

**Findings**
- Internal clients/scripts call root endpoints:
  - `/events/broadcast`, `/events/poll`, `/events/confirm`
- KOI-net reference NodeServer mounts under `/koi-net/*` by default.

**Recommendation**
- Do **not** “move” existing endpoints. Instead:
  - Add a strict external interop surface under `/koi-net/*`
  - Keep root endpoints as internal/legacy until clients are migrated

This avoids breaking forwarders, GAIA monitoring, and sensors during transition.

---

## 4) SignedEnvelope Gap Analysis (strict KOI-net compliance)

### Current state (RegenAI)
File reviewed: `koi-sensors/shared/koi_envelope.py` (and duplicated variant `koi-processor/scripts/koi_envelope.py`).

**Good news**
- Crypto is compatible with KOI-net:
  - ECDSA P-256
  - signature format is raw `r||s` base64
- Verified by running cross-verification tests under Python 3.12:
  - A KOI-net-signed PollEvents envelope verifies via RegenAI `verify_envelope()`
  - A RegenAI-signed PollEvents envelope verifies via KOI-net `SignedEnvelope.verify_with()`

**Blocking gaps for strict SignedEnvelope interop**
1) **Unknown fields cause signature failure (even if parsing succeeds)**
   - KOI-net parses payload into strict Pydantic models, discards unknown keys, then verifies signature on the re-serialized unsigned envelope.
   - Demonstrated failures:
     - PollEvents payload with extra `node_id` → `InvalidSignature`
     - Event payload with extra event-level `timestamp` → `InvalidSignature`
     - Manifest payload with extra `metadata` → `InvalidSignature`
2) **Timestamp string formatting must match KOI-net’s Pydantic serialization**
   - Pydantic serializes UTC datetimes as `...Z` (not `...+00:00`).
   - If we sign `manifest.timestamp` as `+00:00`, KOI-net will re-serialize as `Z` → signature mismatch.

### Specific schema fields that will break KOI-net verification today
These are currently present in RegenAI payloads but are not in KOI-net schemas:

**PollEvents request**
- `node_id` (identity belongs in envelope `source_node`)
- `include_event_ids` (not in KOI-net PollEvents)

**EventsPayload / Event**
- event-level `timestamp`
- event-level `source_node`
- event-level `bundle` (KOI-net uses `manifest` + `contents`)

**Manifest**
- `size_bytes`
- `content_type`
- `version`
- `metadata`
- `content_hash` (KOI-net/rid-lib uses `sha256_hash`)

**Bundle**
- root-level `rid` (rid-lib derives RID from the manifest; bundle is `{manifest, contents}`)

### What changes are needed (feasibility)
Strict SignedEnvelope interop is feasible once we:
- introduce a strict wire model transformation layer (internal ↔ wire)
- ensure signed payloads contain *only* KOI-net schema keys
- ensure timestamp serialization matches KOI-net (`Z` format) by using the same model serialization path (preferably rid-lib/koi-net Pydantic models rather than hand-built dicts)

---

## 5) Internal Client Impact Matrix (who breaks + what to change)

| Client / File | Uses coordinator endpoints | Non-standard fields relied on | Breaks under strict KOI-net SignedEnvelope? | Needed change |
|---|---|---|---|---|
| `koi-processor/scripts/coordinator_to_eventbridge_forwarder.py` | poll + confirm | poll: `node_id`, `include_event_ids`; response: `event_ids`; confirm endpoint itself | Yes | Keep using internal endpoints OR migrate to strict `/koi-net/events/poll` without `event_ids` and replace confirm semantics |
| `koi-processor/scripts/coordinator_to_code_graph_forwarder.py` | poll + confirm | same as above | Yes | same |
| `koi-processor/src/core/coordinator_to_semantic_bridge.py` | poll + confirm | same as above | Yes | same |
| `koi-sensors/koi_protocol/nodes/koi_node.py` | broadcast + poll | broadcast events include event-level `timestamp` + `source_node`; poll includes `node_id` | Yes (if SignedEnvelope enforced by KOI-net) | Split internal vs strict wire event models; identity in envelope, not payload |
| `koi-sensors/sensors/telegram/telegram_sensor.py` | broadcast | heartbeat event uses non-FUN `event_type=HEARTBEAT` and `data` field | Yes | Treat as internal ops-plane message; keep off strict KOI-net surface |
| `GAIA/packages/server/src/api/koi/index.ts` | poll (monitoring) | `node_id` | Yes | Point monitoring to internal endpoint, or sign strict PollEvents via envelope (no `node_id`) |
| `GAIA/packages/server/src/api/koi-proxy.ts` | poll (monitoring) | `node_id` | Yes | same |
| `koi-processor/tests/test_koi_flow_integration.py` | broadcast + poll + confirm | legacy hashing + event_ids flow | Yes | Update tests once wire/internal split and rid-lib hashing are introduced |

Also noted:
- Two separate SignedEnvelope helper implementations exist (`koi-sensors/shared/koi_envelope.py` and `koi-processor/scripts/koi_envelope.py`), which increases drift risk.

---

## 6) Revised Implementation Plan (P0/P1/P2)

This is an updated plan based on the spike + feasibility findings.

### P0 — Foundation (unblocks meaningful interop)
1) Adopt rid-lib hashing (JCS) and RID parsing in core KOI bundle/manifest generation.
2) Add dual-hash support internally (`legacy_content_hash` + rid-lib `sha256_hash`) with a cutover plan.
3) Introduce wire/internal model separation:
   - Internal models keep operational extensions (`event_ids`, confirm semantics, monitoring heartbeats).
   - Wire models match KOI-net schemas exactly.
4) Identify all “timestamp” sources and standardize wire timestamp serialization (`Z` via Pydantic/rid-lib models).

### P1 — Enable SignedEnvelope interop (strict)
1) Add a strict `/koi-net/*` surface that:
   - accepts/returns KOI-net request/response models only
   - signs/verifies using KOI-net-compatible serialization rules
2) Remove all non-schema keys from signed payloads (move necessary extras into `contents._regen` if they must be transmitted).
3) Decide how to handle reliability semantics:
   - keep `/events/confirm` as internal-only, or
   - implement “smart client” reconciliation behavior for strict KOI-net surface.

### P2 — Secure parity + durability
1) If needed for external KOI-net secure interop:
   - implement `KoiNetNode` identity derivation
   - implement NodeProfile bundle creation/distribution and trust bootstrap
2) Add durable bundle/manifest persistence using rid-lib `Cache` (or an equivalent store) so `/bundles/fetch` and `/manifests/fetch` work across restarts.
3) Backfill existing knowledge into the new cache where feasible (define authoritative source: DB vs sensor caches).

---

## 7) Risk Register (new/confirmed risks)

1) **KOI-net library requires Python 3.12+ in practice** (PEP 695 `type` alias) → may force runtime upgrades for strict interop.
2) **100% legacy hash drift** when adopting rid-lib hashing → requires a deliberate migration strategy; “just switch hashing” will break dedup/state and any cross-node verification.
3) **JCS numeric normalization** (e.g., `1.0` → `1`) creates subtle mismatches; canonicaljson-style “canonical JSON” is not sufficient for rid-lib parity.
4) **SignedEnvelope signature failure mode is non-obvious**: extra keys are silently discarded by Pydantic, then signatures fail (`InvalidSignature`), which can look like “crypto mismatch” rather than “schema mismatch”.
5) **Timestamp serialization mismatch (`+00:00` vs `Z`)** will cause signature failures unless wire serialization matches KOI-net exactly.
6) **Coordinator durability gap**: bundle/manifest cache is in-memory; strict KOI-net semantics assume state transfer works across restarts.
7) **Duplicate envelope helper implementations** (koi-sensors vs koi-processor) risk divergence in signing/verification rules over time.
8) **Metadata relocation impact**: downstream consumers currently expect manifest metadata fields (e.g., daily curator URL extraction); moving metadata into `contents._regen` requires coordinated updates and possible backfill.
