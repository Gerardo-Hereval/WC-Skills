# /clean-arch-review — Revisión de Clean Architecture (Next.js)

Revisa el código indicado contra las reglas de arquitectura que usa este equipo.
Si no se pasa argumento, revisa los archivos modificados en la rama actual.

---

## ARQUITECTURA DE 4 CAPAS

Dirección de dependencias (siempre hacia adentro):

```
Domain → Infrastructure → Application → UI
```

- **Domain** nunca importa React, fetch, ni ningún framework. Solo TypeScript puro.
  - Contiene: `interfaces/`, `constants/`, `entities/`, `schemas/`
  - Los Schemas (Zod) validan datos en el boundary — nunca en hooks ni componentes.
  - Las constantes son module-scoped (no class-level) para ser tree-shakeable.

- **Infrastructure** implementa las interfaces del Domain.
  - Contiene: `api/` (Axios/fetch clients), `interceptors/`, `mocks/`
  - Solo cambia aquí cuando cambia el contrato de la API — sin refactors en UI.
  - Los mocks de MSW/test van en `src/mocks/` (top-level), NUNCA dentro de Infrastructure en producción.

- **Application** orquesta casos de uso.
  - Contiene: `utils/`, `services/`, `adapters/`, `hooks/`, `contexts/`
  - Services y Adapters son estáticos (const namespace, no clases) — tree-shakeable, sin overhead de instanciación.
  - Hooks exponen estado reactivo; Services/Adapters son puros.
  - **Problema crítico**: los Contexts viven en Application pero a veces necesitan renderizar UI (toasts, spinners). Solución: Generic Context Factory — el Context recibe el componente UI como parámetro de tipo, no lo importa directamente.

- **UI (Atomic Design)**
  - Atoms → Molecules → Organisms → Templates
  - Atoms: primitivos (Button, Input) — sin hijos compuestos
  - Molecules: agrupan 2-3 atoms con lógica simple — nunca contienen organisms
  - Organisms: secciones de feature — pueden contener otros organisms
  - Templates: layout de una vista completa — sin datos reales ni lógica de negocio

---

## REGLAS CRÍTICAS A VERIFICAR

### Dirección de dependencias
- [ ] ¿Algún archivo en `domain/` importa desde `application/`, `infrastructure/`, o `ui/`?
- [ ] ¿Algún hook en `application/hooks/` importa directamente un componente React de `ui/`?
- [ ] ¿Algún Context en `application/contexts/` renderiza JSX de `ui/` directamente?

### Schemas y validación
- [ ] ¿La validación Zod está en `domain/schemas/` y no dentro de un hook o componente?
- [ ] ¿Los tipos se infieren de los schemas (`z.infer<typeof schema>`) en lugar de definirse por separado?

### Hooks
- [ ] ¿Cada hook tiene una sola responsabilidad conceptual?
- [ ] ¿Los hooks "puros" (data fetching) no dependen de Context? Si necesitan Context, ¿hay un wrapper context-aware en `contexts/`?
- [ ] ¿Los `useEffect` tienen dependencias estables? (cuidado con objetos/funciones recreados en cada render)

### Services y Adapters
- [ ] ¿Los Services son `const` namespaces estáticos, no clases?
- [ ] ¿Los Adapters mapean DTOs de Infrastructure a Domain Entities?

### Atomic Design
- [ ] ¿Un Molecule contiene un Organism? (prohibido)
- [ ] ¿Un Atom contiene una Molecule? (prohibido)
- [ ] ¿Un Template tiene lógica de negocio o llama a hooks de Application? (debe evitarse)
- [ ] ¿El componente está en la carpeta correcta según su nivel de composición?

### Mocks
- [ ] ¿Los mocks están en `src/mocks/` (top-level) y NUNCA en `src/infrastructure/`?
- [ ] ¿`src/mocks/` es importado solo por Route Handlers y archivos de test?

---

## FORMATO DE REPORTE

Para cada problema encontrado:

```
Archivo: <ruta>
Línea: <N>
Capa afectada: Domain | Infrastructure | Application | UI
Regla violada: <nombre de la regla>
Problema: <descripción concisa>
Solución sugerida: <workaround del patrón>
```

Luego muestra una tabla resumen con severidad (Alta / Media / Baja) y estado (Pendiente / Saltado).

---

## WORKAROUNDS CONOCIDOS DEL EQUIPO

**UI dentro de Application Context** → Generic Context Factory:
```ts
// application/contexts/createNotificationContext.ts
export function createNotificationContext<TProps extends NotificationPayload>(
  UIComponent: ComponentType<TProps>
) { ... }
// El componente UI se pasa desde ui/providers/, no se importa en Application
```

**Static Methods difíciles de mockear** → Interface + Static Namespace:
```ts
// domain/interfaces/IUserService.ts
export interface IUserService { getById(id: string): Promise<User> }
// infrastructure/api/UserService.ts
export const UserService: IUserService = { async getById(id) { ... } }
```

**Hooks ↔ Contexts circular** → Separar hooks puros de hooks context-aware:
```ts
// application/hooks/useUserData.ts — sin dependencia de Context
export function useUserData(id: string) { return useSWR(['user', id], ...) }
// application/contexts/UserContext.ts — el Context consume el hook, no al revés
```
