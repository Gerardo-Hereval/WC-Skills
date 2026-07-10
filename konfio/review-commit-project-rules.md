---
name: review-commit-project-rules
description: Reglas de review específicas de konfio-app-web. Cargado automáticamente por el skill global /review-commit.
user-invocable: false
---

# Reglas de proyecto — konfio-app-web

Estas reglas se combinan con las reglas genéricas del skill global `/review-commit`.

---

## REGLAS GENERALES

### Clean Code

- **Nombre engañoso de método vs verbo HTTP** — si un método se llama `deleteX` pero internamente hace `PUT { isActive: false }` (soft-delete), el nombre debe reflejar el contrato real (`deactivateX`) para no engañar al lector sobre el método HTTP usado
- **Lógica duplicada de derivación** — si el mismo valor se calcula de dos formas distintas dentro del mismo handler (ej. `parentId` derivado dos veces por ramas distintas), extraer a una función `resolveX()` que sea testeable de forma aislada
- **Tipos `Partial<Pick<…>>` que pierden garantías requeridas** — si un campo es siempre requerido en creación pero opcional en actualización, dividir en dos tipos distintos en lugar de `Partial` global

### Clean Architecture

- **APIs divididas por componente/flujo** en lugar de por dominio — los métodos de un mismo dominio (ej. `verification`) deben vivir en el archivo de API del dominio (`verification-api.ts`), no en archivos separados por feature
- **Lógica de negocio del mock en route handlers** — los route handlers de mock son solo adaptadores HTTP; la lógica de construir y mutar el estado del store debe vivir en el propio mock store (`infrastructure/mocks/<feature>-mock-store.ts`)
- **Route handlers mock deben envolver respuestas en `{ data: ... }`** para paridad con `BaseApiResponse` del API real — EXCEPTO métodos que retornan `void` (confirm, delete)
- **Archivos de plan no se commitean** — `docs/superpowers/plans/` se queda siempre en local; specs y progress sí se commitean
- **Constantes de infraestructura duplicadas entre archivos de API** — si `ENTERPRISE_PATH` u otra constante de ruta base se usa en más de un archivo de la misma capa, exportarla de un único archivo canónico (`enterprise-api.ts`) e importarla en los demás; nunca redefinirla localmente
- **Campos de payload que la capa de API siempre sobreescribe** — si un campo de la interfaz de dominio (ej. `redirect: boolean`) es invariablemente forzado a un valor fijo en el método de API (ej. `redirect: true`), el campo NO debe existir en la interfaz; se hardcodea solo en la capa de infraestructura para que el caller no tenga que pasarlo ni pueda sobrescribirlo
- **New Relic ausente en servicios nuevos** — cualquier clase `*Service` que envuelve llamadas de API debe importar `NewRelic` de `@kui/lib/services/newrelic` y envolver cada método en `try/catch` con `NewRelic.noticeError(error as Error, { method: '<NombreDeMetodo>', enterpriseId })` seguido de `throw error`; ver `profile-service.ts` como referencia

### Contextos y hooks de aplicación

- **Optional chaining especulativo en valores garantizados por el contexto de auth** — en rutas autenticadas, `userInfo` (y análogos provenientes de `useUserInfoContext`) está garantizado por el middleware de autenticación; usar `userInfo?.enterprise.role` introduce un path `undefined` que nunca ocurre en producción y engaña al compilador sobre la presencia del dato. Usar `userInfo.enterprise.role` directamente

---

## REGLAS FRONTEND

### Hooks de aplicación

- Templates/views con múltiples `useState`, handlers y mutations — ¿debería extraerse a un custom hook `use-<feature>-view.hook.ts`?
- `useMutation` sin `mutationKey` — seguir el mismo patrón que `queryKey` usando constantes en `query-keys.constants.ts`
- **Magic number `0` como fallback para IDs** — si `chart?.id ?? 0` se usa para inicializar mutaciones antes de que el recurso cargue, las mutaciones pueden dispararse con ID inválido ante un race condition; preferir guards o mutaciones condicionales
- **`reset()` del formulario antes de confirmar mutación** — llamar `reset()` sincrónicamente en el handler hace que el usuario pierda los datos si la mutación falla; limpiar el formulario solo en `onSuccess` o al cerrar el drawer

### TypeScript / imports

