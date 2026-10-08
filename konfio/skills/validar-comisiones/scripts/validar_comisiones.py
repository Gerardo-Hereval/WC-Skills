import argparse
import csv
import functools
import os
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Optional

IVA = 0.16
TOLERANCIA = 0.015
TIPOS_TOPUP = (3, 16, 24, 31, 32, 59)
PARAM = {1: "comisión", 2: "tasa", 3: "notional", 4: "plazo"}
CAMPOS_MANUALES = ("loan", "notional", "pct", "depositado", "lf_total")

LOANS_DEL_DIA = """
SELECT DISTINCT t.entity_id AS loan
FROM PAYMENTS.TRANSACTION_ORDER_OUTGOING t
WHERE t.transaction_product_id = 1 AND t.transaction_type_id = 2 AND t.transaction_status_id = 5
  AND t.created_date >= %(desde)s AND t.created_date < %(hasta)s
"""


def _sql_datos() -> str:
    ruta = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "queries", "datos_comisiones.sql")
    sql = open(ruta).read()
    inicio = sql.index("WHERE l.LOAN_ID IN (")
    return sql[:inicio] + "WHERE l.LOAN_ID = %(loan)s"


def f(x) -> Optional[float]:
    if x is None or x == "":
        return None
    return float(x)


def m(x) -> str:
    return "-" if x is None else f"{x:,.2f}"


def igual(a, b) -> bool:
    return a is not None and b is not None and abs(a - b) < TOLERANCIA


@dataclass
class Caso:
    loan: int
    app: Optional[int]
    tipo: str
    rec: str
    dispersado: Optional[str]
    notional: float
    max_notional: Optional[float]
    notional_sel: Optional[float]
    pct: float
    con_iva: bool
    lf_total: Optional[float]
    debio: float
    cobrado: Optional[float]
    factura: Optional[tuple]
    fee_paid: Optional[float]
    negociaciones: list
    lf_sobre_max: bool
    problemas: list
    new_money: Optional[float] = None


def _parsear_negociaciones(texto: Optional[str]) -> list:
    if not texto:
        return []
    por_id: dict = {}
    for parte in texto.split(";"):
        campos = parte.split("|")
        if len(campos) != 8:
            continue
        nid, fecha, por, tipo, param, original, old, new = campos
        n = por_id.setdefault(nid, {"fecha": fecha[:10], "por": por, "tipo": tipo, "cambios": []})
        despues = f(new) if new != "" else f(old)
        antes = f(old) if (old != "" and new != "") else f(original)
        if antes is not None and despues is not None and antes != despues:
            n["cambios"].append(f"{PARAM.get(int(param), param)} de {m(antes)} a {m(despues)}")
    return [f"  {v['fecha']} (tipo {v['tipo']}, por {v['por']}): " + (", ".join(v["cambios"]) or "sin cambios") for v in por_id.values()]


