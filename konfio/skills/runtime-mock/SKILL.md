---
name: runtime-mock
description: >
  Implementa o audita el Runtime Mock Pattern del equipo en konfio-app-web:
  Next.js Route Handlers como servidor mock (SSR y CSR), aislado de producción
  vía env gate. Uso: /runtime-mock
user-invocable: true
---

# /runtime-mock — Implementar o auditar Runtime Mock Pattern (Next.js)

Implementa o revisa el patrón de simulación de mocks en runtime usando Next.js Route Handlers.
Este patrón reemplaza MSW interceptors en runtime — MSW sigue usándose solo en tests.

---

## POR QUÉ ESTE PATRÓN

MSW Service Worker **no** intercepta Server Component fetches (Node.js context).
Este patrón usa Next.js Route Handlers como servidor mock — funciona para SSR y CSR,
es visible en el Network tab, y está completamente aislado del código de producción vía env gate.

---

## FLUJO DE UNA REQUEST

```
UI Layer (Hook/Component)
  ↓ calls apiClient.get('/users/123')
Infrastructure (api/client.ts)
  ↓ checks NEXT_PUBLIC_MOCK_MODE
  ├── TRUE  → /api/__mock__/[resource]  → Scenario Registry → Fixture Data
  └── FALSE → External API → Real Response
  ↓ (en ambos casos)
Adapter (mapea a Domain Entity)
  ↓
Domain Entity ✓
```

---

## ESTRUCTURA DE ARCHIVOS

```
src/mocks/                          ← NUNCA importado por Domain/Infra/App/UI
  fixtures/                         ← datos estáticos tipados
    users/
      user.nominal.ts
      user.empty.ts
      user.suspended.ts
    orders/
      orders.empty.ts
      orders.pending.ts
  scenarios/
    scenarios.registry.ts           ← mapa de casos de uso
  handlers/                         ← MSW handlers (solo para tests)

src/app/api/__mock__/[resource]/
  route.ts                          ← Route Handler catch-all

src/infrastructure/api/
  client.ts                         ← ÚNICO archivo que cambia entre mock/real

src/middleware.ts                   ← Middleware Guard: bloquea /api/__mock__ en producción
```

**Regla clave**: `src/mocks/` es importado SOLO por el Route Handler y archivos de test.
Nunca por Domain, Infrastructure, Application ni UI.

---

## IMPLEMENTACIÓN — 3 ARCHIVOS PRINCIPALES

### 1. `src/mocks/scenarios/scenarios.registry.ts`
```ts
import { userNominal, userEmpty, userSuspended } from '../fixtures/users'
import { ordersEmpty, ordersPending } from '../fixtures/orders'
import type { User } from '@/domain/entities/User'
import type { Order } from '@/domain/entities/Order'

// Tipado fuerte — drift con Domain Entities es error de compilación
type ScenarioFixtures = {
  user: User
  orders: Order[]
}

export const scenarios: Record<string, ScenarioFixtures> = {
  'new-user':       { user: userNominal,   orders: ordersEmpty   },
  'returning-user': { user: userNominal,   orders: ordersPending },
  'suspended':      { user: userSuspended, orders: ordersEmpty   },
  'payment-failed': { user: userNominal,   orders: ordersFailed  },
} as const

export type ScenarioKey = keyof typeof scenarios
```

### 2. `src/app/api/__mock__/[resource]/route.ts`
```ts
import { NextRequest } from 'next/server'
import { scenarios } from '@/mocks/scenarios/scenarios.registry'

export async function GET(
  req: NextRequest,
  { params }: { params: { resource: string } }
) {
  // Scenario comunicado via header — seteado por dev toolbar en la UI
  const scenario = req.headers.get('x-mock-scenario') ?? 'new-user'
  const fixture = scenarios[scenario as keyof typeof scenarios]

  if (!fixture)
    return Response.json({ error: `Unknown scenario: ${scenario}` }, { status: 404 })

  const data = fixture[params.resource as keyof typeof fixture]

  if (!data)
    return Response.json({ error: `Unknown resource: ${params.resource}` }, { status: 404 })

  // Simular latencia realista en dev
  if (process.env.NODE_ENV === 'development')
    await new Promise(r => setTimeout(r, Math.random() * 400 + 100))

  return Response.json(data)
}
```

