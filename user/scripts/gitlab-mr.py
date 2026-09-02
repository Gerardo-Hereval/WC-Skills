#!/usr/bin/env python3
"""
gitlab-mr.py — capa de API de GitLab para el skill /review-commit.

Todo lo mecanico (URLs, encoding, paginacion, SHAs, payloads) vive aqui para que
el modelo no gaste tokens reconstruyendo curl+python inline en cada corrida.

Requiere: GITLAB_TOKEN en el entorno.

Comandos:
  meta        <mr-url>                    Metadata + SHAs -> JSON en stdout
  diff        <mr-url>                    Descarga el diff completo (paginado)
  files       <mr-url> [extra_path ...]   Baja archivos tocados al head_sha
  search      <mr-url> <termino>          Busca en el repo al head_sha
  discussions <mr-url>                    Lista hilos existentes (dedup/re-review)
  publish     <mr-url> <findings.json>    Postea comentarios inline (con fallback)
  reply       <mr-url> <disc_id> <file>   Responde en un hilo
  resolve     <mr-url> <disc_id>          Marca un hilo como resuelto

El workdir por defecto es /tmp/review-<iid>/. Override con REVIEW_DIR.
"""

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

API = "https://gitlab.com/api/v4"


# --------------------------------------------------------------------------
# infra
# --------------------------------------------------------------------------

def die(msg, code=1):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def token():
    t = os.environ.get("GITLAB_TOKEN")
    if not t:
        die("GITLAB_TOKEN no esta en el entorno.\n"
            "Pide al usuario que ejecute:  ! export GITLAB_TOKEN=<su-token>")
    return t


def api(path, params=None, method="GET", body=None, raw=False):
    """Llama la API. Devuelve (data, headers). Falla ruidosamente en != 2xx."""
    url = f"{API}/{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("PRIVATE-TOKEN", token())
    if body is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req) as r:
            payload = r.read()
            headers = dict(r.headers)
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:400]
        hint = ""
        if e.code == 401:
            hint = "  -> token invalido o expirado"
        elif e.code == 404:
            hint = "  -> proyecto/MR inexistente, o el token no tiene acceso"
        die(f"HTTP {e.code} en {path}{hint}\n{detail}")
    except urllib.error.URLError as e:
        die(f"red: {e.reason}")
    if raw:
        return payload, headers
    return json.loads(payload), headers


def paginate(path, params=None):
    """Recorre TODAS las paginas. Arregla el bug de per_page=100 sin loop."""
    params = dict(params or {})
    params["per_page"] = 100
    page, out = 1, []
    while True:
        params["page"] = page
        chunk, headers = api(path, params)
        if not isinstance(chunk, list):
            return chunk
        out.extend(chunk)
        nxt = headers.get("X-Next-Page", "")
        if not nxt.strip():
            break
        page = int(nxt)
    return out


def parse_url(mr_url):
    """https://gitlab.com/<group>/<proj>/-/merge_requests/<iid> -> (enc_path, iid)"""
    if "/merge_requests/" not in mr_url:
        die(f"no parece URL de MR (falta /merge_requests/): {mr_url}")
    left, right = mr_url.split("/merge_requests/", 1)
    project = left.split("gitlab.com/", 1)[-1].rstrip("/")
    if project.endswith("/-"):
        project = project[:-2]
    iid = right.strip("/").split("/")[0].split("?")[0]
    if not iid.isdigit():
        die(f"no pude extraer el IID del MR de: {mr_url}")
    return urllib.parse.quote(project, safe=""), iid


def flat(path):
    """apps/x/[...p]/route.ts -> apps__x__[...p]__route.ts (sin glob, sin cd)."""
    return path.replace("/", "__")


def workdir(iid):
    d = os.environ.get("REVIEW_DIR") or f"/tmp/review-{iid}"
    os.makedirs(d, exist_ok=True)
    return d


def load_meta(mr_url):
    """Metadata cacheada en disco para no re-pegarle a la API en cada comando."""
    enc, iid = parse_url(mr_url)
    cache = os.path.join(workdir(iid), "meta.json")
    if os.path.exists(cache):
        with open(cache) as f:
            return json.load(f)
    return cmd_meta(mr_url, quiet=True)


# --------------------------------------------------------------------------
# comandos
# --------------------------------------------------------------------------

