#!/usr/bin/env python3
"""Turn a source-space story into a create payload for the target space.

Everything space-scoped is rewritten or reported:
  * parent_id      -> the target folder id
  * _uid           -> fresh uuid4 for every block
  * asset filename -> re-pointed to the target space CDN path
  * component_group_uuid, internal_tag_ids -> dropped (they are per-space)

Usage:
  build-payload.py --story story.json --parent-id 185735599984273 \
                   --source-space 1023897 --target-space 567724046872094 \
                   [--asset-map map.json] [--publish] > payload.json

--asset-map is a JSON object {"<source asset id>": {"id":…, "filename":…}}
mapping each source asset to the already-uploaded target asset. Assets are NOT
uploaded by this script: an asset that only exists in the source space renders
a broken image in the target, so unmapped assets are a hard error.
"""
import argparse, json, re, sys, uuid

SPACE_URL = re.compile(r'(https://a-[a-z]{2}\.storyblok\.com/f/)(\d+)(/)')


def refresh_uids(node):
    if isinstance(node, dict):
        if '_uid' in node:
            node['_uid'] = str(uuid.uuid4())
        for v in node.values():
            refresh_uids(v)
    elif isinstance(node, list):
        for v in node:
            refresh_uids(v)


def strip_space_scoped(node):
    if isinstance(node, dict):
        for k in ('component_group_uuid', 'internal_tag_ids', 'internal_tags_list'):
            node.pop(k, None)
        for v in node.values():
            strip_space_scoped(v)
    elif isinstance(node, list):
        for v in node:
            strip_space_scoped(v)


def remap_assets(node, asset_map, source_space, unmapped):
    """Rewrite asset objects in place. Records anything still pointing at source."""
    if isinstance(node, dict):
        if node.get('fieldtype') == 'asset' and node.get('filename'):
            key = str(node.get('id'))
            if key in asset_map:
                node['id'] = asset_map[key]['id']
                node['filename'] = asset_map[key]['filename']
            elif f'/f/{source_space}/' in node['filename']:
                entry = (key, node['filename'])
                if entry not in unmapped:
                    unmapped.append(entry)
        for v in node.values():
            remap_assets(v, asset_map, source_space, unmapped)
    elif isinstance(node, list):
        for v in node:
            remap_assets(v, asset_map, source_space, unmapped)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--story', required=True)
    p.add_argument('--parent-id', required=True, type=int)
    p.add_argument('--source-space', required=True)
    p.add_argument('--target-space', required=True)
    p.add_argument('--asset-map')
    p.add_argument('--publish', action='store_true')
    a = p.parse_args()

    story = json.load(open(a.story))
    story = story.get('story', story)
    content = story['content']

    asset_map = json.load(open(a.asset_map)) if a.asset_map else {}
    unmapped = []

    strip_space_scoped(content)
    remap_assets(content, asset_map, a.source_space, unmapped)
    refresh_uids(content)

    leftover = SPACE_URL.findall(json.dumps(content))
    stale = [m for m in leftover if m[1] == a.source_space]
    if unmapped or stale:
        print('Assets still pointing at the source space:', file=sys.stderr)
        for asset_id, filename in unmapped:
            print(f'  id={asset_id} {filename}', file=sys.stderr)
        print('\nUpload them to the target space and pass --asset-map, or the '
              'target story will render broken images.', file=sys.stderr)
        sys.exit(2)

    payload = {
        'story': {
            'name': story['name'],
            'slug': story['slug'],
            'parent_id': a.parent_id,
            'content': content,
        },
        'publish': 1 if a.publish else 0,
    }
    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)


if __name__ == '__main__':
    main()
