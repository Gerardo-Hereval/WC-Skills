#!/usr/bin/env bash
# Preflight for promoting a story to another space.
# Answers the only question that matters before writing anything:
# is the target space ready to hold this story?
#
# Usage: ./preflight.sh <source_space> <target_space> <full_slug>
# Example: ./preflight.sh 1023897 567724046872094 \
#            konfio-app-web/dashboard/solicitud/buro-de-credito

. "$(dirname "$0")/sb-lib.sh"

SRC="${1:?source space id}"; DST="${2:?target space id}"; SLUG="${3:?full slug}"
fail=0

echo "== Promoting  $SLUG"
echo "   from $(sb_space_name "$SRC")  ->  $(sb_space_name "$DST")"
echo

echo "-- source story"
story="$(sb_find_story "$SRC" "$SLUG")"
if [ -z "$story" ]; then
  echo "   MISSING in source. Nothing to promote."; exit 1
fi
echo "$story" | python3 -c "
import json,sys
s=json.load(sys.stdin)
print(f\"   id={s['id']} published={s['published']} parent_id={s['parent_id']}\")
"

echo
echo "-- components used by the story"
comps="$(echo "$story" | python3 -c "
import json,sys
def walk(n,out):
    if isinstance(n,dict):
        if 'component' in n: out.add(n['component'])
        for v in n.values(): walk(v,out)
    elif isinstance(n,list):
        for v in n: walk(v,out)
out=set(); walk(json.load(sys.stdin)['content'],out)
print('\n'.join(sorted(out)))
")"
target_comps="$(sb_get "$DST" "/components" | python3 -c "
import json,sys
print('\n'.join(c['name'] for c in json.load(sys.stdin).get('components',[])))
")"
while read -r c; do
  [ -z "$c" ] && continue
  if echo "$target_comps" | grep -qx -- "$c"; then
    echo "   OK      $c"
  else
    echo "   MISSING $c"; fail=1
  fi
done <<< "$comps"

echo
echo "-- target parent folder"
parent_path="${SLUG%/*}/"
parent="$(sb_get "$DST" "/stories?with_slug=${parent_path%/}&folder_only=true" | python3 -c "
import json,sys
st=json.load(sys.stdin).get('stories',[])
print(st[0]['id'] if st else '')
")"
if [ -n "$parent" ]; then
  echo "   OK      parent_id=$parent"
else
  echo "   MISSING folder ${parent_path%/} does not exist in target"; fail=1
fi

echo
echo "-- target story (collision check)"
existing="$(sb_find_story "$DST" "$SLUG")"
if [ -n "$existing" ]; then
  echo "$existing" | python3 -c "
import json,sys
s=json.load(sys.stdin)
print(f\"   EXISTS  id={s['id']} — promoting would need an update, not a create\")
"
else
  echo "   OK      slug is free"
fi

echo
echo "-- assets pointing at the source space"
echo "$story" | python3 -c "
import json,re,sys
s=json.load(sys.stdin)
src=sys.argv[1]
urls=set(re.findall(r'https://a-us\.storyblok\.com/f/(\d+)/[^\"\\s]+', json.dumps(s['content'])))
if not urls: print('   none')
elif urls=={src}: print(f'   {len(urls)} asset host(s), all on the source space — MUST be re-pointed')
else: print(f'   asset hosts found: {sorted(urls)}')
" "$SRC"

echo
if [ "$fail" -ne 0 ]; then
  echo "PREFLIGHT FAILED — fix the MISSING items before promoting."
  echo "Components are NOT created by this skill: register them in block-library and let CI deploy them."
  exit 1
fi
echo "PREFLIGHT PASSED"
