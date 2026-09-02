---
name: review-commit
description: >
  Review a commit or GitLab MR for maintainability (code-judo), SOLID, Clean
  Code, Clean Architecture, and frontend/backend standards. Walks through each
  finding one by one, asking the user before posting each one as an inline
  GitLab comment (with file + line number). En modo commit local, --fix aplica los fixes
  seguros en el working tree. Usage: /review-commit <commit-sha|gitlab-mr-url> [--fix]
user-invocable: true
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Grep
  - Glob
  - AskUserQuestion
  - Agent
---

# /review-commit — Code Review con comentarios en GitLab

Argumento recibido: `$ARGUMENTS`

Orquestas un review con **barra estricta de mantenibilidad**: no apruebes solo porque el
código funciona. Tú **no analizas el código directamente** — delegas en agentes y verificas
su trabajo.

## Reparto de trabajo y modelos

| Fase | Quién | Modelo | Por qué |
|---|---|---|---|
| Mecánica GitLab (fetch, diff, publicar) | `gitlab-mr.py` | — | Determinista, cero tokens |
| Orquestación (PASOS 1-2, 4, 6) | tú | sonnet | Coordinar, no razonar sobre código |
| Análisis del diff (PASO 3) | agente `code-reviewer` | **opus** | Es el juicio técnico real |
| Falsificación (PASO 3.5) | agente `code-reviewer` | **opus** | Auditoría independiente |
| Publicación (PASO 5) | agente `gitlab-publisher` | **haiku** | Mecánico sobre texto ya aprobado |

Si la sesión principal no está en sonnet, sigue igual — solo es la recomendación de costo.
Los subagentes **sí** debes lanzarlos con el `model` indicado, explícitamente.

## Regla cero — precisión antes que severidad

Un comentario incorrecto cuesta más que uno omitido: quema la credibilidad de todo el review
y le da al autor razón legítima para descartar el resto. La barra de mantenibilidad es
agresiva; la de **exactitud fáctica** es absoluta.

Tu responsabilidad como orquestador: **nunca publicar un hallazgo que no pasó falsificación
independiente**. No relajes esto aunque el agente suene seguro.

Referencia de tono/severidad: `${CLAUDE_PLUGIN_ROOT}/skills/maintainability-reference/SKILL.md`.

---

## PASO 1 — Detectar modo

- Contiene `gitlab.com` y `/merge_requests/` → **modo MR**
- Hash hexadecimal → **modo commit local**
- Vacío → `HEAD`

**Bandera `--fix`** (solo modo commit local): tras la falsificación, aplica los fixes seguros
en el working tree en vez de solo listarlos. Ver PASO 5-bis. En modo MR se ignora — dilo en
voz alta si te la pasan ahí, no la apliques en silencio.

---

## PASO 2 — Obtener contexto

### Modo MR

Todo con el script. **No escribas `curl` inline** — el script ya maneja paginación,
URL-encoding, rutas con `[...]`, y los nombres reales de los SHAs.

```bash
S=${CLAUDE_PLUGIN_ROOT}/scripts/gitlab-mr.py
python3 $S meta        "<mr-url>"   # título, autor, project_id, base/start/head_sha
python3 $S diff        "<mr-url>"   # -> /tmp/review-<iid>/diff.txt  (paginado completo)
python3 $S files       "<mr-url>"   # -> /tmp/review-<iid>/head/     (todos los tocados)
python3 $S discussions "<mr-url>"   # hilos existentes -> dedup + contexto previo
```

`meta` cachea en `/tmp/review-<iid>/meta.json`; los demás comandos lo reusan.

**`discussions` no es opcional.** Si ya hay hilos de un review anterior, dilo antes de
analizar — puede que el usuario quiera un re-review (ver sección final) y no un review nuevo.

Si el script dice que falta `GITLAB_TOKEN`, pide al usuario:
```
! export GITLAB_TOKEN=<su-token>
```

**Vecinos.** El diff dice qué cambió, no qué hay. Baja también los archivos que el diff
referencia y que el agente va a necesitar para verificar (helpers presuntamente duplicados,
constantes, contextos, servicios, fixtures):

```bash
python3 $S files "<mr-url>" "ruta/al/helper.ts" "ruta/al/contexto.tsx"
```

