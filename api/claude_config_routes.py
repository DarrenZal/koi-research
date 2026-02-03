"""
Claude Config Routes - HTTP endpoint for tiered Claude configuration

Serves Claude Code configuration (CLAUDE.md, contexts, skills, agents) based on
user access tier determined by authentication.

Integration:
    from api.claude_config_routes import config_router
    app.include_router(config_router)

Environment Variables:
    CLAUDE_CONFIG_DIR: Path to config files (default: /app/claude-config)
    GITHUB_WEBHOOK_SECRET: Secret for validating GitHub webhook signatures

Database Requirements:
    - session_tokens table (existing KOI auth)
    - user_config table (new, see migrations/020_claude_config.sql)
    - config_access_log table (new, for audit trail)
"""

from fastapi import APIRouter, Header, HTTPException, Depends, Response, Request
from typing import Optional
import os
import json
import hashlib
import hmac
import subprocess
import urllib.parse
import asyncpg
from datetime import datetime
from contextlib import asynccontextmanager
import logging

logger = logging.getLogger(__name__)

# Router setup
config_router = APIRouter(prefix="/api/koi/claude-config", tags=["claude-config"])

# Configuration
CONFIG_DIR = os.getenv("CLAUDE_CONFIG_DIR", "/app/claude-config")
GITHUB_WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET")

# Tier access levels
TIER_ACCESS = {
    "public": 1,
    "partner": 2,  # Phase 2
    "core": 3
}

