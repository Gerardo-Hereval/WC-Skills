#!/usr/bin/env bash
# Shared helpers for the Storyblok Management API.
# Source this from the other scripts: . "$(dirname "$0")/sb-lib.sh"

set -euo pipefail

# Konfío lives on the US cluster. api.storyblok.com (EU) answers Unauthorized
# with a perfectly valid token, which reads like an auth problem and is not.
SB_API="${SB_API:-https://api-us.storyblok.com/v1}"

SB_DEV_SPACE="${SB_DEV_SPACE:-1023897}"
SB_PROD_SPACE="${SB_PROD_SPACE:-567724046872094}"

sb_require_token() {
  if [ -z "${STORYBLOK_TOKEN:-}" ]; then
    echo "STORYBLOK_TOKEN is not set. Run: source ~/.zshrc" >&2
    exit 1
  fi
}

# sb_get <space_id> <path-with-leading-slash>
sb_get() {
  sb_require_token
  curl -sS -H "Authorization: $STORYBLOK_TOKEN" "$SB_API/spaces/$1$2"
}

# sb_post <space_id> <path> <json-file>
sb_post() {
  sb_require_token
  curl -sS -X POST "$SB_API/spaces/$1$2" \
    -H "Authorization: $STORYBLOK_TOKEN" \
    -H "Content-Type: application/json" \
    -d @"$3"
}

sb_space_name() {
  case "$1" in
    "$SB_DEV_SPACE")  echo "dev" ;;
    "$SB_PROD_SPACE") echo "PROD" ;;
    *)                echo "space $1" ;;
  esac
}

# Prints the id of a story matched by full_slug, or nothing when absent.
# The list endpoint does NOT include `content` — use sb_get_story for that.
# Storyblok also keeps soft-deleted stories reachable by id (HTTP 200 with
# deleted_at set), so never treat "the request succeeded" as "the story exists".
sb_find_story_id() {
  local space="$1" slug="$2" parent_path
  parent_path="${slug%/*}/"
  sb_get "$space" "/stories?starts_with=$parent_path&per_page=100" | python3 -c "
import json,sys
want=sys.argv[1]
for s in json.load(sys.stdin).get('stories',[]):
    if s.get('full_slug')==want and not s.get('deleted_at'):
        print(s['id']); break
" "$slug"
}

# Full story object (including content) by full_slug. Empty when absent.
sb_find_story() {
  local id
  id="$(sb_find_story_id "$1" "$2")"
  [ -z "$id" ] && return 0
  sb_get "$1" "/stories/$id" | python3 -c "
import json,sys
s=json.load(sys.stdin).get('story')
if s and not s.get('deleted_at'): print(json.dumps(s))
"
}
