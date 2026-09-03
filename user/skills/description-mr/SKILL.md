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
- **No filler phrases.** Don't open with "This MR introduces…" — start with the noun.
- Output nothing outside the markdown block.
