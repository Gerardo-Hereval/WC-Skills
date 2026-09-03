---
name: audit-konfio-libraries
description: >-
  Chat-only inventory of @konfio/* and @kui/design-system imports in
  konfio-app-web apps/<app> (or the whole monorepo). Use before or after an NDS
  migration, when asked which legacy Konfio libraries an app still uses, or for
  a per-component import count of @konfio/base|components|forms|icons.
---

# Inventory — `@konfio/*` + `@kui/design-system` imports

Read-only audit of one deployable under `konfio-app-web/apps/<app>`, or of the whole monorepo.

**Output is chat only.** Do not write report files, do not edit code, do not migrate anything.

**Scope:**

| Package                  | Role     |
| ------------------------ | -------- |
| `@konfio/base`           | legacy   |
| `@konfio/components`     | legacy   |
| `@konfio/forms`          | legacy   |
| `@konfio/icons`          | peer     |
| `@konfio/design-tokens`  | tokens (CSS only) |
| `@konfio/design-system`  | published NDS |
| `@konfio/kamila-chatbot` | widget   |
| `@kui/design-system`     | workspace design system |

**Out of scope:** remediation. Migrating `@kui/design-system` → `@konfio/design-system` belongs to
[`migrate-konfio-design-system`](../migrate-konfio-design-system/SKILL.md). Only propose changes if
the user explicitly asks after seeing the inventory.

---

## Procedure

1. **Resolve target.** One app (`apps/<app>`) or the monorepo. If ambiguous, ask.
2. **Read declared versions.** `apps/<app>/package.json` + catalog pins in `pnpm-workspace.yaml`.
   A dependency declared but never imported is worth a line only if the user asks.
3. **Count imports.** Run the grep cheatsheet in [reference.md](reference.md#grep-cheatsheet).
   Always pass `--glob '!**/node_modules/**'`. One import statement = one count.
4. **Normalize paths to component keys** using the table in
   [reference.md](reference.md#import-path-normalization) — `@konfio/base/ui/atoms/button/button`
   and `@konfio/base/button` are both `button`.
5. **Check CSS separately.** `@konfio/design-tokens` and `@source` wiring live in `globals.css`,
   not in TS imports — report as CSS lines, never as import counts.
6. **Report** using the shape in [report-template.md](report-template.md): summary table first,
   then a per-library component table, legacy total last.

## Rules

- Count production and test files, but flag test mocks (`jest.mock(...)`) separately when they
  distort the total.
- Do not include full call-site lists, declared-but-unused deps, or overlap file names by default —
  those are expansions, only on request (see report-template.md).
- Never guess a version: read it from `package.json` / `pnpm-workspace.yaml` or print `—`.
- Report zero honestly. "No legacy imports" is a valid, useful answer.

## Trigger phrases

| User says                                  | Action                          |
| ------------------------------------------ | ------------------------------- |
| `audita las librerías de apps/cards`       | Single-app inventory            |
| `qué apps siguen usando @konfio/base`      | Monorepo table                  |
| `inventario NDS de profile`                | Single app, highlight `@kui/` + `@konfio/design-system` rows |
| `cuántos imports de @konfio/components`    | Single library detail table     |

## Additional resources

- [reference.md](reference.md) — package roles, path normalization, grep cheatsheet
- [report-template.md](report-template.md) — exact output shapes
- `migrate-konfio-design-system` — execution of the kui → konfio migration
