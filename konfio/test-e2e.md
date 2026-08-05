---
name: test-e2e
description: >
  Analyzes source files and writes missing Cypress E2E tests for ANY app in the
  konfio-app-web monorepo (profile, cards, funnel, payments, home, on-boarding,
  bank-account, referrals, main, …). Detects the target app from the path/component,
  discovers that app's own e2e conventions (custom commands, fixture location, required
  session/progress setup), and mirrors them. Accepts an optional path argument (file,
  directory, or component name) to scope the analysis. If no path is given, derives scope
  from currently changed files (git status). If no changed files exist, falls back to the
  last commit. Outputs a test-coverage matrix and a metrics table.
  Trigger keywords: test-e2e, e2e tests, missing tests, cypress tests, agregar tests,
  tests faltantes, cobertura e2e, write e2e, generate tests.
---

# E2E Test Generator — konfio-app-web (multi-app)

You are an expert in the `konfio-app-web` monorepo. Every app under `apps/<app>/` has a
sibling e2e project at `apps/<app>-e2e/`. This skill works for **any** of them. Do not assume
the `profile` app — **detect** the target app and **discover** its conventions before writing.

Follow every step in order.

---

## Step 0 — Record start time

Capture a millisecond timestamp. **Do not use `date +%s%3N`** — `%N` is a GNU extension and
prints a literal `N` on macOS/BSD `date`, producing a garbage value. Use a portable source:

```bash
# Portable across macOS (BSD) and Linux (GNU)
START_MS=$(python3 -c 'import time; print(int(time.time()*1000))' 2>/dev/null \
  || perl -MTime::HiRes=time -e 'printf("%d", time()*1000)' 2>/dev/null \
  || echo $(( $(date +%s) * 1000 )))
echo "START_MS=$START_MS"
```

Store this value; you will use it at the very end to compute elapsed time. If it is empty or
non-numeric, skip the timing metric rather than reporting a wrong number.

---

## Step 1 — Determine scope and detect the target app

Parse the skill `args`:

| Condition | Action |
|-----------|--------|
| `args` is a path, directory, or component name | Use it as the analysis target |
| `args` is empty | Run `git status --porcelain` to find changed files |
| No changed files from git status | Run `git diff --name-only HEAD~1..HEAD` to get files from the last commit |

**Rules for resolving a path arg:**
- If it is a relative path, resolve it from the repo root.
- If it is a component name (e.g. `BusinessDataSection`, `CardBalance`), search across all apps:
  ```bash
  find apps/*/src -iname "*business-data-section*" -not -path "*/node_modules/*"
  ```
- Always expand to the full set of affected files: the organism/component + any organisms
  it imports from the **same app's** `src/`.

**Detect the target app.** From any resolved source path `apps/<app>/...` (or `apps/<app>-e2e/...`),
extract `<app>`. This is the app under test for the rest of the run. Define:

```bash
APP=<app>                      # e.g. profile, cards, funnel, payments, home, on-boarding
SRC_DIR=apps/$APP/src          # source to analyze
E2E_DIR=apps/$APP-e2e          # the e2e project
```

- If the changed files span **multiple apps**, pick the app with the most files in scope and
  state which app you chose; offer to re-run for the others. Never mix two apps in one run.
- If `apps/$APP-e2e` does not exist, stop and report it — there is no e2e project to extend.

**Filter the file list.** Keep only files under `apps/$APP/src/` (source to analyze) and
`apps/$APP-e2e/` (existing tests/fixtures to compare against). Ignore lock files, config,
generated files, `.next/`, and `packages/`.

---

## Step 1b — Discover the app's e2e conventions (do NOT hardcode)

Conventions differ per app (custom commands, fixture folder, required global setup). Discover
them from the app's own e2e project **before** writing anything.

1. **Specs directory & style** — list and skim existing specs to learn the local patterns:
   ```bash
   ls $E2E_DIR/cypress/e2e/
   ```
   Read 2–3 specs closest to your scope (match by component name, route, or feature).

