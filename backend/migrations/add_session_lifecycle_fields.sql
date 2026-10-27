-- Add missing session lifecycle fields.
ALTER TABLE user_sessions
    ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS logout_at TIMESTAMPTZ;
