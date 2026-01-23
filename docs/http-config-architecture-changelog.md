# HTTP Config Architecture: Changelog

**Original:** Gregory Landua, 2026-01-22
**v1 Revision:** Darren Zal, 2026-01-23
**v2 Revision:** Darren Zal, 2026-01-23 (address review feedback)

---

## v2 Changes (This Version)

Fixes identified during code review:

### 1. Fixed Storage Layout Inconsistency

**Problem:** v1 showed `/app/claude-config/{public,partners,core}/...` in diagrams but code assumed flat structure.

**Fix:** All paths now consistently use tier subdirectories:
- `public/CLAUDE.md`, `public/.mcp.json`
- `partners/contexts/*.md`, `partners/skills/*`
- `core/contexts/*.md`, `core/skills/*`, `core/agents/*`, `core/playbooks/*`

Both `FILE_ALLOWLIST` and `REPO_PATHS` in webhook sync now match.

### 2. Added playbooks/* to Implementation

**Problem:** v1 listed `playbooks/*` in tier mapping but never served them.

**Fix:** Added playbooks to:
- `FILE_ALLOWLIST` dict
- `API_PATH_TO_FILE` mapping
- Bundle builder (new `playbooks` key in response)
- `list_available()` endpoint

### 3. Fixed FastAPI Routing Bug

**Problem:** `@config_router.get("/{file_path:path}")` would swallow `/personal` and `/sync`.

**Fix:**
- Moved catch-all route to `/files/{file_path:path}` prefix
- Registered specific routes (`/`, `/bundle`, `/personal`, `/sync`) first
- Added comment: "CATCH-ALL ROUTE - MUST BE REGISTERED LAST"

### 4. Changed Unknown Paths to 404

**Problem:** v1 defaulted `FILE_TIERS.get(file_path, "core")` - unknown files got "try core" behavior.

**Fix:**
- Renamed to `FILE_ALLOWLIST` to emphasize allowlist-only
- Unknown paths now return `404 {"error": "not_found", "detail": "File not in allowlist"}`
- Explicit check: `if file_path not in API_PATH_TO_FILE: raise HTTPException(404)`

### 5. Clarified Partner Tier Feasibility

**Problem:** v1 assumed partners could authenticate, but current auth hard-rejects non-@regen.network.

**Fix:**
- Phase 1 explicitly scoped to "Public + Core only"
- Phase 2 documented as requiring auth changes
- Added note: "PREREQUISITE: Modify auth_service.py to allow partner domains"
- Tier diagram updated to show phase boundaries

### 6. Added Proper HTTP Caching

**Problem:** v1 only had `X-Config-Version` header, missing standard caching primitives.

**Fix:** Added:
- `ETag` header on all responses (MD5 of content)
- `If-None-Match` support → 304 Not Modified
- `Last-Modified` header on file responses
- `Cache-Control: private` for user-specific data (bundle, personal)
- `Cache-Control: public` for public tier files only
- `Vary: Authorization` on all responses

### 7. Fixed Personal Layer skill_overrides

**Problem:** v1 stored `skill_overrides` but never merged them into bundle.

**Fix:**
- Added `merge_skill_overrides()` function
- Bundle now includes `"overrides": {...}` in each skill when user has overrides
- Bundle includes explicit `"personal"` object with raw overrides
- Clients can see both merged result and raw overrides

### 8. Switched to Repo-Relative Paths

**Problem:** v1 used absolute paths like `/Users/darrenzal/projects/regenai/...`

**Fix:** All paths now repo-relative:
- `api/claude_config_routes.py`
- `api/pipeline_metadata_api.py`
- `migrations/020_claude_config.sql`
- `migrations/021_partner_auth.sql`

---

## v1 Changes (From Original)

Summary of changes from Gregory's original proposal:

| Area | Original | v1 | Rationale |
|------|----------|---------|-----------|
| **API Path** | `/api/claude-config/` | `/api/koi/claude-config/` | Consistency with existing `/api/koi/*` namespace |
| **Service** | New standalone endpoint | Integrated into Pipeline Metadata API | Reuse existing CORS, auth, connection pool |
| **Auth** | New token generation endpoint | Reuse existing session tokens | RFC 8628 device flow already exists |
| **Tier Logic** | Email domain only | Email domain + org membership table | More flexible partner management |
| **Delivery** | HTTP only | HTTP + MCP tool | Better local Claude Code experience |
| **Personal Config** | Mentioned but not detailed | Full specification with endpoints | Enables user customization |

---

## Files in This Spec

All paths relative to repo root:

| File | Purpose |
|------|---------|
| `docs/http-config-architecture-v2.md` | This specification |
| `docs/http-config-architecture-changelog.md` | This changelog |

## Files to Create (Implementation)

| File | Purpose |
|------|---------|
| `api/claude_config_routes.py` | FastAPI routes for config endpoint |
| `migrations/020_claude_config.sql` | Phase 1 schema (user_config, audit log) |
| `migrations/021_partner_auth.sql` | Phase 2 schema (user_orgs, partner_orgs) |

## Existing Files to Modify

| File | Change |
|------|--------|
| `api/pipeline_metadata_api.py` | Import and mount `config_router` |
| `src/services/auth_service.py` | Phase 2: Allow partner domains at OAuth |

---

## Review Checklist

Before treating as "the spec":

- [x] Storage layout consistent (tier subdirs everywhere)
- [x] All mapped files served (including playbooks)
- [x] Route ordering correct (catch-all last)
- [x] Unknown paths → 404 (allowlist only)
- [x] Phase 1 scope clear (public + core, no partners)
- [x] HTTP caching complete (ETag, Vary, Cache-Control private/public)
- [x] skill_overrides actually merged
- [x] Paths repo-relative

---

## Open Questions

1. **Partner org management:** Who adds/removes partner orgs? Admin endpoint or manual DB?

2. **Token refresh UX:** Current 1-hour expiry acceptable, or extend for config access?

3. **Skill portability:** Flag skills as "cloud-compatible" vs "local-only"?

4. **Config versioning:** Git-like history needed, or is audit log sufficient?

5. **MCP tool priority:** Should Phase 1 include MCP tool, or defer to Phase 2?