def cmd_meta(mr_url, quiet=False):
    enc, iid = parse_url(mr_url)
    mr, _ = api(f"projects/{enc}/merge_requests/{iid}")
    versions, _ = api(f"projects/{enc}/merge_requests/{iid}/versions")
    if not versions:
        die("el MR no tiene versiones (¿sin commits?)")
    v = versions[0]
    # La API devuelve *_commit_sha, NO *_sha. Este era el bug del skill viejo.
    meta = {
        "project_id": mr["project_id"],
        "project_enc": enc,
        "iid": int(iid),
        "title": mr["title"],
        "author": mr.get("author", {}).get("name"),
        "state": mr["state"],
        "source_branch": mr["source_branch"],
        "target_branch": mr["target_branch"],
        "web_url": mr["web_url"],
        "base_sha": v["base_commit_sha"],
        "start_sha": v["start_commit_sha"],
        "head_sha": v["head_commit_sha"],
        "workdir": workdir(iid),
    }
    with open(os.path.join(meta["workdir"], "meta.json"), "w") as f:
        json.dump(meta, f, indent=2)
    if not quiet:
        print(json.dumps(meta, indent=2, ensure_ascii=False))
    return meta


def cmd_diff(mr_url):
    m = load_meta(mr_url)
    diffs = paginate(f"projects/{m['project_enc']}/merge_requests/{m['iid']}/diffs")
    out = os.path.join(m["workdir"], "diff.txt")
    paths = []
    with open(out, "w") as f:
        for d in diffs:
            p = d["new_path"]
            paths.append(p)
            flags = []
            if d.get("new_file"):
                flags.append("NUEVO")
            if d.get("deleted_file"):
                flags.append("BORRADO")
            if d.get("renamed_file"):
                flags.append(f"RENOMBRADO desde {d['old_path']}")
            f.write(f"=== FILE: {p} ==={('  [' + ', '.join(flags) + ']') if flags else ''}\n")
            f.write(d["diff"])
            f.write("\n\n")
    with open(os.path.join(m["workdir"], "paths.json"), "w") as f:
        json.dump(paths, f, indent=2)
    print(f"diff -> {out}  ({len(diffs)} archivos)")
    for p in paths:
        print(f"  {p}")


def cmd_files(mr_url, extra):
    """Baja los archivos tocados al head_sha. Sin cd, sin glob: inmune a [...path]."""
    m = load_meta(mr_url)
    pj = os.path.join(m["workdir"], "paths.json")
    if not os.path.exists(pj):
        die("corre primero:  gitlab-mr.py diff <mr-url>")
    with open(pj) as f:
        paths = json.load(f)
    head = os.path.join(m["workdir"], "head")
    os.makedirs(head, exist_ok=True)
    for p in list(paths) + list(extra):
        enc = urllib.parse.quote(p, safe="")
        try:
            blob, _ = api(
                f"projects/{m['project_enc']}/repository/files/{enc}/raw",
                {"ref": m["head_sha"]}, raw=True)
        except SystemExit:
            print(f"  MISS  {p}  (borrado en head, o ruta invalida)")
            continue
        dest = os.path.join(head, flat(p))
        with open(dest, "wb") as f:
            f.write(blob)
        n = blob.decode("utf-8", "replace").count("\n") + 1
        warn = "   <-- >1000 lineas" if n > 1000 else ""
        print(f"  OK    {p}  ({n} lineas){warn}")
    print(f"\nhead -> {head}   (nombres aplanados: '/' -> '__')")


def cmd_search(mr_url, term):
    """
    OJO: 'startline' de la API es la primera linea del SNIPPET devuelto, que trae
    lineas de contexto por delante — NO es la linea del match. Citar startline
    produce numeros corridos (verificado: reportaba 31 donde el archivo dice 33).
    Aqui se escanea el snippet y se emite la linea real de cada coincidencia.
    """
    m = load_meta(mr_url)
    res = paginate(f"projects/{m['project_enc']}/search",
                   {"scope": "blobs", "search": term, "ref": m["head_sha"]})
    needle, total = term.lower(), 0
    for r in res:
        start = r.get("startline") or 1
        lines = (r.get("data") or "").split("\n")
        matches = [(start + i, l.strip()[:72])
                   for i, l in enumerate(lines) if needle in l.lower()]
        if not matches:                      # el match cayo fuera del snippet
            print(f"  {r['path']}:~{start}  (linea aproximada: snippet sin coincidencia literal)")
            total += 1
            continue
        for ln, txt in matches:
            print(f"  {r['path']}:{ln}  |  {txt}")
            total += 1
    print(f"  total: {total} coincidencia(s) en {len(res)} bloque(s)"
          f"  (termino: {term!r} @ {m['head_sha'][:8]})")


