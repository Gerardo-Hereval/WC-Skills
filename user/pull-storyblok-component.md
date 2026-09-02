---
name: pull-storyblok-component
description: >
  Downloads a Storyblok component and adds it to the block-library following
  the project conventions. Download, JSON normalization, destination-folder
  resolution, and group creation are all automated by the
  `pnpm download:component` script; this skill only decides the right group
  and verifies the result.
  Usage: /pull-storyblok-component <storyblok-url-or-component-id>
user-invocable: true
allowed-tools:
  - Bash
  - Read
  - Edit
  - AskUserQuestion
---

# /pull-storyblok-component

Argument received: `$ARGUMENTS`

Everything mechanical is automated in `scripts/download-component.sh`, exposed
as `pnpm download:component <source> <group> [parentGroup]`. It accepts a
Storyblok URL, a `spaceId componentId` pair, or a lone `componentId` (spaceId
is inferred from legacy filenames); it resolves the destination folder from the
group hierarchy in `data/components/component-groups.json`, creates the group
entry when a parent is given, downloads the component, strips all
environment-specific metadata, stamps `component_group_name`, fills
`display_name`, fixes `is_root`, and writes the final `<name>.json` in place.

Your job is only judgment: pick the right group, run the script, and verify.

## STEP 1 — Choose the group

Read `data/components/component-groups.json` and ask the user which group the
component belongs to, listing the available groups. If it is a new group, also
ask for its parent group.

Placement rules (mandatory):

- Files under `konfio-app-web/` and `konfio-mx/` must end in `-page`; files
  under `konfio-app-mobile/` must end in `-screen`.
- Nestable components (`is_nestable: true`) that are not full pages/screens
  must NOT go under those template directories — they belong in `molecules`
  even when domain-specific. Only non-nestable, full page/screen components go
  under templates.

## STEP 2 — Run the script

Run `pnpm download:component "$ARGUMENTS" "<group>"` (append the parent group
as a third argument only when creating a new group). It requires
`STORYBLOK_TOKEN` to be exported; if it is not available in your environment,
ask the user to run the same command in their terminal and wait for
confirmation.

The script warns if a nestable component lands under `templates/` — if that
happens, re-run it with the `molecules` group and delete the misplaced file.

## STEP 3 — Verify and confirm

1. Read the final file and sanity-check the schema: field names in
   `camelCase`, generic reusable naming (no campaign-specific names), and the
   filename suffix matching the placement rules above.
2. Show a short summary with the component name, final path, and group, and
   remind the user of the next steps: review the schema, run
   `pnpm run validate:components`, and open an MR (CI deploys it to Storyblok).
