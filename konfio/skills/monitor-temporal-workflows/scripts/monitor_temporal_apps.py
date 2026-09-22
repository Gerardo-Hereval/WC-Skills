#!/usr/bin/env python3
"""
Monitorea el estado de workflows de Temporal (funnel WC / Former OD) para una
lista de application IDs, en loop, y marca rechazos y errores.

Máquina por defecto: wc-ondemand@1.0.0 (Former OD tipos 60/61 + XSell 62/63).
También sirve para wc-ftl@1.0.0 (primer crédito, tipos 1/5) con --machine.

Uso:
  python monitor_temporal_apps.py --env prd --token <TOKEN> --apps 2719676,2719854 --interval 30
  python monitor_temporal_apps.py --env dev --token <TOKEN> --apps 2714684 --cycles 1 --output full

Token:
  - prd: JWT de tu sesión de platform.konfio.mx (aud api.konfio.mx). Vive ~5 min.
  - dev: JWT de dev-platform.konfio.mx (aud dev.api.konfio.mx). Vive ~5 min.
  Sácalo del navegador: F12 -> Network -> request a api.konfio.mx -> header Authorization.
  Si expira, el script lo detecta (401) y te avisa para refrescarlo.

Estados clave (wc-ondemand): check -> personalInfo/companyParticipation -> satCredentials
  -> (waitingRoom | addShareholder->waitShareholder | creditBureau) -> waitingRoom
  -> orchestratorResponse -> offerAccept | rejected.

Flags:
  [REJECTED]  currentState == rejected (o resultPath onRejected). Se muestra si entityOffers
              salió vacío (products {}), que es el motivo mecánico: el scoring no dio oferta WC.
              El motivo de negocio (buró/capacidad/política) NO está en el actor: va en core
              (/funnel/{app}/rejection-reasons con sesión admin, CloudWatch, o BD).
  [ERROR]     errorHistory.count > 0 (falla técnica). Muestra el último error.
  [401]       token expirado -> refresca el token.
"""
import argparse
import sys
import time

import requests


def build_base_url(env: str) -> str:
    prefix = "dev." if env == "dev" else ""
    return f"https://{prefix}api.konfio.mx/i02/c01/workflows/state-machines-api/v1/actors"


def fetch(app_id: int, machine: str, base_url: str, token: str) -> dict:
    url = f"{base_url}/{app_id}_{machine}"
    r = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=25)
    out = {"status": r.status_code}
    try:
        out["body"] = r.json()
    except Exception:
        out["body"] = {"raw": r.text[:200]}
    return out


def summarize(app_id: int, res: dict) -> str:
    status = res["status"]
    body = res["body"]
    if status == 401:
        return f"  [401] {app_id:>10}  TOKEN EXPIRADO — refresca el token y vuelve a correr"
    if status != 200:
        msg = (body.get("error") or {}).get("message") if isinstance(body, dict) else body
        return f"  [{status}] {app_id:>10}  {msg}"
    data = body.get("data") if isinstance(body, dict) else None
    if not data:
        return f"  [ ] {app_id:>10}  sin workflow"
    ctx = (data.get("context") or {}).get("data") or {}
    state = data.get("currentState")
    resp = ctx.get("resultPath")
    errc = ((ctx.get("errorHistory") or {}).get("count")) or 0
    tipo = ctx.get("applicationTypeId")
    np = ctx.get("naturalPersonId")
    rfc = ctx.get("rfc")
    offers = ctx.get("entityOffers") or {}
    products = offers.get("products") if isinstance(offers, dict) else None

    flags = []
    if state == "rejected" or resp == "onRejected":
        empty = " offers vacío (sin oferta WC del scoring)" if products == {} else ""
        flags.append(f"[REJECTED]{empty}")
    if errc:
        last = ((ctx.get("errorHistory") or {}).get("history") or [])
        last_msg = last[-1] if last else ""
        flags.append(f"[ERROR x{errc}: {str(last_msg)[:80]}]")

    symbol = "✗" if flags else "•"
    line = (f"  [{symbol}] {app_id:>10}  {str(state):<20} resp={resp} err={errc} "
            f"tipo={tipo} np={np} rfc={rfc}")
    if flags:
        line += "  " + " ".join(flags)
    return line


def main() -> None:
    p = argparse.ArgumentParser(description="Monitorea estados de workflows Temporal por app ID")
    p.add_argument("--env", choices=["dev", "prd"], default="prd")
    p.add_argument("--token", required=True, help="Bearer (con o sin 'Bearer ')")
    p.add_argument("--apps", required=True, help="IDs separados por coma, ej. 2719676,2719854")
    p.add_argument("--machine", default="wc-ondemand@1.0.0", help="máquina@version (def wc-ondemand@1.0.0)")
    p.add_argument("--interval", type=int, default=30, help="segundos entre ciclos (def 30)")
    p.add_argument("--cycles", type=int, default=0, help="0 = infinito (def 0)")
    p.add_argument("--output", choices=["summary", "full"], default="summary")
    args = p.parse_args()

    token = args.token[len("Bearer "):] if args.token.startswith("Bearer ") else args.token
    base_url = build_base_url(args.env)
    apps = [int(x) for x in args.apps.replace(" ", "").split(",") if x]

    print(f"env={args.env}  machine={args.machine}  apps={apps}  interval={args.interval}s")
    print("-" * 90)

    cycle = 0
    while True:
        cycle += 1
        buckets = {"ok": [], "rejected": [], "error": [], "auth": [], "other": []}
        print(f"[ciclo {cycle}  {time.strftime('%H:%M:%S')}]")
        for app_id in apps:
            try:
                res = fetch(app_id, args.machine, base_url, token)
            except Exception as e:  # noqa: BLE001
                print(f"  [E] {app_id:>10}  {e}")
                buckets["other"].append(app_id)
                continue
            print(summarize(app_id, res))
            if args.output == "full" and res["status"] == 200 and res["body"].get("data"):
                import json
                print(json.dumps(res["body"]["data"].get("context", {}).get("data", {}), indent=2, ensure_ascii=False))
            st = res["status"]
            body = res["body"]
            if st == 401:
                buckets["auth"].append(app_id)
            elif st != 200:
                buckets["other"].append(app_id)
            else:
                data = body.get("data") or {}
                ctx = (data.get("context") or {}).get("data") or {}
                if data.get("currentState") == "rejected" or ctx.get("resultPath") == "onRejected":
                    buckets["rejected"].append(app_id)
                elif ((ctx.get("errorHistory") or {}).get("count")) or 0:
                    buckets["error"].append(app_id)
                else:
                    buckets["ok"].append(app_id)
        print(f"  resumen: ok={buckets['ok']} rejected={buckets['rejected']} "
              f"error={buckets['error']} 401={buckets['auth']} otros={buckets['other']}")
        if buckets["auth"]:
            print("  >> Hay 401: el token expiró. Refresca el token de tu navegador y relanza.")
            sys.exit(2)
        print("-" * 90)

        if args.cycles and cycle >= args.cycles:
            break
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
