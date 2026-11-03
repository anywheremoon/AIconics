CREATE TABLE IF NOT EXISTS eth_vault_transfers (
    id SERIAL PRIMARY KEY,
    request_id VARCHAR(66) NOT NULL UNIQUE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_id VARCHAR(36) NOT NULL,
    sender_address VARCHAR(42) NOT NULL,
    recipient_address VARCHAR(42) NOT NULL,
    amount_wei NUMERIC(78, 0) NOT NULL,
    chain_id BIGINT NOT NULL,
    verifying_contract VARCHAR(42) NOT NULL,
    risk_score INTEGER,
    risk_level VARCHAR(16),
    decision VARCHAR(32),
    status VARCHAR(32) NOT NULL DEFAULT 'PENDING_ANALYSIS',
    requires_auth BOOLEAN NOT NULL DEFAULT FALSE,
    requires_admin_approval BOOLEAN NOT NULL DEFAULT FALSE,
    timelock_until TIMESTAMPTZ,
    signature_deadline TIMESTAMPTZ,
    analysis_hash VARCHAR(66),
    nonce VARCHAR(66) UNIQUE,
    signature TEXT,
    blockchain_tx_hash VARCHAR(66),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_eth_vault_amount_positive CHECK (amount_wei > 0),
    CONSTRAINT ck_eth_vault_risk_score CHECK (
        risk_score IS NULL OR risk_score BETWEEN 0 AND 100
    ),
    CONSTRAINT ck_eth_vault_risk_level CHECK (
        risk_level IS NULL OR risk_level IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')
    )
);

CREATE INDEX IF NOT EXISTS ix_eth_vault_transfers_user_id
    ON eth_vault_transfers(user_id);
CREATE INDEX IF NOT EXISTS ix_eth_vault_transfers_status
    ON eth_vault_transfers(status);
CREATE INDEX IF NOT EXISTS ix_eth_vault_transfers_sender_address
    ON eth_vault_transfers(sender_address);
CREATE INDEX IF NOT EXISTS ix_eth_vault_transfers_recipient_address
    ON eth_vault_transfers(recipient_address);

