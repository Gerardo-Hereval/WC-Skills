---
name: test-e2e
description: >
  Analyzes source files and writes missing Cypress E2E tests for the profile app flow.
  Accepts an optional path argument (file, directory, or component name) to scope the
  analysis. If no path is given, derives scope from currently changed files (git status).
  If no changed files exist, falls back to the last commit. Outputs a test-coverage matrix
  and a metrics table (execution time, estimated tokens, estimated cost).
  Trigger keywords: test-e2e, e2e tests, missing tests, cypress tests, agregar tests,
  tests faltantes, cobertura e2e, write e2e, generate tests.
---

# E2E Test Generator — profile-e2e

You are an expert in the `konfio-app-web` profile app. Follow every step in order.

---

## Step 0 — Record start time

```bash
START_MS=$(date +%s%3N)
```

Store this value; you will use it at the very end to compute elapsed time.

---

## Step 1 — Determine scope

Parse the skill `args`:

| Condition | Action |
|-----------|--------|
| `args` is a path, directory, or component name | Use it as the analysis target |
| `args` is empty | Run `git status --porcelain` to find changed files |
| No changed files from git status | Run `git diff --name-only HEAD~1..HEAD` to get files from the last commit |

**Rules for resolving a path arg:**
- If it is a relative path, resolve it from the repo root.
- If it is a component name (e.g. `BusinessDataSection`), search for the file:
  ```bash
  find apps/profile/src -iname "*business-data-section*"
  ```
- Always expand to the full set of affected files: the organism/component + any organisms
  it imports from `apps/profile/src/`.

**Filter the file list.** Keep only files under:
- `apps/profile/src/` — source to analyze
- `apps/profile-e2e/` — existing tests to compare against

Ignore lock files, config, generated files, and `packages/design-system/`.

---

## Step 2 — Analyze business rules from source files

Read every source file in scope. For each file extract and document:

1. **API endpoints called** — method, URL pattern, response shape used.
2. **State / enable conditions** — when is a button enabled/disabled, what flags gate UI.
3. **Navigation rules** — what triggers `router.push/replace`, what route guard logic applies.
4. **Validation rules** — Zod/RHF schema constraints, error messages (exact strings matter).
5. **Error / loading states** — `StepStateBoundary`, toasts, skeletons, error boundaries.
6. **Data-cy attributes already present** — list every `data-cy="..."` in scope.
7. **Missing data-cy attributes** — identify interactive or assertable elements that lack one.

> **Constraint on data-cy**: you may ADD `data-cy` attributes only to files under
> `apps/profile/src/`. Never modify `packages/design-system/`.

---

## Step 3 — Audit existing E2E coverage

Find the relevant existing test and fixture files:

```bash
# Tests
ls apps/profile-e2e/cypress/e2e/

# Fixtures
ls apps/profile-e2e/src/infrastructure/mocks/
```

Read the test files most likely related to the scope (match by step, organism name, or URL).

For each business rule found in Step 2, determine:

| Rule | Covered? | Test file |
|------|----------|-----------|
| … | ✅ / ❌ | … |

Identify every **uncovered** scenario — these are your targets for Step 4.

---

## Step 4 — Write missing tests and fixtures

For each uncovered scenario:

### 4a — Add data-cy attributes (if needed)

Edit the profile app source file to add `data-cy` to the element that needs asserting.
Only touch `apps/profile/src/` files.

### 4b — Create or extend fixture files

Follow the existing fixture shape:

```typescript
export const mockXxx = {
  data: { … },
  requestId: 'mock-xxx',
  time: '2024-01-01T00:00:00.000Z',
};
```

Place new fixtures in `apps/profile-e2e/src/infrastructure/mocks/`.
Add to an existing fixture file when the new data belongs to the same domain;
create a new `<feature>.fixtures.ts` when it does not.

### 4c — Write the test cases

Follow the patterns already established in `apps/profile-e2e/cypress/e2e/`:

