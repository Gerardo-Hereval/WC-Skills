---
name: amplitude-events
description: >
  Adds one or more Amplitude tracking events to any app in the monorepo.
  Creates the typed wrapper functions in
  packages/analytics/src/application/{app}/tracking-events.ts, exports the
  events file from the package.json exports map, creates the analytics hook
  when warranted, and updates the consumer component.
  Usage: /amplitude-events [app] [event names] [consumer file]
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

Add one or more Amplitude tracking events to any app in the monorepo following
the established pattern.

The source of truth for code shape is the existing code, not this document:
before writing anything, read an existing `tracking-events.ts` and an existing
analytics hook and mirror their patterns. Do not enforce secondary style rules
(import order, formatting, etc.) — the linters handle that.

Usage: `/amplitude-events [app] [event names] [consumer file path]`. If any of
those is missing, ask the user before proceeding.

## STEP 1 — Gather information

Ask the user in a single block for anything missing:

- **App**: which app the events belong to (e.g. funnel, home, on-boarding, profile)
- **Event names**: exactly as they appear in the Amplitude schema, in
  snake_case (e.g. `loan_offer_viewed`)
- **Consumer file**: full path of the file that will fire the event
- **Trigger**: component mount (fires on render), user interaction (click,
  submit, …), or something else the user describes

## STEP 2 — Locate the generated ampli classes

All event classes are auto-generated in
`packages/analytics/src/domain/ampli/index.ts`. For each snake_case event,
confirm the PascalCase class (e.g. `LoanOfferViewed`) and its properties type
(e.g. `LoanOfferViewedProperties`) exist.

If a class is missing, the event has not been pulled from Amplitude yet: tell
the user to run `ampli pull web` inside `packages/analytics`, then re-check
before continuing.

## STEP 3 — Update the tracking-events file

File: `packages/analytics/src/application/{app}/tracking-events.ts`. Read an
existing tracking-events file (this app's, or another app's when creating a new
one) and replicate its pattern. For each event:

1. Import the generated event class and its properties type from the ampli
   domain module, and re-export the properties type.
2. Add one exported wrapper function named `track` + PascalCase event name
   (e.g. `trackLoanOfferViewed`) that receives the typed properties as its only
   parameter and calls `analytics.track` with the generated class's
   `event_type` (not `event_name`), the properties, and
   `AMPLITUDE_ONLY_CONFIG` (which routes the event only to Amplitude).
   Nothing else — no `async`, no `try/catch`, no extra logic.

If the file already exists, read it first and add only the missing events —
never duplicate or reorder what is already there.

## STEP 4 — Export the events file from package.json

In `packages/analytics/package.json`, check the `exports` map. If there is no
entry for the target app, add one mapping `./{app}/events` to
`./src/application/{app}/tracking-events.ts`, so the file is importable as
`@kui/analytics/{app}/events`. If the entry already exists, skip this step.

## STEP 5 — Decide where the event is called from

**Rule**: business logic must not live in UI components. Applied to analytics:

- If firing the event involves **any business logic** — deriving property
  values, conditions, reading state/context, mount-effect timing — that logic
  goes in an **analytics hook** in `apps/{app}/src/application/hooks/`, and the
  component only calls the hook.
- If the call is **trivial** — e.g. an `onClick` that calls the `track*`
  function with values the component already has as props, with no derivation
  or conditions — calling it directly from the UI component is acceptable.
  Don't create a hook that adds nothing.

When a hook is warranted:

- **Naming**: derive from the consumer component filename, dropping the
  framework suffix — `personal-data-section.organism.tsx` becomes
  `use-personal-data-section-analytics.hook.ts`.
- **Parameters**: read the event's properties type in the ampli index.
  Properties constant for this app/component (e.g. `domain`) are hardcoded
  inside the hook as string literals; variable properties (e.g. `entity`,
  `flow_type`) are received as hook parameters through an exported
  `Use{ComponentName}AnalyticsOptions` interface. To find the correct `domain`
  value, check existing analytics hooks in the app or the `DOMAIN_AMPLITUDE`
  constant in the app's domain constants.
- **Pattern A — component mount** (viewed events): the hook calls the `track*`
  function inside a `useEffect` whose dependency array contains the variable
  properties, so the event fires once on render.
- **Pattern B — user interaction** (clicked/submitted events): the hook
  declares a plain function that calls the `track*` function and returns it.
  Do not wrap it in `useCallback` — a simple function is enough.

If the hook file already exists, read it first and extend it with the new
event — do not duplicate what is already there.

## STEP 6 — Update the consumer component and its parent

Read the consumer file, then apply the minimal changes:

1. If a hook was created: import it and call it at the top of the component
   function body — Pattern A as a void call (adding its options to the props
   interface via `extends`), Pattern B destructuring the returned function and
   wiring it to the event handler. Remove any now-redundant direct `track*`
   import.
2. If the direct call was deemed acceptable (STEP 5): import the `track*`
   function from `@kui/analytics/{app}/events` and call it from the handler.

Then search the app's `src/` for the parent that renders this component and
make sure it passes down the variable properties the event needs (e.g.
`entity`, `flowType`).

**Profile app**: `entity` and `flowType` come from the
`useProfileAmplitudeProps` hook
(`apps/profile/src/application/hooks/use-profile-amplitude-props.hook.ts`)
called in the parent, which passes them down as props. If that hook does not
exist yet, create it mirroring the description above (currently it returns
`entity: 'pm'` and `flowType: 'onboarding'`).

## STEP 7 — Audit

After writing all files, launch an **Audit Agent** with the list of every file
created or modified. The agent reads each file and verifies:

- **tracking-events.ts**: every added event has a `track` + PascalCase wrapper
  that only calls `analytics.track` with the class's `event_type`, the
  properties, and `AMPLITUDE_ONLY_CONFIG` — no extra logic; every imported
  properties type is re-exported.
- **Analytics hook** (when one was created): lives in
  `apps/{app}/src/application/hooks/` with the
  `use-{component-name}-analytics.hook.ts` naming; exports its options
  interface; Pattern A uses `useEffect` with all variable properties in the
  dependency array; Pattern B returns a plain function without `useCallback`;
  `domain` is hardcoded as a string literal; the business logic is in the hook,
  not the component.
- **Consumer component**: the hook (when created) is called at the top of the
  component function body; direct `track*` calls (when allowed) contain no
  business logic.
- **package.json**: the new export entry (if added) points to the app's
  tracking-events file, with no duplicates.

Do NOT flag import order, formatting, or other linter-enforced style — the
linters own those.

The agent reports the number of files reviewed and either a clean pass or a
list of issues, each with severity, file path, line, and a one-line
description.

## STEP 8 — Final report

Print a short execution summary: the app, the number of events added, the list
of files created/modified/skipped, the wrapper function names, and the audit
outcome (clean, or the number of observations).
