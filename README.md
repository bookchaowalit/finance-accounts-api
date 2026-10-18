# finance-accounts-api
The Finance accounts cell: its own API (Railway, serverless) and its own Neon
database, first generated from `cell.yaml` (one of the ten finance
services split on 2026-10-12). It
reuses empire-platform for identity, authorization, executions and audit over
HTTP with the caller's token.

| | |
|---|---|
| API | Railway project `finance-accounts-api`, service `finance-accounts-api` (Serverless) |
| Data | Neon project `finance-accounts-api`, database `finance_accounts` |
| Registry | solo-empire `repository-catalog/registries/online-systems.yaml` (`finance-accounts`) |

## API

Every resource has list, stats, get, get-by-legacy-id, create, patch and delete
(see `cellkit/app.py`). Permissions are `finance-accounts.<resource>:read|write|delete`.

| Path | Resource | Filters |
|---|---|---|
| `/v1/accounts` | account | `account_type`, `owner_scope`, `status` |

## Develop and operate

```bash
uv venv .venv && uv pip install --python .venv/bin/python -e ".[dev]"
.venv/bin/pytest -q
NEON_API_KEY=... .venv/bin/finance-accounts-db provision
npm install && railway config apply && railway up --ci --service finance-accounts-api
railway scale --service finance-accounts-api asia-southeast1-eqsg3a=1 us-east4-eqdc4a=0   # next to Neon and the platform
```

Railway variables: `SENTRY_DSN` (error reporting; unset = off, see `src/cellkit/_sentry.py`),
`FINANCE_ACCOUNTS_DB_MODE=hosted`, `FINANCE_ACCOUNTS_DB_URL_API`,
`FINANCE_ACCOUNTS_JWT_PUBLIC_KEY_PEM`, `FINANCE_ACCOUNTS_JWT_ISSUER`, `EMPIRE_PLATFORM_URL`.