def analizar(r: dict) -> Caso:
    rec = (r.get("rec") or "-").strip() or "-"
    tipo_id = int(r["tipo_id"]) if r.get("tipo_id") not in (None, "") else None
    pct = f(r.get("pct")) or 0.0
    lf_total = f(r.get("lf_total"))
    lf_iva = f(r.get("lf_iva")) or 0.0
    con_iva = lf_iva > 0 if r.get("con_iva") in (None, "") else str(r["con_iva"]).lower() in ("1", "true", "si", "sí")
    lf_base = f(r.get("lf_base"))
    if lf_base is None and lf_total is not None:
        lf_base = round(lf_total / (1 + IVA) if con_iva else lf_total, 2)
    notional = f(r["notional"])
    es_topup = rec == "T" and (tipo_id is None or tipo_id in TIPOS_TOPUP)
    liq = f(r.get("liq"))
    new_money = f(r.get("new_money"))
    base_calculo = (new_money if new_money is not None else notional - (liq or 0)) if es_topup else notional
    debio = round(pct * base_calculo * (1 + IVA if con_iva else 1), 2)
    depositado = f(r.get("depositado"))
    cobrado = None if depositado is None else round(base_calculo - depositado, 2)
    factura = None
    if f(r.get("factura_total")) is not None:
        factura = (f(r.get("factura_total")), f(r.get("factura_subtotal")), f(r.get("factura_iva")))
    negs = _parsear_negociaciones(r.get("negociaciones"))
    max_n = f(r.get("max_notional"))
    lf_sobre_max = bool(max_n and notional != max_n and lf_base is not None and abs(lf_base - round(pct * max_n, 2)) < 1 and not negs)
    fee_paid = f(r.get("fee_paid"))
    problemas = []
    if es_topup and new_money is not None and liq is not None and not igual(new_money, notional - liq):
        problemas.append(f"roa.new_money {m(new_money)} ≠ notional − liquidación {m(notional - liq)}")
    if es_topup and new_money is not None and f(r.get("roa_disburse")) is not None and f(r.get("roa_fee")) is not None and not igual(f(r.get("roa_disburse")), new_money - f(r.get("roa_fee"))):
        problemas.append(f"roa.amount_to_disburse {m(f(r.get('roa_disburse')))} ≠ new_money − roa.fee_amount {m(new_money - f(r.get('roa_fee')))}")
    if cobrado is not None and not igual(cobrado, debio):
        problemas.append(f"cobro {m(cobrado)} ≠ esperado {m(debio)}" + (" (LOAN_FEE sobre el monto máximo, caso onboarding)" if lf_sobre_max else ""))
    if lf_sobre_max and cobrado is None:
        problemas.append("LOAN_FEE sobre el monto máximo; al dispersar cobraría de más")
    if factura and cobrado is not None and not igual(factura[0], cobrado):
        problemas.append(f"factura {m(factura[0])} ≠ cobro {m(cobrado)}")
    if cobrado is not None and fee_paid is not None and not igual(fee_paid, cobrado):
        razon = fee_paid / cobrado if cobrado else 0
        detalle = " (= cobro × 1.16: IVA sumado al pago inicial, no al cliente)" if abs(razon - 1.16) < 0.005 else ""
        problemas.append(f"pago inicial {m(fee_paid)} ≠ cobro {m(cobrado)}{detalle}")
    dispersado = r.get("dispersado")
    if hasattr(dispersado, "strftime"):
        dispersado = dispersado.strftime("%d-%b")
    elif dispersado:
        dispersado = str(dispersado)[:10]
    elif depositado is not None:
        dispersado = "fecha no indicada"
    return Caso(int(r["loan"]), int(r["app"]) if r.get("app") not in (None, "") else None, r.get("tipo") or "-", rec, dispersado,
                notional, max_n, f(r.get("notional_sel")), pct, con_iva, lf_total, debio, cobrado, factura, fee_paid, negs, lf_sobre_max, problemas, new_money)


def imprimir(c: Caso) -> str:
    out = [f"Caso {c.loan} (App {c.app or '-'}, {c.tipo}, {('dispersado, ' + c.dispersado if c.dispersado == 'fecha no indicada' else 'dispersado el ' + c.dispersado) if c.dispersado else 'sin dispersar'})"]
    pantalla = f"Monto en pantalla = {m(c.max_notional)}"
    if c.notional_sel is not None and c.notional_sel != c.max_notional:
        pantalla += f"; elegido {m(c.notional_sel)}"
    if c.notional != (c.notional_sel or c.max_notional or c.notional):
        pantalla += f"; notional del crédito {m(c.notional)}"
    out.append("- " + pantalla)
    out.append("- Negociaciones: " + ("ninguna" if not c.negociaciones else ""))
    out += c.negociaciones
    out.append(f"- % comisión = {c.pct * 100:.2f}%, {'con IVA desglosado' if c.con_iva else 'sin IVA desglosado (IVA incluido)'}")
    if c.lf_total is not None:
        out.append(f"- Comisión registrada (LOAN_FEE) = {m(c.lf_total)}" + (" ❌ calculada sobre el monto máximo" if c.lf_sobre_max else ""))
    base = (f"dinero nuevo {m(c.new_money)} (roa.new_money)" if c.new_money is not None else "dinero nuevo") if c.rec == "T" else m(c.notional)
    out.append(f"- Monto que se debió cobrar = {c.pct * 100:.2f}% × {base}{' + IVA' if c.con_iva else ''} = {m(c.debio)}")
    if c.cobrado is not None:
        out.append(f"- Monto cobrado = {m(c.cobrado)} {'✅' if igual(c.cobrado, c.debio) else '❌'}")
    if c.factura:
        ok = c.cobrado is not None and igual(c.factura[0], c.cobrado)
        nota = " (igual al cobro, pero el cobro está mal)" if ok and not igual(c.cobrado, c.debio) else ""
        desglose = f" ({m(c.factura[1])} + IVA {m(c.factura[2])})" if c.factura[1] is not None else ""
        out.append(f"- Factura = {m(c.factura[0])}{desglose} {'✅' if ok else '❌'}{nota}")
    elif c.cobrado is not None:
        out.append("- Factura = sin factura vigente")
    if c.fee_paid is not None and c.cobrado is not None:
        out.append(f"- Pago inicial registrado = {m(c.fee_paid)} {'✅' if igual(c.fee_paid, c.cobrado) else '❌'}")
    out.append("- Veredicto: " + ("sin problemas" if not c.problemas else "; ".join(c.problemas)))
    return "\n".join(out)


