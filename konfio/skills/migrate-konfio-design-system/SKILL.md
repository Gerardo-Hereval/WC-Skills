---
name: migrate-konfio-design-system
description: >-
  Resumable migration of apps/<app> from @kui/design-system to published
  @konfio/design-system: install npm package, update globals.css, rewrite
  imports, optional API diff. Use when migrating NDS, replacing
  @kui/design-system imports, or continuing an apps/* design-system migration.
---

# Migrate `@kui/design-system` → `@konfio/design-system`

Agent-guided, **resumable** migration for one deployable under `konfio-app-web/apps/<app>`.

**Primary goal:** replace workspace `@kui/design-system` with published `@konfio/design-system` (npm catalog pin), including package install, CSS setup, and import rewrites.

**In scope:** `@kui/design-system` ↔ `@konfio/design-system` only (components, utils, hooks, CSS).

**Out of scope (use `audit-konfio-libraries`):**

- Full legacy `@konfio/base|components|forms` audit — one-line overlap note only
- Removing `@kui/design-system` from the monorepo package
- Migrating apps other than the named target

**Repos:**

| Repo | Role |
| ---- | ---- |
| `konfio-app-web` | Consumer apps + workspace `@kui/design-system` at `packages/design-system` |
| `konfio-web-sdk` | Published `@konfio/design-system` — API source of truth for diffs |

**Canonical docs:**

- Notion: [Installation — npm package](https://www.notion.so/39ebc719d0c081528995edbf17382258)
- In-repo reference: [apps/home](apps/home/package.json) (migrated consumer)
- [reference.md](reference.md) — path map, setup, diff checklist
- [report-template.md](report-template.md) — stage artifacts

---

## Execution modes

| User intent | Stages to run |
| ----------- | ------------- |
| `inventory only` | 0 → 1 |
| `plan only` / `diff only` | 0 → 1 → 2 → 3 (no code changes) |
| `setup only` | 0 → 4 |
| `migrate imports` / `implement migration` | 0 → 1 → 4 → 5 → 6 |
| `full migration` | 0 → 1 → 2 → 3 → 4 → 5 → 6 |

Default for **"migrate app X to konfio/design-system"** with no qualifier: run **0 → 1 → 4 → 5 → 6** (skip exhaustive diff unless types fail or user asks).

---

## Progress file (resume contract)

```
apps/<app>/.nds-migration/progress.md
```

On every turn: read `progress.md`, skip completed stages, continue from first incomplete.

```markdown
# NDS migration — apps/<app>

Started: <ISO date>
Last stage: <n>
Status: in_progress | blocked | done
Catalog: @konfio/design-system <version>

## Checklist

- [ ] 0. Scope & preflight
- [ ] 1. Inventory `@kui/design-system`
- [ ] 2. Component diff (optional)
- [ ] 3. Migration plan (optional)
- [ ] 4. Setup npm + CSS
- [ ] 5. Import rewrites + remove `@kui/design-system` dep
- [ ] 6. Verify
```

---

## Stage 0 — Scope & preflight

1. Resolve `apps/<app>`; read `package.json` for `@kui/design-system` and `@konfio/design-system`.
2. Read catalog version: `pnpm-workspace.yaml` → `@konfio/design-system` (use latest pinned semver, e.g. `1.5.0`).
3. Confirm root [`.npmrc`](.npmrc) has `@konfio` GitLab registry + `CI_JOB_TOKEN`.
4. Locate `app/globals.css`; confirm `moduleResolution: "Bundler"` via `@kui/config-typescript/nextjs.json`.
5. Note reference app: `apps/home` or `apps/payments` if already migrated.

---

## Stage 1 — Inventory `@kui/design-system`

Run audit commands from `audit-konfio-libraries` for kui section only, plus:

```bash
rg -n "@kui/design-system" apps/<app> --glob '!**/node_modules/**'
rg -n "packages/design-system" apps/<app> --glob '*.css'
```

Produce:

- File list (production + test mocks)
- Per-component import counts
- CSS wiring (relative path vs `@kui/design-system/css`)
- Import style: deep path vs barrel

Write `apps/<app>/.nds-migration/stage-1-kui-inventory.md` when doing plan/full modes.

---

## Stage 2 — Component diff (optional)

Required when user asks for plan/diff, or when Stage 5 typecheck reveals API mismatches.

Compare each used component:

- **Source:** `konfio-app-web/packages/design-system/src/ui/{atoms,molecules,organisms}/`
- **Target:** `konfio-web-sdk/packages/design-system/src/ui/{atoms,molecules,organisms}/`

Use checklist in [reference.md](reference.md#exhaustive-diff-checklist). Classify: `safe` | `breaking` | `missing` | `stay-on-kui`.

If web-sdk repo is unavailable, mark Stage 2 **BLOCKED** and proceed with path-only rewrites; flag risk in chat.

---

## Stage 3 — Migration plan (optional)

Prioritized plan from Stage 1 (+ Stage 2 if run):

1. Setup (Stage 4)
2. Safe path rewrites (see map below)
3. Breaking call-site fixes with variant/prop tables
4. Blocked components staying on kui
5. CSS migration steps

Stop here unless user asks to implement.

---

## Stage 4 — Setup `@konfio/design-system`

Follow [Notion install guide](https://www.notion.so/39ebc719d0c081528995edbf17382258).

### 1. Install (catalog pin — never `workspace:*`)

```bash
export CI_JOB_TOKEN="glpat-..."  # if not already set
pnpm add @konfio/design-system --filter @app/<app>
```

Expected in `apps/<app>/package.json`:

```json
"@konfio/design-system": "catalog:"
```

### 2. Update `globals.css`

**Replace** workspace kui wiring:

| Remove | Add |
| ------ | --- |
| `@import '../../../packages/design-system/css/index.css'` | `@import '@konfio/design-system/styles.css'` |
| `@source "../../../packages/design-system/src/"` | `@source "../node_modules/@konfio/design-system/dist/"` |

**Keep** during legacy coexistence (home/showcase still on `@konfio/base|components`):

```css
@import '@konfio/design-tokens/css/config/safelist.css';
@import '@konfio/design-tokens/css/design-system-export.css';
@source "../node_modules/@konfio/base/dist/";
@source "../node_modules/@konfio/components/dist/";
```

Do **not** delete app-specific `@theme` brand tokens in this pass — smoke-test visually after migration.

### 3. TypeScript

Ensure `"moduleResolution": "Bundler"` (inherited from shared config is fine).

### 4. Smoke import

```typescript
import { Button } from '@konfio/design-system/ui/atoms/button';
```

---

## Stage 5 — Import rewrites

### Path map (default — path-only migration)

| `@kui/design-system` | `@konfio/design-system` |
| -------------------- | ----------------------- |
| `atoms/<name>` | `ui/atoms/<name>` |
| `atoms/icons/<name>` | `ui/atoms/icons/<name>` |
| `molecules/<name>` | `ui/molecules/<name>` |
| `organisms/<name>` | `ui/organisms/<name>` |
| `organisms` barrel | `ui/organisms/<file>` direct path |
| `utils/lib` | `utils/lib` |
| `utils/format-currency` | `utils/format-currency` |
| `hooks/*` | `hooks/*` (when published) |

**Rules:**

- Prefer direct paths over barrels (`ui/atoms/button`, not `ui/atoms`).
- Update `jest.mock('…')` paths in test files to match production imports.
- Apply breaking fixes from Stage 2/3 when present — do not guess prop mappings.
- Leave **blocked** components on `@kui/design-system` until ported to web-sdk.

### Remove workspace dependency

After all imports + mocks updated:

1. Remove `"@kui/design-system": "workspace:*"` from `apps/<app>/package.json`.
2. Run `pnpm install` at repo root.

Confirm:

```bash
rg "@kui/design-system" apps/<app>
# expect zero matches
```

---

## Stage 6 — Verify

```bash
pnpm --filter @app/<app> check-types
pnpm --filter @app/<app> lint
pnpm --filter @app/<app> test:unit
```

Fix import sort with `lint:fix` if needed. Manual smoke: business-critical flows using NDS components.

Update `progress.md` → `Status: done`.

---

## Trigger phrases

| User says | Action |
| --------- | ------ |
| `migrate apps/payments` | Start/resume full migration |
| `setup only payments NDS` | Stages 0 + 4 |
| `rewrite imports profile` | Stage 5 (after setup) |
| `resume stage 2` | Jump to component diff |

---

## Do not

- Use `workspace:*` for `@konfio/design-system`
- Skip CSS/`@source` setup and only change TS imports
- Delete `packages/design-system` from monorepo
- Treat `@konfio/base|components` as the NDS migration target
- Commit/push unless asked

---

## Additional resources

- [reference.md](reference.md)
- [report-template.md](report-template.md)
- `audit-konfio-libraries` — pre/post migration inventory
