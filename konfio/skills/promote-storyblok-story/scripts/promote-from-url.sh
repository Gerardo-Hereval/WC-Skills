#!/usr/bin/env bash
# One-argument promotion: paste the Storyblok editor URL, get the story in prod.
#
#   ./promote-from-url.sh 'https://app.storyblok.com/#/me/spaces/1023897/stories/0/0/215835417873378'
#
# Same slug, same folder, same published state as the source. Mirrors the
# story's assets into the target space. Dry run unless you pass --apply.
#
# Flags:
#   --apply                 actually write (default: dry run)
#   --target <space_id>     override the target space (default: prod)
#   --asset-folder-id <id>  where uploaded assets land in the target

. "$(dirname "$0")/sb-lib.sh"
HERE="$(cd "$(dirname "$0")" && pwd)"

URL="${1:?Storyblok story URL}"; shift || true
TARGET="$SB_PROD_SPACE"; APPLY=0; ASSET_FOLDER=""
while [ $# -gt 0 ]; do
  case "$1" in
    --apply)            APPLY=1; shift ;;
    --target)           TARGET="$2"; shift 2 ;;
    --asset-folder-id)  ASSET_FOLDER="$2"; shift 2 ;;
    *) echo "unknown flag: $1" >&2; exit 1 ;;
  esac
done

# .../spaces/<space>/stories/0/0/<story_id>
SRC="$(echo "$URL"   | sed -n 's#.*/spaces/\([0-9]\{1,\}\)/.*#\1#p')"
STORY_ID="$(echo "$URL" | sed -n 's#.*/stories/[0-9]*/[0-9]*/\([0-9]\{1,\}\).*#\1#p')"
if [ -z "$SRC" ] || [ -z "$STORY_ID" ]; then
  echo "Could not read space id and story id from the URL." >&2
  echo "Expected .../spaces/<space>/stories/0/0/<story_id>" >&2
  exit 1
fi
if [ "$SRC" = "$TARGET" ]; then
  echo "Source and target are the same space ($SRC). Nothing to promote." >&2
  exit 1
fi

WORK="$(mktemp -d)"; trap 'rm -rf "$WORK"' EXIT
sb_get "$SRC" "/stories/$STORY_ID" | python3 -c "
import json,sys
s=json.load(sys.stdin).get('story')
if not s: sys.exit('story not found')
if s.get('deleted_at'): sys.exit('that story is in the trash')
json.dump(s,open(sys.argv[1],'w'),ensure_ascii=False)
print(s['full_slug']); print('1' if s['published'] else '0')
" "$WORK/story.json" > "$WORK/meta.txt"

SLUG="$(sed -n 1p "$WORK/meta.txt")"
PUBLISHED="$(sed -n 2p "$WORK/meta.txt")"
echo "story:     $SLUG"
echo "published: $([ "$PUBLISHED" = 1 ] && echo yes || echo 'no (draft)')"
echo

"$HERE/preflight.sh" "$SRC" "$TARGET" "$SLUG"

echo
echo "-- assets"
ASSET_ARGS=(--story "$WORK/story.json" --source-space "$SRC" --target-space "$TARGET")
[ -n "$ASSET_FOLDER" ] && ASSET_ARGS+=(--asset-folder-id "$ASSET_FOLDER")
[ "$APPLY" -ne 1 ] && ASSET_ARGS+=(--dry-run)
python3 "$HERE/upload-assets.py" "${ASSET_ARGS[@]}" > "$WORK/asset-map.json"

PARENT="$(sb_get "$TARGET" "/stories?with_slug=$(dirname "$SLUG")&folder_only=true" | python3 -c "
import json,sys; st=json.load(sys.stdin).get('stories',[]); print(st[0]['id'] if st else '')
")"

BUILD=(--story "$WORK/story.json" --parent-id "$PARENT"
       --source-space "$SRC" --target-space "$TARGET" --asset-map "$WORK/asset-map.json")
[ "$PUBLISHED" = 1 ] && BUILD+=(--publish)

if [ "$APPLY" -ne 1 ]; then
  echo
  echo "DRY RUN — nothing was written. Assets were not uploaded, so the payload"
  echo "cannot be built yet. Re-run with --apply (prefix with ! for prod):"
  echo "  ! $0 '$URL' --apply"
  exit 0
fi

python3 "$HERE/build-payload.py" "${BUILD[@]}" > "$WORK/payload.json"

echo
echo "-- creating story in $(sb_space_name "$TARGET")"
sb_post "$TARGET" "/stories" "$WORK/payload.json" | python3 -c "
import json,sys
r=json.load(sys.stdin); s=r.get('story')
if not s: print('ERROR', json.dumps(r)[:400]); sys.exit(1)
print(f\"   OK id={s['id']} {s['full_slug']} published={s['published']}\")
"