### 3. `src/infrastructure/api/client.ts` (único cambio)
```ts
const MOCK_MODE = process.env.NEXT_PUBLIC_MOCK_MODE === 'true'
const BASE_URL = MOCK_MODE
  ? '/api/__mock__'   // → Route Handler
  : process.env.NEXT_PUBLIC_API_URL  // → real backend

export const apiClient = {
  get: <T>(resource: string, scenario?: string): Promise<T> =>
    fetch(`${BASE_URL}/${resource}`, {
      headers: scenario ? { 'x-mock-scenario': scenario } : {},
    }).then(r => r.json()) as Promise<T>,
}
```

### Middleware Guard (seguridad)
```ts
// src/middleware.ts
export function middleware(req: NextRequest) {
  const isMockRoute = req.nextUrl.pathname.startsWith('/api/__mock__')
  const isMockEnabled = process.env.NEXT_PUBLIC_MOCK_MODE === 'true'

  if (isMockRoute && !isMockEnabled)
    return Response.json({ error: 'Not found' }, { status: 404 })
}
```

---

## CASOS DE USO / ESCENARIOS

Cada escenario compone fixtures existentes — no necesita nuevos endpoints:

| Scenario key     | Descripción                                          |
|------------------|------------------------------------------------------|
| `new-user`       | Primera vez, sin pedidos, flujo de onboarding activo |
| `returning-user` | Usuario activo con historial completo y carrito      |
| `suspended`      | Cuenta suspendida — tests de estados de acceso       |
| `payment-failed` | Último pedido en estado de pago fallido              |

Para agregar un nuevo escenario: solo añadir entrada en `scenarios.registry.ts` con fixtures existentes.

---

## IMPACTO EN CAPAS (Clean Architecture)

| Capa           | Cambio requerido                                      |
|----------------|-------------------------------------------------------|
| Domain         | Ninguno. Fixtures se tipan contra Domain Entities.    |
| Infrastructure | Un cambio en `BASE_URL` de `client.ts`.               |
| Application    | Ninguno. Hooks reciben el mismo Entity tipado.        |
| UI             | Opcional: Scenario Switcher atom oculto tras env flag.|
| mocks/         | Dueño de toda la lógica de simulación.                |

---

## AUDITORÍA — CHECKLIST

Cuando revises si el patrón está bien implementado:

- [ ] ¿`src/mocks/` es importado por algún archivo fuera de Route Handlers o tests? (CRÍTICO)
- [ ] ¿Los fixtures están tipados contra Domain Entities?
- [ ] ¿Existe el Middleware Guard bloqueando `/api/__mock__` cuando `MOCK_MODE=false`?
- [ ] ¿`scenarios.registry.ts` usa `as const` para inferencia exhaustiva de tipos?
- [ ] ¿MSW handlers en `mocks/handlers/` comparten los mismos `fixtures/` que el Route Handler?
- [ ] ¿La URL base en `client.ts` es el único punto que cambia entre mock y real?
- [ ] ¿Los nuevos escenarios se agregan solo en el registry, sin crear nuevos Route Handlers?

---

## MSW SIGUE USÁNDOSE EN TESTS

| Contexto                     | Herramienta             |
|------------------------------|-------------------------|
| Unit & integration tests     | MSW (jest/vitest)       |
| Component tests              | MSW + @testing-library  |
| Runtime dev / staging        | Route Handlers          |
| E2E (Cypress/Playwright)     | Route Handlers          |

Ambas herramientas importan los mismos `fixtures/` de `src/mocks/`.
Un fix en un fixture se refleja en tests y en runtime simulation simultáneamente.
