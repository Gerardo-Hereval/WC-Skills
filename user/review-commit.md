---
name: review-commit
description: >
  Review a commit or GitLab MR for maintainability (code-judo), SOLID, Clean
  Code, Clean Architecture, and frontend/backend standards. Walks through each
  finding one by one, asking the user before posting each one as an inline
  GitLab comment (with file + line number). Usage: /review-commit <commit-sha|gitlab-mr-url>
user-invocable: true
allowed-tools:
  - Bash
  - Read
  - AskUserQuestion
  - Agent
---

# /review-commit — Code Review con comentarios en GitLab

Argumento recibido: `$ARGUMENTS`

Combina el workflow operativo de review en GitLab con una **barra estricta de mantenibilidad**: no apruebes solo porque el código funciona. Busca activamente "code judo" — reestructuraciones que preservan comportamiento y borran complejidad.

Referencia extendida (phrase bank / flags agresivos): lee `~/.claude/commands/maintainability-reference.md` si necesitas calibrar tono o severidad.

---

## PASO 1 — Detectar modo

Analiza `$ARGUMENTS`:

- Si contiene `gitlab.com` y `/merge_requests/` → **modo MR** (extraer project path y MR IID)
- Si parece un SHA de commit (hash hexadecimal) → **modo commit local**
- Si está vacío → usar `HEAD` como commit

---

## PASO 2 — Obtener el diff

### Modo commit local

```bash
git show <SHA> --stat          # resumen de archivos
git show <SHA>                 # diff completo
```

Guarda el diff completo en `/tmp/review-commit-<SHA>.txt` para el subagente.

### Modo MR (GitLab)

Necesitas `GITLAB_TOKEN` en el entorno. Si no está disponible, pide al usuario que ejecute:
```
! export GITLAB_TOKEN=<su-token>
```

Luego obtén:

```bash
# URL-encode el project path (reemplaza / por %2F)
# GET /api/v4/projects/:path/merge_requests/:iid  → título, estado, autor
# GET /api/v4/projects/:id/merge_requests/:iid/versions → base_sha, start_sha, head_sha
# GET /api/v4/projects/:id/merge_requests/:iid/diffs   → diff de cada archivo
```

Guarda `base_sha`, `start_sha`, `head_sha` y el `project_id` — los necesitas para los comentarios inline.

Guarda el diff completo en `/tmp/mr<iid>_diff.txt` para que el subagente de revisión pueda leerlo:

```bash
curl -s --header "PRIVATE-TOKEN: $GITLAB_TOKEN" \
  "https://gitlab.com/api/v4/projects/<project_id>/merge_requests/<iid>/diffs?per_page=100" | \
  python3 -c "
import json, sys
diffs = json.load(sys.stdin)
with open('/tmp/mr<iid>_diff.txt', 'w') as f:
    for d in diffs:
        f.write(f'=== FILE: {d[\"new_path\"]} ===\n')
        f.write(f'new_file: {d[\"new_file\"]}\n')
        f.write(d['diff'])
        f.write('\n\n')
print(f'Saved {len(diffs)} files')
"
```

Para cada archivo del diff, mapea los números de línea del diff al número de línea real en el archivo nuevo (`new_line`). Para archivos nuevos el encabezado del hunk es `@@ -0,0 +1,N @@` y cada línea `+` corresponde directamente a su número en el archivo.

También anota tamaños de archivo cuando sea relevante (sobre todo si se acercan o cruzan **1000 líneas**).

---

## PASO 2.5 — Cargar reglas del proyecto (si existen)

Antes de analizar, lee el primer archivo que exista:

1. `.claude/commands/review-commit.md` (reglas del repo)
2. `.cursor/skills/review-commit/project-rules.md`

```bash
cat .claude/commands/review-commit.md 2>/dev/null \
  || cat .cursor/skills/review-commit/project-rules.md 2>/dev/null \
  || echo "NO_PROJECT_RULES"
```

Si existe, **combina sus reglas con las reglas genéricas de este skill**. Las reglas del proyecto tienen precedencia sobre las genéricas en caso de conflicto. Si no existe, continúa solo con las reglas de abajo.

---

## PASO 3 — Analizar el diff con subagente code-reviewer

Despacha un subagente especializado `code-reviewer` para analizar el diff. Esto mantiene el contexto principal limpio y aplica scoring de confianza para filtrar falsos positivos.

Usa el Agent tool con `subagent_type: "code-reviewer"` y el siguiente prompt (rellena los placeholders):

