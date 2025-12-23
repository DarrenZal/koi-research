# KOI Protocol Alignment Status — December 2025

**Date:** 2025-12-23
**Status:** Level 3+ Interop Complete

This checkpoint documents the current production state of the KOI-net interoperability implementation.

---

## Summary

| Phase | Status | Description |
|-------|--------|-------------|
| P0 | ✅ Complete | Foundation (rid-lib JCS hashing, RID parsing) |
| P1a | ✅ Complete | Level 2 interop (strict wire models, Z timestamps) |
| P1b | ✅ Complete | Level 3 interop (SignedEnvelope, exclude_none) |
| P2a | ✅ Complete | Durable state transfer (persistent cache) |
| P2b | ✅ Complete | Retention + monitoring (pruning, metrics) |

**Total Tests:** 61 passing (P0: 24, P1b: 14, P2a: 26, P2b: 21 — some overlap)

---

## What's in Production

### Endpoints

All 5 `/koi-net/*` endpoints operational with optional SignedEnvelope support:
- `POST /koi-net/events/broadcast`
- `POST /koi-net/events/poll` (read-only, use internal `/events/confirm` for acks)
- `POST /koi-net/rids/fetch`
- `POST /koi-net/manifests/fetch`
- `POST /koi-net/bundles/fetch`

### Wire Format

Strict KOI-net schemas on all `/koi-net/*` responses:
- Manifest: `{rid, timestamp, sha256_hash}` only
- Bundle: `{manifest, contents}` only
- Timestamps: `Z` suffix

### Persistent Cache

- **Location:** `/opt/projects/koi-sensors/.rid_cache`
- **Current size:** 2,272 bundles, 26.84 MB
- **Format:** rid-lib Bundle JSON files

### Retention Policy

| Config | Value |
|--------|-------|
| `KOI_CACHE_MAX_SIZE_MB` | 500 (default) |
| `KOI_CACHE_MAX_AGE_DAYS` | 30 (default) |
| `KOI_CACHE_DISK_ALERT_PERCENT` | 80 (default) |

Protected RID patterns (never pruned):
- `orn:koi.node_profile:*`
- `orn:koi.identity:*`
- `orn:koi.config:*`

### Scheduled Jobs

| Timer | Schedule | Script |
|-------|----------|--------|
| `koi-cache-prune.timer` | Daily @ 3 AM | `scripts/prune_bundle_cache.py` |

---

## Key Files

### koi-sensors

| File | Purpose |
|------|---------|
| `koi_protocol/core/persistent_cache.py` | Persistent cache + retention policy |
| `koi_protocol/nodes/koi_node.py` | KOI node base with cache integration |
| `koi_protocol/coordinator/koi_coordinator.py` | Coordinator with `/koi-net/*` endpoints |
| `shared/koi_envelope.py` | SignedEnvelope (canonical implementation) |
| `scripts/prune_bundle_cache.py` | Cache pruning CLI |
| `scripts/seed_bundle_cache.py` | Cache seeding from event queue |
| `systemd/koi-cache-prune.{service,timer}` | Scheduled pruning |
| `tests/test_persistent_cache_p2a.py` | P2a tests (26) |
| `tests/test_cache_retention_p2b.py` | P2b tests (21) |

### koi-processor

| File | Purpose |
|------|---------|
| `scripts/koi_envelope.py` | SignedEnvelope (symlink to koi-sensors) |

### koi-research

| File | Purpose |
|------|---------|
| `docs/KOI_PROTOCOL_ALIGNMENT_REFERENCE.md` | Authoritative alignment reference |
| `reports/KOI_ALIGNMENT_STATUS_2025_12.md` | This checkpoint document |

---

## Rollback Notes

### If P2a/P2b issues occur:

1. **Disable cache persistence:**
   ```bash
   # Unset KOI_CACHE_DIR in .env
   # Restart coordinator
   ```

2. **Disable pruning:**
   ```bash
   sudo systemctl stop koi-cache-prune.timer
   sudo systemctl disable koi-cache-prune.timer
   ```

3. **Clear cache:**
   ```bash
   rm -rf /opt/projects/koi-sensors/.rid_cache/*
   ```

### If SignedEnvelope issues occur:

1. **Disable signature verification:**
   ```bash
   # Set KOI_ENVELOPE_VERIFY=false in .env
   # Restart coordinator
   ```

---

## Not Implemented (Deferred to P3)

1. **KOI-net secure parity:** NodeProfile trust chain (only needed for arbitrary node acceptance)
2. **Historical backfill:** Seeding cache from Postgres koi_* tables
3. **Proxy-node patterns:** Formalized boundary exposure
4. **Provenance/CATs:** Content-addressed transform records

---

## Server Access

```bash
ssh darren@202.61.196.119

# Check cache metrics
cd /opt/projects/koi-sensors
./venv/bin/python scripts/prune_bundle_cache.py --metrics-only

# Check timer status
systemctl status koi-cache-prune.timer

# View coordinator logs
journalctl -u koi-coordinator -f
```

---

*Generated: 2025-12-23*
