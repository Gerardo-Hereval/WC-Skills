---
name: monitor-temporal-workflows
description: >-
  Monitorea el estado de workflows de Temporal del funnel WC / Former OD
  (máquinas wc-ondemand tipos 60/61/62/63, wc-ftl tipos 1/5) para una o varias
  application IDs, en dev o prod. Úsalo cuando pidan "monitorear", "ver el
  estado", "en qué va", "validar estatus" o "por qué se rechazó" de solicitudes
  por su applicationId o actor id (ej. 2719676_wc-ondemand@1.0.0). Detecta
  rechazos y errores y explica el motivo mecánico; el motivo de negocio de un
  rechazo vive en core, no en Temporal.
---

# Monitorear workflows de Temporal (funnel WC / Former OD)

## Cuándo usarlo
Cuando quieran saber en qué estado va una o varias solicitudes del funnel WC en Temporal (Former OD `wc-ondemand` tipos 60/61, XSell 62/63, o primer crédito `wc-ftl` tipos 1/5), seguirlas en el tiempo, o entender por qué se rechazaron. Aceptan un `applicationId` (ej. 2719676) o un actor id (`2719676_wc-ondemand@1.0.0`).

## Reporte del canal desde un export (flujo por defecto)
Si pasan un export de la UI de Temporal (`workflows-<N>-...json`) + "token en portapapeles", sigue el flujo completo sin preguntar en cada paso:

1. **Token primero, vive ~5 min.** Revisa `iss`/`exp` del JWT de `pbpaste` (sin imprimirlo) y corre de inmediato `TK="$(pbpaste)" python3 -I ${CLAUDE_PLUGIN_ROOT}/skills/monitor-temporal-workflows/scripts/report_from_export.py <export.json> --env prd` (solo librería estándar). Consulta todos los actores en paralelo (~15 s para 460), corrige el tipo (el actor trae 62 para XSell PM y 1 para FTL PM: con `entityType=company` pasan a 63 y 5), agrupa errores por mensaje, lista esperas > 40 h y compara contra el último snapshot de `~/.cache/monitor-temporal-workflows/` (solo appId, estado y tipo; sin PII). Los `completed` traen el contexto vacío y heredan el tipo del snapshot anterior. Si da `[401]`, pide otro token.
2. **Última actualización del canal.** Lee `#tmp-migracion-a-temporal` (`C0AQB5BB63G`) y ubica el último "Monitoreo Temporal". Retoma sus pendientes ("Siguiente paso", "Incoherencias BD") y di qué pasó con cada uno.
3. **Redacta** con el formato de abajo: "Cambio desde la pasada anterior" sale de `cambios`, más "Pendientes que siguen abiertos" del paso 2.
4. **Publica** en `C0AQB5BB63G` (markdown estándar, `**negritas**`), empezando con `:robot_face:` + CC a <@U0A0CH4KL20> (Luisa), <@UAS110BE3> (Guille) y <@U0B6T31KXSN> (Efren). Devuelve el link.

No es 100 % desatendido: el token de usuario expira en ~5 min, así que no se puede programar con cron.

## Herramienta principal (apps sueltas, en loop)
Script bundleado: `scripts/monitor_temporal_apps.py` (loop por lote, marca rechazos/errores). Requiere Python con `requests` (`pip install requests`, o un venv que lo tenga).

```bash
python scripts/monitor_temporal_apps.py \
  --env prd --token <TOKEN> --apps 2719676,2719854,2720022 --interval 30 --cycles 0
# --env dev|prd  --machine wc-ondemand@1.0.0 (o wc-ftl@1.0.0)  --cycles 0=infinito  --output full
```

## El token (lo más importante)
El endpoint (`https://{env}api.konfio.mx/i02/c01/workflows/state-machines-api/v1/actors/{id}`) pide un **Bearer de la sesión del usuario**, que **vive ~5 min**:
- **prod:** token de `platform.konfio.mx` (JWT `iss: auth.konfio.mx`, `aud: api.konfio.mx`).
- **dev:** token de `dev-platform.konfio.mx` (`iss: dev.auth.konfio.mx`, `aud: dev.api.konfio.mx`).
- Sacarlo del navegador: F12 → Network → request a `api.konfio.mx` → header `Authorization`.
- **Pide al usuario que lo corra con `!` o lo pegue recién copiado.** No monitorees prod desatendido: el token expira y da 401; el script lo detecta y avisa para refrescar. **Nunca guardes tokens** en memoria ni en archivos.
- Un token `iss: dev.auth.konfio.mx` es de DEV y no sirve para prod (y viceversa). Verifica `iss`/`aud` si algo da 401 o 404.