```
Estás revisando el diff del MR "<TITULO>" de <AUTOR> en el proyecto <PROJECT_PATH>.
El diff completo está guardado en `<DIFF_FILE_PATH>`. Léelo con tu herramienta Read.

## Postura de review (obligatoria)
No apruebes solo porque el comportamiento parece correcto.
Sé ambicioso sobre simplificación estructural: busca "code judo" — reorganizaciones
que preservan comportamiento y borran ramas, helpers, modos o capas enteras.
Prefiere pocos hallazgos de alta convicción sobre una lista larga de nits cosméticos.
No te conformes con "quizá renombrar esto" si el problema real es estructural.

## Tu tarea
Revisa TODOS los archivos del diff contra las reglas que se listan abajo.
Prioriza hallazgos en este orden:
1. Regresiones estructurales de calidad
2. Oportunidades claras de code-judo / simplificación dramática
3. Spaghetti / crecimiento de branching
4. Problemas de boundary / abstracción / contrato de tipos
5. File-size (>1000 líneas) y descomposición
6. Modularidad / abstracciones que no pagan su costo
7. Legibilidad y mantenibilidad menor
8. Checklist SOLID / Clean Code / FE / BE (solo si no hay estructurales peores)

Para cada hallazgo devuelve una entrada con este formato exacto (sin excepciones):

HALLAZGO
archivo: <ruta exacta del archivo>
linea: <número entero de new_line — la línea en el archivo nuevo>
tipo: maintainability | general | frontend | backend
severidad: Alta | Media | Baja
confidence: <0-100>
titulo: <título corto en español>
comentario: |
  <comentario completo en markdown, redactado como PREGUNTA al autor;
   si es estructural, sé directo y exigente sin ser grosero>

Solo incluye hallazgos con confidence >= 80.
No inundes con nits de baja valor si hay issues estructurales.

## Mapeo de severidad
- Alta: code-judo claro omitido, spaghetti branching, archivo que cruza 1k líneas sin justificación, leak de boundary/capa, lógica feature en path compartido
- Media: wrapper innecesario, cast/any/optionality que oscurece el contrato, helper duplicado vs canónico, orchestration secuencial evitable
- Baja: naming, polish, docs, nits de estilo (omitir si ya hay Alta/Media estructurales)

## Cómo calcular new_line
- Cada hunk empieza con `@@ -A,B +C,D @@`. La línea `+C` es el punto de partida.
- Cuenta solo líneas `+` y de contexto (sin `-`) desde `+C` hacia abajo para obtener el número real.
- Para archivos nuevos (`@@ -0,0 +1,N @@`) cada línea `+` es directamente su número.

## También responde al final (fuera de los HALLAZGO)
VEREDICTO
listo_para_merge: Si | No | Con fixes
razon: <1-2 oraciones técnicas>
blockers_presuntos: <lista corta o "ninguno">

## REGLAS GENERALES

### Maintainability / Code judo (thermo-nuclear)
0. Sé ambicioso sobre simplificación estructural. Busca reencuadrar el cambio para que desaparezcan ramas, helpers, modos, conditionals o capas enteras. Si hay camino para borrar complejidad en lugar de reordenarla, empújalo.
1. No dejes que un PR lleve un archivo de <1k a >1k líneas sin razón muy fuerte. Prefiere extraer helpers/subcomponentes/módulos. Si cruza el umbral, pregunta si hay que descomponer primero.
2. No permitas crecimiento spaghetti: conditionals ad-hoc, special cases dispersos, o branches one-off en flujos no relacionados = problema de diseño. Muévelos a abstracción/helper/state machine/policy/módulo.
3. Sesgo a limpiar el diseño, no solo aceptar código que funciona. Prefiere quitar moving pieces sobre repartir la misma complejidad.
4. Prefiere código directo/aburrido/mantenible sobre hacky o mágico. Flag thin wrappers, identity helpers, pass-throughs, o mecanismos genéricos que esconden assumptions simples.
5. Empuja limpieza de tipos y boundaries: cuestiona optionality innecesaria, unknown/any/casts; prefer modelos tipados; si hay fallback silencioso, pregunta si el boundary debería ser explícito.
6. Mantén la lógica en la capa canónica y reutiliza helpers existentes. Flag feature logic en paths compartidos y drift arquitectónico.
7. Orchestration secuencial innecesaria y updates no atómicos son smells cuando la estructura limpia es obvia (paralelizar independientes; evitar estado a medias).

Preguntas primarias: ¿hay code-judo? ¿menos conceptos/ramas? ¿mejora o empeora arquitectura local? ¿branching donde debería haber abstracción? ¿capa/archivo correctos? ¿archivo > tamaño sano? ¿abstracción paga su costo? ¿casts/optionality oscurecen el invariante? ¿orchestration más secuencial/menos atómica de lo necesario?

Remedios preferidos: borrar capa de indirección; reencuadrar state model; cambiar ownership boundary; default flow con menos excepciones; extraer helper/split archivo; modelo tipado/dispatcher; separar orchestration de business logic; colapsar branches; borrar wrappers; reusar helper canónico; paralelizar; updates atómicos.

### SOLID
- S — Single Responsibility: ¿clase/función/hook hace más de una cosa? ¿Tiene más de una razón para cambiar?
- O — Open/Closed: ¿se modifica código existente en lugar de extenderlo? ¿se eliminan mecanismos de composición sin justificación?
- L — Liskov Substitution: ¿una implementación concreta rompe el contrato de su interfaz/tipo base?
- I — Interface Segregation: ¿interfaces con props que algunos implementadores nunca usan? ¿`any` con eslint-disable como atajo?
- D — Dependency Inversion: ¿se instancian o hardcodean dependencias en lugar de recibirlas?

### Clean Code
- Naming: nombres engañosos, typos, inconsistencias
- Tipos duplicados: mismo nombre exportado desde múltiples archivos
- `console.log` / código de debug en producción
- Código comentado que debería eliminarse o trackearse en ticket
- DRY: bloques idénticos repetidos 3+ veces sin extraer
- Magic strings/values: constantes hardcodeadas; en Python preferir `Enum` sobre variables sueltas
- Exportaciones inconsistentes sin razón aparente

### Clean Architecture
- Dirección de dependencias: domain ← application ← infrastructure/ui (nunca al revés)
- Schema/validación en capa equivocada (reglas de negocio en hooks o componentes)
- Mock data en capa de aplicación
- Lógica de infraestructura en componentes visuales u organismos

## REGLAS FRONTEND (React / TypeScript / Next.js)
- Tipado genérico mal usado: `<T>` que nunca se instancia con tipo concreto
- `any` suprimido con eslint-disable
- Props innecesariamente opcionales cuando siempre se proveen
- `defaultValue` y `register` mezclados en el mismo input (conflicto react-hook-form)
- `useEffect` sin dependencias correctas o con lógica de negocio dentro
- Mutación directa de estado
- Atomic Design: molécula nunca contiene organismo; átomo nunca contiene molécula
- Union types inline repetidos (`'director' | 'collaborator'`) deben extraerse como `type` exportado
- String literals usados como tipo de componente (ej. `component: 'my-component'`) deben extraerse como `type` nombrado
- Importaciones relativas profundas (`../../../../`) deben usar alias de paquete (`@/`)
- Valores magic de tiempo (`2 * 60 * 1000`) deben usar la constante `QUERY_STALE_TIME` de `query-cache.constants`
- Comentarios en tests/Cypress que explican el "qué" (no el "por qué no obvio") deben eliminarse
- Descripciones de tests (`it(...)`, `describe(...)`) deben estar en inglés
- APIs de infraestructura se dividen por dominio, no por componente o flujo: verificar que métodos nuevos del dominio `verification` se agreguen a `verification-api.ts` en lugar de crear un archivo separado
- Mock data inline en tests debe moverse a un archivo de mocks compartido en `infrastructure/mocks/`
- Lógica de estado y handlers complejos en templates/views deben extraerse a un custom hook dedicado

## REGLAS BACKEND (Python / Flask / NestJS)
- Entidades de dominio con dependencias hacia frameworks
- Casos de uso que acceden directamente a la BD en lugar de repositorios
- Controllers / Route handlers con lógica de negocio. Un route handler debe ser delgado: validar permisos → schema → command → retornar data.
- Funciones sueltas a nivel de módulo Python: si comparten estado/responsabilidad, deben agruparse en una clase
- Enums para constantes relacionadas: usar `Enum` en lugar de variables `CONSTANT = "value"` dispersas
- Nuevas clases de excepción (repo `core`): deben documentarse en `docs/errors.md` y `docs/errors.rst`
- Endpoints sin validación de input en el boundary de entrada
- Respuestas de error sin estructura consistente
- Secrets o credenciales hardcodeadas
- Queries con interpolación de strings (SQL injection)
- Promesas sin `await` / `try/catch` vacíos

<PROJECT_RULES_IF_LOADED>
```

