# KOI Protocol Alignment Reference

This document captures how we align RegenAI's pipeline with the KOI protocol while collaborating with BlockScience to evolve the protocol without fragmentation.

---

## Status Summary (Dec 2025)

**Pipeline health**: ✅ All services operational, all audit issues resolved.

| Area | Status |
|------|--------|
| POST polling endpoints | ✅ Done — All forwarders and docs use POST |
| Delivery confirmation | ✅ Done — Ack only on `success: true` |
| HTTP error semantics | ✅ Done — Bridges return 500 on failure |
| SignedEnvelope support | ✅ Done — Optional, env-configurable |
| Queue persistence | ✅ Done — JSON file (coordinator + sensors) |
| Pending/processed state | ✅ Done — Sensors track before/after emit |

**Recommended next step** — Research adopting BlockScience packages:

| Package | Replaces | Benefit |
|---------|----------|---------|
| `rid-lib` | Our Bundle/Manifest classes | Standard RID parsing, content hashing, interop |
| `koi-net` | Our coordinator/forwarder | Full NodeInterface, knowledge handlers, network graph |

**Action items:**
1. 🔲 Spike: Install `rid-lib` and test if our payloads are compatible with their classes
2. 🔲 Spike: Evaluate `koi-net` NodeInterface as coordinator replacement
3. 🔲 Document trade-offs: maintenance burden vs. flexibility of custom code
4. 🔲 Decide: adopt, wrap, or continue with compatible implementation

