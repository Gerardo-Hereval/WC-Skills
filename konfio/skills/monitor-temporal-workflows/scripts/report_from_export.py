#!/usr/bin/env python3
"""Consulta todos los actores de un export de Temporal y arma los datos del reporte.

Uso:
  TK="$(pbpaste)" python3 -I report_from_export.py <workflows-export.json> [--env prd|dev]

Deja un snapshot (appId, estado, tipo; sin PII) en ~/.cache/monitor-temporal-workflows/ y lo compara contra el anterior.
"""
import concurrent.futures as cf
import datetime as dt
import json
import os
import re
import sys
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

SNAP_DIR = Path.home() / ".cache" / "monitor-temporal-workflows"
TYPE_NAMES = {"60": "Former OD PFAE", "61": "Former OD PM", "62": "XSell PFAE", "63": "XSell PM", "1": "FTL PFAE", "5": "FTL PM"}
LONG_WAIT_H = 40


def fetch(base, token, wid):
    req = urllib.request.Request(f"{base}/{wid}", headers={"Authorization": f"Bearer {token}", "User-Agent": "curl/8.7.1", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return wid, 200, json.load(r)
    except urllib.error.HTTPError as e:
        return wid, e.code, None
    except Exception:
        return wid, 0, None


def real_type(ctx):
    t = str(ctx.get("applicationTypeId") or "")
    if t == "62" and ctx.get("entityType") == "company":
        return "63"
    if t == "1" and ctx.get("entityType") == "company":
        return "5"
    return t


def main():
    export = Path(sys.argv[1])
    env = sys.argv[sys.argv.index("--env") + 1] if "--env" in sys.argv else "prd"
    token = os.environ["TK"].removeprefix("Bearer ").strip()
    host = "api.konfio.mx" if env == "prd" else "dev.api.konfio.mx"
    base = f"https://{host}/i02/c01/workflows/state-machines-api/v1/actors"

    wfs = json.loads(export.read_text())["workflows"]
    meta = {w["id"]: w for w in wfs}
    with cf.ThreadPoolExecutor(int(os.environ.get("MTW_WORKERS", "4"))) as ex:
        results = list(ex.map(lambda w: fetch(base, token, w), meta))

    codes = Counter(c for _, c, _ in results)
    if codes.get(401):
        print(f"[401] token expirado en {codes[401]} actores; pide uno nuevo", file=sys.stderr)

    now = dt.datetime.now(dt.timezone.utc)
    rows = {}
    for wid, code, body in results:
        app = wid.split("_")[0]
        start = dt.datetime.strptime(meta[wid]["startTime"][:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=dt.timezone.utc)
        hours = round((now - start).total_seconds() / 3600)
        if code != 200:
            rows[app] = {"state": f"HTTP{code}", "type": "", "hours": hours, "status": meta[wid]["status"]}
            continue
        d = body["data"]
        ctx = d["context"]["data"]
        hist = (ctx.get("errorHistory") or {}).get("history") or []
        rows[app] = {
            "state": d["currentState"],
            "type": real_type(ctx),
            "hours": hours,
            "status": meta[wid]["status"],
            "err_count": (ctx.get("errorHistory") or {}).get("count", 0),
            "last_error": re.sub(r"https://\S+", "<url>", hist[-1]["errorMessage"].split(" | Request ID")[0]) if hist else "",
            "products": list((ctx.get("entityOffers") or {}).get("products") or {}),
        }

    SNAP_DIR.mkdir(parents=True, exist_ok=True)
    prev_files = sorted(SNAP_DIR.glob("*.json"))
    prev = json.loads(prev_files[-1].read_text()) if prev_files else {}
    for a, r in rows.items():
        if not r["type"] and a in prev:
            r["type"] = prev[a]["type"]

    starts = sorted(w["startTime"] for w in wfs)
    out = {
        "consulta": now.isoformat(timespec="minutes"),
        "export": export.name,
        "rango_startTime": [starts[0][:16], starts[-1][:16]],
        "http": dict(codes),
        "por_estado": Counter(r["state"] for r in rows.values()).most_common(),
        "por_tipo": {f"{t} {TYPE_NAMES.get(t, 'sin tipo')}": n for t, n in sorted(Counter(r["type"] for r in rows.values() if not r["state"].startswith("HTTP")).items())},
        "rejected_con_productos": {a: r["products"] for a, r in rows.items() if r["state"] == "rejected" and r["products"]},
        "errores": defaultdict(list),
        "esperas_largas": defaultdict(list),
    }
    for a, r in sorted(rows.items(), key=lambda kv: -kv[1]["hours"]):
        if r.get("err_count"):
            out["errores"][r["last_error"]].append(f"{a} ({TYPE_NAMES.get(r['type'], r['type'])}) {r['state']} {r['hours']}h x{r['err_count']}")
        if r["hours"] > LONG_WAIT_H and r["state"] not in ("rejected", "completed") and not r["state"].startswith("HTTP"):
            out["esperas_largas"][r["state"]].append(f"{a} ({TYPE_NAMES.get(r['type'], r['type'])}) {r['hours']}h")

    if prev_files:
        changes = defaultdict(list)
        for a, r in rows.items():
            if a in prev and prev[a]["state"] != r["state"]:
                changes[f"{prev[a]['state']} -> {r['state']}"].append(f"{a} ({TYPE_NAMES.get(r['type'], r['type'])})")
        out["cambios_vs"] = prev_files[-1].name
        out["en_ambas"] = sum(1 for a in rows if a in prev)
        out["nuevas"] = sum(1 for a in rows if a not in prev)
        out["cambios"] = changes
    snap = SNAP_DIR / f"{now.strftime('%Y-%m-%dT%H%M')}.json"
    snap.write_text(json.dumps({a: {"state": r["state"], "type": r["type"]} for a, r in rows.items()}))
    out["snapshot"] = str(snap)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