### Modo commit local

```bash
git show <SHA> --stat
git show <SHA> > /tmp/review-commit-<SHA>.txt
```
Los archivos "al head" son el working tree; el agente los lee directo del repo.

---

## PASO 2.4 — Detectores deterministas (antes del agente)

Hay reglas del equipo que **no son juicio**: o se cumplen o no. Esas no las decide un LLM
—se detectan con regex y emiten texto canónico idéntico en cada corrida.

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/review-detectors.py /tmp/review-<iid>/diff.txt \
  --json /tmp/review-<iid>/deterministic.json
```

Reglas cubiertas hoy:

| Detector | Severidad | Qué marca |
|---|---|---|
| `ui-in-unit-test` | **Alta** | `render()`, `screen.*`, `getBy*`/`findBy*`, `fireEvent`, `userEvent`, `toBeInTheDocument` en `*.test.*`/`*.spec.*` |
| `console-log` | Media | `console.log/debug/dir/trace` |
| `commented-code` | Media | Comentarios que contienen código muerto |
| `explanatory-comment` | Media | **Cualquier comentario de prosa** — incluido el que explica el "porqué" |
| `todo-without-ticket` | Baja | `TODO`/`FIXME` sin ticket (solo con `--allow-comments`) |

Flags: `--allow-jsdoc` exime la prosa JSDoc (`@param`, `@returns`, `@example`, `@see`);
`--allow-comments` apaga `explanatory-comment` por completo.

Garantías del script — **no las repliques ni las relajes**:

- Solo evalúa líneas **agregadas** (`+`). Nunca reclama código preexistente que el autor no tocó.
- Los números de línea salen del parseo de hunks, no de una estimación.
- **`renderHook` NO se marca**, y el import de `@testing-library/react` tampoco: `renderHook`
  vive en esa librería y es el patrón correcto para probar hooks. Marcar el import produce
  falsos positivos sobre tests legítimos.
- Archivos bajo `cypress/`, `e2e/`, `-e2e/` o `*.cy.*` quedan exentos de `ui-in-unit-test`.
- **Las directivas funcionales nunca se marcan** — `eslint-disable`, `@ts-expect-error`,
  `webpackChunkName`, `@vite-ignore`, `/** @type */`, `istanbul ignore`, `prettier-ignore`,
  `biome-ignore`, shebangs, headers de licencia y de código generado. Borrarlas cambia el
  build, el lint o los tipos: no son prosa, son configuración escrita en sintaxis de comentario.
- `explanatory-comment` solo aplica a archivos de código (`.ts`, `.tsx`, `.py`, `.go`…).
  YAML, shell, Dockerfile y `.env` quedan fuera: ahí comentar es idiomático.
- Un TODO en archivo de código lo cubre `explanatory-comment`, no `todo-without-ticket` —
  emitir ambos daría dos mensajes contradictorios sobre la misma línea ("agrégale ticket"
  vs "bórralo").
- Varias ocurrencias en un archivo = **un** comentario en la primera, con las demás listadas
  en el cuerpo. No inunda el MR.

**El texto de estos comentarios es canónico: publícalo tal cual.** No lo parafrasees, no lo
resumas, no le agregues contexto. Su valor está en que el equipo lo reconozca idéntico siempre.

Aun así, **abre con `Read` la línea citada de cada hallazgo Alta** antes de publicar. Es
barato y cubre el caso raro que el regex no previó.

---

## PASO 2.5 — Reglas del proyecto

Busca en orden y usa **el primero que exista**. Las dos últimas rutas son globales: aplican
aunque el review corra fuera del repo (modo MR normalmente no tiene checkout local).

```bash
for p in .claude/review-commit-project-rules.md \
         .cursor/skills/review-commit/project-rules.md \
         ~/.claude/review-commit-project-rules.md \
         ~/.cursor/skills/review-commit/project-rules.md; do
  [ -f "$p" ] && echo "== $p" && cat "$p" && break