2. **Custom Cypress commands** — these are the app's required setup primitives:
   ```bash
   cat $E2E_DIR/cypress/support/commands.ts
   ```
   Note every `Cypress.Commands.add('...')`. Examples of real per-app helpers:
   - `profile`: `cy.setupProfileIntercepts({ summary, progress }, step)`
   - `funnel`: `cy.setupApiInterceptors(scenario)`, `cy.visitCreditPage(...)`, `cy.mockUserInfo(role)`
   - `cards`: `cy.visitCardBalancePage()`, `cy.visitCardsTablePage({ scenario })`, …
   - `home`: `cy.mockLdFlag(flagKey, enabled)`
   - `on-boarding`: `cy.setupAuth()`, `cy.mockAuth0Session(overrides)`
   Some apps (`bank-account`, `main`, `payments`, `referrals`) expose no custom commands — use
   plain `cy.intercept` / `cy.visit` and follow whatever the existing specs do.

3. **Fixture / mock location** — discover it; it is not the same everywhere:
   - Try `$E2E_DIR/src/infrastructure/mocks/` (most apps).
   - `on-boarding` uses `$E2E_DIR/cypress/support/mocks/` and `.../support/*mock-utils.ts`.
   - When unsure, read an existing spec's imports:
     ```bash
     grep -rhoE "from '[^']*(mock|fixture)[^']*'" $E2E_DIR/cypress/e2e/*.cy.ts | sort -u
     ```
   Place new fixtures wherever that app already keeps them.

4. **Fixture shape** — open one existing fixture and mirror its envelope exactly. It varies:
   `profile` uses `{ data, requestId, time }`; other apps may return the raw body. Do not impose
   profile's envelope on an app that doesn't use it.

5. **Required global setup (gotchas)** — read the `beforeEach` of existing specs and note what
   EVERY spec must set up before visiting, then replicate that baseline in each new spec:
   - `profile`: always pass `progress` to `cy.setupProfileIntercepts` (route guard redirects otherwise).
   - `on-boarding`: auth/session must be mocked (`cy.setupAuth()` / `cy.mockAuth0Session`).
   - `home`: LaunchDarkly flags via `cy.mockLdFlag(...)`.
   - `funnel`/`cards`: a scenario is selected (often via a cookie the visit command sets).
   If a spec skips the app's required setup, it will pass locally (dev mock server fills the gap)
   and fail in CI. Always include it.

Write down (for use in Steps 3–4): specs dir, fixtures dir, the setup command(s) to call, the
fixture envelope, and the app's base route(s).

### Profile-specific reference (only when `APP == profile`)

Progress fixture by route (from `apps/profile-e2e/src/infrastructure/mocks/profile-completion-flow.fixtures.ts`,
except `mockProgressStep4` which is in `bank-section.fixtures.ts`):

| Route visited | Fixture |
|---------------|---------|
| `/dashboard/perfil/datos-personales` | `mockProgressStep1` |
| `/dashboard/perfil/identificacion` | `mockProgressStep2` |
| `/dashboard/perfil/accionistas` | `mockProgressStep3` |
| `/dashboard/perfil/negocio` or `/negocio/**` | `mockProgressStep4` |
| `/dashboard/perfil/documentos` | `mockProgressStep5` |
| `/dashboard/perfil/contrato` | `mockProgressStep6` |
| Any subpath not in the step's `allowed` array (`/org-chart`, `/accionista/:id`, `/configuracion/**`, `/visitas`) | `mockProgressCompleted` |

`mockProgressCompleted` sets `complete: true`, which disables the route guard — safe for routes
outside the step-by-step flow.

---

## Step 2 — Analyze business rules from source files

Read every source file in scope (`apps/$APP/src/...`). For each file extract and document:

1. **API endpoints called** — method, URL pattern, response shape used.
2. **State / enable conditions** — when a button is enabled/disabled, what flags gate UI.
3. **Navigation rules** — what triggers `router.push/replace`, what route/guard logic applies.
4. **Validation rules** — Zod/RHF schema constraints, error messages (exact strings matter).
5. **Error / loading states** — error boundaries, toasts, skeletons.
6. **Data-cy attributes already present** — list every `data-cy="..."` in scope.
7. **Missing data-cy attributes** — interactive/assertable elements that lack one.

> **Constraint on data-cy**: you may ADD `data-cy` attributes only to files under
> `apps/$APP/src/`. Never modify `packages/`.

---

## Step 3 — Audit existing E2E coverage

Using the paths discovered in Step 1b, find the relevant existing tests and fixtures (match by
component name, route, or feature). Read them.

For each business rule found in Step 2, determine:

| Rule | Covered? | Test file |
|------|----------|-----------|
| … | ✅ / ❌ | … |

Identify every **uncovered** scenario — these are your targets for Step 4.

---

## Step 4 — Write missing tests and fixtures

For each uncovered scenario:

### 4a — Add data-cy attributes (if needed)