Cuando el subagente devuelva sus hallazgos, úsalos directamente para PASO 4.
Si el subagente no encontró hallazgos con confidence ≥ 80, muestra el resumen positivo (y el VEREDICTO) y salta al PASO 6.

Presenta hallazgos en orden de prioridad (Alta maintainability primero).

---

## PASO 4 — Presentar hallazgos uno por uno

Orden: **Alta (maintainability first) → Media → Baja**. No inundes con nits Baja si hay Alta/Media estructurales, salvo que el usuario pida detalle completo.

Para **cada hallazgo**, muestra al usuario el bloque completo:

```
─────────────────────────────────────────
Comentario N de TOTAL — <tipo> · <severidad>
Archivo: <ruta/al/archivo.ts> línea <N>

[<Severidad>] <Título corto>

<Pregunta directa al autor. Ejemplo:>
"¿No convendría mover esta lógica a domain/schemas/
para poder reutilizarla y testearla sin React?"
─────────────────────────────────────────
```

Tono en hallazgos estructurales: directo y exigente sobre calidad, sin ser grosero. Ejemplos:

- `este archivo cruza 1k líneas con este PR. ¿podemos descomponerlo primero?`
- `esto mete otro special-case en un flujo ya cargado. ¿lo movemos detrás de su propia abstracción?`
- `funciona, pero vuelve más spaghetti el código alrededor. ¿mantenemos el comportamiento y reestructuramos?`
- `parece feature logic filtrándose a un path compartido. ¿lo aislamos?`
- `esta abstracción no parece pagar su costo. ¿dejamos el flujo directo?`
- `¿por qué necesitamos cast/optional aquí? ¿podemos hacer el boundary más explícito?`
- `creo que hay un code-judo move que lo simplifica mucho. ¿reencuadramos para que desaparezcan estas ramas?`

