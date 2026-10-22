# cellkit notes

`src/cellkit/` is this service's own framework code. It was first generated from `cell.yaml` by the shared generator (solo-cell-kit, retired 2026-10-12), and it is changed here only. Nothing upstream is synced; other cells keep their own copies (owner decision 2026-10-21).

## Before Wave 2

At `c267efd` this copy was the finance copy: already reported a failed inline publish to Sentry; nosemgrep/noqa comments in the finance wording. In a comparison of all 24 cell copies (AST, comments and formatting ignored) there were only two behaviours: with or without Sentry `capture` on a failed inline publish.

## Changed in Wave 2 (2026-10-22)

- Strict typing (mypy strict on `cellkit.*` except the contract suite) and Ruff fixes; no behaviour change.
- `ranges` resource key: a write that leaves `[start, end]` both set must keep start <= end (422 `invalid_value`); only a patch that changes one of them is checked. No schema change.
- Integers are bounded to their column (`int` = 32-bit, `bigint`/`ref` = 64-bit) and real fields refuse NaN/Infinity: 422 instead of a 500 or a silent NULL. The 422 handler makes such inputs JSON-safe.
- A failed inline publish is passed to Sentry `capture()` as well as logged.
- Contract tests for each of these (`src/cellkit/contract.py`).

Commits touching `src/cellkit/` or `cell.yaml`:

- `cbc06f1 fix: refuse integers past their column and NaN/Infinity reals with 422`
- `1bd0740 test: integers past their column and non-finite reals must be refused with 422 (red)`
- `ecc8da2 fix: check a range only when the patch changes it; spec in review`
- `fe5ddc9 fix: refuse an account that closes before it opens; strict mypy on src, wider Ruff`
- `b67f82e chore: L2 baseline — locked deps, mypy, domain tests, PRODUCT.md, CI v1.1.1`

## Fixes per need of this cell

| Fix | Does this cell need it? | Evidence |
|---|---|---|
| Inline publish failure → Sentry | no: no resource has graph events, so the inline publisher never runs. The line is in the copy but inert. | — |
| `ranges` rule | yes: `account` opened_on..closed_on | 3ec0292 · `.venv/bin/pytest -q tests/test_account_validation.py` · `assert 201 == 422` |
| Column limits / finite reals | yes: `account.opening_balance` | 1bd0740 · `.venv/bin/pytest -q -k numbers_fit` · `AssertionError: ('opening_balance', 'NaN', ...)` (201, stored as null) |
| `/health` names the running commit (`RAILWAY_GIT_COMMIT_SHA`) | yes: this cell is the CD pilot; the post-deploy smoke test compares it ([runbook](runbooks/cd-pilot.md)). Other cells add it when they move to CD | `tests/test_health.py` (red first, 2026-10-23) |

## Deliberately not applied

- No other fix was skipped: no cell copy had a fix this one lacks after Wave 2, and there were no domain-specific differences to keep (the other differences were comments and formatting).

Change this code here, with a failing test first (ADR-0004). Records: `specs/` (SPEC-001 red/green log).