- Use `cy.setupProfileIntercepts({ summary, progress }, stepNumber)` for progress + summary.
- Intercept API calls with `cy.intercept(method, pattern, { statusCode, body }).as('alias')`.
- `cy.wait('@alias')` before asserting on data-driven content.
- Assert with `data-cy` selectors first; fall back to `cy.contains()` for text-only assertions.
- Use `cy.location('pathname')` to assert navigation (with a `timeout`).
- Group related scenarios under nested `describe` blocks.
- Keep each `it` block focused on a single business rule.

Prefer extending an existing `.cy.ts` file when the new scenarios belong to the same
step; create a new file (e.g. `<feature>-additional.cy.ts`) when scope is clearly separate.

#### Progress intercept — required in every spec

**Always** pass `progress` to `cy.setupProfileIntercepts`. Without it the `ProfileFlowContext`
route guard may redirect the browser before the component mounts, causing the test to fail in
CI even when it passes locally (the local dev server's mock API fills the gap; CI does not).

Choose the fixture based on the route under test:

| Route visited | Fixture to use |
|---------------|----------------|
| `/dashboard/perfil/datos-personales` | `mockProgressStep1` |
| `/dashboard/perfil/identificacion` | `mockProgressStep2` |
| `/dashboard/perfil/accionistas` | `mockProgressStep3` |
| `/dashboard/perfil/negocio` or `/negocio/**` | `mockProgressStep4` (from `bank-section.fixtures`) |
| `/dashboard/perfil/documentos` | `mockProgressStep5` |
| `/dashboard/perfil/contrato` | `mockProgressStep6` |
| Any subpath not listed in the step's `allowed` array (e.g. `/org-chart`, `/accionista/:id`, `/configuracion/**`, `/visitas`) | `mockProgressCompleted` |

All fixtures are exported from
`apps/profile-e2e/src/infrastructure/mocks/profile-completion-flow.fixtures.ts`
(except `mockProgressStep4`, which lives in `bank-section.fixtures.ts`).

**Why `mockProgressCompleted` for unlisted subpaths**: the context's route guard only runs
when `progress.complete === false`. Setting `complete: true` prevents any redirect,
making it safe for routes that are not part of the step-by-step flow.

---

## Step 5 — Output the test matrix

Print a markdown table covering **every** business rule found in Step 2:

```markdown
## Test Matrix — <scope>

| Business rule | Scenario | Status | Test file |
|---------------|----------|--------|-----------|
| … | … | ✅ Already covered | … |
| … | … | ✅ Added now | … |
| … | … | ⚠️ Skipped (no data-cy, complex integration) | … |
```

Use **✅ Already covered** for pre-existing tests, **✅ Added now** for tests you just wrote,
and **⚠️ Skipped** with a brief reason when a scenario is too complex to automate reliably
(e.g. iframe interactions, external OAuth flows).

---

## Step 6 — Output the metrics table

Compute elapsed time and output the final metrics. Run this to get the end timestamp:

```bash
END_MS=$(date +%s%3N)
ELAPSED_MS=$((END_MS - START_MS))
ELAPSED_S=$(echo "scale=2; $ELAPSED_MS / 1000" | bc)
echo "Elapsed: ${ELAPSED_S}s"
```

Then estimate tokens and cost:

- **Input tokens** ≈ sum of tokens in files read (rough rule: 1 token ≈ 4 characters of source).
- **Output tokens** ≈ sum of tokens in tests + fixtures + matrix written by this skill.
- **Model**: `claude-sonnet-4-6`
- **Pricing** (Sonnet tier, as of mid-2025):
  - Input: **$3.00 / 1 M tokens**
  - Output: **$15.00 / 1 M tokens**
- **Cost** = `(input_tokens / 1_000_000) × 3 + (output_tokens / 1_000_000) × 15`

Print this table at the very end of your response:

```markdown
## Skill Metrics

| Metric | Value |
|--------|-------|
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

- **Never** modify `packages/design-system/`.
- **Never** add `data-cy` outside `apps/profile/src/`.
- Fixtures must follow the `{ data, requestId, time }` envelope.
- Intercept URL patterns must use `**/` glob prefix to match any hostname.
- Every new `it` block must have a description that names the specific business rule.
- Do not write tests for scenarios that cannot be driven without real external services
  (Incode iframe, MiFiel signing widget).
- If a scenario is already covered, skip it — do not duplicate.
- Output the test matrix and metrics table even if no new tests were written.
