import logging
from sqlalchemy import text
from app.db.database import engine

logger = logging.getLogger(__name__)


async def init_db_schema():
    """Ensure all required tables and columns exist in PostgreSQL."""
    statements = [
        """
        CREATE TABLE IF NOT EXISTS user_activity_logs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
            user_id UUID REFERENCES users(id) ON DELETE SET NULL,
            user_name VARCHAR(255) NOT NULL DEFAULT 'System',
            user_role VARCHAR(50) NOT NULL DEFAULT 'system',
            action_type VARCHAR(100) NOT NULL,
            target_type VARCHAR(100) NOT NULL,
            target_id VARCHAR(255),
            target_title VARCHAR(500),
            domain VARCHAR(100) NOT NULL DEFAULT 'General',
            details JSONB DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_activity_organization ON user_activity_logs(organization_id);",
        "CREATE INDEX IF NOT EXISTS idx_activity_user ON user_activity_logs(user_id);",
        "CREATE INDEX IF NOT EXISTS idx_activity_created_at ON user_activity_logs(created_at);",
        "CREATE INDEX IF NOT EXISTS idx_activity_action_type ON user_activity_logs(action_type);",
        "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS domain_whitelist JSONB DEFAULT '[]'::jsonb;",
        "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS allowed_auth_methods JSONB DEFAULT '[]'::jsonb;",
        "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS governance_config JSONB DEFAULT '{}'::jsonb;",
        "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS setup_completed BOOLEAN DEFAULT FALSE;",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_url VARCHAR(500);",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS title VARCHAR(100);",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS department VARCHAR(100);",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS phone VARCHAR(50);",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS bio TEXT;",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS timezone VARCHAR(100);",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS user_preferences JSONB DEFAULT '{}'::jsonb;",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS active_session_id VARCHAR(255);",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS last_active_device VARCHAR(255);",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS hashed_password VARCHAR(255);",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_verified BOOLEAN DEFAULT TRUE;",
        "ALTER TABLE users DROP CONSTRAINT IF EXISTS users_email_key;",
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'uq_users_org_email'
            ) THEN
                ALTER TABLE users ADD CONSTRAINT uq_users_org_email UNIQUE (organization_id, email);
            END IF;
        END $$;
        """,
        "ALTER TABLE data_sources ADD COLUMN IF NOT EXISTS domain VARCHAR(100) DEFAULT 'General';",
        "ALTER TABLE data_sources ADD COLUMN IF NOT EXISTS owner_id UUID REFERENCES users(id) ON DELETE SET NULL;",
        "ALTER TABLE data_sources ADD COLUMN IF NOT EXISTS connection_config JSONB DEFAULT '{}'::jsonb;",
        "ALTER TABLE data_sources ADD COLUMN IF NOT EXISTS source_family VARCHAR(50) NOT NULL DEFAULT 'document';",
        "ALTER TABLE data_sources ADD COLUMN IF NOT EXISTS source_intent VARCHAR(50) NOT NULL DEFAULT 'governance_policy';",
        "ALTER TABLE data_sources ADD COLUMN IF NOT EXISTS scope_config JSONB DEFAULT '{}'::jsonb;",
        "ALTER TABLE data_sources ADD COLUMN IF NOT EXISTS capabilities JSONB DEFAULT '{}'::jsonb;",
        "ALTER TABLE documents ADD COLUMN IF NOT EXISTS domain VARCHAR(100) DEFAULT 'General';",
        "ALTER TABLE documents ADD COLUMN IF NOT EXISTS owner_id UUID REFERENCES users(id) ON DELETE SET NULL;",
        """
        CREATE TABLE IF NOT EXISTS chat_sessions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
            user_id UUID REFERENCES users(id) ON DELETE SET NULL,
            user_name VARCHAR(255) NOT NULL DEFAULT 'Anonymous',
            user_role VARCHAR(50) NOT NULL DEFAULT 'developer',
            title VARCHAR(500) NOT NULL DEFAULT 'New Conversation',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_chat_sessions_org_user ON chat_sessions(organization_id, user_id);",
        "CREATE INDEX IF NOT EXISTS idx_chat_sessions_created_at ON chat_sessions(created_at);",
        "ALTER TABLE chat_sessions ADD COLUMN IF NOT EXISTS workspace_id VARCHAR(100) DEFAULT 'all';",
        "ALTER TABLE chat_sessions ADD COLUMN IF NOT EXISTS domain VARCHAR(100) DEFAULT 'global';",
        """
        CREATE TABLE IF NOT EXISTS chat_messages (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
            role VARCHAR(50) NOT NULL,
            content TEXT NOT NULL,
            metadata_json JSONB DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_chat_messages_session ON chat_messages(session_id);",
        "CREATE INDEX IF NOT EXISTS idx_chat_messages_created_at ON chat_messages(created_at);",
        """
        CREATE TABLE IF NOT EXISTS webhook_subscriptions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
            name VARCHAR(255) NOT NULL,
            url VARCHAR(1000) NOT NULL,
            channel_type VARCHAR(50) NOT NULL DEFAULT 'slack',
            min_liability_threshold_usd NUMERIC(12,2) NOT NULL DEFAULT 5000.0,
            trigger_on_block BOOLEAN NOT NULL DEFAULT TRUE,
            trigger_on_review BOOLEAN NOT NULL DEFAULT TRUE,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            secret_token VARCHAR(255),
            last_triggered_at TIMESTAMPTZ,
            last_status_code INTEGER,
            last_error TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_webhooks_organization ON webhook_subscriptions(organization_id);",
        "CREATE INDEX IF NOT EXISTS idx_webhooks_active ON webhook_subscriptions(organization_id, is_active);",
        """
        CREATE TABLE IF NOT EXISTS webhook_dispatch_logs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            webhook_id UUID NOT NULL REFERENCES webhook_subscriptions(id) ON DELETE CASCADE,
            organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
            event_type VARCHAR(50) NOT NULL,
            liability_prevented_usd NUMERIC(12,2) NOT NULL DEFAULT 0.0,
            actor_id VARCHAR(100) NOT NULL DEFAULT 'system',
            verdict VARCHAR(50) NOT NULL,
            response_status INTEGER,
            response_body TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_dispatch_webhook ON webhook_dispatch_logs(webhook_id);",
        "CREATE INDEX IF NOT EXISTS idx_dispatch_org ON webhook_dispatch_logs(organization_id);",
        "CREATE INDEX IF NOT EXISTS idx_dispatch_created_at ON webhook_dispatch_logs(created_at);",
        """
        CREATE TABLE IF NOT EXISTS hitl_escalations (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
            audit_id VARCHAR(100) NOT NULL,
            actor_id VARCHAR(100) NOT NULL,
            actor_role VARCHAR(100) NOT NULL,
            action_prompt TEXT NOT NULL,
            reasons JSONB DEFAULT '[]'::jsonb,
            category VARCHAR(100) NOT NULL DEFAULT 'Operational Triage',
            liability_prevented_usd NUMERIC(12,2) NOT NULL DEFAULT 0.0,
            status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
            suggested_action TEXT,
            resolved_by_name VARCHAR(255),
            resolved_by_role VARCHAR(100),
            resolution_decision VARCHAR(50),
            resolution_notes TEXT,
            resolved_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_hitl_org ON hitl_escalations(organization_id);",
        "CREATE INDEX IF NOT EXISTS idx_hitl_status ON hitl_escalations(organization_id, status);",
        "CREATE INDEX IF NOT EXISTS idx_hitl_created_at ON hitl_escalations(created_at);",
        """
        CREATE TABLE IF NOT EXISTS decision_evaluations (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            audit_id VARCHAR(50) NOT NULL UNIQUE,
            organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
            actor_id VARCHAR(100) NOT NULL,
            actor_role VARCHAR(50) NOT NULL DEFAULT 'support',
            decision_prompt TEXT NOT NULL,
            verdict VARCHAR(20) NOT NULL DEFAULT 'ALLOW',
            risk_level VARCHAR(20) NOT NULL DEFAULT 'LOW',
            reasons JSONB,
            preferred_source VARCHAR(255),
            suggested_action TEXT,
            context_items JSONB,
            audit_token VARCHAR(64) NOT NULL,
            execution_ms INTEGER NOT NULL DEFAULT 10,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_decision_evaluations_org ON decision_evaluations(organization_id);",
        "CREATE INDEX IF NOT EXISTS idx_decision_evaluations_audit_id ON decision_evaluations(audit_id);",
        "CREATE INDEX IF NOT EXISTS idx_decision_evaluations_verdict ON decision_evaluations(verdict);",
        "CREATE INDEX IF NOT EXISTS idx_decision_evaluations_created_at ON decision_evaluations(created_at);",
        "CREATE INDEX IF NOT EXISTS idx_decision_evaluations_actor ON decision_evaluations(actor_id);",
        """
        CREATE TABLE IF NOT EXISTS organization_invites (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
            email VARCHAR(255) NOT NULL,
            role VARCHAR(50) NOT NULL DEFAULT 'developer',
            token VARCHAR(255) NOT NULL UNIQUE,
            invited_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
            expires_at TIMESTAMPTZ NOT NULL,
            status VARCHAR(50) NOT NULL DEFAULT 'pending',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_org_invites_org ON organization_invites(organization_id);",
        "CREATE INDEX IF NOT EXISTS idx_org_invites_token ON organization_invites(token);",
        "CREATE INDEX IF NOT EXISTS idx_org_invites_email ON organization_invites(email);",
    ]

    async with engine.begin() as conn:
        for stmt in statements:
            stmt_clean = stmt.strip()
            if stmt_clean:
                await conn.execute(text(stmt_clean))
    logger.info("Database schema initialized successfully.")
