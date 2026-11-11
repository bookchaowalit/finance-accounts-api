-- SPEC-003 (2026-11-11): exact money, ISO 4217 currency, workspace-defined scope (finance-accounts).
-- Amounts move from double precision to numeric; currency codes must be three upper-case letters;
-- owner_scope (the owner's own life areas) becomes scope, a free label each workspace defines.
-- Append-only: do not edit once applied.

-- account
ALTER TABLE finance_accounts.accounts NO FORCE ROW LEVEL SECURITY;
UPDATE finance_accounts.accounts SET currency = upper(btrim(currency));
ALTER TABLE finance_accounts.accounts FORCE ROW LEVEL SECURITY;
ALTER TABLE finance_accounts.accounts RENAME COLUMN owner_scope TO scope;
DO $$ DECLARE c text; BEGIN FOR c IN SELECT conname FROM pg_constraint WHERE conrelid = 'finance_accounts.accounts'::regclass AND contype = 'c' AND conkey = ARRAY[(SELECT attnum FROM pg_attribute WHERE attrelid = 'finance_accounts.accounts'::regclass AND attname = 'scope')] LOOP EXECUTE format('ALTER TABLE finance_accounts.accounts DROP CONSTRAINT %I', c); END LOOP; END $$;
ALTER TABLE finance_accounts.accounts ALTER COLUMN scope SET DEFAULT '';
ALTER TABLE finance_accounts.accounts ADD CONSTRAINT accounts_scope_check CHECK (length(scope) <= 64);
DO $$ DECLARE i text; BEGIN SELECT indexname INTO i FROM pg_indexes WHERE schemaname = 'finance_accounts' AND tablename = 'accounts' AND indexdef LIKE '%(workspace_id, scope)'; IF i IS NOT NULL THEN EXECUTE format('ALTER INDEX finance_accounts.%I RENAME TO accounts_scope', i); END IF; END $$;
DO $$ DECLARE c text; BEGIN FOR c IN SELECT conname FROM pg_constraint WHERE conrelid = 'finance_accounts.accounts'::regclass AND contype = 'c' AND conkey = ARRAY[(SELECT attnum FROM pg_attribute WHERE attrelid = 'finance_accounts.accounts'::regclass AND attname = 'currency')] LOOP EXECUTE format('ALTER TABLE finance_accounts.accounts DROP CONSTRAINT %I', c); END LOOP; END $$;
ALTER TABLE finance_accounts.accounts ADD CONSTRAINT accounts_currency_check CHECK (currency ~ '^[A-Z]{3}$');
DO $$ DECLARE c text; BEGIN FOR c IN SELECT conname FROM pg_constraint WHERE conrelid = 'finance_accounts.accounts'::regclass AND contype = 'c' AND conkey = ARRAY[(SELECT attnum FROM pg_attribute WHERE attrelid = 'finance_accounts.accounts'::regclass AND attname = 'opening_balance')] LOOP EXECUTE format('ALTER TABLE finance_accounts.accounts DROP CONSTRAINT %I', c); END LOOP; END $$;
ALTER TABLE finance_accounts.accounts ALTER COLUMN opening_balance TYPE numeric(19,4) USING opening_balance::numeric(19,4);
