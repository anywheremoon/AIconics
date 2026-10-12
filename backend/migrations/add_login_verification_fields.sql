ALTER TABLE user_sessions
    ADD COLUMN IF NOT EXISTS auth_status VARCHAR(24) NOT NULL DEFAULT 'AUTHENTICATED',
    ADD COLUMN IF NOT EXISTS auth_reason_codes JSON NOT NULL DEFAULT '[]',
    ADD COLUMN IF NOT EXISTS verification_code_hash VARCHAR(64),
    ADD COLUMN IF NOT EXISTS verification_expires_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS verification_requested_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS verification_attempts INTEGER NOT NULL DEFAULT 0;

CREATE INDEX IF NOT EXISTS ix_user_sessions_auth_status
    ON user_sessions(auth_status);