## Cómo leer el resultado
Por app: `estado`, `resp` (resultPath), `err` (errorHistory.count), `tipo`, `np`, `rfc`. Flags:
- `[REJECTED]` → `currentState=rejected` o `resultPath=onRejected`. Si `entityOffers.products` salió `{}`, el motivo **mecánico** es que el scoring no generó oferta WC. `err=0` = no es falla técnica, es decisión de negocio.
- `[ERROR xN]` → `errorHistory.count > 0` (falla técnica; muestra el último error).
- `[401]` → token expirado.

Secuencia `wc-ondemand`: `check → personalInfo/companyParticipation → satCredentials → (waitingRoom | addShareholder→waitShareholder | creditBureau) → waitingRoom → orchestratorResponse → offerAccept | rejected`. `satCredentials`/`waitingRoom` son estados de **espera** (no atorados).

## El motivo FINO de un rechazo NO está en Temporal
El actor solo muestra que la oferta salió vacía. El porqué (buró, capacidad, política, oferta expirada) vive en **core**:
1. `GET /core/funnel/{appId}/rejection-reasons` — necesita **cookie/token admin de prod** (no el Bearer de usuario, que además solo ve sus propias apps).
2. **CloudWatch prod** — logs del `orchestratorResponse`/scoring por `applicationId` (log group `/aws/ecs/i02-use1-c01-prd/i02-use1-c01-workflows-workflows-workers-prd`).
3. **BD prod** — resultado de scoring / `RecurrentOffer` de la app.

## Consultar UNA app rápido (sin loop)
```bash
curl -s "https://api.konfio.mx/i02/c01/workflows/state-machines-api/v1/actors/<appId>_wc-ondemand@1.0.0" \
  -H "Authorization: Bearer ${T#Bearer }" \
 | jq '{estado:.data.currentState, resp:.data.context.data.resultPath, err:(.data.context.data.errorHistory.count//0), tipo:.data.context.data.applicationTypeId, np:.data.context.data.naturalPersonId, rfc:.data.context.data.rfc, offers:.data.context.data.entityOffers.products}'
```
(el id pelón `<appId>` sin `_wc-ondemand@1.0.0` también resuelve la máquina.)

## Si no tienes las apps
Derívalas: por persona con `GET /core/funnel/person/{np}/active` (trae `externalReferenceId` = app id); o de CloudWatch (las transiciones traen el `applicationId`).

## Formato de reporte para Slack (aprobado 08-oct-2026)
Siempre con el **tipo de la app** (según BD: 60 Former OD PFAE, 61 Former OD PM, 62 XSell PFAE, 63 XSell PM, 1/5 FTL) junto a cada id. Medir antigüedad con el `startTime` del export de Temporal, NO con `lastTransitionTimestamp` (se refresca con cada lectura). Bloque de código con markdown de Slack (`*negritas*`, `•`, `:warning:`):

```
*Monitoreo Temporal — <N> workflows <máquina> (<rango de startTime>)*
Consulta: <fecha hora>. <ok>/<N> actores respondieron.

*Por estado*
• rejected: N — sin error técnico; M con `entityOffers.products` vacío (scoring sin oferta WC). <excepciones con id (tipo)>
• offerAccept: N
• satCredentials: N (espera del cliente)
• orchestratorResponse: N (esperando scoring)
• personalInfo: N
• waitingRoom / waitShareholder / discretional: ...

*Por tipo*
• 60 Former OD PFAE: N · 61 Former OD PM: N · 62 XSell PFAE: N · 63 XSell PM: N

*Errores técnicos (N)*
• <id> (<tipo>), <id> (<tipo>) — `<estado>`: "<errorMessage literal>" (<lectura: cliente / nuestra>)
• <id> (<tipo>) — `<estado>` desde hace <h> h: "<error>" :warning: <por qué importa>

*Esperas largas (horas desde inicio del workflow)*
• `<estado>` > 40 h — :warning: N apps ..., <patrón por tipo si lo hay>:
   <id> (<tipo>), ...
• <id> (<tipo>) — `<estado>` <h> h, <lectura>

*Cambio desde la pasada anterior*
• <id> (<tipo>): <estado anterior> → <estado nuevo>

*Hallazgo aparte (contexto, no bloquea)*
• ...

*Siguiente paso propuesto*
• ...
```
Cerrar con una observación de patrón (ej. "7 de 8 atoradas en orquestador son XSell PM"). Los `applicationId` sí van; nunca correos ni RFC.
