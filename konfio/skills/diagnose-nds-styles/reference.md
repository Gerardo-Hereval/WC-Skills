# Reference — probes and wiring facts

## Browser proof (layer 5)

Run in the page console (or `javascript_tool` in claude-in-chrome). Works on any page of the app; the drawer does not need to be open because the probe uses the same utility class the SDK component emits.

```js
const cs = getComputedStyle(document.documentElement);
const roles = ['background','foreground','card','popover','primary','muted','accent','destructive','border','input','ring'];
const vars = Object.fromEntries(roles.map(r => [r, cs.getPropertyValue('--color-' + r).trim() || '(invalid)']));

const probe = cls => { const d = document.createElement('div'); d.className = cls; document.body.appendChild(d);
  const v = getComputedStyle(d).backgroundColor; d.remove(); return v; };
({ vars, bgBackground: probe('bg-background'), bgWhite: probe('bg-white') });
```

Reading:

- `(invalid)` on a role and `rgba(0, 0, 0, 0)` on `bg-background` while `bg-white` paints → layer 4 (cycle). Confirm the diagnosis in place: `document.documentElement.style.setProperty('--color-background', '#fff')` turns the probe white.
- `bg-background` probe is `rgba(0, 0, 0, 0)` and there is no `.bg-background` rule in `document.styleSheets` → layer 3 (utility not generated).
- Everything paints but the wrong hex → app `@theme` override or token drift, compare against `theme.css` of the installed version.

## How the SDK wires tokens (≥ 1.11.0)

```
@konfio/design-system/styles.css
  └─ src/styles/tokens/index.css     → theme.css defines --color-<role> and the palette (@theme)
  └─ src/styles/shadcn/tokens.css    → :root { --<role>: var(--color-<role>) }   (alias, NOT the reverse)
```

Tailwind v4 concatenates every `@theme`; the app's `globals.css` comes after the import, so anything it declares replaces the SDK value for that variable. An app line `--color-background: var(--background)` therefore points at the alias that points back at it.

Before 1.11.0 the alias was concrete (`--background: var(--color-gray-0)`), which is why older `globals.css` blocks copied from shadcn templates used to work.

## Where the CSS ends up

- Dev compiled CSS: `apps/<app>/.next/dev/static/chunks/*globals*.css` (exists once the page has been visited).
- Installed package: `readlink -f apps/<app>/node_modules/@konfio/design-system` → `dist/ui/{atoms,molecules,organisms}/*.js` for classes, `src/styles/**` for tokens.
- A `2.0.0` exists in the registry from a failed release; `latest` is the 1.x line. Never pin `^2` or `latest`.

## Related skills

- `migrate-konfio-design-system` — the migration itself; run this skill when the smoke test after a migration shows a visual defect.
- `audit-konfio-libraries` — inventory of which package each app really imports.