See [Future work](#future-work-when-prioritized) for detailed research questions.

---

## KOI Protocol Source of Truth

**Authoritative sources** (BlockScience):

| Package | GitHub | PyPI | What it provides |
|---------|--------|------|------------------|
| **rid-lib** | [BlockScience/rid-lib](https://github.com/BlockScience/rid-lib) | `pip install rid-lib` (v3.2.12) | RID parsing, Manifest, Bundle, Cache classes |
| **koi-net** | [BlockScience/koi-net](https://github.com/BlockScience/koi-net) | `pip install koi-net` (v1.2.4) | NodeInterface, protocol endpoints, knowledge handlers |

**rid-lib** defines the data structures:
- `RID` — Reference Identifier class with `from_string()`, context/reference parsing
- `Manifest` — Descriptor with `rid`, `timestamp`, `sha256_hash`; use `Manifest.generate(rid, data)`
- `Bundle` — Manifest + contents; the actual knowledge object
- `Cache` — Local filesystem storage for bundles

**koi-net** defines the protocol:
- 5 endpoints: `/events/broadcast`, `/events/poll`, `/bundles/fetch`, `/manifests/fetch`, `/rids/fetch`
- All POST with JSON body; event types are NEW, UPDATE, FORGET ("FUN")
- Full nodes (servers) vs partial nodes (pollers)
- `NodeInterface` class with knowledge processing pipeline

**Local copies** (for offline reference):
- `koi-research/sources/blockscience/koi-net`
- `koi-research/sources/blockscience/rid-lib`

**Our implementations** (compatible but don't use the packages directly):
| Component | Location |
|-----------|----------|
| Coordinator | `koi-sensors/koi_protocol/coordinator/koi_coordinator.py` |
| Forwarder | `koi-processor/scripts/coordinator_to_eventbridge_forwarder.py` |
| Event bridge v2 | `koi-processor/src/core/koi_event_bridge_v2.py` |
| Event bridge semantic | `koi-processor/src/core/koi_event_bridge_semantic.py` |
| Protocol overview | `koi-sensors/koi_protocol/README.md` |

**Key principle**: BlockScience's packages are the contract. Our implementations produce compatible payloads and behaviors. We can extend (e.g., `/events/confirm`) but must not break interop. Adopting `rid-lib` directly would give us standard RID parsing and content hashing.

## Protocol alignment principles
1. **Protocol-first**: Follow KOI-net request/response semantics and payload shapes.
2. **Minimal extensions**: Add only what is necessary for reliability or observability, and keep extensions optional.
3. **Backwards compatibility**: Maintain interop with reference implementations; deprecate local deviations gradually.
4. **Upstream first**: If a change is generally useful (ack/confirm, queue persistence), propose it upstream.
5. **No fragmentation**: Avoid forking the protocol; keep all changes compatible or documented as optional extensions.

## Current local behavior (summary)
- Coordinator supports legacy `GET /events/poll` and KOI-net `POST /events/poll`; internal forwarders now use POST with `include_event_ids`.
- Forwarder confirms delivery only when downstream returns `success: true` in the response body.
- Coordinator now exposes KOI-net compatible POST endpoints (`/events/poll`, `/rids/fetch`, `/manifests/fetch`, `/bundles/fetch`) with optional SignedEnvelope handling.
- SignedEnvelope verification/signing is supported when keys are configured; GET endpoints remain for legacy clients.
- Event bridge expects KOI-like event payloads but does not enforce signed envelopes.

## Divergences from KOI-net (to address)
- **HTTP method**: Legacy GET endpoints remain for compatibility; docs now reference POST as preferred.
- **Signed envelopes**: Supported; key distribution and target validation defaults documented (env vars below).
- **Delivery confirmation**: `/events/confirm` is a local extension (not in KOI-net).
- **Pending/confirmed state**: sensors now mark pending before emit and processed on success; retry policy documented (not enforced automatically).
- **Error semantics**: ✅ Event bridges now return HTTP 500 on failure (with `success=false` in body); forwarders handle both status codes and body.

## Audit issue status (KOI-related)

| Issue | Status | Notes |
|-------|--------|-------|
| Forwarder confirms on HTTP 200 only | DONE | Forwarders now confirm only on `success: true`. |
| Bridges return HTTP 200 on failure | DONE | Bridges now return HTTP 500 on failure; forwarders handle both. |
| Events acked when processing failed | DONE | Acks only after downstream success. |
| Double-enqueue in coordinator | DONE | Broadcast no longer queues twice. |
| No SignedEnvelope handling | DONE | Optional SignedEnvelope support added. |
| Event queue is in-memory only | DONE | Queue persists to JSON. |
| No pending vs confirmed state | DONE | Pending tracking added in sensor state. |

## Recent fixes (implemented)
- Forwarder confirm now checks `success` in the event bridge response body before acking.
- Coordinator no longer double-enqueues events (broadcast handles queueing).
- Coordinator supports KOI-net compatible POST endpoints and unsigned envelope payloads.
- Coordinator event queue now persists to disk across restarts.
- Sensor persistent state now tracks pending vs confirmed items, and sensors mark processed only after successful emission.
- Forwarder and partial nodes now use POST polling; optional SignedEnvelope signing/verification added.
- Code graph and semantic forwarders now use POST polling and confirm only on success.
- GAIA KOI API proxies use POST polling for coordinator status/health.
- Added an in-process integration test that validates broadcast → poll → forward → confirm.
- All user-facing docs updated to reference POST polling: QUICKSTART.md, koi_protocol/README.md, INTEGRATION_GUIDE.md, KOI-PIPELINE-INTEGRATION.md.
- Retry policy and key distribution defaults documented in this file.
- Event bridges (v2 and semantic) now return HTTP 500 on failure (instead of 200 with `success=false`).
- Forwarders updated to extract error details from non-200 responses.
- Added integration test for bridge failure scenario (HTTP 500 → no confirm).

## Alignment plan (near-term)
1. ✅ **Migrate remaining docs/scripts to POST endpoints** — Completed; all docs now reference POST polling.
2. ✅ **Document key distribution defaults** — Env vars and target validation defined.
3. 🔲 **Use `rid-lib` models** for RID/Manifest/Bundle parsing and hashing to align semantics.
4. ✅ **Define retry behavior for pending items** — Retry policy table added above.
5. 🔲 **Confirm queue persistence strategy** (current JSON file vs SQLite/Postgres).

## Proposed upstream contributions
- **Delivery confirmation extension**: Optional `/events/confirm` with event_ids for ack-based cleanup.
- **Queue persistence**: Wire `_load_event_queues()` and `_save_event_queues()` into lifecycle in `koi-net`.
- **Reliability notes**: Clarify that broadcast is best-effort and recommend polling/state fetch for durability.
- **Compatibility guidance**: Document optional ack/confirm extension and idempotent processing expectations.

## Retry policy for pending items (recommended defaults)

Sensors mark items `pending` before emit and `processed` only on success. The following policy handles failures:

| Condition | Retry Behavior |
|-----------|----------------|
| Network timeout or 5xx from coordinator | Exponential backoff: 10s, 30s, 60s, 300s, then hourly up to 24h |
| 4xx from coordinator (bad request) | Log and drop; likely a data issue; manual review |
| Coordinator ack (HTTP 200) but downstream bridge fails | Event remains queued; forwarder re-polls automatically |
| Sensor restart while pending | Items re-emitted on next collection cycle (idempotent via content hash) |

**Implementation notes:**
- Sensors use `shared/persistent_state.py` for pending/processed tracking (JSON file).
- Forwarders poll with `include_event_ids=true` and call `/events/confirm` only after downstream success.
- Events that remain unconfirmed for >24h should trigger an alert (future reconciliation job).

## Key distribution and target validation (defaults)

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

**Target validation** (when `KOI_ENVELOPE_VERIFY=true`):
- Envelope `target_node` must match the local `node_id` when `KOI_ENVELOPE_VERIFY_TARGET=true`.
- Sender must have a public key in `KOI_PUBLIC_KEYS_JSON`/`KOI_PUBLIC_KEYS_PATH`.
- If validation fails, return HTTP 400 and log the rejection.

**Key rotation guidance:**
- Rotate keys quarterly or on suspected compromise.
- Keep previous public keys in `KOI_TRUSTED_KEYS_DIR` for overlap period (7 days).
- Announce new public keys out-of-band (e.g., shared config repo or manual distribution).

## Operational safeguards (non-protocol)
- systemd units for coordinator, forwarder, event bridge, and other critical services.
- Email alerts on service failure and queue backlog thresholds.
- Reconciliation job to detect "scraped but not stored" and re-queue.

## Open questions to resolve with BlockScience
- Is an ack/confirm endpoint acceptable as an optional protocol extension?
- Should queue persistence be recommended or required for full nodes?
- Preferred signing/envelope expectations for partial nodes (optional vs required).
- Are POST-only endpoints strictly required, or can GET remain as a compatible fallback?

## Future work (when prioritized)

### Research: Adopting rid-lib and koi-net

**Why consider this?**
- Reduces maintenance burden (BlockScience maintains the packages)
- Guarantees interop with other KOI-net nodes
- Gets us bug fixes and improvements automatically
- Enables collaboration on shared codebase

**rid-lib research questions:**
- Can we deserialize our existing payloads into `rid_lib.Bundle` / `rid_lib.Manifest`?
- Does their `sha256_hash` match our content hashing approach?
- Can we use `rid_lib.Cache` for our coordinator's event queue?
- What's the migration path for existing stored data?

**koi-net research questions:**
- Can `NodeInterface` replace our `KOICoordinator` class?
- How do their knowledge handlers map to our event processing?
- Does their polling model support our `include_event_ids` + `/events/confirm` extension?
- Can we register custom handlers for our semantic extraction pipeline?
- What's the impact on our sensors (partial nodes)?

**Adoption options:**
1. **Full adoption** — Replace our code with their packages entirely
2. **Wrap** — Use their classes internally, keep our API surface
3. **Selective** — Adopt `rid-lib` for data structures, keep custom coordinator
4. **Stay compatible** — Continue with our implementation, ensure payload compatibility

### Upstream contributions (when ready)
- Draft issue/PR for `/events/confirm` extension in `koi-net`
- Propose queue persistence hooks for full nodes
- Document our retry policy as a recommended pattern

### Infrastructure improvements (as needed)
- Migrate queue persistence from JSON to SQLite/Postgres for durability
- Add 24h reconciliation alerting for unconfirmed events
- Consider deprecating legacy GET endpoints after migration period
