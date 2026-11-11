-- SPEC-006 (2026-11-11): cross-service references between the finance cells (finance-accounts).
-- Append-only: do not edit once applied.

-- The relay sends a record's events in insert order (the row lock makes it the commit order).
ALTER TABLE finance_accounts.outbox ADD COLUMN seq bigint GENERATED ALWAYS AS IDENTITY;
DROP INDEX finance_accounts.outbox_unrelayed;
CREATE INDEX outbox_unrelayed ON finance_accounts.outbox (seq) WHERE relayed_at IS NULL;

-- SPEC-006: cross-service references, fed by finance.events.v1.
CREATE TABLE finance_accounts.ref_targets (
    workspace_id   uuid NOT NULL,
    target         text NOT NULL,
    record_id      bigint NOT NULL,
    status         text,
    deleted        boolean NOT NULL DEFAULT false,
    record_version bigint NOT NULL DEFAULT 0,
    event_seq      bigint NOT NULL DEFAULT 0,
    updated_at     timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (workspace_id, target, record_id)
);
CREATE TABLE finance_accounts.ref_sources (
    workspace_id    uuid NOT NULL,
    source          text NOT NULL,
    source_id       bigint NOT NULL,
    field           text NOT NULL,
    target_resource text NOT NULL,
    target_id       bigint,
    deleted         boolean NOT NULL DEFAULT false,
    record_version  bigint NOT NULL DEFAULT 0,
    event_seq       bigint NOT NULL DEFAULT 0,
    updated_at      timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (workspace_id, source, source_id, field)
);
CREATE INDEX ref_sources_live ON finance_accounts.ref_sources (workspace_id, target_resource, target_id) WHERE NOT deleted;
CREATE TABLE finance_accounts.ref_offsets (
    topic       text NOT NULL,
    partition   integer NOT NULL,
    next_offset bigint NOT NULL,
    PRIMARY KEY (topic, partition)
);
ALTER TABLE finance_accounts.ref_targets ENABLE ROW LEVEL SECURITY;
ALTER TABLE finance_accounts.ref_targets FORCE ROW LEVEL SECURITY;
CREATE POLICY workspace_isolation ON finance_accounts.ref_targets USING (workspace_id = finance_accounts.current_workspace());
CREATE POLICY publisher_sync ON finance_accounts.ref_targets TO finance_accounts_publisher USING (true) WITH CHECK (true);
GRANT SELECT ON finance_accounts.ref_targets TO finance_accounts_api;
GRANT SELECT, INSERT, UPDATE ON finance_accounts.ref_targets TO finance_accounts_publisher;
ALTER TABLE finance_accounts.ref_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE finance_accounts.ref_sources FORCE ROW LEVEL SECURITY;
CREATE POLICY workspace_isolation ON finance_accounts.ref_sources USING (workspace_id = finance_accounts.current_workspace());
CREATE POLICY publisher_sync ON finance_accounts.ref_sources TO finance_accounts_publisher USING (true) WITH CHECK (true);
GRANT SELECT ON finance_accounts.ref_sources TO finance_accounts_api;
GRANT SELECT, INSERT, UPDATE ON finance_accounts.ref_sources TO finance_accounts_publisher;
GRANT SELECT, INSERT, UPDATE ON finance_accounts.ref_offsets TO finance_accounts_publisher;

-- Rows written before SPEC-005 announce themselves once, so other cells learn their ids.
ALTER TABLE finance_accounts.outbox NO FORCE ROW LEVEL SECURITY;
ALTER TABLE finance_accounts.accounts NO FORCE ROW LEVEL SECURITY;
INSERT INTO finance_accounts.outbox (workspace_id, type, subject, classification, payload, correlation_id) SELECT workspace_id, 'finance-accounts.account.snapshot', 'empire:finance-accounts:account:' || id, 'confidential', jsonb_build_object('account_type', account_type, 'scope', scope, 'currency', currency, 'status', status, 'opened_on', opened_on, 'closed_on', closed_on, 'version', version, 'deleted', false), 'spec-006-snapshot' FROM finance_accounts.accounts ORDER BY id;
ALTER TABLE finance_accounts.accounts FORCE ROW LEVEL SECURITY;
ALTER TABLE finance_accounts.outbox FORCE ROW LEVEL SECURITY;
