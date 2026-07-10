---
name: amplitude-events
description: >
  Agregar uno o más eventos de Amplitude tracking a cualquier app del monorepo.
  Genera las funciones wrapper tipadas en packages/analytics/src/application/{app}/tracking-events.ts
  y actualiza el package.json exports si es necesario. Incluye agente de auditoría al final.
  Uso: /amplitude-events [app] [nombres de eventos]
user-invocable: true
allowed-tools:
  - Bash
  - Read
  - Edit
  - Write
  - Agent
  - AskUserQuestion
---

# amplitude-events — Add Amplitude tracking events

Add one or more Amplitude tracking events to any app in the monorepo following the established pattern.

## Usage

```
/amplitude-events [app] [event names]
```

If the app or event names are not provided, ask the user before proceeding.

---

## INSTRUCTIONS

### STEP 1 — Gather information

Ask the user in a single block if any of the following is missing:

```
To add the Amplitude events I need to confirm a few things:

❓ App: Which app are the events for? (e.g. funnel, home, on-boarding)
❓ Event names: What are the event names exactly as they appear in the Amplitude schema?
   (e.g. loan_offer_viewed, loan_setup_submitted — use snake_case)
❓ Usage: Where will these events be called from? (component name, hook, or context — optional but helpful)
```

---

### STEP 2 — Locate the generated ampli classes

All event classes are auto-generated. Read the ampli index to confirm the event classes and their property types exist:

```
packages/analytics/src/domain/ampli/index.ts
```

For each event in snake_case (e.g. `loan_offer_viewed`), the generated class is PascalCase (`LoanOfferViewed`) and its properties type is `LoanOfferViewedProperties`.

**If a class is missing**: the event has not been pulled from Amplitude yet. Tell the user to run:
```bash
cd packages/analytics && ampli pull web
```
Then re-check before continuing.

---

### STEP 3 — Update the tracking-events file

File: `packages/analytics/src/application/{app}/tracking-events.ts`

**If the file does not exist**, create it following this template:

```typescript
import { analytics } from '../../config';
import {
  EventClassName,
  type EventClassNameProperties,
} from '../../domain/ampli';
import { AMPLITUDE_ONLY_CONFIG } from '../../domain/constants/config';

export type { EventClassNameProperties };

export function trackEventClassName(
  properties: EventClassNameProperties,
): ReturnType<typeof analytics.track> {
  return analytics.track(
    new EventClassName(properties).event_type,
    properties,
    AMPLITUDE_ONLY_CONFIG,
  );
}
```

**If the file already exists**, read it first, then add only the missing events:

1. Add the new class and type imports to the existing import block from `../../domain/ampli`
2. Add the new `export type { ... }` entries
3. Add the new `export function track...` at the bottom

**Import ordering rule** (enforced by the linter):
- `../../config` first
- `../../domain/ampli` second (all event classes and types, alphabetically)
- `../../domain/constants/config` last

**Function naming**: `track` + PascalCase event name → `trackLoanOfferViewed`

---

### STEP 4 — Update package.json exports (only if the app entry is missing)

File: `packages/analytics/package.json`

Check the `exports` map. If there is no entry for the target app, add it:

```json
"./{app}/events": "./src/application/{app}/tracking-events.ts"
```

Example — adding funnel:
```json
{
  "exports": {
    ".": "./src/config.ts",
    "./funnel/events": "./src/application/funnel/tracking-events.ts"
  }
}
```

If the entry already exists, skip this step.

---

### STEP 5 — Show usage example

Print how to consume the new events in the target app:

```typescript
import { trackLoanOfferViewed } from '@kui/analytics/{app}/events';

// inside a component or hook:
trackLoanOfferViewed({
  // EventClassNameProperties fields here
});
```

---

### STEP 6 — Audit

After writing all files, launch an **Audit Agent** passing it the list of every file that was created or modified.

