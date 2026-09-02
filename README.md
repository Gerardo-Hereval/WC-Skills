# WC-Skills

Registry de skills de Claude Code usados en el equipo. Incluye skills propios del plugin oficial de Claude y skills personalizados creados para el proyecto `konfio-app-web`.

## Estructura

Este repo es un **marketplace de plugins de Claude Code** con dos plugins instalables:

```
wc-skills/
├── .claude-plugin/marketplace.json   # Manifest del marketplace "wc-skills"
├── user/                             # Plugin: wc-user-skills (aplica a cualquier proyecto)
│   ├── .claude-plugin/plugin.json
│   ├── skills/                       # gen-api, maintainability-reference,
│   │                                 # pull-storyblok-component, review-commit
│   ├── agents/                       # code-reviewer, gitlab-publisher, review-fixer
│   └── scripts/                      # gitlab-mr.py, review-detectors.py
├── konfio/                           # Plugin: wc-konfio-skills (monorepo konfio-app-web)
│   ├── .claude-plugin/plugin.json
│   └── skills/                       # amplitude-events, clean-arch-review, component-spec,
│                                     # review-commit-project-rules, runtime-mock,
│                                     # shadcn-ui, test-e2e
└── scripts/                          # Scripts que se instalan en su repo destino
    └── block-library/download-component.sh
```

> Los skills marcados con **(Claude oficial)** provienen del plugin `claude-plugins-official` y se gestionan automáticamente — no se versionan aquí, solo se documentan como referencia.

---

## Cómo usar un skill

En Claude Code, escribe `/nombre-del-skill` en el prompt. Algunos aceptan argumentos:

```
/gen-api [imagen o JSON]
/amplitude-events funnel loan_offer_viewed
/review-commit abc1234
/pull-storyblok-component https://app.storyblok.com/...
```

### Instalación rápida (30 segundos)

Dentro de una sesión de Claude Code:

```
/plugin marketplace add Gerardo-Hereval/WC-Skills
/plugin install wc-user-skills@wc-skills
/plugin install wc-konfio-skills@wc-skills
```

O desde la terminal:

```bash
claude plugin marketplace add Gerardo-Hereval/WC-Skills
claude plugin install wc-user-skills@wc-skills
claude plugin install wc-konfio-skills@wc-skills
```

`wc-user-skills` sirve en cualquier proyecto; `wc-konfio-skills` solo tiene sentido si trabajas en `konfio-app-web`. Los updates llegan con `/plugin marketplace update wc-skills`. Si antes copiabas los `.md` a `~/.claude/commands/` o `.claude/commands/`, borra esas copias al instalar los plugins para no tener cada skill duplicado.

---

## Registry de Skills

### Skills de Proceso — Claude oficial

Estos skills vienen preinstalados con el plugin `superpowers` de Claude Code. Se invocan automáticamente o manualmente según el contexto.

---

#### `superpowers:brainstorming` (Claude oficial)

Explora el intent, requisitos y opciones de diseño **antes** de escribir código. Se invoca automáticamente al iniciar cualquier tarea de creación de features.

**Cuándo usarlo:** antes de implementar algo nuevo — features, componentes, modificaciones de comportamiento.

```
/brainstorming
```

---

#### `superpowers:systematic-debugging` (Claude oficial)

Workflow estructurado para diagnóstico de bugs, fallos de tests o comportamiento inesperado. Evita saltar a fixes sin entender la causa raíz.

**Cuándo usarlo:** cuando algo no funciona y no se sabe por qué.

```
/systematic-debugging
```

---

#### `superpowers:writing-plans` (Claude oficial)

Genera un plan de implementación paso a paso antes de tocar código. Identifica archivos críticos y trade-offs arquitectónicos.

**Cuándo usarlo:** ante tareas multi-paso con spec o requisitos definidos.

```
/writing-plans
```

---

#### `superpowers:executing-plans` (Claude oficial)

Ejecuta un plan existente siguiendo su estructura de tareas.

```
/executing-plans
```

---

#### `superpowers:subagent-driven-development` (Claude oficial)

Ejecuta planes de implementación usando subagentes paralelos para tareas independientes. Es el modo de ejecución estándar del equipo.

**Cuándo usarlo:** siempre que haya un plan listo para ejecutar.

```
/subagent-driven-development
```

---

#### `superpowers:test-driven-development` (Claude oficial)

Guía la implementación con ciclos rojo-verde-refactor. Escribe el test antes del código.

```
/test-driven-development
```

---

#### `superpowers:finishing-a-development-branch` (Claude oficial)

Al terminar la implementación, presenta opciones estructuradas de integración: merge, PR o cleanup.

```
/finishing-a-development-branch
```

---

#### `superpowers:requesting-code-review` / `superpowers:receiving-code-review` (Claude oficial)

