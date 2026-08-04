---
name: amplitude-events
description: >
  Agregar uno o más eventos de Amplitude tracking a cualquier app del monorepo.
  Genera las funciones wrapper tipadas en packages/analytics/src/application/{app}/tracking-events.ts,
  crea el analytics hook en apps/{app}/src/application/hooks/ y actualiza el componente consumidor.
  Actualiza el package.json exports si es necesario. Incluye agente de auditoría al final.
  Uso: /amplitude-events [app] [nombres de eventos] [archivo consumidor]
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
/amplitude-events [app] [event names] [consumer file path]
```

If the app, event names, or consumer file are not provided, ask the user before proceeding.

---

## INSTRUCTIONS

### STEP 1 — Gather information

Ask the user in a single block if any of the following is missing:

```
To add the Amplitude events I need to confirm a few things:

❓ App: Which app are the events for? (e.g. funnel, home, on-boarding, profile)
❓ Event names: What are the event names exactly as they appear in the Amplitude schema?
   (e.g. loan_offer_viewed, loan_setup_submitted — use snake_case)
❓ Consumer file: Which file will call this event? (full path, e.g. apps/profile/src/ui/organisms/my-section.organism.tsx)
❓ Trigger: How is the event fired?
     • component mount  → fires automatically when the component renders
     • button click     → fires when the user clicks a specific button
     • other            → describe the interaction
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

### STEP 5 — Create the analytics hook

> **Rule enforced by the repo bot:** ❌ No business logic in UI components.
> Analytics calls count as business logic. Never call `track*` functions directly inside
> a UI component (organisms, molecules, atoms). Always wrap them in an analytics hook
> placed in `apps/{app}/src/application/hooks/`.

**Hook file path**: derive the name from the consumer component filename, dropping the framework suffix:
- `personal-data-section.organism.tsx` → `use-personal-data-section-analytics.hook.ts`
- `profile-stepper-layout.organism.tsx` → `use-profile-stepper-layout-analytics.hook.ts`

**Full path**: `apps/{app}/src/application/hooks/use-{component-name}-analytics.hook.ts`

Read the event's properties interface in `packages/analytics/src/domain/ampli/index.ts` to identify which properties need to be received as hook parameters. Properties that are constant for this app/component (e.g. `domain`) should be hardcoded inside the hook. Variable properties (e.g. `entity`, `flow_type`, `empty_state_type`) must be received as parameters.

To determine the correct `domain` value: check existing analytics hooks in `apps/{app}/src/application/hooks/` for the value used, or look at `apps/{app}/src/domain/constants/global.ts` for a `DOMAIN_AMPLITUDE` constant.

#### Pattern A — Component mount (viewed events)

Use when the trigger is **component mount**. The hook fires the event once on render.

```typescript
import { useEffect } from 'react';

import {
  type {EventName}Properties,
  track{EventName},
} from '@kui/analytics/{app}/events';

type {Prop} = {EventName}Properties['{prop}'];

export interface Use{ComponentName}AnalyticsOptions {
  {prop}: {Prop};
}

export function use{ComponentName}Analytics({
  {prop},
}: Use{ComponentName}AnalyticsOptions) {
  useEffect(() => {
    track{EventName}({
      domain: '{domain-value}',
      {prop},
    });
  }, [{prop}]);
}
```

The component then extends the hook options and calls it at the top of the function body:

```typescript
interface {Component}Props extends Use{ComponentName}AnalyticsOptions {
  // other props
}

function {Component}({ {prop}, ...otherProps }: {Component}Props) {
  use{ComponentName}Analytics({ {prop} });
  // ...
}
```

#### Pattern B — Button click (clicked events)

Use when the trigger is **button click**. The hook returns a typed callback.

```typescript
import { useCallback } from 'react';

import {
  type {EventName}Properties,
  track{EventName},
} from '@kui/analytics/{app}/events';

type {Prop} = {EventName}Properties['{prop}'];

export interface Use{ComponentName}AnalyticsOptions {
  {prop}: {Prop};
}

export function use{ComponentName}Analytics({
  {prop},
}: Use{ComponentName}AnalyticsOptions) {
  const track{ButtonLabel}Clicked = useCallback(() => {
    track{EventName}({
      domain: '{domain-value}',
      {prop},
    });
  }, [{prop}]);

  return { track{ButtonLabel}Clicked };
}
```

The component destructs the returned callback and attaches it to the button's `onClick`:

