CREATE TABLE IF NOT EXISTS devices (
    device_id VARCHAR(255) PRIMARY KEY,
    first_seen TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS device_user_links (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR(255) NOT NULL REFERENCES devices(device_id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    first_seen TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_device_user_link UNIQUE (device_id, user_id)
);

CREATE INDEX IF NOT EXISTS ix_device_user_links_device_id
    ON device_user_links(device_id);
CREATE INDEX IF NOT EXISTS ix_device_user_links_user_id
    ON device_user_links(user_id);

CREATE TABLE IF NOT EXISTS user_sessions (
    session_id VARCHAR(36) PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    device_id VARCHAR(255) NOT NULL REFERENCES devices(device_id) ON DELETE RESTRICT,
    ip_address VARCHAR(45),
    location VARCHAR(255),
    login_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    device_trust_status VARCHAR(20) NOT NULL,
    repeated_login_detected BOOLEAN NOT NULL DEFAULT FALSE,
    account_switch_detected BOOLEAN NOT NULL DEFAULT FALSE,
    recent_login_count INTEGER NOT NULL DEFAULT 1,
    recent_device_account_count INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX IF NOT EXISTS ix_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS ix_user_sessions_device_id ON user_sessions(device_id);
CREATE INDEX IF NOT EXISTS ix_user_sessions_login_at ON user_sessions(login_at);

ALTER TABLE behavior_events
    ADD COLUMN IF NOT EXISTS session_id VARCHAR(36);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'fk_behavior_events_session_id'
          AND conrelid = 'behavior_events'::regclass
    ) THEN
        ALTER TABLE behavior_events
            ADD CONSTRAINT fk_behavior_events_session_id
            FOREIGN KEY (session_id)
            REFERENCES user_sessions(session_id)
            ON DELETE RESTRICT;
    END IF;
END
$$;

CREATE INDEX IF NOT EXISTS ix_behavior_events_session_id
    ON behavior_events(session_id);