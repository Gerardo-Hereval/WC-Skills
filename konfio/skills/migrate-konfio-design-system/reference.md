# Reference — `@kui/design-system` → `@konfio/design-system`

Supporting material for [SKILL.md](SKILL.md). Read on demand per stage.

## Package roles

| Package | Location | Role |
| ------- | -------- | ---- |
| `@kui/design-system` | `packages/design-system` | Workspace source — apps import today |
| `@konfio/design-system` | GitLab npm (`pnpm-workspace.yaml` catalog) | Published target — e.g. `1.5.0` |

Supporting (not migration targets):

| Package | Role during rollout |
| ------- | ------------------- |
| `@konfio/design-tokens` | Safelist + Gilroy — keep until legacy MUI UI gone |
| `@konfio/icons` | Peer; verify version if target components embed icons |

---

## Import path map

### CSS

| Source | Target |
| ------ | ------ |
| `@kui/design-system/css` | `@konfio/design-system/styles.css` |
| Relative `packages/design-system/css/index.css` | `@konfio/design-system/styles.css` |
| `@source …/packages/design-system/src/` | `@source …/node_modules/@konfio/design-system/dist/` |

### Components & utils

| Source | Target |
| ------ | ------ |
| `@kui/design-system/atoms/<name>` | `@konfio/design-system/ui/atoms/<name>` |
| `@kui/design-system/molecules/<name>` | `@konfio/design-system/ui/molecules/<name>` |
| `@kui/design-system/organisms/<name>` | `@konfio/design-system/ui/organisms/<name>` |
| `@kui/design-system/organisms` barrel | `@konfio/design-system/ui/organisms/<file>` |
| `@kui/design-system/utils/lib` | `@konfio/design-system/utils/lib` |

### Deprecated konfio paths (avoid)

| Deprecated | Canonical |
| ---------- | --------- |
| `@konfio/design-system/lib/utils` | `@konfio/design-system/utils/lib` |
| `@konfio/design-system/ui/button` | `@konfio/design-system/ui/atoms/button` |

---

## Setup (npm package)

Source: [Installation — npm package](https://www.notion.so/39ebc719d0c081528995edbf17382258)

### Auth

Root `.npmrc` (already in konfio-app-web):

```
@konfio:registry=https://gitlab.com/api/v4/packages/npm/
//gitlab.com/api/v4/projects/69265473/packages/npm/:_authToken=${CI_JOB_TOKEN}
```

### Install

```bash
pnpm add @konfio/design-system --filter @app/<app>
```

Pin via catalog in `pnpm-workspace.yaml` — update semver there first when bumping (e.g. `1.5.0`).

### globals.css stack (MUI-era coexistence)

```css
@import 'tailwindcss';
@import '@konfio/design-tokens/css/config/safelist.css';
@import '@konfio/design-tokens/css/design-system-export.css';
@import '@konfio/design-system/styles.css';

@source "../node_modules/@konfio/design-system/dist/";
@source "../node_modules/@konfio/base/dist/";
@source "../node_modules/@konfio/components/dist/";
```

### Colors 2.0 (Notion)

Consumers use `@import '@konfio/design-system/styles.css'` — no manual token wiring. Avoid new app-level shadcn `:root` / `@theme` overrides that duplicate package semantics.

Prefer in app code: `bg-primary`, `text-muted-foreground`, `bg-purple-600`, `bg-gray-0` (Konfio neutrals). Avoid `--nds-color-*` in new app code.

---

## Exhaustive diff checklist {#exhaustive-diff-checklist}

Use when Stage 2 runs. Fill every row or mark `n/a`.

| # | Dimension | Compare |
| - | --------- | ------- |
| 1 | Presence | Component in kui vs konfio target |
| 2 | Named exports | All public exports match |
| 3 | Props interface | Field names, optionality, types |
| 4 | Variants / sizes | `cva` keys and allowed values |
| 5 | Polymorphism | `href`, `as`, `asChild`, `render` |
| 6 | Subcomponents | Compound API (`DialogHeader`, …) |
| 7 | Events / refs | `onClick`, ref forwarding |
| 8 | CSS tokens | `--nds-*` vs shadcn semantics |
| 9 | Client boundary | `'use client'` placement |

### Classification

| Class | Criteria |
| ----- | -------- |
| `safe` | Path-only rewrite |
| `breaking` | Prop/variant/export mismatch |
| `missing` | Not in `@konfio/design-system` |
| `stay-on-kui` | Defer until web-sdk port |

---

## Grep cheatsheet

```bash
# Remaining kui imports (post-migration should be 0 or blocked list)
rg -n "@kui/design-system" apps/<app> --glob '!**/node_modules/**'

# New konfio-ds imports
rg -n "@konfio/design-system" apps/<app>/src

# CSS traces
rg -n "design-system/css|styles.css|packages/design-system" apps/<app>

# Props for diff (example)
rg -n 'variant="' apps/<app> --glob '*.tsx'
```

### Live target inventory (web-sdk)

```bash
ls konfio-web-sdk/packages/design-system/src/ui/atoms/*.tsx 2>/dev/null | grep -v stories
ls konfio-web-sdk/packages/design-system/src/ui/molecules/*.tsx 2>/dev/null | grep -v stories
ls konfio-web-sdk/packages/design-system/src/ui/organisms/*.tsx 2>/dev/null | grep -v stories
```

---

## Migrated app references (in-repo)

| App | State | Notes |
| --- | ----- | ----- |
| `apps/home` | npm NDS | Button-heavy; `@konfio/design-system/styles.css` |
| `apps/payments` | npm NDS | Business-link flow; removed `@kui/design-system` |

---

## Out of scope — legacy packages

Use `audit-konfio-libraries` for `@konfio/base|components|forms` inventory. Note one-line overlap when same file mixes legacy + NDS.

---

## External docs

- [Installation — npm package](https://www.notion.so/39ebc719d0c081528995edbf17382258)
- web-sdk: `packages/design-system/docs/migration-from-kui.md`
- web-sdk: `packages/design-system/docs/atom-migration-inventory.md`