done || echo "NO_PROJECT_RULES"
```

Si existen, **pásalas íntegras al agente** en el prompt. Tienen **precedencia** sobre las
reglas genéricas del agente en caso de conflicto — díselo explícitamente.

**Si el resultado es `NO_PROJECT_RULES`, dilo en voz alta antes de analizar.** Correr un
review sin las reglas del equipo produce hallazgos que no aplican y omite los que sí — y
desde afuera se ve idéntico a un review correcto.

---

## PASO 3 — Análisis (agente `code-reviewer`, modelo `opus`)

El agente ya lleva dentro toda la rúbrica (code-judo, SOLID, Clean Code, Clean Architecture,
FE/BE, tests, cache/invalidación) y el formato de salida. **No la repitas en el prompt.**

Lanza con `subagent_type: "code-reviewer"` y `model: "opus"`. El prompt solo lleva lo
específico de este MR:

```
MODO: ANALIZAR

MR "<TITULO>" de <AUTOR>, proyecto <PROJECT_PATH>, head_sha <HEAD_SHA>.
URL (para el comando search): <MR_URL>

- Diff: /tmp/review-<iid>/diff.txt          (qué cambió)
- Archivos al head_sha: /tmp/review-<iid>/head/   (qué hay; '/' aplanado a '__')

Lee AMBOS. Revisa los <N> archivos del diff.

## Contexto ya verificado por el orquestador (no lo re-reportes si es correcto)
<hechos que YA confirmaste tú, con cita — evita que el agente gaste tokens
 redescubriéndolos y evita falsos positivos sobre cosas que ya validaste>

## Dudas específicas que quiero que resuelvas
<puntos concretos donde sospechas algo, redactados como pregunta abierta,
 NO como conclusión — no contamines su juicio>

## Patrones preexistentes (no atribuibles a este autor)
<p.ej. duplicación entre dos mock files que ya existía antes del diff —
 pídele que lo verifique antes de reportarlo>

## Ya cubierto por detectores deterministas — NO lo reportes
<lista de PASO 2.4: "ui-in-unit-test en foo.test.tsx:7", "console-log en bar.ts:12">
Estos ya tienen comentario canónico asignado. Reportarlos otra vez duplica el
comentario en el MR. Enfócate en lo que un regex NO puede ver: estructura,
boundaries, code-judo, invariantes.

## Reglas del proyecto (precedencia sobre las tuyas)
<contenido de PASO 2.5, o "ninguna">
```

Si no devuelve hallazgos con confidence ≥ 80, muestra el resumen positivo y el VEREDICTO,
y salta al PASO 6.

---

## PASO 3.5 — Falsificación (agente `code-reviewer` en modo FALSIFICAR, `opus`)

**Nunca publiques lo que devolvió el análisis sin auditarlo.** Lanza una **segunda instancia
independiente** — no continúes la primera con `SendMessage`: un agente que audita su propio
razonamiento lo confirma, no lo tumba. La instancia nueva ve los hallazgos y el código, pero
no el razonamiento que los produjo.

```
MODO: FALSIFICAR

Audita estos hallazgos sobre el MR <MR_URL> al head_sha <HEAD_SHA>.
Tu trabajo es TUMBARLOS, no confirmarlos.

- Archivos al head_sha: /tmp/review-<iid>/head/
- Diff: /tmp/review-<iid>/diff.txt

<pega aquí los bloques HALLAZGO tal cual los devolvió el análisis>

## Reglas del proyecto
<igual que PASO 3, o "ninguna">
```

Cuando vuelva, **tú abres al menos una cita de cada hallazgo VERIFICADO** con `Read`/`Grep`.
Es barato y es tu última línea de defensa: si el falsificador se equivocó, aquí se ve.

Informa antes de publicar:

```
Verificación: 7 hallazgos → 5 VERIFICADOS, 1 reescrito (PARCIAL), 1 descartado (REFUTADO: <razón>)
```

---

## PASO 4 — Presentar y decidir

Orden: **Alta (maintainability primero) → Media → Baja**. No inundes con nits Baja si hay
Alta/Media estructurales, salvo que el usuario pida detalle completo.

```
─────────────────────────────────────────
Comentario N de TOTAL — <tipo> · <severidad>
Archivo: <ruta> línea <N>

[<Severidad>] <Título corto>