# ALLOWLIST ONLY - unknown paths return 404
# This is the security boundary - only these files can be served
FILE_ALLOWLIST = {
    # Public tier (anyone)
    "public/CLAUDE.md": "public",
    "public/.mcp.json": "public",
    "public/setup/install.sh": "public",

    # Partner tier (Phase 2 - ecosystem partners)
    "partners/CLAUDE.md": "partner",
    "partners/contexts/REGISTRY_PROJECTS.md": "partner",
    "partners/contexts/METHODOLOGY_DEV.md": "partner",
    "partners/contexts/CREDIT_ISSUANCE.md": "partner",
    "partners/skills/project-registration/SKILL.md": "partner",
    "partners/skills/methodology-review/SKILL.md": "partner",

    # Core tier (@regen.network team)
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

# API path mapping (user-facing paths to internal file paths)
API_PATH_TO_FILE = {
    ".mcp.json": "public/.mcp.json",
    "CLAUDE.md": None,  # Special: merged from tiers
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


# =============================================================================
# Database dependency
# =============================================================================

# Database configuration from environment
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5433"))
DB_NAME = os.getenv("DB_NAME", "eliza")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")


async def get_db():
    """
    Database connection dependency.

    Creates a connection per-request (matching pipeline_metadata_api.py pattern).
    """
    conn = await asyncpg.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    try:
        yield conn
    finally:
        await conn.close()


# =============================================================================
# Helper functions
# =============================================================================

def can_access(user_tier: str, required_tier: str) -> bool:
    """Check if user tier has access to required tier."""
    return TIER_ACCESS.get(user_tier, 0) >= TIER_ACCESS.get(required_tier, 999)


def compute_etag(content: str) -> str:
    """Compute ETag from content hash."""
    return f'"{hashlib.md5(content.encode()).hexdigest()}"'


def load_file(relative_path: str) -> Optional[str]:
    """Load file from config directory. Path must be in allowlist."""
    if relative_path not in FILE_ALLOWLIST:
        return None

    # Normalize and resolve the path
    full_path = os.path.normpath(os.path.join(CONFIG_DIR, relative_path))

    # CRITICAL: Ensure resolved path is within CONFIG_DIR (prevent path traversal)
    config_dir_abs = os.path.abspath(CONFIG_DIR)
    if not full_path.startswith(config_dir_abs + os.sep):
        logger.warning(f"Path traversal attempt blocked: {relative_path}")
        return None

    # Use try/except instead of exists() check to avoid TOCTOU race
    try:
        with open(full_path, 'r') as f:
            return f.read()
    except (FileNotFoundError, IOError, PermissionError):
        return None


def get_file_mtime(relative_path: str) -> Optional[datetime]:
    """Get file modification time."""
    full_path = os.path.normpath(os.path.join(CONFIG_DIR, relative_path))

    # Ensure path is within CONFIG_DIR
    config_dir_abs = os.path.abspath(CONFIG_DIR)
    if not full_path.startswith(config_dir_abs + os.sep):
        return None

    try:
        return datetime.fromtimestamp(os.path.getmtime(full_path))
    except (FileNotFoundError, OSError):
        return None


def load_merged_claude_md(tier: str) -> str:
    """Build CLAUDE.md by merging tiers up to user's level."""
    parts = []

    # Tier 1: Public base (always included)
    public = load_file("public/CLAUDE.md")
    if public:
        parts.append(public)

    # Tier 2: Partner additions (Phase 2)
    if TIER_ACCESS.get(tier, 0) >= 2:
        partner = load_file("partners/CLAUDE.md")
        if partner:
            parts.append("\n\n<!-- Partner Extensions -->\n\n")
            parts.append(partner)

    # Tier 3: Core additions
    if TIER_ACCESS.get(tier, 0) >= 3:
        core = load_file("core/CLAUDE.md")
        if core:
            parts.append("\n\n<!-- Core Extensions -->\n\n")
            parts.append(core)

    return "".join(parts)


async def get_user_tier(
    authorization: Optional[str] = Header(None),
    db=Depends(get_db)
) -> tuple[str, Optional[str], list[str]]:
    """
    Get user's access tier from session token.

    Returns: (tier, email, orgs)
    """
    if not authorization or not authorization.startswith("Bearer "):
        return ("public", None, [])

    token = authorization[7:]
    token_hash = hashlib.sha256(token.encode()).hexdigest()

    try:
        row = await db.fetchrow("""
            SELECT user_email FROM session_tokens
            WHERE token_hash = $1 AND expires_at > NOW()
        """, token_hash)
    except Exception:
        return ("public", None, [])

    if not row:
        return ("public", None, [])

    email = row["user_email"]

    # Phase 1: Only public and core tiers supported.
    # Partner tier requires OAuth allowlist changes (Phase 2).
    # Authenticated non-@regen.network users get public tier.
    if email and email.endswith("@regen.network"):
        tier = "core"
    else:
        tier = "public"

    # Phase 2: Add org lookup for partner tier (requires auth changes)
    # org_rows = await db.fetch(
    #     "SELECT org_slug FROM user_orgs WHERE user_email = $1", email
    # )
    # orgs = [r["org_slug"] for r in org_rows]
    # tier = determine_tier_with_orgs(email, orgs)
    orgs = []

    return (tier, email, orgs)


async def load_personal_config(email: str, db) -> dict:
    """Load user's personal config from database."""
    if not email:
        return {"claude_md_additions": "", "skill_overrides": {}}

    try:
        row = await db.fetchrow("""
            SELECT claude_md_additions, skill_overrides, updated_at
            FROM user_config WHERE user_email = $1
        """, email)
    except Exception:
        return {"claude_md_additions": "", "skill_overrides": {}}

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
        merged[skill_name] = dict(skill_data)
        if skill_name in overrides:
            merged[skill_name]["overrides"] = overrides[skill_name]
    return merged


async def log_access(db, email: Optional[str], tier: str, path: str, granted: bool):
    """Log config access for audit trail."""
    try:
        await db.execute("""
            INSERT INTO config_access_log (user_email, tier, resource_path, access_granted)
            VALUES ($1, $2, $3, $4)
        """, email, tier, path, granted)
    except Exception:
        pass  # Don't fail request on logging errors


# =============================================================================
# Routes - ORDER MATTERS: specific routes before catch-all
# =============================================================================

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


@config_router.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    config_exists = os.path.exists(CONFIG_DIR)

    # Count files per tier
    tier_counts = {"public": 0, "partner": 0, "core": 0}
    for file_path, tier in FILE_ALLOWLIST.items():
        if os.path.exists(os.path.join(CONFIG_DIR, file_path)):
            tier_counts[tier] = tier_counts.get(tier, 0) + 1

    # Get last sync times from git
    last_sync = {}
    for tier_name in ["public", "partners", "core"]:
        tier_path = os.path.join(CONFIG_DIR, tier_name)
        if os.path.exists(os.path.join(tier_path, ".git")):
            try:
                result = subprocess.run(
                    ["git", "-C", tier_path, "log", "-1", "--format=%cI"],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    last_sync[tier_name] = result.stdout.strip()
            except Exception:
                pass

    return Response(
        content=json.dumps({
            "status": "ok",
            "config_dir_exists": config_exists,
            "tiers": tier_counts,
            "last_sync": last_sync
        }),
        media_type="application/json",
        headers={"Cache-Control": "no-cache"}
    )


@config_router.get("/bundle")
async def get_bundle(
    auth: tuple = Depends(get_user_tier),
    db=Depends(get_db),
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
        claude_md += "\n\n<!-- Personal Extensions -->\n\n"
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
                try:
                    agents[name] = json.loads(content)
                except json.JSONDecodeError:
                    agents[name] = {"error": "invalid JSON"}

    # Build playbooks dict
    playbooks = {}
    for file_path, required_tier in FILE_ALLOWLIST.items():
        if "/playbooks/" in file_path and can_access(tier, required_tier):
            content = load_file(file_path)
            if content:
                name = file_path.split("/playbooks/")[1].replace(".md", "")
                playbooks[name] = content

    # Load MCP config
    mcp_content = load_file("public/.mcp.json")
    mcp = json.loads(mcp_content) if mcp_content else {}

    bundle = {
        "tier": tier,
        "user_email": email,
        "mcp": mcp,
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

    # Log access
    await log_access(db, email, tier, "bundle", True)

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
    db=Depends(get_db)
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
    db=Depends(get_db)
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
    await log_access(db, email, tier, "personal", True)

    return {"status": "saved", "updated_at": datetime.now().isoformat()}


@config_router.post("/sync")
async def sync_from_github(
    request: Request,
    x_hub_signature_256: Optional[str] = Header(None)
):
    """GitHub webhook handler - syncs config on push."""
    if not GITHUB_WEBHOOK_SECRET:
        raise HTTPException(status_code=500, detail="Webhook secret not configured")

    # Validate signature header exists before comparing
    if not x_hub_signature_256:
        raise HTTPException(status_code=401, detail="Missing signature header")

    body = await request.body()
    expected_sig = "sha256=" + hmac.new(
        GITHUB_WEBHOOK_SECRET.encode(),
        body,
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected_sig, x_hub_signature_256):
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

    try:
        result = subprocess.run(
            ["git", "-C", repo_path, "pull", "--ff-only"],
            capture_output=True,
            text=True,
            timeout=30
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=500, detail="Git pull timed out")

    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=f"Git pull failed: {result.stderr}")

    commit = payload.get("after", "unknown")[:7]

    return {
        "status": "synced",
        "repo": repo_name,
        "commit": commit,
        "output": result.stdout
    }


# =============================================================================
# CATCH-ALL ROUTE - MUST BE REGISTERED LAST
# =============================================================================

@config_router.get("/files/{file_path:path}")
async def get_file_endpoint(
    file_path: str,
    auth: tuple = Depends(get_user_tier),
    db=Depends(get_db),
    if_none_match: Optional[str] = Header(None),
    if_modified_since: Optional[str] = Header(None)
):
    """Get individual config file. Only allowlisted files are served."""
    tier, email, orgs = auth

    # Security: decode URL encoding and validate path
    file_path = urllib.parse.unquote(file_path)

    # Check for null bytes, path traversal, and absolute paths
    if '\0' in file_path or ".." in file_path or file_path.startswith("/"):
        logger.warning(f"Invalid path attempt: {file_path!r}")
        raise HTTPException(status_code=400, detail="Invalid path")

    # Special case: CLAUDE.md returns merged version
    if file_path == "CLAUDE.md":
        content = load_merged_claude_md(tier)
        etag = compute_etag(content)

        if if_none_match and if_none_match == etag:
            return Response(status_code=304)

        await log_access(db, email, tier, "CLAUDE.md", True)

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
        await log_access(db, email, tier, file_path, False)
        raise HTTPException(status_code=404, detail="File not in allowlist")

    actual_path = API_PATH_TO_FILE[file_path]
    if actual_path is None:
        raise HTTPException(status_code=404, detail="File not found")

    # Check tier access
    required_tier = FILE_ALLOWLIST.get(actual_path)
    if not required_tier:
        raise HTTPException(status_code=404, detail="File not in allowlist")

    if not can_access(tier, required_tier):
        await log_access(db, email, tier, file_path, False)
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

    await log_access(db, email, tier, file_path, True)

    return Response(content=content, media_type=media_type, headers=headers)