- Importaciones relativas profundas (`../../../`) en lugar de alias `@/` — señal de que el archivo está lejos de su capa
- Union types inline repetidos (`'director' | 'collaborator'`) — extraer como `type` exportado para que otros archivos lo reusen
- **Assertion `as SomeEnum` sin validación runtime** — un cast directo `item.roleId as StaffRole` hace que valores inesperados del API pasen silenciosamente; reemplazar con una función validadora que verifique membership en el set de valores válidos del enum y lance un error explícito si no coincide (ver `toStaffRole()` en `staff-member.adapter.ts` como referencia)
- String literals como discriminante de componente (`component: 'my-block'`) — extraer como `type` nombrado (`type MyBlockComponent = 'my-block'`)
- Valores magic de tiempo en `staleTime` (`2 * 60 * 1000`) — usar `QUERY_STALE_TIME` de `query-cache.constants.ts`
- Constantes de validación (regex, listas de valores) definidas dentro de schemas o componentes — moverlas a `domain/constants/validation.constants.ts`
- **Magic strings de dominio** (`'director'`, `'collaborator'`, IDs de bloque CMS) usados directamente en adaptadores — extraer a `const` o `enum` en `domain/constants/<feature>.constants.ts` y referenciarlos desde ahí
- **Componentes de UI duplicados entre apps y design-system** — si ya existe un componente equivalente en `@kui/design-system`, usar ese en lugar de crear uno local en la app; importar por subpath (`@kui/design-system/atoms/<nombre>`)

### Atomic Design

Jerarquía según la spec original de Brad Frost:

- **Atom**: unidad mínima, sin hijos compuestos
- **Molecule**: agrupa 2-3 atoms con lógica simple; **no puede contener organismos**
- **Organism**: agrupa molecules, atoms u **otros organismos** — esto es válido y esperado
- **Template**: define el layout de una vista completa; sin datos reales
- **Page**: instancia un template con datos reales

Restricciones reales (las únicas que aplican):
- Molécula **nunca** contiene un organismo
- Átomo **nunca** contiene una molécula

Lo que sí hay que revisar:
- ¿El componente cumple la convención de carpetas acordada por el equipo (`atoms/`, `molecules/`, `organisms/`, `templates/`)?
- ¿Un "organismo padre" mezcla responsabilidades de layout (template) con lógica de negocio?

### Estilos

- Constantes CSS/Tailwind duplicadas entre componentes hermanos
- Clases mágicas sin referencia a tokens del design system
- **Mezcla de familias de tokens CSS** — `var(--nds-color-*)` y `var(--color-*)` no deben mezclarse en el mismo componente; usar una sola fuente de verdad definida en `css/tokens`

---

## REGLAS DE TESTS

- **Cobertura por capa (pirámide):** los **unit tests** se escriben de "hooks para abajo" — hooks (`application/hooks/**`), services/adapters (`application/services/**`, `application/adapters/**`), schemas y utils/constantes de dominio (`domain/**`), que es donde vive la lógica (validación, state-machines, mapeos). Los componentes de **UI (organisms / molecules / atoms) NO llevan unit tests de render**; se cubren con **integración / e2e**. Si un MR agrega un unit test de render sobre un componente de UI, es un HALLAZGO (desviación de la convención).
- **E2E: solo el happy path**, salvo que el ticket pida explícitamente casos de error.
- Descripciones `it(...)` / `describe(...)` en español — deben estar en inglés
- Mock data inline (objetos de 10+ líneas dentro de `mockResolvedValue` o `mockReturnValue`) — mover a `infrastructure/mocks/<feature>.mock.ts`
- Comentarios que explican el "qué" del test (no el "por qué no obvio") — eliminar; el nombre del test ya lo dice
- `jest.mock` con ruta relativa cuando el import usa alias `@/` — deben coincidir
- **Fixtures de E2E duplican interfaces del dominio** — los tipos de fixture en `apps/profile-e2e` no deben redefinir estructuras ya definidas en `apps/profile/src/domain`; importar los tipos del dominio directamente para evitar drift
- **Fixtures de Cypress sin wrapper `BaseApiResponse`** — si `cy.intercept` captura llamadas al backend real y el cliente usa `response.data.data`, los fixtures deben envolverse en `{ data: ... }` para respetar la forma del response real
