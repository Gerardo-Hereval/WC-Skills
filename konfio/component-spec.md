---
name: component-spec
description: >
  Analyzes a React component given its file path or name and produces a structured artifact with:
  endpoints (HTTP method, URL, payload/params), field origin chain (props → store → API),
  business rules, a prioritized test matrix, and code improvements/dead code.
  Works with any component in any monorepo.
  Trigger keywords: component-spec, analiza componente, analyze component, endpoints componente,
  matriz de prueba, test matrix component, reglas de negocio componente, mejoras de codigo.
---

# Component Spec Analyzer

Given a React component file path (or enough context to locate it), produce a complete spec artifact
covering endpoints, field origins, business rules, test matrix, and code improvements.

---

## Step 1 — Locate the component

If `args` is a file path use it directly. If it is a component name, find it:

```
find . -type f -name "*.tsx" | xargs grep -l "ComponentName" | head -5
```

Read the full file before proceeding.

---

## Step 2 — Gather all dependencies (run in parallel)

For every service/API call found in the component:

1. **Trace service implementations** — find the service file and read the HTTP method, URL, and payload shape for each call.
2. **Trace types** — find and read the response type interfaces referenced.
3. **Trace constants** — find any domain/enum constants (e.g. `DYNAMIC_STAGES_DOMAINS`, feature flags).
4. **Find the parent component(s)** — grep for the component's name to find where it is rendered. Read the parent(s) to understand how props are passed.
5. **Trace prop origins** — for each prop, follow the chain: parent component → Redux selector / React Router param / API call, until you reach the original source (store, URL param, API endpoint).

Do not guess. Read the actual files.

---

## Step 3 — Identify business rules

Business rules are conditional behaviors encoded in the component logic. Look for:

- Computed values derived from API responses (`useMemo`, derived state)
- Conditions controlling UI visibility or interactivity (`disabled`, conditional rendering)
- State transitions triggered by API success or error
- Timer / countdown logic
- Hardcoded domain values or magic numbers
- Any behavior that has a "why" beyond pure rendering

Write each rule concisely: what the condition is, what it produces, which values it depends on.

---

## Step 4 — Identify code improvements

Scan for the following categories. Only report what is actually present; do not invent issues.

**Bugs** — incorrect behavior, not just style:
- Dependency array entries that are never read inside the effect body (ghost deps that can cause double-execution)
- Duplicate expressions in JSX props (e.g. same loading flag twice in an OR chain)
- Type generic mismatch between `useApiCall<T>` and the actual service return type

**Smells** — not bugs but will mislead maintainers or cause subtle issues:
- Over-broad useEffect dependencies (whole state object when only `.data` is needed)
- `useState(derivedValue)` where the initial value is always the zero-state and a separate effect handles reset — confusing initialization intent
- Constant names that misrepresent their usage (e.g. `MIN_X` used as a threshold, not a minimum)
- Handlers without `useCallback` passed as onClick to multiple buttons

**Optional** — low-priority improvements:
- Anything else that is clearly suboptimal but has no functional impact

For each finding provide: a one-line summary, the problematic code snippet, and the corrected snippet.

---

## Step 5 — Build the test matrix

Cover these categories:

| Category | What to test |
|---|---|
| Initial load | One case per distinct `deliveryMedium` / state variant returned by the API |
| Render | Static props (name, masked phone, labels) |
| Button states | Each enable/disable condition independently |
| Timer | Decrement, stop at 0, restart after resend |
| POST success | Correct payload, side-effects (re-fetch, snackbar) |
| POST error | Error snackbar, no side-effects |
| Loading states | GET in-flight, POST in-flight |
| Prop changes | Re-triggers to GET when relevant props change |
| Edge cases | `undefined`/`0`/empty string in API fields, negative computed values |

Assign priority:
- **High** — core flows, correctness of API calls, button enable/disable, error handling
- **Medium** — secondary UI states, loading indicators, prop reactivity
- **Low** — pure display (labels, formatting)
- **Edge** — boundary values, missing fields, unexpected API shapes

---

## Step 6 — Produce the artifact

Load the `artifact-design` skill, then build a single-page HTML artifact with these sections:

1. **Endpoints** — one card per endpoint showing method badge, URL (with path params highlighted), path params, query params / request body, response type, and trigger events (when the call is made).
2. **Field origins** — one entry per field used in the API calls plus display-only props, showing the full chain from the component prop down to the original source (Redux selector → thunk → HTTP endpoint → response field).
3. **Business rules** — numbered list, each with title and logic snippet in a code block.
4. **Test matrix** — full data table with ID, scenario, preconditions, action, expected result, rule reference, and priority chip.
5. **Code improvements** — color-coded by severity (red = bug, amber = smell, neutral = optional), each with problematic and corrected code snippets.

Design guidance:
- Technical document treatment — polished but utilitarian, not editorial.
- Use a dark navy ground (dark mode) / light slate (light mode) with a blue accent.
- Monospace font for all code, paths, IDs, and method badges.
- Method badges: GET in green, POST in amber, PUT/PATCH in blue, DELETE in red.
- Priority chips: High red, Medium amber, Low green, Edge purple — all with 3px border-radius.
- Tables must be inside `overflow-x: auto` containers.
- Full light/dark theme support via CSS custom properties.

Publish the artifact and return its URL.

---

## Rules

- Read actual files — never assume service signatures, type shapes, or prop origins.
- Report only findings that exist in the code. Do not pad the matrix with obvious cases that cannot fail.
- If a prop chain cannot be fully traced (e.g. comes from a context with no visible provider), note the gap explicitly rather than guessing.
- Output the artifact URL and a brief bullet summary of what was found. Nothing else.
