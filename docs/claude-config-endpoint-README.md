# Claude Config HTTP Endpoint

Implementation of the [HTTP Config Architecture v2](https://github.com/DarrenZal/koi-research/blob/regen-prod/docs/http-config-architecture-v2.md) for serving tiered Claude configuration.

## Overview

This endpoint serves Claude Code configuration (CLAUDE.md, contexts, skills, agents) based on user access tier:

| Tier | Who | What They Get |
|------|-----|---------------|
| **public** | Anyone | Basic CLAUDE.md, MCP config |
| **partner** | Ecosystem partners | + Partner contexts & skills (Phase 2) |
| **core** | @regen.network team | + Full contexts, skills, agents, playbooks |
| **personal** | Authenticated users | + User-specific customizations |

## Files

```
koi-research/
├── api/
│   └── claude_config_routes.py    # FastAPI router implementation
├── migrations/
│   └── 020_claude_config.sql      # Database schema
└── docs/
    ├── http-config-architecture-v2.md  # Architecture spec
    └── claude-config-endpoint-README.md  # This file
```

## Integration

### 1. Database Setup

Run the migration against your PostgreSQL database:

```bash
psql $DATABASE_URL -f migrations/020_claude_config.sql
```

### 2. Server Integration

Add the router to your FastAPI application:

```python
from fastapi import FastAPI
from api.claude_config_routes import config_router

app = FastAPI()

# Add the config router
app.include_router(config_router)
```

### 3. Database Dependency

Replace the `get_db` function in `claude_config_routes.py` with your actual database connection:

```python
from your_db_module import db_pool

async def get_db():
    async with db_pool.acquire() as conn:
        yield conn
```

### 4. Environment Variables

```bash
# Required
CLAUDE_CONFIG_DIR=/app/claude-config     # Path to config files

# Optional
GITHUB_WEBHOOK_SECRET=your_secret        # For /sync endpoint
```

### 5. Config Directory Setup

Clone the config repos to the config directory:

```bash
mkdir -p /app/claude-config
cd /app/claude-config

# Public tier (from public repo)
git clone https://github.com/regen-network/regen-ai-claude.git public

# Core tier (from private repo)
git clone https://github.com/regen-network/regen-ai-core.git core

# Partner tier (Phase 2)
# git clone https://github.com/regen-network/regen-ai-partners.git partners
```

Structure should be:
```
/app/claude-config/
├── public/           # regen-ai-claude repo
│   ├── CLAUDE.md
│   └── .mcp.json
├── core/             # regen-ai-core repo
│   ├── CLAUDE.md
│   ├── contexts/
│   ├── skills/
│   └── agents/
└── partners/         # Phase 2
```

## API Endpoints

### List Available Resources
```
GET /api/koi/claude-config/
Authorization: Bearer {token}  # Optional

Response: { tier, user_email, available: { contexts, skills, agents, playbooks } }
```

### Get Full Bundle
```
GET /api/koi/claude-config/bundle
Authorization: Bearer {token}  # Optional

Response: { tier, user_email, mcp, claude_md, contexts, skills, agents, playbooks, personal }
```

### Get Individual File
```
GET /api/koi/claude-config/files/CLAUDE.md
GET /api/koi/claude-config/files/contexts/ECOCREDIT.md
Authorization: Bearer {token}  # Optional

Response: File contents (text/markdown or application/json)
```

### Personal Config
```
GET /api/koi/claude-config/personal
PUT /api/koi/claude-config/personal
Authorization: Bearer {token}  # Required

Body (PUT): { claude_md_additions, skill_overrides }
```

### Health Check
```
GET /api/koi/claude-config/health

Response: { status, config_dir_exists, tiers: { public, partner, core }, last_sync }
```

### GitHub Webhook Sync
```
POST /api/koi/claude-config/sync
X-Hub-Signature-256: sha256=...

Triggered on push to config repos, runs git pull.
```

## Security

1. **Allowlist-only**: Only files in `FILE_ALLOWLIST` are served
2. **Path traversal blocked**: `..` in paths returns 400
3. **Token validation**: Uses existing KOI session_tokens table
4. **Audit logging**: All access logged to config_access_log
5. **Webhook validation**: GitHub signatures verified via HMAC-SHA256

## Caching

- `ETag` headers on all responses
- `304 Not Modified` support via `If-None-Match`
- `Cache-Control: private` for authenticated responses
- `Cache-Control: public` for public tier files
- `Vary: Authorization` on all responses

## Testing

```bash
# Health check
curl https://regen.gaiaai.xyz/api/koi/claude-config/health

# List available (unauthenticated = public tier)
curl https://regen.gaiaai.xyz/api/koi/claude-config/

# Get bundle with auth
curl -H "Authorization: Bearer $REGEN_TOKEN" \
  https://regen.gaiaai.xyz/api/koi/claude-config/bundle

# Get merged CLAUDE.md
curl -H "Authorization: Bearer $REGEN_TOKEN" \
  https://regen.gaiaai.xyz/api/koi/claude-config/files/CLAUDE.md
```

## Related Repositories

- [regen-network/regen-ai-claude](https://github.com/regen-network/regen-ai-claude) - Public config (public/)
- [regen-network/regen-ai-core](https://github.com/regen-network/regen-ai-core) - Core team config (core/)
- [DarrenZal/koi-research](https://github.com/DarrenZal/koi-research) - Architecture docs
