# Regen Knowledge Commons: HTTP Config Architecture

**Date:** 2026-01-22
**Status:** Implementation Specification
**Revised:** 2026-01-23 (v2 - address review feedback)
**Solves:** Cross-platform authentication for Claude Code (local, cloud, co-work)

---

## Problem Statement

```
Local Claude Code ──────► GitHub (authenticated via SSH/credential helper)
                              │
                              ▼
                         Private Repos ✅

Cloud Claude Code ──────► GitHub (no persistent auth)
                              │
                              ▼
                         Private Repos ❌ (requires PAT each session)
```

**Current pain points:**

- Cloud/browser Claude Code can't access private GitHub repos
- Pasting PAT every session is bad UX
- Doesn't scale for team onboarding
- GitHub-based tiered access model breaks in cloud

---

## Solution: HTTP Config Endpoint

Serve configuration from existing Regen infrastructure with token-based auth:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│   ANY Claude Code Session                                                   │
│   (local, cloud, co-work, desktop)                                         │
│                                                                             │
│        │                                                                    │
│        │ WebFetch / HTTP Request                                           │
│        │ Authorization: Bearer $REGEN_TOKEN                                │
│        ▼                                                                    │
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────┐      │
│   │                                                                 │      │
│   │   https://regen.gaiaai.xyz/api/koi/claude-config/               │      │
│   │                                                                 │      │
│   │   ├── bundle                 (full config for tier)            │      │
│   │   ├── CLAUDE.md              (context - tier-appropriate)      │      │
│   │   ├── contexts/{name}.md     (domain contexts)                 │      │
│   │   ├── skills/{name}/         (skill definitions)               │      │
│   │   ├── agents/{name}.json     (agent templates)                 │      │
│   │   └── personal               (user-specific overrides)         │      │
│   │                                                                 │      │
│   │   Returns: Content appropriate to token's access tier          │      │
│   │                                                                 │      │
│   └─────────────────────────────────────────────────────────────────┘      │
│                                                                             │
│        ▲                                                                    │
│        │ Also available as MCP tool (local Claude Code)                    │
│        │ mcp__plugin_koi_regen-koi__get_claude_config                      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Architecture Overview

### Unified Auth Flow

```
┌──────────────────────────────────────────────────────────────────────────┐
│                           REGEN AUTH SYSTEM                              │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   User authenticates ONCE via:                                           │
│   • regen_koi_authenticate (RFC 8628 Device Flow - existing)            │
│   • Returns session token (already implemented)                          │
│                                                                          │
│                            ▼                                             │
│                                                                          │
│   ┌────────────────────────────────────────────────────────────────┐    │
│   │                    SESSION TOKEN (existing)                     │    │
│   │                                                                 │    │
│   │   Validated against session_tokens table                        │    │
│   │   Returns user_email from get_authorized_user()                │    │
│   │                                                                 │    │
│   │   Extended to include:                                          │    │
│   │   • access_tier (public | core)         [Phase 1]              │    │
│   │   • access_tier (public | partner | core) [Phase 2]            │    │
│   │   • org_memberships (from user_orgs table)                     │    │
│   │                                                                 │    │
│   └────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│                            ▼                                             │
│                                                                          │
│   Token works for:                                                       │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                 │
│   │ KOI Search   │  │ Claude       │  │ Future HTTP  │                 │
│   │ (existing)   │  │ Config       │  │ MCP Gateway  │                 │
│   │ port 8007    │  │ (new)        │  │ (Phase 3)    │                 │
│   └──────────────┘  └──────────────┘  └──────────────┘                 │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

### Tiered Config Delivery

```
Token Tier          →    Config Delivered
─────────────────────────────────────────────────────
No token / invalid  →    Tier 1 (Public)
                         • Basic CLAUDE.md
                         • Public MCP configs

core tier           →    Tier 1 + Tier 3 (Core)       [Phase 1]
(@regen.network)         • Full CLAUDE.md
                         • All contexts
                         • All skills
                         • All agent templates
                         • All playbooks

partner tier        →    Tier 1 + Tier 2 (Partners)   [Phase 2]
(requires auth change)   • Extended CLAUDE.md
                         • Partner contexts
                         • Partner skills

+ personal layer    →    User-specific overrides
                         • Personal CLAUDE.md additions
                         • Custom skill configs
```

> **Phase 1 Scope:** Public + Core tiers only. Current KOI auth enforces `@regen.network` domain at OAuth callback. Partner tier requires expanding the OAuth allowlist, which is Phase 2 work.

---

## API Specification

### Base URL

```
https://regen.gaiaai.xyz/api/koi/claude-config/
```

> **Note:** Integrated into existing Pipeline Metadata API (port 8002) rather than separate service. This reuses existing CORS, auth, and connection pool infrastructure.

### Endpoints

### 1. Get Full Config Bundle

```
GET /api/koi/claude-config/bundle
Authorization: Bearer {SESSION_TOKEN}  # Optional