#### AUDIT AGENT instructions

Read each file with `Read` and verify the following checklist:

**Imports**
- [ ] `../../config` is the first import in tracking-events
- [ ] All event classes and their property types are imported from `../../domain/ampli` in a single block, sorted alphabetically
- [ ] `AMPLITUDE_ONLY_CONFIG` is imported from `../../domain/constants/config` as the last import
- [ ] No event class or type is imported that was not added as a wrapper function

**Exports**
- [ ] Every imported property type has a matching `export type { ... }` entry
- [ ] Every added event has a corresponding `export function track...` with the correct name

**Function shape** — each wrapper must follow this exact pattern:
```typescript
export function track{EventName}(
  properties: {EventName}Properties,
): ReturnType<typeof analytics.track> {
  return analytics.track(
    new {EventName}(properties).event_type,
    properties,
    AMPLITUDE_ONLY_CONFIG,
  );
}
```
- [ ] No `async`, no `try/catch`, no extra logic inside the function body
- [ ] `new {EventName}(properties).event_type` — uses `.event_type`, not `.event_name` or `.name`

**package.json**
- [ ] If a new entry was added, the path matches `./src/application/{app}/tracking-events.ts` exactly
- [ ] No duplicate entries in the `exports` map

**Quality**
- [ ] No `console.log` in any file
- [ ] No hardcoded app name in paths when it should be dynamic
- [ ] Function names are `track` + PascalCase (e.g. `trackLoanOfferViewed`, not `trackLoan_offer_viewed`)

**Audit report format:**

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔍 AUDIT — amplitude-events / {app}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Files reviewed: {N}

✅ No issues — all files follow the project pattern

(or if there are issues:)
⚠️  Issues found ({N}):
  [CRITICAL] path/to/file.ts:{line}
  → description of the problem

Audit agent tokens: ~{N}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

### STEP 7 — Final report

Print the execution summary after the audit completes:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 amplitude-events — Execution report
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
App       : {app}
Events    : {N} added

Files modified:
  ✅ packages/analytics/src/application/{app}/tracking-events.ts
  {✅ | ⏭ } packages/analytics/package.json (./{app}/events entry)

Events added:
  ✅ track{EventName}
  ...

Audit     : ✅ No issues | ⚠️  {N} observations

Estimated tokens:
  Orchestrator  : ~{N} tokens
  Audit agent   : ~{N} tokens
  ─────────────────────────────
  Total output  : ~{total} tokens
  Approx cost   : ~${cost} USD  (Sonnet 4.6: $15/MTok output)
  Approx time   : ~{time} seconds

Usage:
  import { track{EventName} } from '@kui/analytics/{app}/events';
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Token estimation rules:**
- Estimate ~4 characters per output token
- Count characters in all files written/modified and divide by 4
- Add ~500 tokens for orchestrator reasoning
- Add ~300 tokens for audit agent reasoning
- Price: Sonnet 4.6 output = $15/MTok → cost = (total tokens / 1,000,000) × 15
- Time: estimate ~3 seconds per 1,000 output tokens

---

## Pattern reference

| Layer | File | Responsibility |
|---|---|---|
| Domain | `packages/analytics/src/domain/ampli/index.ts` | Auto-generated event classes (do not edit) |
| Application | `packages/analytics/src/application/{app}/tracking-events.ts` | Typed wrapper functions |
| Package entry | `packages/analytics/package.json` exports | Public import path |
| Consumer | App component / hook | Calls `track*` functions |

Each wrapper function follows this exact shape:

```typescript
export function trackMyEvent(
  properties: MyEventProperties,
): ReturnType<typeof analytics.track> {
  return analytics.track(
    new MyEvent(properties).event_type,
    properties,
    AMPLITUDE_ONLY_CONFIG,
  );
}
```

`AMPLITUDE_ONLY_CONFIG` ensures events are sent only to Amplitude and not to other analytics plugins.