<Pregunta directa al autor>
─────────────────────────────────────────
```

Tono estructural: directo y exigente sobre calidad, sin ser grosero.

- `este archivo cruza 1k líneas con este PR. ¿podemos descomponerlo primero?`
- `esto mete otro special-case en un flujo ya cargado. ¿lo movemos detrás de su propia abstracción?`
- `funciona, pero vuelve más spaghetti el código alrededor. ¿reestructuramos preservando comportamiento?`
- `parece feature logic filtrándose a un path compartido. ¿lo aislamos?`
- `esta abstracción no parece pagar su costo. ¿dejamos el flujo directo?`
- `¿por qué necesitamos cast/optional aquí? ¿podemos hacer el boundary más explícito?`
- `creo que hay un code-judo que lo simplifica mucho. ¿reencuadramos para que desaparezcan estas ramas?`

**Regla de auto-publicación** — publica **todo lo que sobreviva a la falsificación**:

- **Auto-publicar** e informar `→ Auto-publicado`: **cualquier severidad** (Alta, Media, Baja)
  y **cualquier tipo**, tanto **VERIFICADO** como **PARCIAL** reescrito.
- **NO uses `AskUserQuestion`** para decidir qué publicar. No preguntes por severidad, ni por
  tipo, ni por haber reescrito un hallazgo. Publica y reporta.
- **Lo único que no se publica** es lo **REFUTADO** en PASO 3.5. Eso se descarta y se explica
  en el resumen del PASO 6.
- Estructura del comentario: afirmación con su cita primero, escenario de fallo si existe, y
  la pregunta/remedio al final. Sin ese orden el autor no puede verificarte.

**Esto NO relaja la Regla cero.** El filtro sigue siendo la falsificación, no una pregunta al
usuario. Antes de publicar sigues obligado a:

- Lanzar PASO 3.5 con una instancia independiente. Sin falsificación no se publica nada.
- Abrir con `Read`/`Grep` al menos una cita de **cada** hallazgo, VERIFICADO o PARCIAL.
- Publicar el hallazgo **con la reescritura del falsificador**, no con el texto original del
  análisis. Un PARCIAL se auto-publica porque ya fue corregido — si no incorporaste la
  corrección, no está listo.
- Descartar cualquier hallazgo cuya cita no puedas abrir y confirmar tú mismo.

Un PARCIAL es, por definición, un hallazgo al que la falsificación ya le encontró una parte
incorrecta. Auto-publicarlo sube la apuesta sobre la calidad de la reescritura: si dudas de
un remedio concreto (una API, una versión, una firma), **verifícalo ejecutándolo o leyéndolo**
antes de publicar. Corregir el remedio es parte del trabajo, no motivo para preguntar.

**Excepción — acciones fuera del MR.** La regla cubre publicar comentarios. Sigue preguntando
antes de: resolver hilos ajenos, responder en hilos de otras personas, o cualquier acción que
el usuario no pidió. Publicar un hallazgo ≠ cerrar la conversación de alguien más.

---

## PASO 5 — Publicar (agente `gitlab-publisher`, modelo `haiku`)

Junta los aprobados en un solo JSON — los deterministas de `deterministic.json` **más** los
del agente que pasaron falsificación. **Tú** redactas el texto final; haiku solo lo transporta:

```json
{"findings": [{"file": "ruta/archivo.ts", "line": 39, "body": "<markdown completo>"}]}
```

Los deterministas ya vienen con `body` canónico listo — **cópialo literal, no lo reescribas**.

Guárdalo en `/tmp/review-<iid>/to-publish.json` y lanza `gitlab-publisher` con
`model: "haiku"`, pasándole la URL del MR y la ruta del JSON. Que reporte la tabla de
resultados y la verificación.

El script maneja solo el fallback inline→general y el dedup contra hilos existentes.

En **modo commit local** no hay MR: muestra los hallazgos formateados y dilo explícitamente.

---

## PASO 5-bis — Aplicar fixes (`--fix`, solo modo commit local)

Solo si el usuario pasó `--fix`. Modifica el working tree: es la única parte destructiva del
skill fuera de publicar.

### Antes de tocar nada

```bash
git status --porcelain
```

- **Working tree limpio** → adelante.
- **Sucio** → **detente y pregunta.** Muestra qué hay sin commitear. El usuario decide si
  commitea, hace stash, o prefiere que apliques encima. **Nunca hagas stash ni commit tú.**
  Sin esto, un fix mal aplicado se mezcla con trabajo del usuario y no hay cómo separarlos.

### Qué se aplica y qué no

Solo entran hallazgos que pasaron falsificación. Dentro de esos, se separan por riesgo:

| Clase | Ejemplos | `--fix` |
|---|---|---|
| **Mecánico** | `console.log`, comentario explicativo, código comentado, TODO | **Aplica** |
| **Estructural de bajo riesgo** | colapsar `!== null && !== undefined` a truthy, renombrar, extraer constante | **Aplica** si el hallazgo dice exactamente qué escribir |
| **Estructural de criterio** | "colapsar tres capas de tests", "agregar ancla positiva", "reencuadrar el state model" | **NO aplica** — se lista como sugerencia |
| **PARCIAL / cualquier duda** | — | **NO aplica** |

La línea divisoria: si el fix requiere decidir *qué debería hacer el código*, no lo automatices.
Si solo requiere aplicar lo que el hallazgo ya especificó, adelante.

Los hallazgos mecánicos vienen de PASO 2.4 con `archivo:línea` exactos — son los candidatos
más seguros, pero **no son un `sed`**: un `console.log` multilínea o un `if (x) console.log(y);`
sin llaves rompen la sintaxis si se borra la línea a ciegas. Por eso los aplica un agente que
lee el contexto, no un script.

### Ejecución

Lanza `review-fixer` con `model: "sonnet"`, pasándole:

- la lista de fixes a aplicar, cada uno con `archivo:línea`, qué quitar/cambiar, y el texto
  exacto si el hallazgo lo especifica
- la ruta del repo
- explícitamente: **qué NO debe tocar** (los estructurales de criterio)

El agente verifica con typecheck/lint/tests del repo y revierte con `Edit` cualquier cambio
que rompa algo. **No comitea** — eso queda para el usuario.

### Al terminar

```bash
git diff --stat
git diff
```

Muestra el diff real y reporta: aplicados / saltados / fallidos, el comando de verificación
que corrió y su salida. Si el repo no tenía typecheck ni tests, **dilo**: los cambios quedaron
sin validar. Los hallazgos estructurales no aplicados se listan como pendientes, con su
sugerencia — no desaparecen por no ser automatizables.

---

## PASO 6 — Resumen final + approval bar

| # | Archivo | Línea | Tipo | Severidad | Verificación | Estado |
|---|---------|-------|------|-----------|--------------|--------|
| 1 | `path/file.ts` | 24 | Maintainability | Alta | VERIFICADO | Publicado |
| 2 | `path/other.ts` | 10 | General | Media | PARCIAL (reescrito) | Saltado |

Indica publicados, saltados, **descartados en falsificación y por qué**, el enlace al MR, y
el **`head_sha` contra el que revisaste** — el siguiente re-review lo necesita como línea base.

Luego el **VEREDICTO**: `Ready to merge? Si | No | Con fixes`

### Approval bar (no aprobar solo porque "funciona")

Un veredicto positivo requiere: sin regresión estructural clara; sin oportunidad obvia de
simplificación dramática desaprovechada; sin explosión injustificada de un archivo más allá
de 1000 líneas; sin spaghetti por special-case branching; sin abstracción hacky/mágica; sin
wrapper/cast/optionality innecesario que oscurezca el diseño; sin leak de boundary
arquitectónico ni duplicación evitable de un helper canónico; sin descomposición obvia omitida.

**Presumptive blockers** salvo justificación clara del autor: el PR preserva complejidad
incidental cuando hay code-judo plausible; lleva un archivo de <1000 a >1000 líneas; añade
branching ad-hoc que enreda un flujo existente; resuelve un problema local dispersando
feature checks en código compartido; añade wrapper/contrato cast-heavy innecesario; duplica
un helper existente o pone lógica en la capa equivocada.

No suavices el veredicto a "LGTM" solo porque el comportamiento parece correcto.

---

## Re-review — validar fixes y réplicas

Cuando el usuario pida validar si los comentarios fueron atendidos ("revisa los comentarios
que nos dejaron", "valida si ya arreglaron", "resuelve los correspondientes"):

### Recolección

```bash
S=${CLAUDE_PLUGIN_ROOT}/scripts/gitlab-mr.py
cp -r /tmp/review-<iid>/head /tmp/review-<iid>/head-prev   # conserva la línea base
python3 $S meta        "<mr-url>"    # head_sha NUEVO
python3 $S diff        "<mr-url>"
python3 $S files       "<mr-url>"
python3 $S discussions "<mr-url>"    # TODOS, incluidos resueltos
diff -r /tmp/review-<iid>/head-prev /tmp/review-<iid>/head
```

Ese `diff -r` archivo-por-archivo es **la única prueba** de qué cambió desde tu review.

**Cuidado con el rebase:** `repository/compare` contra el head viejo calcula desde el
merge-base y devuelve el MR entero más commits de main — parece "todo cambió". Si ves commits
ajenos al MR, ignóralo y usa el `diff -r`.

Un hilo **resuelto sin reply** normalmente significa "lo arreglé en código". Verifícalo igual.

### Evaluación por hilo

| Categoría | Cómo se detecta | Acción |
|---|---|---|
| **Arreglado** | el diff muestra el cambio pedido | resolver en silencio; mencionarlo en el resumen |
| **Trade-off aceptado** | el autor explica un costo consciente y el dato es correcto | aceptar, resolver, registrar como deuda |
| **Réplica que no aplica** | describe algo que el código no hace, o responde otra pregunta | dejar abierto y responder citando la línea real |
| **Nuestro error** | al verificar, la afirmación original era falsa | retractar explícitamente |

Verificaciones que no puedes omitir:

- **"ya lo arreglé"** → corre el diff del archivo. Si es idéntico byte a byte, dilo así:
  "verifiqué con diff directo, el archivo está idéntico entre `<sha1>` y `<sha2>`". Puede que
  el autor se refiera a un fix que ya existía cuando revisaste — nómbralo para separar los
  dos temas sin acusar.
- **Réplica que suena a rebuttal pero confirma el hecho** ("sí, es otra llamada porque el key
  cambia") → separa *hecho* de *valoración*: el hecho quedó confirmado, el autor considera el
  costo aceptable. Es cierre legítimo, no refutación.
- **Réplica que reafirma la intención sin tocar el mecanismo** → responde con análisis de
  implicación; si el impacto real es nulo, dilo y recomienda cerrar.

### Redacción de replies

- **Retractación primero.** Si algo era incorrecto, ábrelo reconociéndolo y nombrando qué
  retiras, antes de sostener el resto. El autor lo iba a encontrar de todas formas.
- Un reply = una afirmación con cita + una pregunta accionable. Sin párrafos de contexto.
- Cita `archivo:línea` al **HEAD nuevo** — las líneas se mueven, reverifícalas.
- Concede los sub-puntos válidos explícitamente y reencuadra hacia el problema de fondo si sigue vivo.
- **No pelees puntos cosméticos.** Si tener razón no cambia el código ni evita un bug,
  recomienda cerrar y dilo: "tener razón aquí no compra nada".
- Nunca rubber-stamp: si el código aún no cumple el ask, el hilo queda abierto.

### Publicación (haiku)

Escribe cada reply a un archivo y delega en `gitlab-publisher`:

```bash
python3 $S reply   "<mr-url>" <discussion_id> /tmp/review-<iid>/reply-1.md
python3 $S resolve "<mr-url>" <discussion_id>
```

Preferencia del proyecto: **resolver sin reply** si el código ya atiende el comentario. Nada
de notas "LGTM/gracias/ya quedó" en hilos que simplemente están hechos. Responde solo para
aceptar un no-fix justificado, rechazar un "Hecho" falso, aclarar, o acordar un follow-up
(déjalo abierto hasta que aterrice).

Si el usuario pidió "no los contestes" o "solo analiza": **redacta y muestra, no publiques**.

### Cierre

Reporta por hilo: qué feedback dieron, qué verificaste, y el veredicto (arreglado /
trade-off / no aplica / era nuestro error). Cierra con los hallazgos nuevos que aparecieron
y qué vale reabrir — normalmente solo lo que tiene costo de mantenimiento real. Di
explícitamente qué **no** ejecutaste (CI, tests) para no atribuirte verificación que no hiciste.