Response 200:
{
  "tier": "core",
  "user_email": "user@regen.network",
  "mcp": { ... },           // .mcp.json contents
  "claude_md": "...",       // CLAUDE.md contents (merged for tier + personal)
  "contexts": {
    "ECOCREDIT": "...",
    "REGEN_LEDGER": "...",
    ...
  },
  "skills": {
    "weekly-digest": {
      "content": "...",
      "overrides": { ... }  // User-specific overrides merged in
    },
    ...
  },
  "agents": {
    "researcher": { ... },
    ...
  },
  "playbooks": {
    "incident-response": "...",
    ...
  },
  "personal": {                      // Explicit personal layer
    "claude_md_additions": "...",
    "skill_overrides": { ... }
  }
}

Headers:
  ETag: "abc123..."
  Cache-Control: private, max-age=3600
  Vary: Authorization
```

### 2. Get Individual Files

```
GET /api/koi/claude-config/files/CLAUDE.md
GET /api/koi/claude-config/files/contexts/ECOCREDIT.md
GET /api/koi/claude-config/files/skills/weekly-digest/SKILL.md
GET /api/koi/claude-config/files/agents/researcher.json
GET /api/koi/claude-config/files/playbooks/incident-response.md
Authorization: Bearer {SESSION_TOKEN}  # Optional

Response 200:
{file contents - text/plain or application/json}

Headers:
  ETag: "def456..."
  Last-Modified: Fri, 23 Jan 2026 10:00:00 GMT
  Cache-Control: public, max-age=3600   # (or private if tier-specific)
  Vary: Authorization
  X-Config-Tier: core

Response 304 (Not Modified):
  # When If-None-Match or If-Modified-Since matches

Response 403:
{
  "error": "insufficient_access",
  "required_tier": "core",
  "your_tier": "public",
  "upgrade_info": "Contact team@regen.network for core access"
}

Response 404:
{
  "error": "not_found",
  "detail": "File not in allowlist"
}
```

### 3. List Available Resources

```
GET /api/koi/claude-config/
Authorization: Bearer {SESSION_TOKEN}  # Optional

Response 200:
{
  "tier": "core",
  "user_email": "user@regen.network",
  "orgs": [],
  "available": {
    "mcp": true,
    "claude_md": true,
    "contexts": ["ECOCREDIT", "REGEN_LEDGER", "KOI_KNOWLEDGE", "GOVERNANCE", "INFRASTRUCTURE"],
    "skills": ["weekly-digest", "credit-analysis", "code-review", "ledger-query", "incident-response"],
    "agents": ["researcher", "developer", "analyst", "operator"],
    "playbooks": ["incident-response", "release-checklist"]
  }
}

Headers:
  ETag: "..."
  Cache-Control: private, max-age=300
  Vary: Authorization
```

### 4. Personal Config Layer

```
GET /api/koi/claude-config/personal
Authorization: Bearer {SESSION_TOKEN}  # Required

Response 200:
{
  "claude_md_additions": "# My custom instructions\n...",
  "skill_overrides": {
    "weekly-digest": { "custom_param": "value" }
  },
  "updated_at": "2026-01-20T15:00:00Z"
}

Headers:
  ETag: "..."
  Cache-Control: private, no-cache
  Vary: Authorization

PUT /api/koi/claude-config/personal
Authorization: Bearer {SESSION_TOKEN}  # Required
Content-Type: application/json

{
  "claude_md_additions": "# My custom instructions\n...",
  "skill_overrides": { ... }
}

Response 200:
{
  "status": "saved",
  "updated_at": "2026-01-23T12:00:00Z"
}
```

### 5. Webhook Sync (GitHub → Config Server)

```
POST /api/koi/claude-config/sync
X-Hub-Signature-256: sha256=...
Content-Type: application/json

{GitHub webhook payload}

Response 200:
{
  "status": "synced",
  "repo": "regen-ai-claude",
  "commit": "abc123",
  "files_updated": 3
}
```

---

## Tier Determination Logic

### Phase 1: Public + Core Only

```python
# Simplified tier logic for Phase 1
# Current auth already enforces @regen.network at OAuth callback

def determine_tier(email: Optional[str]) -> str:
    """
    Phase 1: Only public and core tiers.

    - Authenticated @regen.network users → core
    - Everyone else → public
    """
    if email and email.endswith("@regen.network"):
        return "core"
    return "public"
```

### Phase 2: Add Partner Tier (Requires Auth Changes)

```python
# Extended tier logic for Phase 2
# PREREQUISITE: Modify auth_service.py to allow partner domains at OAuth

CORE_DOMAINS = ["@regen.network"]
CORE_ORGS = ["rnd-pbc", "regen-foundation"]

PARTNER_DOMAINS = ["@toucan.earth", "@flowcarbon.com", "@klimadao.earth"]
PARTNER_ORGS = ["toucan-protocol", "flowcarbon", "klimadao", "moss-earth"]