Par de skills para el flujo de code review. El primero prepara el diff; el segundo procesa los comentarios recibidos.

```
/requesting-code-review
/receiving-code-review
```

---

#### `superpowers:verification-before-completion` (Claude oficial)

Checklist de verificación antes de marcar una tarea como completada.

```
/verification-before-completion
```

---

#### `superpowers:using-git-worktrees` (Claude oficial)

Configura y usa git worktrees para trabajar en ramas paralelas sin cambiar el working directory principal.

```
/using-git-worktrees
```

---

#### `superpowers:writing-skills` (Claude oficial)

Guía para crear nuevos skills siguiendo el formato correcto de frontmatter y estructura.

```
/writing-skills
```

---

### Skills de Frontend — Claude oficial

---

#### `frontend-design:frontend-design` (Claude oficial)

Guidance de diseño de componentes frontend: tokens, spacing, jerarquía visual, accesibilidad.

**Cuándo usarlo:** antes de implementar cualquier componente UI.

```
/frontend-design
```

---

#### `shadcn-ui` — Konfio

Implementa, refactoriza o audita componentes de `@kui/design-system` usando shadcn/ui y Tailwind. Solo para componentes reutilizables que viven en `packages/design-system/src/ui/` (atoms, molecules, organisms).

**Cuándo usarlo:** al crear o modificar componentes del design system, no componentes app-local.

**Archivo:** [`konfio/skills/shadcn-ui/SKILL.md`](konfio/skills/shadcn-ui/SKILL.md)

```
/shadcn-ui
```

---

### Skills de Herramientas — Claude oficial

---

#### `verify` (Claude oficial)

Verifica que un cambio funcione end-to-end arrancando el flujo afectado y observando el comportamiento real, no solo tests.

```
/verify
```

---

#### `run` (Claude oficial)

Arranca el app del proyecto y observa comportamiento. Busca primero un skill de proyecto que ya cubra el arranque; si no existe, usa patrones built-in.

```
/run
```

---

#### `code-review` (Claude oficial)

Revisa el diff actual en busca de bugs de correctness, oportunidades de simplificación y eficiencia. Acepta flags `--comment` (postea en PR) y `--fix` (aplica los cambios).

**Cuándo usarlo:** antes de abrir un MR o como segunda opinión sobre cambios.

```
/code-review
/code-review --fix
/code-review --comment
```

---

#### `simplify` (Claude oficial)

Revisa el código modificado en busca de oportunidades de simplificación, reutilización y limpieza. Solo calidad — no busca bugs.

```
/simplify
```

---

#### `security-review` (Claude oficial)

Audita el diff en busca de vulnerabilidades de seguridad.

```
/security-review
```

---

#### `deep-research` (Claude oficial)

Investigación multi-fuente con verificación adversarial y reporte citado. Hace fan-out de búsquedas web, fetch de fuentes y síntesis.

**Cuándo usarlo:** preguntas que requieren múltiples fuentes verificadas.

```
/deep-research ¿Cómo implementar rate limiting en Next.js Route Handlers?
```

---

#### `update-config` (Claude oficial)

Configura hooks y comportamientos automáticos en `settings.json`. Necesario para frases del tipo "cada vez que X, haz Y".

```
/update-config
```

---

#### `loop` (Claude oficial)

Ejecuta un comando o skill en un intervalo recurrente.

```
/loop 5m /verify
```

---

#### `claude-api` (Claude oficial)

Referencia de la API de Claude/Anthropic: model IDs, pricing, parámetros, streaming, tool use, MCP, caching.

```
/claude-api
```

---

#### `handoff` (Claude oficial)

Compacta la conversación actual en un documento de handoff para que otro agente o sesión pueda continuar el trabajo.

```
/handoff "implementar la vista de pagos"
```

---

### Skills Konfio — Proyecto `konfio-app-web`

Estos skills son específicos del monorepo `konfio-app-web`. Se colocan en `.claude/commands/` en la raíz del proyecto.

---

#### `amplitude-events`

Agrega uno o más eventos de Amplitude tracking al monorepo. Genera las funciones wrapper tipadas en `packages/analytics/src/application/{app}/tracking-events.ts`, exporta el archivo de eventos desde el `package.json` exports, crea el analytics hook cuando hay lógica de negocio (mount → `useEffect`; interacción → función simple sin `useCallback`) y actualiza el componente consumidor. Incluye un agente de auditoría al final. El skill no contiene templates de código: instruye a leer el código existente como fuente de verdad y deja las reglas de estilo (orden de imports, formato) a los linters.

**Cuándo usarlo:** cuando hay que instrumentar un nuevo evento de analytics en cualquier app del monorepo.

**Archivo:** [`konfio/skills/amplitude-events/SKILL.md`](konfio/skills/amplitude-events/SKILL.md)