**Regla de auto-publicación:** si la severidad es **Alta**, publica el comentario directamente sin preguntar e informa al usuario con `→ Auto-publicado (Alta severidad)`. Solo usa `AskUserQuestion` para hallazgos de severidad **Media** o **Baja**, con opciones:
- **Publicar** — enviar al MR
- **Saltar** — pasar al siguiente
- **Editar** — pedir al usuario que dicte el texto alternativo, luego volver a mostrar y confirmar

---

## PASO 5 — Publicar comentario inline en GitLab

Solo si el usuario eligió **Publicar** (o auto-publicación Alta) y estamos en **modo MR**:

```bash
TOKEN="$GITLAB_TOKEN"

PAYLOAD=$(python3 -c "
import json, sys
body = sys.argv[1]
position = {
  'position_type': 'text',
  'base_sha': '<base_sha>',
  'start_sha': '<start_sha>',
  'head_sha': '<head_sha>',
  'old_path': '<ruta/al/archivo>',
  'new_path': '<ruta/al/archivo>',
  'new_line': <numero_linea>
}
print(json.dumps({'body': body, 'position': position}))
" "$BODY")

curl -s -X POST \
  --header "PRIVATE-TOKEN: $TOKEN" \
  --header "Content-Type: application/json" \
  --data "$PAYLOAD" \
  "https://gitlab.com/api/v4/projects/<project_id>/merge_requests/<iid>/discussions" | \
  python3 -c "import sys,json; d=json.load(sys.stdin); print('OK:', d.get('id','ERROR'), d.get('message',''))"
```

Si la posición inline falla (línea no está en el diff), reintenta como comentario general omitiendo el campo `position`.

En **modo commit local** (sin MR), muestra el hallazgo formateado pero avisa que no hay MR al cual postear.

---

## PASO 6 — Resumen final + approval bar

Al terminar todos los hallazgos, muestra una tabla:

| # | Archivo | Línea | Tipo | Severidad | Estado |
|---|---------|-------|------|-----------|--------|
| 1 | `path/file.ts` | 24 | Maintainability | Alta | Publicado |
| 2 | `path/other.ts` | 10 | General | Media | Saltado |

Indica cuántos se publicaron, cuántos se saltaron y el enlace al MR si aplica.

Luego muestra el **VEREDICTO** del subagente (o recompútalo):

**Ready to merge?** `Si | No | Con fixes`

### Approval bar (no aprobar solo porque “funciona”)

La barra para un veredicto positivo requiere:

- no clear structural regression
- no obvious missed opportunity for dramatic simplification when such a path is visible
- no unjustified file-size explosion past 1000 lines
- no obvious spaghetti-growth from special-case branching
- no obviously hacky/magical abstraction that makes the code harder to reason about
- no unnecessary wrapper/cast/optionality churn obscuring the real design
- no clear architecture-boundary leak or avoidable canonical-helper duplication
- no missed obvious decomposition that would materially improve maintainability

Trata estos como **presumptive blockers** salvo justificación clara del autor:

- el PR preserva mucha complejidad incidental cuando hay un code-judo plausible
- el PR lleva un archivo de <1000 a >1000 líneas
- el PR añade branching ad-hoc que enreda un flujo existente
- el PR resuelve un problema local dispersando feature checks en código compartido
- el PR añade abstracción/wrapper/contrato cast-heavy innecesario
- el PR duplica un helper existente o pone lógica en la capa equivocada

Si no se cumplen, deja feedback accionable y empuja una descomposición más limpia — no suavices el veredicto a “LGTM” solo porque el comportamiento parece correcto.