```typescript
function {Component}({ {prop}, ...otherProps }: {Component}Props) {
  const { track{ButtonLabel}Clicked } = use{ComponentName}Analytics({ {prop} });

  return <button onClick={track{ButtonLabel}Clicked}>...</button>;
}
```

**If the hook file already exists** (the component already has other analytics hooks), read it first and add only the new event — do not duplicate existing hooks in the same file.

---

### STEP 6 — Update the consumer component and its parent

Read the consumer file, then apply the minimal changes needed:

1. Remove any direct import of `track*` from `@kui/analytics/{app}/events` in the component file
2. Add the import of the analytics hook
3. If using Pattern A: add the hook options to the component's props interface (via `extends`) and call the hook at the top of the function body
4. If using Pattern B: call the hook at the top of the function body and wire the returned callback to the button's `onClick`

**Then find the parent** that renders this component (search with `grep -rn "ComponentName"` in the app's `src/` directory). Update the parent to:
- Call `useProfileAmplitudeProps()` (profile app) or the equivalent app-level hook to derive `entity` and `flowType`
- Pass `entity` and `flowType` as props to the consumer component

---

### Profile app — deriving `entity` and `flowType`

In the **profile app**, `entity` and `flowType` are not passed through from above — they come from a dedicated hook:

```typescript
import { useProfileAmplitudeProps } from '@/application/hooks/use-profile-amplitude-props.hook';

// inside the parent component:
const { entity, flowType } = useProfileAmplitudeProps();
```

Then pass them down:

```tsx
<ConsumerComponent entity={entity} flowType={flowType} ... />
```

The hook lives at `apps/profile/src/application/hooks/use-profile-amplitude-props.hook.ts` and currently returns:
- `entity: 'pm'` — always Persona Moral (EntityType.organization) for now
- `flowType: 'onboarding'` — the profile onboarding flow

If the hook does not exist yet, create it with the pattern above before updating the parent.

---

### STEP 7 — Audit

After writing all files, launch an **Audit Agent** passing it the list of every file that was created or modified.

#### AUDIT AGENT instructions

Read each file with `Read` and verify the following checklist:

**tracking-events.ts**
- [ ] `../../config` is the first import
- [ ] All event classes and their property types are imported from `../../domain/ampli` in a single block, sorted alphabetically
- [ ] `AMPLITUDE_ONLY_CONFIG` is imported from `../../domain/constants/config` as the last import
- [ ] No event class or type is imported that was not added as a wrapper function
- [ ] Every imported property type has a matching `export type { ... }` entry
- [ ] Every added event has a corresponding `export function track...` with the correct shape:
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
- [ ] No `async`, no `try/catch`, no extra logic inside wrappers
- [ ] Uses `.event_type`, not `.event_name` or `.name`

**Analytics hook**
- [ ] File is in `apps/{app}/src/application/hooks/`
- [ ] Name follows `use-{component-name}-analytics.hook.ts`
- [ ] `UseXxxAnalyticsOptions` interface is exported
- [ ] Pattern A (mount): uses `useEffect` — dependency array contains all variable properties
- [ ] Pattern B (click): uses `useCallback` — dependency array contains all variable properties; hook returns the callback
- [ ] `domain` is hardcoded as a string literal (not a variable from props)
- [ ] No direct import of `track*` functions in the UI component file

**Consumer component**
- [ ] No import of `track*` functions from `@kui/analytics` directly in the UI file
- [ ] Hook is imported from `@/application/hooks/`
- [ ] Hook is called at the top of the component function body (Pattern A: void call; Pattern B: destructured return)
- [ ] Pattern A: component props interface extends `UseXxxAnalyticsOptions`
- [ ] Pattern B: returned callback is wired to the correct `onClick` handler

**package.json**
- [ ] If a new entry was added, the path matches `./src/application/{app}/tracking-events.ts` exactly
- [ ] No duplicate entries in the `exports` map

**Quality**
- [ ] No `console.log` in any file
- [ ] Function names are `track` + PascalCase

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

### STEP 8 — Final report

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
  ✅ apps/{app}/src/application/hooks/use-{component}-analytics.hook.ts
  ✅ {consumer file path}

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
  import { use{ComponentName}Analytics } from '@/application/hooks/use-{component}-analytics.hook';
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
| Analytics hook | `apps/{app}/src/application/hooks/use-{component}-analytics.hook.ts` | Isolates tracking logic from UI |
| Consumer | UI organism / component | Calls the analytics hook only |

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