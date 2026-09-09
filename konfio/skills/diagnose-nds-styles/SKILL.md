---
name: diagnose-nds-styles
description: >-
  Use when a component imported from @konfio/design-system renders wrong in a
  konfio-app-web app: transparent background, missing border, black text,
  unstyled drawer/modal/popover, or a color that differs from Figma. Also use
  before adding bg-white/bg-gray-0 to an SDK component, before bumping the
  @konfio/design-system version to "fix" a visual bug, or when someone asks
  whether the SDK needs a token sync. Triggers: "se ve transparente", "sin
  fondo", "le falta un token", "hay que sincronizar el SDK", "bg-background no
  pinta", "después de migrar al NDS se ve mal".
---

# Diagnose `@konfio/design-system` styles

Visual bugs after the NDS migration are almost never in the component and almost never in the SDK. They live in the CSS wiring of the app: version, `@source`, `@theme`, token aliases. Find the broken layer first; the fix is usually a few lines in `globals.css`.

Scope: apps whose `package.json` lists `@konfio/design-system`. Apps still on the workspace `@kui/design-system` (`main`, `on-boarding`) keep their own token wiring and are out of scope.

**Never do as a first move:** add `bg-white`/`bg-gray-0`/`className` overrides to an SDK component, bump the catalog, add the missing token to the app `@theme`, or edit `packages/design-system` (that is the legacy `@kui` package, apps migrated to the SDK never see it).

## Layers, in order — stop at the first one that fails

| # | Layer | Command | Healthy |
| - | ----- | ------- | ------- |
| 1 | Installed version | `readlink -f apps/<app>/node_modules/@konfio/design-system` and `grep '"@konfio/design-system"' apps/<app>/package.json` | Version matches what you assumed. `catalog:` follows `pnpm-workspace.yaml`; a hard pin (cards, payments) does **not** receive catalog bumps |
| 2 | Utility the SDK emits | `grep -n "className\|cva(" <installed>/dist/ui/<level>/<component>.js` | You know the exact class: `bg-background`, `bg-popover`, `border-border`, `text-muted-foreground`… |
| 3 | Utility generated | `grep -n '@source' apps/<app>/app/globals.css`; `grep -c '\.bg-background' apps/<app>/.next/dev/static/chunks/*globals*.css` | `@source "../node_modules/@konfio/design-system/dist/"` present and the rule exists in compiled CSS |
| 4 | Token resolution | `grep -nE -- '--color-[a-z-]+: var\(--[a-z-]+\)' apps/<app>/app/globals.css` | **Zero matches.** Since SDK 1.11.0 `theme.css` owns `--color-<role>` and `shadcn/tokens.css` aliases `--<role>: var(--color-<role>)`. An app `@theme` with `--color-background: var(--background)` closes a cycle and the browser invalidates both |
| 5 | Browser proof | see [reference.md](reference.md) | Computed `--color-<role>` on `:root` is a color, not empty; a probe `div.bg-<role>` paints |

Layer 4 is the migration-era classic: valid on SDK ≤ 1.10 (the alias pointed the other way), it silently breaks every shadcn role at once (`bg-primary`, `border-border`, `text-destructive`…), not only the one you were asked about.

## Fix by layer

| Broken layer | Fix |
| ------------ | --- |
| 1 | Change the pin or the catalog on purpose, with the owning team's OK; verify with `readlink` again |
| 3 | Add the `@source` line; keep the `@import '@konfio/design-system/styles.css'` |
| 4 | Delete the whole "shadcn semantic tokens" alias block from the app `@theme`. Keep brand/app tokens (`--color-co-*`, `--color-primary-600`, gradients, shadows). Reference app: `apps/cards/app/globals.css` |
| Token really missing in SDK `theme.css` | That is the only case for a SDK change: changeset in `konfio-web-sdk`, then bump. Confirm first with `grep -- '--color-<role>' <installed>/src/styles/tokens/theme.css` |

After fixing, remove the symptom patches the bug left behind (`className="bg-gray-0"` on SDK components, `bg-white` wrappers) and sweep the siblings: `grep -l -- '--color-background: var(--background)' apps/*/app/globals.css` lists every app with the same wiring.

## Report

1. Root cause in one sentence, naming the layer.
2. Evidence: the command output that proves it, not the reasoning.
3. Fix: file and exact lines.
4. SDK verdict: bump / sync / token — and why not.
5. Other apps sharing the wiring, from the grep, marked verified or unverified.

## Common mistakes

- Reading only the SDK `theme.css` to judge a token: the app `@theme` is appended after it and wins. Look at the compiled CSS or the computed value.
- Diffing the SDK against the monorepo to "sync" when layer 4 already explained it.
- Bumping the catalog and declaring victory: cards and payments pin by hand and never receive it.
- Proving it by eye in a screenshot. `rgba(0, 0, 0, 0)` on the probe is the proof; the screenshot is the symptom.
