-- Migration: 020_claude_config.sql
-- Purpose: Create tables for Claude Config HTTP endpoint
-- Date: 2026-01-28

-- =============================================================================
-- User personal config storage
-- =============================================================================
-- Stores user-specific CLAUDE.md additions and skill configuration overrides.
-- This is the "personal layer" that gets merged with tier-appropriate config.

CREATE TABLE IF NOT EXISTS user_config (
    user_email VARCHAR(255) PRIMARY KEY,
    claude_md_additions TEXT,                    -- Personal CLAUDE.md content to append
    skill_overrides JSONB DEFAULT '{}',          -- Per-skill parameter overrides
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE user_config IS 'Personal Claude configuration per user';
COMMENT ON COLUMN user_config.claude_md_additions IS 'User-specific CLAUDE.md content appended to tier config';
COMMENT ON COLUMN user_config.skill_overrides IS 'JSON object with skill-name keys and override parameters';


-- =============================================================================
-- Config access logging (audit trail)
-- =============================================================================
-- Tracks all config endpoint access for security auditing and usage analytics.

CREATE TABLE IF NOT EXISTS config_access_log (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255),                     -- NULL for unauthenticated requests
    tier VARCHAR(50) NOT NULL,                   -- 'public', 'partner', or 'core'
    resource_path VARCHAR(255) NOT NULL,         -- What was requested
    access_granted BOOLEAN NOT NULL,             -- Whether access was allowed
    accessed_at TIMESTAMP DEFAULT NOW(),
    client_ip INET,                              -- Optional: client IP for security
    user_agent TEXT                              -- Optional: client user agent
);

CREATE INDEX IF NOT EXISTS idx_config_access_log_email ON config_access_log(user_email);
CREATE INDEX IF NOT EXISTS idx_config_access_log_time ON config_access_log(accessed_at);
CREATE INDEX IF NOT EXISTS idx_config_access_log_tier ON config_access_log(tier);

COMMENT ON TABLE config_access_log IS 'Audit log for Claude config endpoint access';


-- =============================================================================
-- Phase 2: Partner organization tables (for partner tier support)
-- =============================================================================
-- Uncomment when implementing partner tier

/*
-- User organization memberships
-- Used to determine partner tier access based on org affiliation

CREATE TABLE IF NOT EXISTS user_orgs (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) NOT NULL,
    org_slug VARCHAR(100) NOT NULL,              -- GitHub org slug or custom identifier
    source VARCHAR(50) DEFAULT 'manual',         -- 'github', 'manual', 'oauth'
    verified_at TIMESTAMP,                       -- When membership was verified
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_email, org_slug)
);

CREATE INDEX IF NOT EXISTS idx_user_orgs_email ON user_orgs(user_email);
CREATE INDEX IF NOT EXISTS idx_user_orgs_org ON user_orgs(org_slug);

COMMENT ON TABLE user_orgs IS 'User organization memberships for tier determination';


-- Partner organizations reference table
-- Defines which orgs qualify for partner tier

CREATE TABLE IF NOT EXISTS partner_orgs (
    org_slug VARCHAR(100) PRIMARY KEY,
    org_name VARCHAR(255),
    tier VARCHAR(50) DEFAULT 'partner',          -- Could be 'partner' or 'core' for special partners
    contact_email VARCHAR(255),
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE partner_orgs IS 'Reference table for partner organizations';

-- Seed initial partner orgs
INSERT INTO partner_orgs (org_slug, org_name, tier) VALUES
    ('toucan-protocol', 'Toucan Protocol', 'partner'),
    ('flowcarbon', 'Flowcarbon', 'partner'),
    ('klimadao', 'KlimaDAO', 'partner'),
    ('moss-earth', 'Moss.Earth', 'partner')
ON CONFLICT DO NOTHING;
*/


-- =============================================================================
-- Helper function: Update timestamp trigger
-- =============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to user_config
DROP TRIGGER IF EXISTS update_user_config_updated_at ON user_config;
CREATE TRIGGER update_user_config_updated_at
    BEFORE UPDATE ON user_config
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();


-- =============================================================================
-- Verification queries (run after migration)
-- =============================================================================

-- Check tables exist:
-- SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name LIKE '%config%';

-- Check indexes:
-- SELECT indexname, tablename FROM pg_indexes WHERE tablename LIKE '%config%';
