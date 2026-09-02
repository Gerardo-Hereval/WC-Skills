#!/usr/bin/env bash
# Downloads a Storyblok component and adds it to the block-library following
# the project conventions.
#
# Usage:
#   STORYBLOK_TOKEN=xxx pnpm download:component <source> <group> [parentGroup]
#
# Arguments:
#   source       One of:
#                  - Storyblok URL (https://app.storyblok.com/#/me/spaces/:spaceId/components/:componentId)
#                  - "<spaceId> <componentId>" as two numeric args
#                  - "<componentId>" alone (spaceId is inferred from legacy
#                    *-XXXXXX.json filenames in data/components)
#   group        component_group_name for the component (e.g. "molecules")
#   parentGroup  Only needed when <group> does not exist yet in
#                component-groups.json — the group is created under this parent
#
# What it does:
#   - Resolves the destination directory by walking the group's parent chain
#     in data/components/component-groups.json (creating the group entry first
#     when parentGroup is provided)
#   - Downloads the component via scripts/download-component.ts
#   - Removes environment-specific metadata (id, created_at, updated_at,
#     internal_tags_list, internal_tag_ids, component_group_uuid,
#     schema field ids, option _uid, empty component_denylist)
#   - Adds component_group_name at the end of the JSON
#   - Fills display_name (Title Case) when null
#   - Forces is_root: false when is_nestable: true
#   - Writes <name>.json into the destination directory and cleans up

set -euo pipefail

GROUPS_FILE="data/components/component-groups.json"
COMPONENTS_ROOT="data/components"
TMP_DIR="./tmp-download"

SPACE_ID=""
COMPONENT_ID=""
GROUP=""
PARENT_GROUP=""

for arg in "$@"; do
  if [[ "$arg" =~ spaces/([0-9]+)/components/([0-9]+) ]]; then
    SPACE_ID="${BASH_REMATCH[1]}"
    COMPONENT_ID="${BASH_REMATCH[2]}"
  elif [[ "$arg" =~ ^[0-9]+$ ]]; then
    if [ -z "$COMPONENT_ID" ]; then
      COMPONENT_ID="$arg"
    else
      # Two numeric args: first was spaceId, second is componentId
      SPACE_ID="$COMPONENT_ID"
      COMPONENT_ID="$arg"
    fi
  elif [ -z "$GROUP" ]; then
    GROUP="$arg"
  else
    PARENT_GROUP="$arg"
  fi
done

if [ -z "$COMPONENT_ID" ] || [ -z "$GROUP" ]; then
  sed -n '2,28p' "$0"
  exit 1
fi

if [ -z "$SPACE_ID" ]; then
  # Infer from legacy filenames like some-component-1023897.json
  SPACE_ID=$(find "$COMPONENTS_ROOT" -name '*-[0-9]*.json' 2>/dev/null |
    sed -E 's/.*-([0-9]{6,})\.json/\1/' | grep -E '^[0-9]+$' | sort | uniq -c |
    sort -rn | head -1 | awk '{print $2}')
  if [ -z "$SPACE_ID" ]; then
    echo "❌ Could not infer spaceId from legacy filenames. Pass it explicitly." >&2
    exit 1
  fi
  echo "ℹ️  Inferred spaceId: $SPACE_ID"
fi

if [ -z "${STORYBLOK_TOKEN:-}" ]; then
  echo "❌ STORYBLOK_TOKEN is not set. Export it and retry." >&2
  exit 1
fi

# Resolve destination directory from the group hierarchy (creating the group
# entry when parentGroup is provided and the group is missing).
DEST_DIR=$(node - "$GROUPS_FILE" "$COMPONENTS_ROOT" "$GROUP" "$PARENT_GROUP" <<'EOF'
const fs = require('fs');
const path = require('path');

const [groupsFile, componentsRoot, group, parentGroup] = process.argv.slice(2);
const data = JSON.parse(fs.readFileSync(groupsFile, 'utf8'));
const groups = data.component_groups;
const byName = new Map(groups.map((g) => [g.name, g]));

if (!byName.has(group)) {
  if (!parentGroup) {
    console.error(`❌ Group "${group}" is not in ${groupsFile}.`);
    console.error(`   Pass a parentGroup to create it, or use one of:`);
    console.error(`   ${groups.map((g) => g.name).join(', ')}`);
    process.exit(1);
  }
  if (parentGroup !== 'null' && !byName.has(parentGroup)) {
    console.error(`❌ Parent group "${parentGroup}" does not exist.`);
    process.exit(1);
  }
  const entry = { name: group, parent_name: parentGroup === 'null' ? null : parentGroup };
  groups.push(entry);
  byName.set(group, entry);
  fs.writeFileSync(groupsFile, `${JSON.stringify(data, null, 2)}\n`);
  console.error(`✅ Group "${group}" added to component-groups.json (parent: ${entry.parent_name})`);
}

const segments = [];
let current = byName.get(group);
while (current) {
  segments.unshift(current.name);
  current = current.parent_name ? byName.get(current.parent_name) : null;
}
console.log(path.join(componentsRoot, ...segments));
EOF
)

mkdir -p "$TMP_DIR" "$DEST_DIR"
echo "📁 Destination: $DEST_DIR"

./node_modules/.bin/ts-node -r tsconfig-paths/register scripts/download-component.ts \
  "$SPACE_ID" "$COMPONENT_ID" "$STORYBLOK_TOKEN" "$TMP_DIR"

SRC_FILE="$TMP_DIR/component-$COMPONENT_ID.json"
if [ ! -f "$SRC_FILE" ]; then
  echo "❌ Expected download at $SRC_FILE but it was not found." >&2
  exit 1
fi

node - "$SRC_FILE" "$GROUP" "$DEST_DIR" <<'EOF'
const fs = require('fs');
const path = require('path');

const [src, group, destDir] = process.argv.slice(2);
const component = JSON.parse(fs.readFileSync(src, 'utf8'));

// Environment-specific metadata that breaks CI
delete component.id;
delete component.created_at;
delete component.updated_at;
delete component.internal_tags_list;
delete component.internal_tag_ids;
delete component.component_group_uuid;

for (const field of Object.values(component.schema ?? {})) {
  delete field.id;
  if (
    field.type === 'bloks' &&
    Array.isArray(field.component_denylist) &&
    field.component_denylist.length === 0
  ) {
    delete field.component_denylist;
  }
  if (field.type === 'option' && Array.isArray(field.options)) {
    for (const option of field.options) delete option._uid;
  }
}

if (component.display_name == null) {
  component.display_name = component.name
    .split('-')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

if (component.is_nestable === true) component.is_root = false;

// Re-insert so it always lands at the end of the JSON
delete component.component_group_name;
component.component_group_name = group;

const destFile = path.join(destDir, `${component.name}.json`);
fs.writeFileSync(destFile, `${JSON.stringify(component, null, 2)}\n`);

if (component.is_nestable === true && /templates/.test(destDir)) {
  console.warn(
    `⚠️  ${component.name} is nestable but was placed under templates/ — nestable blocks belong in molecules/ unless they are full pages/screens.`,
  );
}

console.log(`✅ ${component.name} → ${destFile} (group: ${group})`);
EOF

rm -f "$SRC_FILE"
rmdir "$TMP_DIR" 2>/dev/null || true
