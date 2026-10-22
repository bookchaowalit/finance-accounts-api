# CD pilot: deploy from CI after it passes (finance-accounts-api)

Owner decision D3 (2026-10-23, ADR-0003): deploys start from Git after CI passes, end with a
post-deploy smoke test, and never come from a working tree. This cell is the only pilot
(platform-ci-workflows `deploy-railway.yml` v1.2.0, `77c996e`). Nothing else moves until the
pilot has deployed cleanly.

## Why

The Railway service deploys from GitHub `main` with "Wait for CI" (`checkSuites: true`). Railway
waits for **every** check suite on the commit, and ten GitHub apps installed on the account
(Vercel, Render, Smithery, GitGuardian, …) leave theirs `queued` forever, so no push has deployed
since 2026-10-18: production runs `c267efd`, `main` is 8 commits ahead (2026-10-23).

With CD in GitHub Actions, the `deploy` job in `.github/workflows/ci.yml` runs only after the `api`
and `security` jobs pass on `main`, asks Railway to build exactly that commit from the GitHub source
(`serviceInstanceDeployV2(commitSha)`), waits for `SUCCESS`, checks the deployment's commit, then
calls `/health` and requires `"status":"ok"` and `"commit"` = the SHA. On any failure the job goes
red with the rollback command for the last good deployment.

## Current state (read-only check, 2026-10-23)

| Item | Value |
|---|---|
| Railway project / environment / service | `f4781a08-96ca-4965-b12f-09aeb8de6aae` / production `6ea4583c-ec3b-4e87-a2c1-d571a38e15b9` / `99890e22-3638-457f-aed0-af23190b28f0` |
| Source | GitHub `bookchaowalit/finance-accounts-api` |
| Branch trigger (the auto-deploy) | `bd25e2f0-fe4b-4d73-be8b-e7510f9f02b8`: branch `main`, `checkSuites: true` |
| Live deployment | `026b7b4f-6bec-4fa6-b37d-d7bb1ac1ec36`, `SUCCESS`, commit `c267efd` (2026-10-18) |
| Health | `https://finance-accounts-api-production.up.railway.app/health` → 200 |
| `deploy` job | in CI, off: runs only when the repository variable `CD_DEPLOY` is `true` |

`railway config plan` showed that the IaC cannot remove a branch trigger (dropping `branch` from
`.railway/railway.ts` leaves it in place, and dropping `checkSuites` alone would make Railway deploy
every push **without** waiting for CI). So the change is one API call, plus an IaC edit so that a
later `railway config apply` does not put the trigger back.

## What ships on the first deploy

`main` is ahead of production by these commits (all CI-green; two are bug fixes with tests):
`b67f82e` L2 baseline (locked deps, mypy, domain tests), `3d32b83` `--no-dev` image, `3ec0292`/`fe5ddc9`
refuse an account that closes before it opens, `ecc8da2` range check only when the patch changes it,
`1bd0740`/`cbc06f1` refuse out-of-range integers and NaN/Infinity with 422, `89e1714` docs, and the
`/health` commit field plus this runbook.

## Steps (after the owner's OK)

1. **Railway project token (owner).** Railway → project `finance-accounts-api` → Settings → Tokens →
   new token for environment `production`. Store it in Infisical `/railway` as
   `RAILWAY_TOKEN_FINANCE_ACCOUNTS_API`, then set the repository secret without printing it:

   ```bash
   infisical run --projectId "$INFISICAL_PROJECT_ID" --env dev --path /railway --silent -- \
     bash -c 'printf %s "$RAILWAY_TOKEN_FINANCE_ACCOUNTS_API" | gh secret set RAILWAY_TOKEN -R bookchaowalit/finance-accounts-api'
   ```

2. **Turn Railway's auto-deploy off (the production config change).** Delete the branch trigger;
   the GitHub source stays:

   ```bash
   railway api 'mutation { deploymentTriggerDelete(id: "bd25e2f0-fe4b-4d73-be8b-e7510f9f02b8") }'
   railway api 'query { deploymentTriggers(projectId: "f4781a08-96ca-4965-b12f-09aeb8de6aae", environmentId: "6ea4583c-ec3b-4e87-a2c1-d571a38e15b9", serviceId: "99890e22-3638-457f-aed0-af23190b28f0") { edges { node { id } } } serviceInstance(serviceId: "99890e22-3638-457f-aed0-af23190b28f0", environmentId: "6ea4583c-ec3b-4e87-a2c1-d571a38e15b9") { source { repo } } }'
   ```

   Expect no triggers and `source.repo = bookchaowalit/finance-accounts-api`. Nothing is deployed by
   this step; production keeps running `c267efd`.

3. **IaC (same day, commit on `main`).** In `.railway/railway.ts` remove `branch: "main",` and
   `checkSuites: true,` from the `github` source and change the comment to "Railway builds from this
   repo, but deploys only when CI's deploy job asks (CD pilot, 2026-10-23); no branch trigger." Then
   `railway config plan` must show only `source.checkSuites (true → null)` and nothing else;
   do not run `railway config apply` before step 2.

4. **Turn the job on and deploy `main`:**

   ```bash
   gh variable set CD_DEPLOY -R bookchaowalit/finance-accounts-api --body true
   gh workflow run CI -R bookchaowalit/finance-accounts-api --ref main
   ```

5. **Verify.** The run's `deploy` job is green and its summary names the deployment; then

   ```bash
   curl -s https://finance-accounts-api-production.up.railway.app/health   # "commit" = main HEAD
   railway deployment list -p f4781a08-96ca-4965-b12f-09aeb8de6aae -s finance-accounts-api -e production --json | head
   ```

   and the uptime monitor stays green. Every later push to `main` deploys by itself after CI.

## If it goes wrong

- **The deploy job fails:** follow the rollback command in the job summary
  (`railway api 'mutation { deploymentRollback(id: "<last good id>") }'`), then revert the commit on
  `main`. With the trigger removed nothing else deploys meanwhile.
- **`serviceInstanceDeployV2` is refused without a trigger** (not seen yet; the first run proves it):
  put the trigger back and switch the job off, which restores today's state exactly:

  ```bash
  gh variable set CD_DEPLOY -R bookchaowalit/finance-accounts-api --body false
  railway api 'mutation { deploymentTriggerCreate(input: { projectId: "f4781a08-96ca-4965-b12f-09aeb8de6aae", environmentId: "6ea4583c-ec3b-4e87-a2c1-d571a38e15b9", serviceId: "99890e22-3638-457f-aed0-af23190b28f0", provider: "github", repository: "bookchaowalit/finance-accounts-api", branch: "main", checkSuites: true }) { id } }'
  git revert <the IaC commit>
  ```

## Rollout (not part of the pilot)

After one clean deploy and one clean ordinary push, the same three changes (trigger, IaC, `deploy`
job + secret) apply per service, after a drift check of what each `main` would ship.