```
/amplitude-events
/amplitude-events funnel loan_offer_viewed
/amplitude-events home home_dashboard_viewed home_banner_clicked
```

**Flujo:**
1. Pide app + nombres de eventos + archivo consumidor + trigger si faltan
2. Verifica que las clases existan en `domain/ampli/index.ts`
3. Genera/actualiza `tracking-events.ts` replicando el patrón existente
4. Actualiza `package.json` exports si el app entry no existe
5. Decide hook vs llamada directa (aceptable solo si no hay lógica de negocio)
6. Actualiza consumidor y parent, lanza agente de auditoría e imprime reporte

---

#### `clean-arch-review`

Revisa el código indicado contra las reglas de Clean Architecture del equipo (4 capas: Domain → Infrastructure → Application → UI). Si no se pasa argumento, revisa los archivos modificados en la rama actual.

**Cuándo usarlo:** al finalizar una feature para asegurar que no se violaron las capas.

**Archivo:** [`konfio/skills/clean-arch-review/SKILL.md`](konfio/skills/clean-arch-review/SKILL.md)

```
/clean-arch-review
/clean-arch-review apps/profile/src/application/hooks/use-staff.hook.ts
```

**Qué revisa:**
- Dirección de dependencias entre capas
- Schemas Zod en `domain/` (no en hooks ni componentes)
- Hooks con responsabilidad única
- Services como `const` namespaces estáticos (no clases)
- Atomic Design: jerarquía Atom → Molecule → Organism → Template
- Mocks en `src/mocks/` (nunca en `src/infrastructure/`)

---

#### `review-commit-project-rules`

Reglas de review específicas de `konfio-app-web`. **Se carga automáticamente** junto con el skill global `/review-commit` — no se invoca directamente.

**Archivo:** [`konfio/skills/review-commit-project-rules/SKILL.md`](konfio/skills/review-commit-project-rules/SKILL.md)

Incluye reglas de:
- Clean Code (nombres de métodos vs verbo HTTP, tipos Partial, lógica duplicada)
- Clean Architecture (APIs por dominio, route handlers mock, constantes de infraestructura)
- New Relic en servicios nuevos
- Contextos y hooks de aplicación
- TypeScript / imports (alias `@/`, enums, union types)
- Atomic Design
- Tests (pirámide de cobertura, fixtures, Cypress)

---

#### `runtime-mock`

Implementa o audita el Runtime Mock Pattern del equipo: Next.js Route Handlers como servidor mock, funciona para SSR y CSR, visible en el Network tab, aislado del código de producción via env gate.

**Cuándo usarlo:** al configurar el entorno mock de una nueva app o auditar si el patrón está bien implementado.

**Archivo:** [`konfio/skills/runtime-mock/SKILL.md`](konfio/skills/runtime-mock/SKILL.md)

```
/runtime-mock
```

**Patrón:**

```
NEXT_PUBLIC_MOCK_MODE=true
  → apiClient → /api/__mock__/[resource]
  → Route Handler → Scenario Registry → Fixture Data

NEXT_PUBLIC_MOCK_MODE=false
  → apiClient → External API → Real Response
```

**Estructura de archivos que genera:**
- `src/mocks/fixtures/` — datos estáticos tipados contra Domain Entities
- `src/mocks/scenarios/scenarios.registry.ts` — mapa de casos de uso
- `src/app/api/__mock__/[resource]/route.ts` — Route Handler catch-all
- `src/middleware.ts` — guard que bloquea el mock en producción

---

### Skills Usuario — Nivel global

Estos skills están en `~/.claude/commands/` y aplican a cualquier proyecto.

---

#### `gen-api`

Generador multi-agente de la capa completa de integración de un endpoint. A partir de una imagen o JSON de respuesta, genera en paralelo: Domain (interfaces + query keys), Infrastructure (API class + mock data + Next.js route handler) y Application (service + adapter + hook), con auditoría al final.

**Cuándo usarlo:** al integrar un nuevo endpoint de backend — ahorra el setup manual de las 3 capas.

**Archivo:** [`user/skills/gen-api/SKILL.md`](user/skills/gen-api/SKILL.md)

```
/gen-api [imagen del swagger o JSON de respuesta]
```

**Flujo:**
1. Analiza imagen o JSON; pide datos faltantes (URL, método HTTP, params)
2. Lanza 3 agentes en paralelo: Domain Agent, Infrastructure Agent, Application Agent
3. Agente de auditoría verifica consistencia entre capas
4. Reporte final con archivos generados y tokens consumidos

---

#### `review-commit`

Revisa un commit o MR de GitLab en busca de problemas de mantenibilidad (code-judo), SOLID, Clean Code y Clean Architecture. Recorre cada hallazgo uno por uno, pidiendo confirmación antes de postear cada comentario inline en GitLab.

