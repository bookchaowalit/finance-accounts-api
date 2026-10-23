# CD pilot: verify Railway's deploy after CI passes (finance-accounts-api)

Owner decision D3 (2026-10-23, ADR-0003) and its addendum A1: deploys start from Git after CI
passes, end with a post-deploy smoke test, and never come from a working tree. On 2026-10-23 the
owner chose **verify mode**: Railway keeps deploying by itself, CI checks the result. This cell is
the only pilot (platform-ci-workflows `deploy-railway.yml` v1.3.0, `761fd15`, `mode: verify`).

## How it works

1. A push to `main` runs CI (`api` + `security`).
2. Railway's branch trigger (`main`, "Wait for CI") deploys the commit by itself, as it has since
   2026-10-18. **No Railway setting changes.**
3. When CI is green, the `deploy` job in `.github/workflows/ci.yml` (read-only):
   - skips if `main` has already moved on (the newer commit's run checks that one);
   - records the last good deployment of another commit (the rollback target);
   - waits up to 15 minutes for Railway's deployment whose `meta.commitHash` is this commit; none
     → fails ("is the trigger on / Wait for CI stuck?");
   - waits for `SUCCESS` (or `SLEEPING`: the service sleeps when idle); `FAILED`/`CRASHED` or a
     timeout fails; `SKIPPED`/`REMOVED` (Railway replaced it with a newer commit) is a skip;
   - smoke test: `/health` must answer 2xx with `"status":"ok"` and `"commit"` = this commit
     (retried, so a sleeping service can wake);
   - on any failure: an `::error` annotation and the job summary give
     `railway api 'mutation { deploymentRollback(id: "<last good id>") }'`.

The job never deploys and never changes anything on Railway; the token is used for read queries only.

## State (2026-10-23)

| Item | Value |
|---|---|
| Railway project / environment / service | `f4781a08-96ca-4965-b12f-09aeb8de6aae` / production `6ea4583c-ec3b-4e87-a2c1-d571a38e15b9` / `99890e22-3638-457f-aed0-af23190b28f0` |
| Branch trigger | `bd25e2f0-fe4b-4d73-be8b-e7510f9f02b8`, `main`, `checkSuites: true` — **kept** (the v1.2.0 plan to delete it is dropped) |
| Live | `main`, deployed by the trigger; `/health` reports the commit |
| `deploy` job | in CI, **off**: runs only when the repository variable `CD_DEPLOY` is `true` |

## Owner steps to turn it on

1. **Railway project token** (Railway has no read-only token type; a project token is the smallest
   scope, one environment of one project). Railway dashboard → project `finance-accounts-api` →
   Settings → Tokens → *Create token*, environment **production**, name `github-ci-verify`.
   Store it in Infisical `/railway` as `RAILWAY_TOKEN_FINANCE_ACCOUNTS_API`, then set the GitHub
   repository secret without printing it:

   ```bash
   infisical run --projectId "$INFISICAL_PROJECT_ID" --env dev --path /railway --silent -- \
     bash -c 'printf %s "$RAILWAY_TOKEN_FINANCE_ACCOUNTS_API" | gh secret set RAILWAY_TOKEN -R bookchaowalit/finance-accounts-api'
   ```

2. **Turn the job on and check the current `main`:**

   ```bash
   gh variable set CD_DEPLOY -R bookchaowalit/finance-accounts-api --body true
   gh workflow run CI -R bookchaowalit/finance-accounts-api --ref main
   ```

   The `deploy` job finds Railway's existing deployment of `main`, checks it and smoke-tests it.
   From then on every push to `main` is checked the same way.

Until step 1 is done the job stays off (`CD_DEPLOY` unset), so CI shows `deploy` as skipped.

## If it goes wrong

- **The job fails after a push:** run the rollback command from the job summary, then revert the
  commit on `main` (the revert deploys through the trigger and is checked again).
- **"Railway started no deployment":** the trigger did not fire (for example Wait for CI stuck on
  queued check suites, as from 2026-10-18 to 2026-10-22). Check
  `railway deployment list -p f4781a08-96ca-4965-b12f-09aeb8de6aae -s finance-accounts-api -e production --json`.
- **Turn it off:** `gh variable set CD_DEPLOY -R bookchaowalit/finance-accounts-api --body false`.

## Rollout (not part of the pilot)

After a few clean checks, other Railway services add the same job with their IDs and a project
token each, plus a `commit` field in `/health` if they want the commit check.
