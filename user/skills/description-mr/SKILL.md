---
name: description-mr
description: >
  Generates a GitLab MR description in English for the current branch's changes.
  Use when you want to document what changed, why, and how to test it before opening
  or updating a merge request. Works in any repo.
  Trigger keywords: mr docs, mr description, document changes, gitlab description,
  describe mr, write mr, genera descripcion, documenta cambios, descripcion del mr,
  description-mr.
---

# MR Description Generator

Generate a clear, structured GitLab MR description in English based on the actual
diff between this branch and the main branch.

---

## Step 1 — Gather branch context (mandatory, run in parallel)

Run ALL of these before writing anything:

```
git log main..HEAD --oneline
git diff main...HEAD --stat
git diff main...HEAD
```

If `main` does not exist, try `master` or `origin/HEAD`.

Read the full diff carefully. Group changes by feature area — do not summarize blindly.

Then decide whether the MR touches the presentation layer: components, pages, templates,
styles, stories, design tokens, or anything under a `ui/` folder or a design-system package.
If it does, Step 1b is mandatory.

---

## Step 1b — Visual evidence (mandatory for any UI change)

Team rule since 2026-10-23 (requested by the web tech lead): every MR that changes UI,
especially agent-generated ones, must prove the change working, not only compiling.
Tests alone are not enough.

Collect, or ask the author for:

1. **Before vs after.** Screenshots and a screen recording of `main` and of this branch,
   with the real component inside its real container (e.g. the drawer or modal it lives in),
   not an isolated sandbox only.
2. **Desktop and mobile.** At least one desktop width and a 375px mobile viewport.
3. **Interaction.** Show the states the change affects: click, typing, focus, error,
   loading, empty. If the bug only appears on focus or on a given width, show that state.
4. **A measurable check when possible.** E.g. overflow in px, element width, a Cypress or
   Playwright assertion that fails on `main` and passes on the branch.
5. **Upload the files to the MR** (GitLab uploads API) so they render inline, and post the
   same evidence in the Slack thread where the MR is shared.

If the MR changes a published package (e.g. the `@konfio/design-system` SDK), also:

6. **Test the snapshot in a consumer app.** Install the snapshot version the MR pipeline
   publishes (`0.0.0-<timestamp>`) in an app that consumes the package and exercise the real
   flow that uses the component.
7. **Integrated check without a real session.** Run the consumer app locally with its mocks
   and the e2e intercepts/fixtures of its `apps/<app>-e2e` package. Run the relevant
   existing e2e spec against the current published version and against the snapshot, and
   report both results. Failures that already happen on `main` must be named as pre-existing.

Never invent evidence. If something is missing, keep the section with an explicit
`TODO:` line naming what still has to be attached, and tell the user.

---

## Step 1c — Verification results (mandatory for every MR)

Same team rule as Step 1b, for every MR, UI or not: the description shows what was run
and what came out, not only a checklist for the reviewer. A "How to test" list alone is
not evidence.

1. **Run the checks yourself** on this branch and record the real outcome: typecheck,
   lint, format and the unit tests of the affected workspace, plus the relevant e2e spec
   when there is one. Use the workspace scripts (`check-types`, `lint`, `test:unit`).
2. **Compare against `main`** when a check is not clean. Run the same command on `main`
   and name every failure that also happens there as pre-existing (e.g. errors coming
   from outdated dependencies). Never call a red check "unrelated" without that run.
3. **Prove the behavior, not only the build.** Add one check that fails on `main` (or
   without the change) and passes on the branch: a test, a Cypress assertion, a measured
   value, or for types-only MRs a temporary file with `@ts-expect-error` lines showing what
   the new types reject. Say whether that check is committed or temporary.
4. **Integrated check without a real session.** When the change runs inside an app, run
   it locally with its mocks and the e2e intercepts/fixtures of its `apps/<app>-e2e`
   package instead of asking for a session.
5. **Report numbers.** Test counts, error counts, measured px. "Passes" alone is not a result.

Never invent results. If a check could not run, list it with `TODO:` and the reason.

---

## Step 2 — Write the description

Output ONLY the raw markdown below. No preamble, no explanation, no trailing commentary.

```markdown
## What

<!-- One or two sentences: what this MR adds, changes, or fixes. Be concrete. -->

## Why

<!-- The motivation: bug fix, feature request, tech debt, compliance, performance. -->

## Changes

<!-- Group by area (e.g. Service, Schema, Router, Tests, Docs).
     Name the file and method/field — not just "updated logic". -->

### <Area 1>
- ...

### <Area 2>
- ...

## How to test

<!-- Actionable checklist the reviewer can follow to verify the happy path and edge cases. -->

- [ ] ...

## Results

<!-- Mandatory for every MR. Commands actually run on this branch and on main, with numbers.
     Name pre-existing failures. Include the check that fails without the change. -->

| Check | Command | main | This branch |
| --- | --- | --- | --- |
| ... | ... | ... | ... |

## Visual evidence

<!-- Only for UI changes. Before vs after, desktop and 375px mobile, with interaction.
     Embed the uploaded screenshots and video; add the measured result if there is one. -->

| | Before (main) | After (this branch) |
| --- | --- | --- |
| Desktop | ![]() | ![]() |
| Mobile 375px | ![]() | ![]() |

Video: ...

## Integrated check in a consumer app

<!-- Only for published packages (SDK). Snapshot version, consumer app and flow,
     how it ran without a real session, and the e2e results on current vs snapshot. -->

- Snapshot: `<package>@0.0.0-<timestamp>`
- Consumer: `apps/<app>` — <flow>
- Results:

| Check | Current version | Snapshot |
| --- | --- | --- |
| ... | ... | ... |

## Notes

<!-- Breaking changes, migration steps, env vars, feature flags, caveats. Omit if none. -->
```

---

## Rules

- **English only.** No Spanish anywhere in the output.
- **Concrete over vague.** Name the file, the method, the field — not "updated some logic".
- **Group by concern**, not by file. If three files all touch the same feature, one section covers them.
- **Test plan must be actionable.** Each item should describe an explicit action and expected result.
- **Omit empty sections entirely.** If there are no notes, drop the Notes header too.
  Exception: every MR keeps `Results`; a UI change always keeps `Visual evidence`, and a published-package change
  always keeps `Integrated check in a consumer app` (with `TODO:` lines if evidence is missing).
- **How to test for UI changes** includes the viewport and the interaction to reproduce,
  not only "open the page".
- **No filler phrases.** Don't open with "This MR introduces…" — start with the noun.
- **Results come from real runs.** Every row in `Results` matches a command you ran in this
  session; failures that also happen on `main` are labeled pre-existing.
- Output nothing outside the markdown block, except a short list of missing evidence
  (the `TODO:` items).
