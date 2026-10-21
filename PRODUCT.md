# Product

<!-- impeccable:product-schema 1 -->

## Platform

api

## Users

- The Solo Empire owner, through `life-dashboard-web` (finance pages), the cell's own MCP server
  (`finance-accounts-mcp`) and the hosted tool hub (`platform-mcp-remote-worker`).
- Other finance services, which point at an account by its id: `finance-transactions-api`,
  `finance-investments-api` and `finance-liabilities-api` (`account_id`, a plain number, not a
  foreign key).
- Automations with an `empire-platform` token (for example `owner-mcp`), within the permissions
  `finance-accounts.account:read|write|delete`.

## Product Purpose

The single list of places where money is held or owed: bank, cash, wallet, payment, credit,
investment and receivable accounts, per owner scope (personal, solo_empire, venture, client,
shared). Every other finance service refers to an account here instead of keeping its own copy.

Success: each real account exists once, other finance services resolve every `account_id` they
store, and closed accounts keep their history.

## Positioning

One capability, one service: its own API (Railway), its own database (Neon) with row-level
security per workspace, and authorization, executions and audit through `empire-platform`. It is
workspace-scoped, so the same service can serve other tenants without code changes.

## Operating Context

- Production: `https://finance-accounts-api-production.up.railway.app` (`/health`), deployed by
  merging to `main` after CI.
- Data starts empty (created 2026-10-12 from the retired `finance_*` tables' fields); imports keep
  old ids in `legacy_id`.
- Monitored by `platform-uptime-worker`; errors go to Sentry without personal data.

## Capabilities and Constraints

- `/v1/accounts`: list (filters `account_type`, `owner_scope`, `status`), stats, get,
  get-by-legacy-id, create (with `Idempotency-Key`), patch (with `expected_version`), delete.
- Rules: `name` is unique within an `owner_scope` and at most 200 characters; `account_type` and
  `status` are fixed enums; `currency` defaults to THB; `metadata` is a JSON object; `closed_on`
  cannot be before `opened_on` (422 `invalid_value`).
- Deleting an account other records still point at is the caller's responsibility to check in the
  other finance services (cross-service ids are not foreign keys).
- Out of scope: balances over time (computed from `finance-transactions-api`), bank connections
  and payments.

## Measures

- Accounts with at least one transaction in `finance-transactions-api` in the last 90 days.
- Unresolved `account_id` references reported by other finance services (target: 0).
- 5xx rate and p95 latency on `/v1/accounts` (Sentry and uptime worker).