Edit the app source file (`apps/$APP/src/`) to add `data-cy` to the element that needs asserting.
Only touch `apps/$APP/src/`. Never touch `packages/`.

### 4b — Create or extend fixture files

Mirror the app's existing fixture shape (discovered in Step 1b) — do not impose another app's
envelope. Place fixtures in the app's fixture location. Add to an existing fixture file when the
new data belongs to the same domain; create a new `<feature>.fixtures.ts` (or the app's naming
convention) when it does not.

### 4c — Write the test cases

Follow the patterns already established in `$E2E_DIR/cypress/e2e/`:

- Call the app's required setup command(s) discovered in Step 1b in every spec's `beforeEach`
  (e.g. `cy.setupProfileIntercepts(...)`, `cy.setupAuth()`, `cy.mockLdFlag(...)`, a `cy.visit*`
  helper). Do not skip the app's baseline setup.
- Intercept API calls with `cy.intercept(method, pattern, { statusCode, body }).as('alias')`.
- `cy.wait('@alias')` before asserting on data-driven content.
- Assert with `data-cy` selectors first; fall back to `cy.contains()` for text-only assertions.
- Use `cy.location('pathname', { timeout })` to assert navigation.
- Group related scenarios under nested `describe` blocks; keep each `it` focused on one rule.

Prefer extending an existing `.cy.ts` file when the new scenarios belong to the same feature;
create a new file (e.g. `<feature>-additional.cy.ts`) when scope is clearly separate.

---

## Step 5 — Output the test matrix

Print a markdown table covering **every** business rule found in Step 2:

```markdown
## Test Matrix — <app> · <scope>

| Business rule | Scenario | Status | Test file |
|---------------|----------|--------|-----------|
| … | … | ✅ Already covered | … |
| … | … | ✅ Added now | … |
| … | … | ⚠️ Skipped (no data-cy, complex integration) | … |
```

Use **✅ Already covered**, **✅ Added now**, and **⚠️ Skipped** (with a brief reason when a
scenario is too complex to automate reliably — iframes, external OAuth, signing widgets).

---

## Step 6 — Output the metrics table

Compute elapsed time using the **same portable source** as Step 0 (never `date +%s%3N`):

```bash
END_MS=$(python3 -c 'import time; print(int(time.time()*1000))' 2>/dev/null \
  || perl -MTime::HiRes=time -e 'printf("%d", time()*1000)' 2>/dev/null \
  || echo $(( $(date +%s) * 1000 )))
ELAPSED_MS=$((END_MS - START_MS))
ELAPSED_S=$(echo "scale=2; $ELAPSED_MS / 1000" | bc)
echo "Elapsed: ${ELAPSED_S}s"
```

If `START_MS` was never captured (empty/non-numeric), report `Execution time` as `n/a`
instead of a bogus value.

Then estimate tokens and cost:

- **Input tokens** ≈ sum of tokens in files read (rough rule: 1 token ≈ 4 characters of source).
- **Output tokens** ≈ sum of tokens in tests + fixtures + matrix written by this skill.
- **Cost** = `(input_tokens / 1_000_000) × input_price + (output_tokens / 1_000_000) × output_price`,
  using the pricing of the model actually running this skill.

Print this table at the very end of your response:

```markdown
## Skill Metrics

| Metric | Value |
|--------|-------|
| App under test | <app> |
| Execution time | Xs |
| Estimated input tokens | ~N k |
| Estimated output tokens | ~M k |
| Estimated cost | ~$X.XX USD |
| Files analyzed | N |
| New test cases written | N |
| Fixtures created / updated | N |
| data-cy attributes added | N |
```

---

## Constraints (always enforced)

- **Never** modify `packages/` (shared libraries, incl. `design-system`).
- **Never** add `data-cy` outside the app under test's `apps/$APP/src/`.
- One app per run — never mix source or fixtures from two apps.
- Mirror the target app's fixture shape and fixture location; do not impose another app's envelope.
- Always replicate the app's required global setup (auth/session/progress/flags/scenario) in every
  new spec — skipping it passes locally but fails in CI.
- Intercept URL patterns must use a `**/` glob prefix to match any hostname.
- Every new `it` block must have a description that names the specific business rule.
- Do not write tests for scenarios that cannot be driven without real external services
  (Incode iframe, MiFiel signing widget, external OAuth).
- If a scenario is already covered, skip it — do not duplicate.
- Output the test matrix and metrics table even if no new tests were written.
```
