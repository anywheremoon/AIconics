CREATE TABLE IF NOT EXISTS eth_vault_transfers (
    id SERIAL PRIMARY KEY,
    deployment_id VARCHAR(36) NOT NULL,
    request_id VARCHAR(66) NOT NULL,
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
    verification_session_id VARCHAR(36),
    verification_code_hash VARCHAR(64),
    verification_requested_at TIMESTAMPTZ,
    verification_expires_at TIMESTAMPTZ,
    verification_attempts INTEGER NOT NULL DEFAULT 0,
    verification_confirmed_at TIMESTAMPTZ,
    auth_tx_hash VARCHAR(66),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_eth_vault_deployment_request UNIQUE (
        deployment_id,
        chain_id,
        verifying_contract,
        request_id
    ),
    CONSTRAINT ck_eth_vault_amount_positive CHECK (amount_wei > 0),
    CONSTRAINT ck_eth_vault_risk_score CHECK (
        risk_score IS NULL OR risk_score BETWEEN 0 AND 100
    ),
    CONSTRAINT ck_eth_vault_risk_level CHECK (
        risk_level IS NULL OR risk_level IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')
    )
);

-- Reconcile databases created by an earlier version of this migration.
ALTER TABLE eth_vault_transfers
    ADD COLUMN IF NOT EXISTS deployment_id VARCHAR(36),
    ADD COLUMN IF NOT EXISTS verification_session_id VARCHAR(36),
    ADD COLUMN IF NOT EXISTS verification_code_hash VARCHAR(64),
    ADD COLUMN IF NOT EXISTS verification_requested_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS verification_expires_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS verification_attempts INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS verification_confirmed_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS auth_tx_hash VARCHAR(66);

UPDATE eth_vault_transfers
SET deployment_id = '00000000-0000-0000-0000-000000000000'
WHERE deployment_id IS NULL;

ALTER TABLE eth_vault_transfers
    ALTER COLUMN deployment_id SET NOT NULL;

ALTER TABLE eth_vault_transfers
    DROP CONSTRAINT IF EXISTS eth_vault_transfers_request_id_key;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'uq_eth_vault_deployment_request'
    ) THEN
        ALTER TABLE eth_vault_transfers
            ADD CONSTRAINT uq_eth_vault_deployment_request UNIQUE (
                deployment_id,
                chain_id,
                verifying_contract,
                request_id
            );
    END IF;
END
$$;

CREATE INDEX IF NOT EXISTS ix_eth_vault_transfers_user_id
    ON eth_vault_transfers(user_id);
CREATE INDEX IF NOT EXISTS ix_eth_vault_transfers_deployment_id
    ON eth_vault_transfers(deployment_id);
CREATE INDEX IF NOT EXISTS ix_eth_vault_transfers_status
    ON eth_vault_transfers(status);
CREATE INDEX IF NOT EXISTS ix_eth_vault_transfers_sender_address
    ON eth_vault_transfers(sender_address);
CREATE INDEX IF NOT EXISTS ix_eth_vault_transfers_recipient_address
    ON eth_vault_transfers(recipient_address);

