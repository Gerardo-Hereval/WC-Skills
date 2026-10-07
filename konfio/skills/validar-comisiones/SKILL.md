---
name: validar-comisiones
description: >-
  Valida las comisiones iniciales de los créditos WC dispersados en una fecha
  (o una lista de loans): monto en pantalla vs negociado, LOAN_FEE y su
  convención de IVA, lo que se debió cobrar, lo que Kanto cobró, la factura y
  el pago inicial registrado, con veredicto por crédito. Úsalo cuando pidan
  "validar las comisiones del día X", "revisar estos loans", "¿se cobró doble
  IVA?", "¿la comisión está sobre el monto correcto?" o el análisis caso por
  caso de un loan.
---

# Validar comisiones iniciales por día o por loan

## Qué hace
Para cada crédito, reconstruye el cálculo completo y lo presenta en el formato que usa el equipo:

```
Caso <loan> (App <app>, <tipo>, dispersado el <fecha> | sin dispersar)
- Monto en pantalla = <max_notional de PRODUCT_OFFERING_RESULT> → elegido <notional de PRODUCT_OFFERING_SELECTED>
- Negociaciones: <fecha> tipo <n>: notional a X, comisión de A% a B% ...
- % comisión = <Σ fee_percent>, con IVA desglosado | sin IVA desglosado
- Monto que se debió cobrar = % × notional [+ IVA] = ...
- Monto cobrado = notional [− liquidación] − depósito Kanto = ... ✅/❌
- Factura = total (subtotal + IVA) ✅/❌
- Pago inicial registrado = fee_paid ✅/❌
- Veredicto
```

Reglas (acordadas con el lead, 2026-10):
- **Cobro real** = `LOAN.NOTIONAL − depósito Kanto`; en TopUp además `− (roa.principal_due + roa.interest_due)`.
- **Convención de IVA**: si las filas activas de `LOAN_FEE` traen `fee_iva_amount` 0, el porcentaje ya incluye el IVA; si traen IVA, va encima. No se compara contra el contrato.
- **Qué factura la lambda**: `roa.fee_amount` en TopUp/Former; `INITIAL_PAYMENT.fee_paid` en el resto.
- **Comisión sobre el monto correcto**: `LOAN_FEE.fee_amount_base` debe ser `fee_percent × LOAN.NOTIONAL`. Si coincide con `fee_percent × max_notional` y el notional es menor, es el caso 488197 (onboarding no recalcula).
- **Notional mayor al elegido**: si hay negociación de Salesforce con el notional como parámetro, el +3% es el tope de la regla y es válido.

## Cómo obtener los datos (tres modos, según el acceso que tenga quien valida)

| Tienes | Modo | Comando |
|---|---|---|
| Sesión AWS SSO + proyecto `~/Documents/porjects/script` (venv, `.env`, `global-bundle.pem`) | **BD directa** | `--env prod --fecha 2026-10-06` o `--env prod --loan 473839 --loan 479692` |
| Solo lectura a la réplica de MySQL (Metabase, DBeaver, Redshift espejo) | **TSV exportado** | correr `queries/datos_comisiones.sql` con la fecha deseada, exportar a TSV/CSV y pasar `--datos archivo.tsv` |
| Nada de lo anterior, solo los números del caso | **Manual** | `--manual "loan=488197,notional=125000,pct=5.17,con_iva=1,lf_total=19430.93,depositado=105569.07,fee_paid=19430.93,factura_total=19430.93,max_notional=324000"` |

El script no necesita AWS ni BD en los modos TSV y manual; solo Python 3. En modo BD se corre desde el proyecto `script`:

```bash
cd ~/Documents/porjects/script
PYTHONPATH=. .venv/bin/python <skill>/scripts/validar_comisiones.py --env prod --fecha 2026-10-06 --solo-problemas --tsv ~/Downloads/comisiones-2026-10-06.tsv
PYTHONPATH=. .venv/bin/python <skill>/scripts/validar_comisiones.py --env prod --loan 473839 --loan 479692
```

Modos sin BD (hay un archivo de muestra en `examples/datos_comisiones.ejemplo.tsv`, con 4 créditos del 2026-10-05, uno con problema):

```bash
python3 <skill>/scripts/validar_comisiones.py --datos ~/Downloads/datos_comisiones.tsv --solo-problemas
python3 <skill>/scripts/validar_comisiones.py --manual "loan=...,notional=...,pct=...,con_iva=1,lf_total=...,depositado=...,fee_paid=...,factura_total=..."
```

Campos del modo manual: obligatorios `loan`, `notional`, `pct` (acepta 5.17 o 0.0517), `depositado`, `lf_total`; opcionales `con_iva` (1/0; sin él se asume incluido), `fee_paid`, `factura_total`, `factura_subtotal`, `factura_iva`, `max_notional`, `notional_sel`, `liq` (TopUp: liquidación del crédito anterior), `rec` (T/F), `app`, `tipo`. Si alguien pasa cifras de pantalla, pídele notional, depósito de Kanto y la comisión registrada; con eso ya sale el veredicto de cobro.

`--fecha` y la consulta toman los créditos con depósito de Kanto completado ese día (CDMX). `--solo-problemas` oculta los ✅. `--tsv` guarda la tabla.

## Cómo leer el resultado
- ✅ en cobro, factura y pago inicial: el crédito está bien.
- ❌ en cobro con LOAN_FEE sobre `max_notional`: caso onboarding (488197); corregir LOAN_FEE por DDL si no se ha dispersado, devolución si ya se dispersó.
- ❌ solo en pago inicial con razón 1.16: el post-dispersión sumó IVA a una comisión cobrada sin IVA; es un dato, no un cobro doble. Corregir `fee_due/fee_paid` por DDL (precedente #6026).
- ❌ en factura: ver si hay cancelación en curso (`FINANCE.CFDI_CANCELLING`) antes de pedir otra.
- "IVA doble" reportado por contabilidad: casi siempre es IVA dentro de la factura + IVA sumado en `INITIAL_PAYMENT`; al cliente se le cobró una vez.

## Trampas
- El modo TSV detecta tabulador o coma por el encabezado; la columna `negociaciones` trae `;` y `|` adentro, no la rompas al exportar.
- No encadenar la salida con `head`: el script escribe al final.
- La BD guarda `TAX_STAMP_TS` en CDMX y `LOAN_CHANGE_REQUEST` una hora adelantada.
- Consultas sobre `PAYMENTS.TRANSACTION_ORDER_OUTGOING` siempre por loan (subconsulta), nunca JOIN a toda la tabla.
