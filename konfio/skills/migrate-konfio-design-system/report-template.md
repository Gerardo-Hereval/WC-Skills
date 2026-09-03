# Report templates — NDS migration

Write artifacts under `apps/<app>/.nds-migration/` when running plan/full modes. Chat summaries stay short.

---

## Stage 0

```markdown
# Stage 0 — Scope

- App: `apps/<app>`
- Package: `@app/<app>`
- `@kui/design-system`: yes/no (version workspace:*)
- `@konfio/design-system`: yes/no (catalog version)
- globals.css: `app/globals.css`
- moduleResolution: Bundler (inherited)
- Reference app: home | payments | none
```

---

## Stage 1 — `stage-1-kui-inventory.md`

```markdown
# Stage 1 — `@kui/design-system` — apps/<app>

## Summary

| Metric | Count |
| ------ | ----: |
| Production files | |
| Test mock files | |
| Import lines | |
| Atoms | |
| Molecules | |
| Organisms | |
| Utils | |

## By component

| Component | Layer | Path style | Files | Imports |
| --------- | ----- | ---------- | ----: | ------: |
| **button** | atom | deep | 2 | 2 |
| DrawerPanel | molecule | deep | 4 | 4 |

## CSS

| Current | Target |
| ------- | ------ |
| `packages/design-system/css/index.css` | `@konfio/design-system/styles.css` |

## Call-site index (optional)

| File | Symbols |
| ---- | ------- |
| … | … |
```

---

## Stage 2 — `stage-2-component-diff.md`

```markdown
# Stage 2 — Component diff — apps/<app>

| Component | In kui | In konfio | Class | Notes |
| --------- | :----: | :-------: | ----- | ----- |
| button | ✓ | ✓ | safe | path only |
| foo | ✓ | ✗ | missing | stay on kui |

## Per-component detail (breaking/missing only)

### `component-name`

- Prop diff: …
- Variant mapping: …
- Affected files: …
```

---

## Stage 3 — `stage-3-migration-plan.md`

```markdown
# Stage 3 — Migration plan — apps/<app>

## Order of work

1. Stage 4 setup
2. Safe rewrites (N components, M files)
3. Breaking rewrites (list)
4. Blocked on kui (list)
5. Verify

## Import rewrite table

| File | Before | After |
| ---- | ------ | ----- |
| … | `@kui/…/atoms/button` | `@konfio/…/ui/atoms/button` |
```

---

## Stage 4 — `stage-4-setup-notes.md`

```markdown
# Stage 4 — Setup — apps/<app>

## Changed

- [ ] `package.json` — added `@konfio/design-system: catalog:`
- [ ] `globals.css` — styles.css + dist @source
- [ ] Removed kui CSS / @source

## Unchanged

- `@konfio/design-tokens` imports (legacy coexistence)
- App `@theme` brand tokens

## Catalog version

@konfio/design-system @ <semver>
```

---

## Stage 6 — verification checklist

```markdown
- [ ] `rg "@kui/design-system" apps/<app>` → 0
- [ ] check-types pass
- [ ] lint pass
- [ ] test:unit pass
- [ ] Manual smoke: <flows>
```