def cmd_discussions(mr_url):
    """Hilos existentes: para dedup antes de postear y para el re-review."""
    m = load_meta(mr_url)
    ds = paginate(f"projects/{m['project_enc']}/merge_requests/{m['iid']}/discussions")
    out = []
    for d in ds:
        notes = [n for n in d.get("notes", []) if not n.get("system")]
        if not notes:
            continue
        first = notes[0]
        pos = first.get("position") or {}
        out.append({
            "id": d["id"],
            "resolved": bool(first.get("resolved")),
            "author": first.get("author", {}).get("username"),
            "file": pos.get("new_path"),
            "line": pos.get("new_line"),
            "notes": len(notes),
            "body": first.get("body", ""),
            "last_author": notes[-1].get("author", {}).get("username"),
        })
    dest = os.path.join(m["workdir"], "discussions.json")
    with open(dest, "w") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    for d in out:
        mark = "resuelto" if d["resolved"] else "ABIERTO "
        loc = f"{d['file']}:{d['line']}" if d["file"] else "(general)"
        print(f"  [{mark}] {d['id'][:8]}  {loc}  notas={d['notes']}  por @{d['author']}")
        print(f"            {d['body'][:100].splitlines()[0] if d['body'] else ''}")
    print(f"\n{len(out)} hilos -> {dest}")


def cmd_publish(mr_url, findings_file):
    """
    findings.json:  {"findings": [{"file":..., "line":..., "body":...}, ...]}
    Postea inline; si la linea no esta en el diff, cae a comentario general.
    Deduplica contra hilos ya existentes en el mismo archivo:linea.
    """
    m = load_meta(mr_url)
    with open(findings_file) as f:
        payload = json.load(f)
    findings = payload["findings"] if isinstance(payload, dict) else payload

    existing = set()
    dj = os.path.join(m["workdir"], "discussions.json")
    if os.path.exists(dj):
        with open(dj) as f:
            for d in json.load(f):
                if d.get("file"):
                    existing.add((d["file"], d["line"]))

    base = f"projects/{m['project_enc']}/merge_requests/{m['iid']}/discussions"
    for i, fd in enumerate(findings, 1):
        path, line, body = fd["file"], fd.get("line"), fd["body"]
        if (path, line) in existing:
            print(f"  {i}. SKIP (ya existe hilo en {path}:{line})")
            continue
        pos = {
            "position_type": "text",
            "base_sha": m["base_sha"],
            "start_sha": m["start_sha"],
            "head_sha": m["head_sha"],
            "old_path": path,
            "new_path": path,
            "new_line": line,
        }
        try:
            d, _ = api(base, method="POST", body={"body": body, "position": pos})
            print(f"  {i}. OK inline   {path}:{line}  -> {d['id'][:8]}")
        except SystemExit:
            d, _ = api(base, method="POST",
                       body={"body": f"**`{path}:{line}`**\n\n{body}"})
            print(f"  {i}. OK general  {path}:{line}  -> {d['id'][:8]}  (inline fallo)")


def cmd_reply(mr_url, disc_id, body_file):
    m = load_meta(mr_url)
    with open(body_file) as f:
        body = f.read()
    api(f"projects/{m['project_enc']}/merge_requests/{m['iid']}/discussions/{disc_id}/notes",
        method="POST", body={"body": body})
    print(f"OK reply -> {disc_id[:8]}")


def cmd_resolve(mr_url, disc_id):
    m = load_meta(mr_url)
    api(f"projects/{m['project_enc']}/merge_requests/{m['iid']}/discussions/{disc_id}",
        method="PUT", body={"resolved": True})
    print(f"OK resuelto -> {disc_id[:8]}")


# --------------------------------------------------------------------------

def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(0 if len(sys.argv) < 2 else 1)
    cmd, url, rest = sys.argv[1], sys.argv[2], sys.argv[3:]
    table = {
        "meta": lambda: cmd_meta(url),
        "diff": lambda: cmd_diff(url),
        "files": lambda: cmd_files(url, rest),
        "search": lambda: cmd_search(url, rest[0]),
        "discussions": lambda: cmd_discussions(url),
        "publish": lambda: cmd_publish(url, rest[0]),
        "reply": lambda: cmd_reply(url, rest[0], rest[1]),
        "resolve": lambda: cmd_resolve(url, rest[0]),
    }
    if cmd not in table:
        die(f"comando desconocido: {cmd}\n{__doc__}")
    table[cmd]()


if __name__ == "__main__":
    main()