**Cuándo usarlo:** para revisar cualquier commit o MR antes de merge.

**Archivo:** [`user/skills/review-commit/SKILL.md`](user/skills/review-commit/SKILL.md)

> En `konfio-app-web` se combina automáticamente con [`konfio/skills/review-commit-project-rules/SKILL.md`](konfio/skills/review-commit-project-rules/SKILL.md) para aplicar también las reglas del proyecto.

```
/review-commit abc1234
/review-commit https://gitlab.com/org/repo/-/merge_requests/42
```

**Flujo:**
1. Obtiene el diff del commit o MR
2. Analiza con barra estricta de mantenibilidad (busca "code judo")
3. Por cada hallazgo pregunta si postear el comentario inline en GitLab
4. Postea comentario con archivo + línea si el usuario confirma

---

#### `maintainability-reference`

Referencia companion de `/review-commit`. Define qué escalar agresivamente en reviews de mantenibilidad y cómo calibrar severidad. **Se carga automáticamente** al redactar comentarios estructurales — no se invoca directamente.

**Archivo:** [`user/skills/maintainability-reference/SKILL.md`](user/skills/maintainability-reference/SKILL.md)

**Qué marca como hallazgo crítico:**
- Implementaciones complicadas donde un reencuadre más limpio borraría categorías enteras de complejidad
- Refactors que mueven código sin reducir el número de conceptos
- Archivos que superan 1000 líneas por el PR
- Booleanos one-off, modos nullable o flags que complican el flujo de control existente
- Lógica específica de feature filtrándose a módulos de propósito general
- Wrappers delgados que agregan indirección sin simplificar nada

---

#### `pull-storyblok-component`

Descarga un componente de Storyblok y lo agrega al block-library con las convenciones del proyecto. Toda la parte mecánica está automatizada en el script `download-component.sh` del repo `block-library` (expuesto como `pnpm download:component`): parseo de URL/IDs, inferencia del spaceId legacy, resolución de la carpeta destino desde `component-groups.json`, alta del grupo nuevo, limpieza de metadatos de entorno, `component_group_name`, `display_name`, `is_root` y renombrado del archivo. El skill solo decide el grupo correcto y verifica el resultado.

**Cuándo usarlo:** al incorporar un nuevo componente CMS de Storyblok al proyecto.

**Archivo:** [`user/skills/pull-storyblok-component/SKILL.md`](user/skills/pull-storyblok-component/SKILL.md)
**Script:** [`scripts/block-library/download-component.sh`](scripts/block-library/download-component.sh) — debe existir en `block-library/scripts/` con el entry `download:component` en su `package.json`.

```
/pull-storyblok-component https://app.storyblok.com/#/me/spaces/123456/components/789
/pull-storyblok-component 123456 789
/pull-storyblok-component 789
```

---

## Instalación

### Plugins del equipo

Ver **Instalación rápida** arriba: `/plugin marketplace add Gerardo-Hereval/WC-Skills` y luego `/plugin install` de cada plugin. Los plugins incluyen los skills, los agents del flujo de review (`code-reviewer`, `gitlab-publisher`, `review-fixer`) y los scripts que estos usan (`gitlab-mr.py`, `review-detectors.py`) — no hace falta copiar nada a mano.

Requisitos de runtime:
- `/review-commit` en modo MR necesita `GITLAB_TOKEN` exportado en el entorno
- `/pull-storyblok-component` necesita `STORYBLOK_TOKEN` y el script instalado en `block-library` (abajo)

### Scripts que acompañan a los skills

```bash
# pull-storyblok-component depende de este script en el repo block-library
cp scripts/block-library/download-component.sh /ruta/a/block-library/scripts/
# y del entry en block-library/package.json:
#   "download:component": "bash scripts/download-component.sh"
```

### Skills de Claude oficial

Se instalan a través del plugin marketplace de Claude Code:

```
superpowers       → claude-plugins-official/superpowers
frontend-design   → claude-plugins-official/frontend-design
```

---

## Contribuir

Para agregar un nuevo skill:

1. Crea `konfio/skills/<nombre>/SKILL.md` o `user/skills/<nombre>/SKILL.md` según el alcance
2. Agrega el frontmatter con `name`, `description` y `user-invocable`
3. Valida con `claude plugin validate ./konfio` (o `./user`)
4. Documenta en este README: qué hace, cuándo usarlo y ejemplos
5. Abre un MR — al mergear, quienes tienen el plugin reciben el skill con `/plugin marketplace update wc-skills`

**Formato mínimo de frontmatter:**

```yaml
---
name: mi-skill
description: >
  Descripción de una línea de qué hace el skill.
  Uso: /mi-skill [argumento]
user-invocable: true
allowed-tools:
  - Bash
  - Read
  - Edit
  - Write
---
```
