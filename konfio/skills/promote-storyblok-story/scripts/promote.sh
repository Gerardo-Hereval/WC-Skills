#!/usr/bin/env bash
# End-to-end promotion of one story between spaces.
# Runs preflight, builds the payload, and stops before writing unless --apply.
#
# Usage:
#   ./promote.sh <source_space> <target_space> <full_slug> [--asset-map f.json]
#                [--publish] [--apply]
#
# Without --apply it is a dry run: it prints the payload and writes nothing.
# Writing to PROD from inside Claude Code is blocked by the permission
# classifier — run the printed command yourself with a leading `!`.

. "$(dirname "$0")/sb-lib.sh"
HERE="$(cd "$(dirname "$0")" && pwd)"

SRC="${1:?source space id}"; DST="${2:?target space id}"; SLUG="${3:?full slug}"; shift 3
ASSET_MAP=""; PUBLISH=""; APPLY=0
while [ $# -gt 0 ]; do
  case "$1" in
    --asset-map) ASSET_MAP="$2"; shift 2 ;;
    --publish)   PUBLISH="--publish"; shift ;;
    --apply)     APPLY=1; shift ;;
    *) echo "unknown flag: $1" >&2; exit 1 ;;
  esac
done

"$HERE/preflight.sh" "$SRC" "$DST" "$SLUG"

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

sb_find_story "$SRC" "$SLUG" > "$WORK/story.json"
PARENT="$(sb_get "$DST" "/stories?with_slug=$(dirname "$SLUG")&folder_only=true" | python3 -c "
import json,sys; st=json.load(sys.stdin).get('stories',[]); print(st[0]['id'] if st else '')
")"

ARGS=(--story "$WORK/story.json" --parent-id "$PARENT"
      --source-space "$SRC" --target-space "$DST" $PUBLISH)
[ -n "$ASSET_MAP" ] && ARGS+=(--asset-map "$ASSET_MAP")

python3 "$HERE/build-payload.py" "${ARGS[@]}" > "$WORK/payload.json"

echo
echo "-- payload summary"
python3 -c "
import json,sys
p=json.load(open(sys.argv[1]))['story']
print(f\"   name={p['name']} slug={p['slug']} parent_id={p['parent_id']}\")
print(f\"   root component={p['content']['component']}\")
" "$WORK/payload.json"

if [ "$APPLY" -ne 1 ]; then
  KEEP="$(mktemp -t sb-payload).json"; cp "$WORK/payload.json" "$KEEP"
  echo
  echo "DRY RUN — nothing was written."
  echo "Payload saved at: $KEEP"
  echo
  echo "To apply, run this yourself (prefix with ! inside Claude Code):"
  echo "  curl -sS -X POST '$SB_API/spaces/$DST/stories' \\"
  echo "    -H \"Authorization: \$STORYBLOK_TOKEN\" -H 'Content-Type: application/json' \\"
  echo "    -d @$KEEP"
  exit 0
fi

echo
echo "-- creating story in $(sb_space_name "$DST")"
sb_post "$DST" "/stories" "$WORK/payload.json" | python3 -c "
import json,sys
r=json.load(sys.stdin); s=r.get('story')
if not s: print('ERROR', json.dumps(r)[:400]); sys.exit(1)
print(f\"   OK id={s['id']} {s['full_slug']} published={s['published']}\")
"