def filas_desde_bd(env: str, fecha: Optional[date], loans: list) -> list:
    import mysql.connector
    from dotenv import load_dotenv

    from refacturacion.config import Settings
    from refacturacion.db import DatabaseConnection
    from refacturacion_inicial.cli import token_provider

    load_dotenv(os.path.join(os.getcwd(), ".env"))
    settings = Settings.from_env(env)
    db = DatabaseConnection(host=settings.db_host, user=settings.db_user, database=settings.db_name, port=settings.db_port,
                            ssl_ca=settings.ssl_ca, token_provider=token_provider(settings, "iam"),
                            connect=functools.partial(mysql.connector.connect, use_pure=True, auth_plugin="mysql_clear_password"))
    sql = _sql_datos()
    with db:
        ids = list(loans)
        if fecha:
            desde = datetime.combine(fecha, datetime.min.time())
            ids += [int(r["loan"]) for r in db.query(LOANS_DEL_DIA, {"desde": desde, "hasta": desde + timedelta(days=1)})]
        filas = []
        for loan in sorted(set(ids)):
            filas += db.query(sql, {"loan": loan})
    return filas


def filas_desde_tsv(ruta: str) -> list:
    with open(ruta, newline="") as fh:
        encabezado = fh.readline()
        fh.seek(0)
        delimitador = "\t" if "\t" in encabezado else ","
        return list(csv.DictReader(fh, delimiter=delimitador))


def fila_manual(texto: str) -> dict:
    fila = dict(p.split("=", 1) for p in texto.split(","))
    faltan = [c for c in CAMPOS_MANUALES if c not in fila]
    if faltan:
        raise SystemExit(f"--manual necesita al menos {', '.join(CAMPOS_MANUALES)}; faltan: {', '.join(faltan)}")
    if float(fila["pct"]) > 1:
        fila["pct"] = str(float(fila["pct"]) / 100)
    return fila


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Valida comisiones iniciales por día, por loan, desde un TSV exportado o con datos manuales. Solo lectura.")
    p.add_argument("--env", choices=("dev", "prod"), help="con acceso a BD: ambiente")
    p.add_argument("--fecha", type=date.fromisoformat, help="día de dispersión (CDMX); requiere --env")
    p.add_argument("--loan", type=int, action="append", help="loan_id; requiere --env")
    p.add_argument("--datos", help="TSV/CSV exportado con queries/datos_comisiones.sql (sin acceso a BD)")
    p.add_argument("--manual", action="append", help='sin BD: "loan=488197,notional=125000,pct=5.17,con_iva=1,lf_total=19430.93,depositado=105569.07,fee_paid=19430.93,factura_total=19430.93,max_notional=324000"')
    p.add_argument("--solo-problemas", action="store_true")
    p.add_argument("--tsv", help="guardar la tabla de resultados")
    a = p.parse_args(argv)
    if a.datos:
        filas = filas_desde_tsv(a.datos)
    elif a.manual:
        filas = [fila_manual(t) for t in a.manual]
    elif a.env and (a.fecha or a.loan):
        filas = filas_desde_bd(a.env, a.fecha, a.loan or [])
    else:
        p.error("usa --env con --fecha/--loan, o --datos archivo, o --manual ...")
    casos = [analizar(r) for r in filas]
    mostrados = [c for c in casos if c.problemas or not a.solo_problemas]
    print(f"{len(casos)} créditos, {sum(1 for c in casos if c.problemas)} con problemas\n")
    print("\n\n".join(imprimir(c) for c in mostrados))
    if a.tsv:
        with open(a.tsv, "w", newline="") as fh:
            w = csv.writer(fh, delimiter="\t")
            w.writerow(["Loan", "App", "Tipo", "Rec", "Dispersado", "Notional", "MaxNotional", "Pct", "ConIVA", "LOAN_FEE", "Esperado", "Cobrado", "Factura", "PagoInicial", "Problemas"])
            for c in casos:
                w.writerow([c.loan, c.app, c.tipo, c.rec, c.dispersado, c.notional, c.max_notional, c.pct, c.con_iva, c.lf_total, c.debio, c.cobrado,
                            c.factura[0] if c.factura else None, c.fee_paid, "; ".join(c.problemas)])
        print(f"\nTSV: {a.tsv}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
