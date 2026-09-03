#!/usr/bin/env python3
"""Mirror a story's assets into the target space and emit an asset map.

For every asset the story references on the SOURCE space CDN:
  1. reuse a target asset with the same basename when one already exists
  2. otherwise download the bytes and run Storyblok's 3-step signed upload
     (create record -> POST to S3 -> finish_upload)

Prints {"<source asset id>": {"id":…, "filename":…}} on stdout, ready for
build-payload.py --asset-map.

Usage:
  upload-assets.py --story story.json --source-space 1023897 \
                   --target-space 567724046872094 [--asset-folder-id N] [--dry-run]

Needs STORYBLOK_TOKEN in the environment.
"""
import argparse, json, os, re, sys, urllib.request, urllib.error

API = 'https://api-us.storyblok.com/v1'
# /f/<space>/<dimensions>/<hash>/<filename>
CDN = re.compile(r'https://a-[a-z]{2}\.storyblok\.com/f/(\d+)/([^/]+)/([^/]+)/([^"?\s]+)')


def api(method, path, token, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(f'{API}{path}', data=data, method=method)
    req.add_header('Authorization', token)
    if data:
        req.add_header('Content-Type', 'application/json')
    with urllib.request.urlopen(req) as r:
        body = r.read()
    return json.loads(body) if body else {}


def collect_assets(node, source_space, found):
    """Asset objects in the story that still live on the source space."""
    if isinstance(node, dict):
        fn = node.get('filename')
        if node.get('fieldtype') == 'asset' and isinstance(fn, str):
            m = CDN.search(fn)
            if m and m.group(1) == source_space:
                found.setdefault(str(node.get('id')), {
                    'filename': fn, 'dimensions': m.group(2), 'basename': m.group(4),
                })
        for v in node.values():
            collect_assets(v, source_space, found)
    elif isinstance(node, list):
        for v in node:
            collect_assets(v, source_space, found)


def existing_by_basename(space, token):
    out, page = {}, 1
    while True:
        res = api('GET', f'/spaces/{space}/assets?per_page=100&page={page}', token)
        assets = res.get('assets', [])
        for a in assets:
            fn = a.get('filename') or ''
            m = CDN.search(fn)
            if m:
                out.setdefault(m.group(4), a)
        if len(assets) < 100:
            return out
        page += 1


def upload(space, token, meta, folder_id):
    """create record -> signed S3 POST -> finish_upload. Returns the asset."""
    payload = {'filename': meta['basename'], 'size': meta['dimensions']}
    if folder_id:
        payload['asset_folder_id'] = int(folder_id)
    signed = api('POST', f'/spaces/{space}/assets/', token, payload)

    with urllib.request.urlopen(meta['filename']) as r:
        blob = r.read()

    # multipart: every signed field first, `file` LAST — S3 answers 411 otherwise.
    boundary = '----storyblokpromote'
    parts = []
    for k, v in signed['fields'].items():
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
    parts.append(
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; '
        f'filename="{meta["basename"]}"\r\n\r\n'.encode() + blob + b'\r\n')
    parts.append(f'--{boundary}--\r\n'.encode())
    body = b''.join(parts)

    req = urllib.request.Request(signed['post_url'], data=body, method='POST')
    req.add_header('Content-Type', f'multipart/form-data; boundary={boundary}')
    with urllib.request.urlopen(req) as r:
        if r.status not in (200, 201, 204):
            raise RuntimeError(f'S3 upload failed: HTTP {r.status}')

    # finish_upload works with the Management token. (A sibling skill claims it
    # 404s and that MCP is required — that is the /finish path, not this one.)
    return api('GET', f'/spaces/{space}/assets/{signed["id"]}/finish_upload', token) or signed


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--story', required=True)
    p.add_argument('--source-space', required=True)
    p.add_argument('--target-space', required=True)
    p.add_argument('--asset-folder-id')
    p.add_argument('--dry-run', action='store_true')
    a = p.parse_args()

    token = os.environ.get('STORYBLOK_TOKEN')
    if not token:
        sys.exit('STORYBLOK_TOKEN is not set. Run: source ~/.zshrc')

    story = json.load(open(a.story))
    story = story.get('story', story)

    found = {}
    collect_assets(story['content'], a.source_space, found)
    if not found:
        print('{}')
        print('No source-space assets to mirror.', file=sys.stderr)
        return

    existing = existing_by_basename(a.target_space, token)
    mapping = {}
    for src_id, meta in found.items():
        hit = existing.get(meta['basename'])
        if hit:
            print(f"reuse  {meta['basename']} -> {hit['id']}", file=sys.stderr)
            mapping[src_id] = {'id': hit['id'], 'filename': hit['filename']}
            continue
        if a.dry_run:
            print(f"upload {meta['basename']} (dry run, not uploaded)", file=sys.stderr)
            continue
        asset = upload(a.target_space, token, meta, a.asset_folder_id)
        print(f"upload {meta['basename']} -> {asset['id']}", file=sys.stderr)
        mapping[src_id] = {'id': asset['id'], 'filename': asset['filename']}

    json.dump(mapping, sys.stdout, ensure_ascii=False, indent=2)


if __name__ == '__main__':
    main()