def determine_tier(email: Optional[str], orgs: list[str]) -> str:
    """
    Phase 2: Public, partner, and core tiers.

    Priority: core > partner > public
    """
    if not email:
        return "public"

    # Core tier: Regen team members
    if any(email.endswith(d) for d in CORE_DOMAINS):
        return "core"
    if any(org in CORE_ORGS for org in orgs):
        return "core"

    # Partner tier: Ecosystem partners
    if any(email.endswith(d) for d in PARTNER_DOMAINS):
        return "partner"
    if any(org in PARTNER_ORGS for org in orgs):
        return "partner"

    # Default: public tier
    return "public"
```

### Org Membership Storage (Phase 2)

```sql
-- New table for org memberships (synced from GitHub or manual)
CREATE TABLE user_orgs (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) NOT NULL,
    org_slug VARCHAR(100) NOT NULL,
    source VARCHAR(50) DEFAULT 'manual',  -- 'github', 'manual', 'oauth'
    verified_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_email, org_slug)
);

CREATE INDEX idx_user_orgs_email ON user_orgs(user_email);

-- Partner orgs reference table
CREATE TABLE partner_orgs (
    org_slug VARCHAR(100) PRIMARY KEY,
    org_name VARCHAR(255),
    tier VARCHAR(50) DEFAULT 'partner',
    contact_email VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## File-to-Tier Mapping (Allowlist)

```yaml
# Config served based on access tier
# IMPORTANT: Only files in this allowlist are served. Unknown paths → 404.

tier_1_public:
  - public/.mcp.json
  - public/CLAUDE.md
  - public/setup/install.sh

tier_2_partners:                    # Phase 2
  inherits: tier_1_public
  adds:
    - partners/CLAUDE.md            # Merged with public
    - partners/contexts/REGISTRY_PROJECTS.md
    - partners/contexts/METHODOLOGY_DEV.md
    - partners/contexts/CREDIT_ISSUANCE.md
    - partners/skills/project-registration/SKILL.md
    - partners/skills/methodology-review/SKILL.md

tier_3_core:
  inherits: tier_2_partners
  adds:
    - core/CLAUDE.md                # Merged with public (+ partners in Phase 2)
    - core/contexts/ECOCREDIT.md
    - core/contexts/REGEN_LEDGER.md
    - core/contexts/KOI_KNOWLEDGE.md
    - core/contexts/GOVERNANCE.md
    - core/contexts/INFRASTRUCTURE.md
    - core/skills/weekly-digest/SKILL.md
    - core/skills/credit-analysis/SKILL.md
    - core/skills/code-review/SKILL.md
    - core/skills/ledger-query/SKILL.md
    - core/skills/incident-response/SKILL.md
    - core/agents/researcher.json
    - core/agents/developer.json
    - core/agents/analyst.json
    - core/agents/operator.json
    - core/playbooks/incident-response.md
    - core/playbooks/release-checklist.md

personal_layer:
  # Per-user additions (stored in database, not filesystem)
  - claude_md_additions          # Appended to tier CLAUDE.md
  - skill_overrides              # Merged into skill configs
```

---

## Config Storage Structure

```
/app/claude-config/
├── public/                      # Synced from regen-ai-claude repo (PUBLIC)
│   ├── CLAUDE.md
│   ├── .mcp.json
│   └── setup/
│       └── install.sh
├── partners/                    # Synced from regen-ai-partners repo (PRIVATE) [Phase 2]
│   ├── CLAUDE.md
│   ├── contexts/
│   │   ├── REGISTRY_PROJECTS.md
│   │   ├── METHODOLOGY_DEV.md
│   │   └── CREDIT_ISSUANCE.md
│   └── skills/
│       ├── project-registration/
│       │   └── SKILL.md
│       └── methodology-review/
│           └── SKILL.md
└── core/                        # Synced from regen-ai-core repo (PRIVATE)
    ├── CLAUDE.md
    ├── contexts/
    │   ├── ECOCREDIT.md
    │   ├── REGEN_LEDGER.md
    │   ├── KOI_KNOWLEDGE.md
    │   ├── GOVERNANCE.md
    │   └── INFRASTRUCTURE.md
    ├── skills/
    │   ├── weekly-digest/
    │   │   └── SKILL.md
    │   ├── credit-analysis/
    │   │   └── SKILL.md
    │   ├── code-review/
    │   │   └── SKILL.md
    │   ├── ledger-query/
    │   │   └── SKILL.md
    │   └── incident-response/
    │       └── SKILL.md
    ├── agents/
    │   ├── researcher.json
    │   ├── developer.json
    │   ├── analyst.json
    │   └── operator.json
    └── playbooks/
        ├── incident-response.md
        └── release-checklist.md
```

---

## Implementation

### Phase 1: Config Endpoint (Week 1)

**Add routes to existing `api/pipeline_metadata_api.py`:**

```python
# api/claude_config_routes.py
# Import this router in pipeline_metadata_api.py

from fastapi import APIRouter, Header, HTTPException, Depends, Response, Request
from typing import Optional
import os
import json
import hashlib
from datetime import datetime

config_router = APIRouter(prefix="/api/koi/claude-config", tags=["claude-config"])

# Config storage - uses tier subdirectories
CONFIG_DIR = os.getenv("CLAUDE_CONFIG_DIR", "/app/claude-config")

TIER_ACCESS = {
    "public": 1,
    "partner": 2,  # Phase 2
    "core": 3
}

# ALLOWLIST ONLY - unknown paths return 404
FILE_ALLOWLIST = {
    # Public tier
    "public/.mcp.json": "public",
    "public/CLAUDE.md": "public",
    "public/setup/install.sh": "public",

    # Partner tier (Phase 2)
    "partners/CLAUDE.md": "partner",
    "partners/contexts/REGISTRY_PROJECTS.md": "partner",
    "partners/contexts/METHODOLOGY_DEV.md": "partner",
    "partners/contexts/CREDIT_ISSUANCE.md": "partner",
    "partners/skills/project-registration/SKILL.md": "partner",
    "partners/skills/methodology-review/SKILL.md": "partner",

    # Core tier
    "core/CLAUDE.md": "core",
    "core/contexts/ECOCREDIT.md": "core",
    "core/contexts/REGEN_LEDGER.md": "core",
    "core/contexts/KOI_KNOWLEDGE.md": "core",
    "core/contexts/GOVERNANCE.md": "core",
    "core/contexts/INFRASTRUCTURE.md": "core",
    "core/skills/weekly-digest/SKILL.md": "core",
    "core/skills/credit-analysis/SKILL.md": "core",
    "core/skills/code-review/SKILL.md": "core",
    "core/skills/ledger-query/SKILL.md": "core",
    "core/skills/incident-response/SKILL.md": "core",
    "core/agents/researcher.json": "core",
    "core/agents/developer.json": "core",
    "core/agents/analyst.json": "core",
    "core/agents/operator.json": "core",
    "core/playbooks/incident-response.md": "core",
    "core/playbooks/release-checklist.md": "core",
}

# Reverse mapping for API paths (without tier prefix)
API_PATH_TO_FILE = {
    ".mcp.json": "public/.mcp.json",
    "CLAUDE.md": None,  # Special case: merged from tiers
    "contexts/ECOCREDIT.md": "core/contexts/ECOCREDIT.md",
    "contexts/REGEN_LEDGER.md": "core/contexts/REGEN_LEDGER.md",
    "contexts/KOI_KNOWLEDGE.md": "core/contexts/KOI_KNOWLEDGE.md",
    "contexts/GOVERNANCE.md": "core/contexts/GOVERNANCE.md",
    "contexts/INFRASTRUCTURE.md": "core/contexts/INFRASTRUCTURE.md",
    "contexts/REGISTRY_PROJECTS.md": "partners/contexts/REGISTRY_PROJECTS.md",
    "contexts/METHODOLOGY_DEV.md": "partners/contexts/METHODOLOGY_DEV.md",
    "contexts/CREDIT_ISSUANCE.md": "partners/contexts/CREDIT_ISSUANCE.md",
    "skills/weekly-digest/SKILL.md": "core/skills/weekly-digest/SKILL.md",
    "skills/credit-analysis/SKILL.md": "core/skills/credit-analysis/SKILL.md",
    "skills/code-review/SKILL.md": "core/skills/code-review/SKILL.md",
    "skills/ledger-query/SKILL.md": "core/skills/ledger-query/SKILL.md",
    "skills/incident-response/SKILL.md": "core/skills/incident-response/SKILL.md",
    "skills/project-registration/SKILL.md": "partners/skills/project-registration/SKILL.md",
    "skills/methodology-review/SKILL.md": "partners/skills/methodology-review/SKILL.md",
    "agents/researcher.json": "core/agents/researcher.json",
    "agents/developer.json": "core/agents/developer.json",
    "agents/analyst.json": "core/agents/analyst.json",
    "agents/operator.json": "core/agents/operator.json",
    "playbooks/incident-response.md": "core/playbooks/incident-response.md",
    "playbooks/release-checklist.md": "core/playbooks/release-checklist.md",
}


def can_access(user_tier: str, required_tier: str) -> bool:
    return TIER_ACCESS.get(user_tier, 0) >= TIER_ACCESS.get(required_tier, 999)


async def get_user_tier(
    authorization: Optional[str] = Header(None),
    db = Depends(get_db)
) -> tuple[str, Optional[str], list[str]]:
    """
    Extended auth that returns (tier, email, orgs).
    Returns ("public", None, []) for unauthenticated requests.
    """
    if not authorization or not authorization.startswith("Bearer "):
        return ("public", None, [])

    token = authorization[7:]
    token_hash = hashlib.sha256(token.encode()).hexdigest()

    row = await db.fetchrow("""
        SELECT user_email FROM session_tokens
        WHERE token_hash = $1 AND expires_at > NOW()
    """, token_hash)

    if not row:
        return ("public", None, [])

    email = row["user_email"]

    # Phase 1: Simple tier determination
    tier = "core" if email.endswith("@regen.network") else "public"

    # Phase 2: Add org lookup
    # org_rows = await db.fetch("SELECT org_slug FROM user_orgs WHERE user_email = $1", email)
    # orgs = [r["org_slug"] for r in org_rows]
    # tier = determine_tier(email, orgs)
    orgs = []

    return (tier, email, orgs)


def compute_etag(content: str) -> str:
    """Compute ETag from content hash."""
    return f'"{hashlib.md5(content.encode()).hexdigest()}"'


def load_file(relative_path: str) -> Optional[str]:
    """Load file from config directory. Path must be in allowlist."""
    if relative_path not in FILE_ALLOWLIST:
        return None
    full_path = os.path.join(CONFIG_DIR, relative_path)
    if not os.path.exists(full_path):
        return None
    with open(full_path, 'r') as f:
        return f.read()


def get_file_mtime(relative_path: str) -> Optional[datetime]:
    """Get file modification time."""
    full_path = os.path.join(CONFIG_DIR, relative_path)
    if not os.path.exists(full_path):
        return None
    return datetime.fromtimestamp(os.path.getmtime(full_path))


def load_merged_claude_md(tier: str) -> str:
    """Build CLAUDE.md by merging tiers up to user's level."""
    parts = []

    # Tier 1: Public base (always included)
    public = load_file("public/CLAUDE.md")
    if public:
        parts.append(public)

    # Phase 2: Partner additions
    # if TIER_ACCESS[tier] >= 2:
    #     partner = load_file("partners/CLAUDE.md")
    #     if partner:
    #         parts.append("\n\n<!-- Partner Extensions -->\n\n")
    #         parts.append(partner)

    if TIER_ACCESS[tier] >= 3:
        core = load_file("core/CLAUDE.md")
        if core:
            parts.append("\n\n<!-- Core Extensions -->\n\n")
            parts.append(core)

    return "".join(parts)


async def load_personal_config(email: str, db) -> dict:
    """Load user's personal config from database."""
    if not email:
        return {"claude_md_additions": "", "skill_overrides": {}}

    row = await db.fetchrow("""
        SELECT claude_md_additions, skill_overrides, updated_at
        FROM user_config WHERE user_email = $1
    """, email)

    if not row:
        return {"claude_md_additions": "", "skill_overrides": {}}

    return {
        "claude_md_additions": row["claude_md_additions"] or "",
        "skill_overrides": json.loads(row["skill_overrides"] or "{}"),
        "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None
    }


def merge_skill_overrides(skills: dict, overrides: dict) -> dict:
    """Merge user's skill overrides into skill configs."""
    merged = {}
    for skill_name, skill_data in skills.items():
        merged[skill_name] = dict(skill_data)  # Copy
        if skill_name in overrides:
            merged[skill_name]["overrides"] = overrides[skill_name]
    return merged


# ============================================================
# ROUTE ORDER MATTERS: Specific routes before catch-all
# ============================================================

@config_router.get("/")
async def list_available(
    auth: tuple = Depends(get_user_tier)
):
    """List available config files for user's tier."""
    tier, email, orgs = auth

    available = {
        "tier": tier,
        "user_email": email,
        "orgs": orgs,
        "available": {
            "mcp": True,
            "claude_md": True,
            "contexts": [],
            "skills": [],
            "agents": [],
            "playbooks": []
        }
    }

    for file_path, required_tier in FILE_ALLOWLIST.items():
        if can_access(tier, required_tier):
            if "/contexts/" in file_path:
                name = file_path.split("/contexts/")[1].replace(".md", "")
                if name not in available["available"]["contexts"]:
                    available["available"]["contexts"].append(name)
            elif "/skills/" in file_path:
                name = file_path.split("/skills/")[1].split("/")[0]
                if name not in available["available"]["skills"]:
                    available["available"]["skills"].append(name)
            elif "/agents/" in file_path:
                name = file_path.split("/agents/")[1].replace(".json", "")
                if name not in available["available"]["agents"]:
                    available["available"]["agents"].append(name)
            elif "/playbooks/" in file_path:
                name = file_path.split("/playbooks/")[1].replace(".md", "")
                if name not in available["available"]["playbooks"]:
                    available["available"]["playbooks"].append(name)

    content = json.dumps(available)
    return Response(
        content=content,
        media_type="application/json",
        headers={
            "ETag": compute_etag(content),
            "Cache-Control": "private, max-age=300",
            "Vary": "Authorization"
        }
    )


@config_router.get("/bundle")
async def get_bundle(
    auth: tuple = Depends(get_user_tier),
    db = Depends(get_db),
    if_none_match: Optional[str] = Header(None)
):
    """Get full config bundle for user's tier."""
    tier, email, orgs = auth

    # Load personal config
    personal = await load_personal_config(email, db) if email else {
        "claude_md_additions": "",
        "skill_overrides": {}
    }

    # Build claude_md with personal additions
    claude_md = load_merged_claude_md(tier)
    if personal["claude_md_additions"]:
        claude_md += f"\n\n<!-- Personal Extensions -->\n\n"
        claude_md += personal["claude_md_additions"]

    # Build skills dict
    skills = {}
    for file_path, required_tier in FILE_ALLOWLIST.items():
        if "/skills/" in file_path and can_access(tier, required_tier):
            content = load_file(file_path)
            if content:
                name = file_path.split("/skills/")[1].split("/")[0]
                skills[name] = {"content": content}

    # Merge skill overrides
    skills = merge_skill_overrides(skills, personal["skill_overrides"])

    # Build contexts dict
    contexts = {}
    for file_path, required_tier in FILE_ALLOWLIST.items():
        if "/contexts/" in file_path and can_access(tier, required_tier):
            content = load_file(file_path)
            if content:
                name = file_path.split("/contexts/")[1].replace(".md", "")
                contexts[name] = content

    # Build agents dict
    agents = {}
    for file_path, required_tier in FILE_ALLOWLIST.items():
        if "/agents/" in file_path and can_access(tier, required_tier):
            content = load_file(file_path)
            if content:
                name = file_path.split("/agents/")[1].replace(".json", "")
                agents[name] = json.loads(content)

    # Build playbooks dict
    playbooks = {}
    for file_path, required_tier in FILE_ALLOWLIST.items():
        if "/playbooks/" in file_path and can_access(tier, required_tier):
            content = load_file(file_path)
            if content:
                name = file_path.split("/playbooks/")[1].replace(".md", "")
                playbooks[name] = content

    bundle = {
        "tier": tier,
        "user_email": email,
        "mcp": json.loads(load_file("public/.mcp.json") or "{}"),
        "claude_md": claude_md,
        "contexts": contexts,
        "skills": skills,
        "agents": agents,
        "playbooks": playbooks,
        "personal": personal
    }

    content = json.dumps(bundle)
    etag = compute_etag(content)

    # Check If-None-Match for 304
    if if_none_match and if_none_match == etag:
        return Response(status_code=304)

    return Response(
        content=content,
        media_type="application/json",
        headers={
            "ETag": etag,
            "Cache-Control": "private, max-age=3600",
            "Vary": "Authorization"
        }
    )


@config_router.get("/personal")
async def get_personal_config(
    auth: tuple = Depends(get_user_tier),
    db = Depends(get_db)
):
    """Get user's personal config additions."""
    tier, email, orgs = auth

    if not email:
        raise HTTPException(status_code=401, detail="Authentication required")

    personal = await load_personal_config(email, db)
    content = json.dumps(personal)

    return Response(
        content=content,
        media_type="application/json",
        headers={
            "ETag": compute_etag(content),
            "Cache-Control": "private, no-cache",
            "Vary": "Authorization"
        }
    )


@config_router.put("/personal")
async def update_personal_config(
    request: Request,
    auth: tuple = Depends(get_user_tier),
    db = Depends(get_db)
):
    """Update user's personal config additions."""
    tier, email, orgs = auth

    if not email:
        raise HTTPException(status_code=401, detail="Authentication required")

    config = await request.json()

    await db.execute("""
        INSERT INTO user_config (user_email, claude_md_additions, skill_overrides, updated_at)
        VALUES ($1, $2, $3, NOW())
        ON CONFLICT (user_email) DO UPDATE SET
            claude_md_additions = $2,
            skill_overrides = $3,
            updated_at = NOW()
    """, email, config.get("claude_md_additions", ""), json.dumps(config.get("skill_overrides", {})))

    # Audit log
    await db.execute("""
        INSERT INTO config_access_log (user_email, tier, resource_path, access_granted)
        VALUES ($1, $2, 'personal', true)
    """, email, tier)

    return {"status": "saved", "updated_at": datetime.now().isoformat()}


@config_router.post("/sync")
async def sync_from_github(
    request: Request,
    x_hub_signature_256: Optional[str] = Header(None)
):
    """GitHub webhook handler - syncs config on push."""
    import hmac
    import subprocess

    GITHUB_WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET")

    if not GITHUB_WEBHOOK_SECRET:
        raise HTTPException(status_code=500, detail="Webhook secret not configured")

    body = await request.body()
    expected_sig = "sha256=" + hmac.new(
        GITHUB_WEBHOOK_SECRET.encode(),
        body,
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected_sig, x_hub_signature_256 or ""):
        raise HTTPException(status_code=401, detail="Invalid signature")

    payload = json.loads(body)
    repo_name = payload.get("repository", {}).get("name")

    # Map repos to subdirectories
    REPO_PATHS = {
        "regen-ai-claude": os.path.join(CONFIG_DIR, "public"),
        "regen-ai-partners": os.path.join(CONFIG_DIR, "partners"),
        "regen-ai-core": os.path.join(CONFIG_DIR, "core")
    }

    if repo_name not in REPO_PATHS:
        return {"status": "ignored", "reason": "unknown repo"}

    repo_path = REPO_PATHS[repo_name]
    result = subprocess.run(
        ["git", "-C", repo_path, "pull", "--ff-only"],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=f"Git pull failed: {result.stderr}")

    commit = payload.get("after", "unknown")[:7]

    return {
        "status": "synced",
        "repo": repo_name,
        "commit": commit,
        "output": result.stdout
    }


# ============================================================
# CATCH-ALL ROUTE - MUST BE REGISTERED LAST
# ============================================================

@config_router.get("/files/{file_path:path}")
async def get_file_endpoint(
    file_path: str,
    auth: tuple = Depends(get_user_tier),
    if_none_match: Optional[str] = Header(None),
    if_modified_since: Optional[str] = Header(None)
):
    """Get individual config file. Only allowlisted files are served."""
    tier, email, orgs = auth

    # Security: prevent directory traversal
    if ".." in file_path:
        raise HTTPException(status_code=400, detail="Invalid path")

    # Special case: CLAUDE.md returns merged version
    if file_path == "CLAUDE.md":
        content = load_merged_claude_md(tier)
        etag = compute_etag(content)

        if if_none_match and if_none_match == etag:
            return Response(status_code=304)

        return Response(
            content=content,
            media_type="text/markdown",
            headers={
                "ETag": etag,
                "Cache-Control": "private, max-age=3600",
                "Vary": "Authorization",
                "X-Config-Tier": tier
            }
        )

    # Map API path to file path
    if file_path not in API_PATH_TO_FILE:
        raise HTTPException(status_code=404, detail="File not in allowlist")

    actual_path = API_PATH_TO_FILE[file_path]
    if actual_path is None:
        raise HTTPException(status_code=404, detail="File not found")

    # Check tier access
    required_tier = FILE_ALLOWLIST.get(actual_path)
    if not required_tier:
        raise HTTPException(status_code=404, detail="File not in allowlist")

    if not can_access(tier, required_tier):
        raise HTTPException(
            status_code=403,
            detail={
                "error": "insufficient_access",
                "required_tier": required_tier,
                "your_tier": tier,
                "upgrade_info": "Contact team@regen.network for access"
            }
        )

    content = load_file(actual_path)
    if not content:
        raise HTTPException(status_code=404, detail="File not found")

    etag = compute_etag(content)
    mtime = get_file_mtime(actual_path)

    # Check conditional headers
    if if_none_match and if_none_match == etag:
        return Response(status_code=304)

    media_type = "application/json" if file_path.endswith(".json") else "text/markdown"

    # Use public cache for public tier files, private for others
    cache_control = "public, max-age=3600" if required_tier == "public" else "private, max-age=3600"

    headers = {
        "ETag": etag,
        "Cache-Control": cache_control,
        "Vary": "Authorization",
        "X-Config-Tier": tier
    }

    if mtime:
        headers["Last-Modified"] = mtime.strftime("%a, %d %b %Y %H:%M:%S GMT")

    return Response(content=content, media_type=media_type, headers=headers)
```

### Phase 1: Database Schema

```sql
-- migrations/020_claude_config.sql

-- User personal config storage
CREATE TABLE IF NOT EXISTS user_config (
    user_email VARCHAR(255) PRIMARY KEY,
    claude_md_additions TEXT,
    skill_overrides JSONB DEFAULT '{}',
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Config access logging (audit trail)
CREATE TABLE IF NOT EXISTS config_access_log (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255),
    tier VARCHAR(50),
    resource_path VARCHAR(255),
    access_granted BOOLEAN,
    accessed_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_config_access_log_email ON config_access_log(user_email);
CREATE INDEX IF NOT EXISTS idx_config_access_log_time ON config_access_log(accessed_at);
```

### Phase 2: Partner Auth + Org Tables

```sql
-- migrations/021_partner_auth.sql

-- User org memberships for tier determination
CREATE TABLE IF NOT EXISTS user_orgs (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) NOT NULL,
    org_slug VARCHAR(100) NOT NULL,
    source VARCHAR(50) DEFAULT 'manual',
    verified_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_email, org_slug)
);

CREATE INDEX IF NOT EXISTS idx_user_orgs_email ON user_orgs(user_email);

-- Partner organizations reference
CREATE TABLE IF NOT EXISTS partner_orgs (
    org_slug VARCHAR(100) PRIMARY KEY,
    org_name VARCHAR(255),
    tier VARCHAR(50) DEFAULT 'partner',
    contact_email VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Seed partner orgs
INSERT INTO partner_orgs (org_slug, org_name, tier) VALUES
    ('toucan-protocol', 'Toucan Protocol', 'partner'),
    ('flowcarbon', 'Flowcarbon', 'partner'),
    ('klimadao', 'KlimaDAO', 'partner'),
    ('moss-earth', 'Moss.Earth', 'partner')
ON CONFLICT DO NOTHING;
```

### Phase 3: MCP Tool

```python
# In MCP plugin definition

@mcp_tool(
    name="get_claude_config",
    description="Fetch tier-appropriate Claude configuration from Regen servers"
)
async def get_claude_config(
    resource: str = "bundle",
    include_personal: bool = True
) -> dict:
    """
    Fetch Claude configuration based on your access tier.

    Args:
        resource: What to fetch - "bundle" for everything, or "files/{path}"
        include_personal: Whether to include personal config additions

    Returns:
        Configuration content appropriate to your access tier
    """
    import httpx

    token = os.getenv("REGEN_TOKEN")
    headers = {"Authorization": f"Bearer {token}"} if token else {}

    base_url = "https://regen.gaiaai.xyz/api/koi/claude-config"

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{base_url}/{resource}",
            headers=headers,
            params={"include_personal": include_personal}
        )
        response.raise_for_status()

        if resource == "bundle":
            return response.json()
        else:
            return {
                "content": response.text,
                "tier": response.headers.get("X-Config-Tier"),
                "etag": response.headers.get("ETag")
            }
```

---

## User Experience

### Onboarding Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     NEW TEAM MEMBER                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. AUTHENTICATE (one-time)                                     │
│     ┌─────────────────────────────────────────────────────────┐│
│     │  In any Claude Code session:                            ││
│     │  > "Authenticate with Regen KOI"                        ││
│     │                                                         ││
│     │  → Triggers regen_koi_authenticate                      ││
│     │  → Opens browser for Google OAuth                       ││
│     │  → Returns session token                                ││
│     │  → Token stored as REGEN_TOKEN                          ││
│     └─────────────────────────────────────────────────────────┘│
│                                                                 │
│  2. SET TOKEN (per-machine, persists)                          │
│     ┌─────────────────────────────────────────────────────────┐│
│     │  # Add to shell profile (~/.zshrc or ~/.bashrc)         ││
│     │  export REGEN_TOKEN="regen_xxx..."                      ││
│     │                                                         ││
│     │  # Or in Claude Code settings                           ││
│     │  claude config set REGEN_TOKEN "regen_xxx..."           ││
│     └─────────────────────────────────────────────────────────┘│
│                                                                 │
│  3. USE ANYWHERE                                                │
│     ┌─────────────────────────────────────────────────────────┐│
│     │  # Local, Cloud, Co-work, Desktop - all work            ││
│     │                                                         ││
│     │  > "Load Regen config"                                  ││
│     │  → Fetches tier-appropriate config                      ││
│     │  → Full capabilities based on role                      ││
│     └─────────────────────────────────────────────────────────┘│
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Security Considerations

1. **Allowlist-only file access:** Unknown paths return 404, not "try core tier"
2. **Token reuse:** Uses existing session tokens (no new auth surface)
3. **Token storage:** SHA-256 hashes in database (existing pattern)
4. **Token expiry:** 1-hour sessions (existing behavior)
5. **Cache-Control:** `private` for any response with user-specific data
6. **Vary header:** `Authorization` on all responses
7. **Path traversal:** Blocked via `..` check + allowlist
8. **Webhook security:** GitHub signatures validated via HMAC-SHA256
9. **Audit logging:** All access logged to `config_access_log`
10. **No secrets in config:** MCP configs use env var references

---

## Summary

| Problem | Solution |
| --- | --- |
| Cloud Claude can't auth with GitHub | HTTP endpoint with existing session token |
| PAT per session is bad UX | One REGEN_TOKEN works everywhere |
| Team onboarding complexity | "Authenticate once, set env var, done" |
| Platform inconsistency | Same endpoint for all platforms |
| Tiered access via GitHub teams | Tiered access via email domain (Phase 1) + org membership (Phase 2) |

**Phase 1 delivers:**
- ✅ Works in cloud/browser Claude Code
- ✅ Reuses existing OAuth + session token system
- ✅ Public + Core tiers (covers @regen.network team)
- ✅ Personal customization layer
- ✅ Proper HTTP caching (ETag, Cache-Control, Vary)
- ✅ Allowlist-only security
- ✅ Audit trail

**Phase 2 adds:**
- Partner tier (requires auth changes)
- Org membership management
- GitHub org sync

---

## Next Actions

### Phase 1 (This Sprint)
- [ ] Create tiered CLAUDE.md files (split current version into `public/`, `core/`)
- [ ] Run migration `020_claude_config.sql`
- [ ] Add `claude_config_routes.py` to pipeline_metadata_api.py
- [ ] Test with existing OAuth tokens
- [ ] Deploy to regen.gaiaai.xyz
- [ ] Document and announce

### Phase 2 (Next Sprint)
- [ ] Modify `auth_service.py` to allow partner domains
- [ ] Run migration `021_partner_auth.sql`
- [ ] Add `get_claude_config` MCP tool
- [ ] Set up GitHub webhooks on source repos
- [ ] Create `/load-regen-config` skill

---

*This architecture enables cross-platform Regen AI access while maintaining tiered security.*
