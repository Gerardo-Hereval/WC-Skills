---
name: gen-api
description: >
  Generador multi-agente de la capa completa de integración de un endpoint.
  A partir de una imagen o JSON de respuesta, genera Domain (interfaces + keys),
  Infrastructure (API class + mock data + Next.js route) y Application (service +
  adapter + hook) en paralelo, con auditoría al final.
  Uso: /gen-api [imagen | JSON response]
user-invocable: true
allowed-tools:
  - Bash
  - Read
  - Edit
  - Write
  - Agent
  - AskUserQuestion
---

# gen-api — Generador multi-agente de capa API

Genera la capa completa de integración de un endpoint usando una arquitectura multi-agente: tres agentes especializados trabajando en paralelo y un agente de auditoría al final.

## Uso

```
/gen-api [imagen | JSON response]
```

Si la imagen o el JSON no incluyen URL, método HTTP, path params o body schema, el orquestador te preguntará antes de proceder.

---

## ORQUESTADOR — Instrucciones principales

Eres el agente orquestador. Tu trabajo es:
1. Analizar el input del usuario (imagen o JSON)
2. Recolectar información faltante preguntando al usuario
3. Construir un **spec completo** del endpoint
4. Lanzar **tres agentes especializados en paralelo**
5. Lanzar **un agente de auditoría** al finalizar
6. Reportar tokens consumidos

---

### FASE 1 — Analizar el input y recolectar info faltante

Si el usuario pasó una **imagen**, analízala visualmente y extrae:
- URL o path del endpoint
- Método HTTP (GET / POST / PUT / DELETE)
- Path params (segmentos con `{id}` o `:param`)
- Query params (si los hay)
- Body schema (para POST/PUT)
- JSON de respuesta

Si el usuario pasó **JSON directamente**, extrae la misma información.

Luego evalúa qué información falta y **pregunta al usuario en un solo bloque** por todo lo que no se pudo inferir, incluyendo siempre estas preguntas al final:

```
Para generar los archivos necesito confirmar algunos datos:

❓ URL del endpoint: [lo que inferiste o "no encontré en la imagen"]
❓ Método HTTP: [GET / POST / inferido]
❓ Path params: [lo que inferiste o "¿cuáles son los parámetros dinámicos?"]
❓ Body (si es POST/PUT): [inferido o "¿qué campos recibe el body?"]

❓ Respuesta: ¿Qué devuelve el endpoint?
   - void → no hay body de respuesta (ej: eventos de tracking)
   - JSON → pega el JSON o describe los campos

❓ App destino: ¿En qué app quieres generar los archivos?
   Opciones detectadas en el monorepo: funnel | on-boarding | (escribe el nombre de la carpeta en apps/)

❓ Campos enum/typeof: ¿Algún campo del response o body debe tiparse como enum o como
   typeof en lugar de string/number plano? (ej: status: 'active' | 'inactive')
   Si sí → proporciona el nombre del campo, el nombre del tipo y sus valores posibles.
   Si no → escribe "ninguno".

❓ Mocks por escenario: (solo si respondiste que hay campos enum/typeof en el response)
   ¿Quieres un mock separado por cada valor del enum para cubrir los distintos escenarios?
   Responde sí o no.

❓ Transformación de body (solo si es POST/PUT): ¿El body que se envía tiene campos en
   snake_case o requiere conversión desde camelCase?
   - sí → indica qué campos son boolean que deben mapearse a "0"|"1", el resto se convierte
     automáticamente con camelToSnake
   - no → el body se envía tal cual

❓ Capa de aplicación: ¿Quieres generar service, adapter o ambos?
   - service → clase estática con try/catch y NewRelic (patrón actual)
   - adapter → clase estática que mapea el tipo raw al tipo Domain (GET) o transforma el
     body antes de enviarlo (POST con snake_case)
   - ambos  → genera los dos

❓ Integración del hook: (opcional) ¿El hook generado se consumirá en un hook existente
   o se usará directamente desde un componente/contexto nuevo?
   - Si se integra en un hook existente → indica el path del archivo y una línea de contexto
     de cómo se usará (ej: "en use-offer-wc.hook.ts, para cargar los statements al montar").
     El Agente 3 añadirá el import y el call del hook en ese archivo.
   - Si es un hook nuevo / standalone → escribe "nuevo".
```

Solo omite las preguntas de endpoint (URL, método, params) si ya están 100% claras en el input. Las preguntas nuevas (respuesta, app, enums, mocks, transformación, capa, integración) **siempre** se hacen.

---

### FASE 2 — Construir el spec

Con toda la información recolectada, construye el siguiente spec que pasarás a todos los agentes:

```
SPEC:
  url: <URL completa>
  method: GET | POST | PUT | DELETE
  appName: <nombre de la carpeta en apps/> (ej: funnel, on-boarding)
  appPath: apps/{appName}
  resourceName: <camelCase> (ej: paymentPlan, loanSchedule)
  ResourceName: <PascalCase> (ej: PaymentPlan, LoanSchedule)
  RESOURCE_NAME: <SNAKE_UPPER> (ej: PAYMENT_PLAN, LOAN_SCHEDULE)
  resource-name: <kebab-case> (ej: payment-plan, loan-schedule)
  pathPrefix: <primer segmento del path> (ej: /enterprise, /loans)
  pathConst: <NOMBRE_PATH> (ej: ENTERPRISE_PATH, LOANS_PATH)
  dynamicPath: <path con params> (ej: /${enterpriseId}/payment-plans)
  httpClient: coreClient | createBrowserClient
  mockContext: <ruta dentro de app/api/mock/> (ej: core/enterprise | state-machine)
  pathSegmentToMatch: <string para el if en el mock route> (ej: payment-plans)
  queryKeyEnum: <enum existente o nuevo> (ej: OfferQueryKey | StateMachineQueryKey)
  pathParams: [{ name: string, type: 'number' | 'string' }]
  queryParams: [{ name: string, type: string, optional: boolean }]
  responseVoid: true | false
  responseInterface: <nombre de la interfaz cruda o "void"> (ej: PaymentPlan | void)
  responseFields: [{ name: string, type: string, nullable: boolean }] | null
  enumFields: [{ fieldName: string, typeName: string, values: string[] }] | null
  generateMockScenarios: true | false
  needsDomainInterface: true | false
  domainFields: [{ name: string, type: string }] | null
  hasBodyTransformation: true | false
  bodyInputFields: [{ name: string, type: string }] | null
  bodyWireFields: [{ name: string, type: string }] | null
  booleanBodyFields: string[] | null
  generateService: true | false
  generateAdapter: true | false
  hookIntegration: null | { targetFile: string, context: string }
```

**Reglas para determinar `httpClient`:**
- URL contiene `/core/` o dominio `platform.konfio.mx` → `coreClient`
- URL contiene `/workflows/`, `/state-machines/`, `/i02/`, o dominio diferente a `platform.konfio.mx` → `createBrowserClient`
- Para importar `coreClient`, usa siempre el path local de la app: `@/infrastructure/api/core-api`
  (No uses `@kui/api-core/client` directamente en los archivos generados — la app lo re-exporta con interceptores)

**Reglas para derivar `resourceName` desde la URL:**
- Toma el último segmento de path significativo (antes de path params) y conviértelo a camelCase
- `/enterprise/{id}/payment-plans` → `paymentPlan`
- `/actors/{id}/events` → `stateMachineEvent`
- `/funnel/person/{id}/active` → `activeFunnel`

**Reglas para `mockContext`:**
- Si `httpClient = coreClient` → `core/{primerSegmentoDelPath}` (ej: `core/enterprise`)
- Si `httpClient = createBrowserClient` → nombre corto del servicio (ej: `state-machine`, `loans`)

**Reglas para `responseVoid`:**
- `true` cuando el endpoint no devuelve body (ej: analytics/tracking, acciones fire-and-forget)
- Cuando `responseVoid = true`: no hay `responseInterface`, `responseFields` es null, `needsDomainInterface = false`, el mock mockea el INPUT (no la respuesta), el route retorna 204

**Reglas para `needsDomainInterface`:**
- `true` si `generateAdapter = true` Y `responseVoid = false` (adapter de respuesta GET)
- `false` si `responseVoid = true` o si no hay adapter
- `false` si el adapter es solo de transformación de body POST (las interfaces van en el archivo de API)

**Reglas para `hasBodyTransformation`:**
- `true` si el body POST/PUT se envía en snake_case y/o tiene campos boolean → "0"|"1"
- Cuando `true`: en `bodyInputFields` van los campos TS-friendly (camelCase, boolean), en `bodyWireFields` van los campos wire (snake_case, "0"|"1")
- `booleanBodyFields`: lista de nombres camelCase de los campos boolean que se mapean a "0"|"1"

---

### FASE 3 — Lanzar agentes en paralelo

Una vez que el spec esté completo, lanza estos tres agentes **en el mismo mensaje** (en paralelo):

#### Agente 1 — Domain
**Tarea:** Generar interfaces TypeScript, enums/tipos literales y actualizar `keys.ts`

#### Agente 2 — Infrastructure
**Tarea:** Generar API class, mock data (con escenarios si aplica) y Next.js mock route

#### Agente 3 — Application
**Tarea:** Generar service y/o adapter según el spec

---

### FASE 4 — Auditoría

Cuando los tres agentes terminen, lanza el **Agente de Auditoría** pasándole la lista de todos los archivos generados.

---

### FASE 5 — Reporte final de tokens

Imprime el resumen:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Gen-API — Reporte de ejecución
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Endpoint  : {url}
App       : {appName}
Cliente   : {httpClient}
Método    : {method}
Recurso   : {ResourceName}

Archivos generados:
  🟦 DOMAIN
     ✅ domain/interfaces/api/{resource-name}.interface.ts
     {✅ | ⏭ } domain/interfaces/{resource-name}.interface.ts
     ✅ domain/constants/keys.ts (entrada añadida)
  🟩 INFRASTRUCTURE
     ✅ infrastructure/api/{resource-name}-api.ts
     ✅ infrastructure/mocks/{resource-name}-mock.ts
     {si generateMockScenarios: ✅ infrastructure/mocks/{resource-name}-{valor}-mock.ts (x N)}
     ✅ app/api/mock/{mockContext}/[...path]/route.ts
  🟨 APPLICATION
     {si generateService: ✅ application/services/{resource-name}-service.ts}
     {si generateAdapter: ✅ application/adapters/{resource-name}.adapter.ts}
     ✅ application/hooks/queries/use-{get|create|...}-{resource-name}.hook.ts
     {si hookIntegration: ✅ {targetFile} (import + call añadidos)}

Auditoría : ✅ Sin issues | ⚠️  {N} observaciones

Tokens estimados:
  Orquestador  : ~{N} tokens
  Agente 1     : ~{N} tokens
  Agente 2     : ~{N} tokens
  Agente 3     : ~{N} tokens
  Agente audit : ~{N} tokens
  ─────────────────────────────
  Total output : ~{total} tokens
  Costo aprox  : ~${cost} USD  (Sonnet 4.6: $15/MTok output)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Para el cálculo: estima ~4 caracteres por token en el output generado. Precio Sonnet 4.6 output: $15/MTok.

---

---

## AGENTE 1 — Domain

Recibes el spec del orquestador. Genera estos archivos **en orden**:

### 1.1 Interfaz de API — `{appPath}/src/domain/interfaces/api/{resource-name}.interface.ts`

**Si `responseVoid = true` Y `hasBodyTransformation = true`:**

Genera dos interfaces: una para el input TS-friendly y otra para el wire format. Los tipos enum van antes de las interfaces.

```typescript
// Tipos enum si existen
export type {TypeName} = 'value1' | 'value2';

export const {RESOURCE_NAME}_ACTIONS = {
  ACTION_NAME: 'action-value',
} as const;
export type {ResourceName}Action = typeof {RESOURCE_NAME}_ACTIONS[keyof typeof {RESOURCE_NAME}_ACTIONS];

// Input: lo que el consumidor TS pasa (camelCase, booleans)
export interface {ResourceName}Input {
  {campo}: {tipo};
}

// Body: wire format que se envía a la API (snake_case, "0"|"1")
export interface {ResourceName}Body {
  {campo_snake}: {tipo_wire};
  source: 'web';
  send_timestamp: string;
}
```

**Si `responseVoid = false`:**

Mapea cada campo de `responseFields` al tipo TypeScript correspondiente. Reglas:
- Campos `nullable: true` → `type | null`
- Objetos anidados → interfaz separada en el mismo archivo
- Arrays → `TypeItem[]`
- Si `enumFields` no es null → usa union type o enum según el usuario indique

```typescript
export interface {ResponseInterface} {
  {campo}: {tipo};
}
```

No envuelvas en `BaseApiResponse` aquí — eso va solo en los mocks.

**Si `enumFields` no es null:** define los tipos antes de la interfaz principal:

```typescript
export type {TypeName} = 'value1' | 'value2' | 'value3';
```

### 1.2 Interfaz de dominio — `{appPath}/src/domain/interfaces/{resource-name}.interface.ts`

Crea este archivo solo si `needsDomainInterface = true`.

```typescript
import { {ResponseInterface} } from '@/domain/interfaces/api/{resource-name}.interface';

export interface {ResourceName}Domain extends {ResponseInterface} {
  formatted{MonetaryField}: string;
}
```

Si `needsDomainInterface = false`, imprime:
```
⏭  AGENTE 1 — domain/interfaces/{resource-name}.interface.ts (no necesario)
```

### 1.3 Query key en `{appPath}/src/domain/constants/keys.ts`

**Lee el archivo primero.**

- Si `queryKeyEnum` es un enum ya existente → añade la nueva entrada con `Edit`
- Si `queryKeyEnum` es nuevo → añade el nuevo enum al final del archivo con `Edit`

Nombre de la key:
- GET → `GET_{RESOURCE_NAME}`
- POST → `CREATE_{RESOURCE_NAME}`

```typescript
CREATE_{RESOURCE_NAME} = 'create{ResourceName}',
```

---

---

## AGENTE 2 — Infrastructure

Recibes el spec del orquestador. Genera estos archivos:

### 2.1 API class — `{appPath}/src/infrastructure/api/{resource-name}-api.ts`

**Regla de importación de `coreClient`:** siempre usa `@/infrastructure/api/core-api`, nunca `@kui/api-core/client`.

**Si `httpClient = coreClient` Y `responseVoid = false`:**

```typescript
import { coreClient } from '@/infrastructure/api/core-api';
import { BaseApiResponse } from '@/domain/interfaces/api/base-response.interface';
import { {ResponseInterface} } from '@/domain/interfaces/api/{resource-name}.interface';

const {pathConst} = '{pathPrefix}';

export default class {ResourceName}Api {
  static async get{ResourceName}({pathParams, queryParams}): Promise<{ResponseInterface}> {
    const response = await coreClient.get<BaseApiResponse<{ResponseInterface}>>(
      `${pathConst}{dynamicPath}`,
    );
    return response.data.data;
  }
}
```

**Si `httpClient = coreClient` Y `responseVoid = true` (POST void):**

La API class recibe el body ya transformado (`{ResourceName}Body`) — la transformación la hace el service/adapter.

```typescript
import { coreClient } from '@/infrastructure/api/core-api';
import { {ResourceName}Body } from '@/domain/interfaces/api/{resource-name}.interface';

const {pathConst} = '{pathPrefix}';

export default class {ResourceName}Api {
  static async create{ResourceName}(body: {ResourceName}Body): Promise<void> {
    await coreClient.post<void>(`${pathConst}{dynamicPath}`, body);
  }
}
```

Para métodos POST/PUT con response (no void): añade el payload como segundo parámetro usando `{ResourceName}Body` y usa `.post()` / `.put()`. Retorna `Promise<{ResponseInterface}>` con `response.data.data`.

**Si `httpClient = createBrowserClient`:**

```typescript
import { AxiosInstance } from 'axios';
import { createBrowserClient } from '@kui/api-client/rest/browser-client';
import { ENV } from '@kui/config/service/env';
import { NewRelic } from '@kui/lib/services/newrelic';
import { handleLogout } from '@kui/session/utils/session-utils';
import { BaseApiResponse } from '@/domain/interfaces/api/base-response.interface';
import { {ResponseInterface} } from '@/domain/interfaces/api/{resource-name}.interface';
import { setupRequestTrackingInterceptor } from '@/infrastructure/interceptors/request-tracking-interceptor';
import { setupGlobalHeadersInterceptor } from '@/infrastructure/interceptors/setup-global-headers-interceptor';
import { setupUnauthorizedInterceptor } from '@/infrastructure/interceptors/unauthorized-interceptor';

const {resourceName}Client: AxiosInstance = createBrowserClient(
  process.env.NEXT_PUBLIC_VERCEL_TARGET_ENV === 'development'
    ? `${process.env.NEXT_PUBLIC_MOCK_API_URL}/{mockSegment}`
    : `${ENV.API_FED_URL}/{apiPath}`,
);

setupGlobalHeadersInterceptor({resourceName}Client);
setupRequestTrackingInterceptor({resourceName}Client);
if (process.env.NEXT_PUBLIC_VERCEL_TARGET_ENV !== 'development') {
  setupUnauthorizedInterceptor({resourceName}Client, handleLogout);
}

export default class {ResourceName}Api {
  static async get{ResourceName}({params}): Promise<{ResponseInterface}> {
    const response = await {resourceName}Client.get<BaseApiResponse<{ResponseInterface}>>(
      `{dynamicPath}`,
    );
    NewRelic.addPageAction('get{ResourceName}Response', { payload: response.data });
    return response.data.data;
  }
}
```

### 2.2 Mock data — `{appPath}/src/infrastructure/mocks/{resource-name}-mock.ts`

**Si `responseVoid = false`:** mock de la respuesta.

```typescript
import { BaseApiResponse } from '@/domain/interfaces/api/base-response.interface';
import { {ResponseInterface} } from '@/domain/interfaces/api/{resource-name}.interface';

export const {resourceName}Mock: BaseApiResponse<{ResponseInterface}> = {
  data: {
    // campos con valores reales del JSON
  },
  requestId: 'mock-{resource-name}-id',
  time: new Date().toISOString(),
};
```

**Si `responseVoid = true` Y `hasBodyTransformation = true`:** mock del INPUT body (lo que el consumidor pasa al hook/service).

```typescript
import { {RESOURCE_NAME}_ACTIONS, {ResourceName}Input } from '@/domain/interfaces/api/{resource-name}.interface';

export const {resourceName}InputMock: {ResourceName}Input = {
  action: {RESOURCE_NAME}_ACTIONS.{FIRST_ACTION},
  // campos con valores representativos
};
```

**Si `enumFields` no es null Y `generateMockScenarios = true`:**

Crea un archivo por cada valor de enum en `enumFields`:
`{appPath}/src/infrastructure/mocks/{resource-name}-{kebab-value}-mock.ts`

### 2.3 Next.js Mock Route — `{appPath}/app/api/mock/{mockContext}/[...path]/route.ts`

**Primero verifica si el archivo ya existe.**
- Si ya existe: añade los nuevos handlers usando `Edit`.
- Si no existe: crea el archivo nuevo.

**Para GET (responseVoid = false):**

```typescript
import { NextRequest, NextResponse } from 'next/server';
import { {resourceName}Mock } from '@/infrastructure/mocks/{resource-name}-mock';

export async function GET(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params;
  const fullPath = path.join('/');

  if (fullPath.includes('{pathSegmentToMatch}')) {
    return NextResponse.json({resourceName}Mock);
  }

  return NextResponse.json({ error: `Mock not found: ${fullPath}` }, { status: 404 });
}
```

**Para POST void (responseVoid = true):**

```typescript
import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params;
  const fullPath = path.join('/');

  if (fullPath.includes('{pathSegmentToMatch}')) {
    return new NextResponse(null, { status: 204 });
  }

  return NextResponse.json({ error: `Mock not found: ${fullPath}` }, { status: 404 });
}
```

**Para POST con response (responseVoid = false):**

```typescript
export async function POST(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params;
  const fullPath = path.join('/');

  if (fullPath.includes('{pathSegmentToMatch}')) {
    return NextResponse.json({resourceName}Mock);
  }

  return NextResponse.json({ error: `Mock not found: ${fullPath}` }, { status: 404 });
}
```

---

---

## AGENTE 3 — Application

Recibes el spec del orquestador. Genera los archivos que correspondan según `generateService` y `generateAdapter`.

### 3.1 Service (solo si `generateService = true`)

Archivo: `{appPath}/src/application/services/{resource-name}-service.ts`

**Caso GET (responseVoid = false, sin adapter):**

```typescript
import { NewRelic } from '@kui/lib/services/newrelic';
import { {ResponseInterface} } from '@/domain/interfaces/api/{resource-name}.interface';
import {ResourceName}Api from '@/infrastructure/api/{resource-name}-api';

export default class {ResourceName}Service {
  static async get{ResourceName}({params}): Promise<{ResponseInterface}> {
    try {
      return await {ResourceName}Api.get{ResourceName}({args});
    } catch (error: unknown) {
      NewRelic.noticeError(error as Error, {
        errorType: 'Failed to get {resourceName}',
      });
      throw new Error('Servicios no disponibles');
    }
  }
}
```

**Caso POST void con body transformation (responseVoid = true, generateAdapter = true):**

El service recibe `{ResourceName}Input` (TS-friendly), llama al adapter para transformar a `{ResourceName}Body` (wire format), y pasa el resultado a la API class.

```typescript
import { NewRelic } from '@kui/lib/services/newrelic';
import { {ResourceName}Input } from '@/domain/interfaces/api/{resource-name}.interface';
import {ResourceName}Api from '@/infrastructure/api/{resource-name}-api';

import { {ResourceName}Adapter } from '../adapters/{resource-name}.adapter';

export default class {ResourceName}Service {
  static async create{ResourceName}(input: {ResourceName}Input): Promise<void> {
    try {
      await {ResourceName}Api.create{ResourceName}({ResourceName}Adapter.map{ResourceName}Body(input));
    } catch (error: unknown) {
      NewRelic.noticeError(error as Error, {
        errorType: 'Failed to create {resourceName}',
      });
      throw new Error('Servicios no disponibles');
    }
  }
}
```

**Caso GET con adapter (responseVoid = false, generateAdapter = true):**

```typescript
import { NewRelic } from '@kui/lib/services/newrelic';
import { {ResourceName}Domain } from '@/domain/interfaces/{resource-name}.interface';
import {ResourceName}Api from '@/infrastructure/api/{resource-name}-api';

import { {ResourceName}Adapter } from '../adapters/{resource-name}.adapter';

export default class {ResourceName}Service {
  static async get{ResourceName}({params}): Promise<{ResourceName}Domain> {
    try {
      const raw = await {ResourceName}Api.get{ResourceName}({args});
      return {ResourceName}Adapter.map{ResourceName}(raw);
    } catch (error: unknown) {
      NewRelic.noticeError(error as Error, {
        errorType: 'Failed to get {resourceName}',
      });
      throw new Error('Servicios no disponibles');
    }
  }
}
```

### 3.2 Adapter (solo si `generateAdapter = true`)

Archivo: `{appPath}/src/application/adapters/{resource-name}.adapter.ts`

**Caso adapter de respuesta GET (`responseVoid = false`):**

Patrón de `LoanOfferAdapter`: clase estática con `map{ResourceName}` que recibe el tipo raw y retorna el tipo Domain.

```typescript
import { formatMexicanPesos } from '@/application/utils/number-helper';
import { {ResponseInterface} } from '@/domain/interfaces/api/{resource-name}.interface';
import { {ResourceName}Domain } from '@/domain/interfaces/{resource-name}.interface';

export class {ResourceName}Adapter {
  static map{ResourceName}(raw: {ResponseInterface}): {ResourceName}Domain {
    return {
      ...raw,
      // campos formateados según domainFields del spec
    };
  }
}
```

**Caso adapter de body POST (`responseVoid = true`, `hasBodyTransformation = true`):**

Usa `boolToString` y `toSnakeCaseBody` de `@/application/utils/events-amplitud.utils`.
Patrón:
1. Sobreescribe los campos boolean con `boolToString()` usando spread
2. Llama a `toSnakeCaseBody()` para convertir todas las keys a snake_case
3. Añade manualmente los campos que NO vienen del input (`source`, `send_timestamp`, etc.)

```typescript
import { boolToString, toSnakeCaseBody } from '@/application/utils/events-amplitud.utils';
import {
  {ResourceName}Body,
  {ResourceName}Input,
} from '@/domain/interfaces/api/{resource-name}.interface';

export class {ResourceName}Adapter {
  static map{ResourceName}Body(input: {ResourceName}Input): {ResourceName}Body {
    const mapped = {
      ...input,
      {boolField1}: boolToString(input.{boolField1}),
      {boolField2}: boolToString(input.{boolField2}),
      // ... resto de campos boolean de booleanBodyFields
    };

    return {
      ...(toSnakeCaseBody(mapped as Record<string, unknown>) as Omit<
        {ResourceName}Body,
        'source' | 'send_timestamp'
      >),
      source: 'web',
      send_timestamp: String(Date.now()),
    };
  }
}
```

Si `booleanBodyFields` está vacío o es null, omite el paso del spread con `boolToString` y llama directamente a `toSnakeCaseBody`.

### 3.3 Hook — `{appPath}/src/application/hooks/queries/use-{verb}-{resource-name}.hook.ts`

Siempre se genera. Nombre del archivo:
- GET → `use-get-{resource-name}.hook.ts`
- POST → `use-create-{resource-name}.hook.ts`
- PUT → `use-update-{resource-name}.hook.ts`

**Para GET (useQuery):**

```typescript
import { useQuery } from '@tanstack/react-query';
import {ResourceName}Service from '@/application/services/{resource-name}-service';
import { {queryKeyEnum} } from '@/domain/constants/keys';

interface Get{ResourceName}Options {
  {pathParam}?: {paramType};
  enabled?: boolean;
}

export const useGet{ResourceName} = (options: Get{ResourceName}Options) => {
  const { {pathParam}, enabled = true } = options;

  return useQuery({
    queryKey: [{queryKeyEnum}.GET_{RESOURCE_NAME}, {pathParam}],
    queryFn: () => {ResourceName}Service.get{ResourceName}({pathParam}),
    staleTime: 2 * 60 * 1000,
    refetchOnWindowFocus: false,
    enabled: !!{pathParam} && enabled,
  });
};
```

**Para POST void (useMutation sin invalidación):**

```typescript
import { useMutation } from '@tanstack/react-query';
import {ResourceName}Service from '@/application/services/{resource-name}-service';
import { {ResourceName}Input } from '@/domain/interfaces/api/{resource-name}.interface';

export const useCreate{ResourceName} = () => {
  return useMutation({
    mutationFn: (input: {ResourceName}Input) => {ResourceName}Service.create{ResourceName}(input),
  });
};
```

**Para POST con response (useMutation con invalidación):**

```typescript
import { useMutation, useQueryClient } from '@tanstack/react-query';
import {ResourceName}Service from '@/application/services/{resource-name}-service';
import { {queryKeyEnum} } from '@/domain/constants/keys';
import { {BodyInterface} } from '@/domain/interfaces/api/{resource-name}.interface';

export const useCreate{ResourceName} = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: {BodyInterface}) => {ResourceName}Service.create{ResourceName}(input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [{queryKeyEnum}.GET_{RESOURCE_NAME}] });
    },
  });
};
```

Si `generateService = false` (solo adapter), importa el adapter directamente en el hook.

### 3.4 Integración en hook existente (solo si `hookIntegration` no es null)

Si `hookIntegration = { targetFile, context }`:

1. **Lee** el archivo `targetFile` antes de modificarlo.
2. Añade el import del hook generado respetando el orden `simple-import-sort`.
3. Añade el call del hook en el lugar indicado por `context`.
4. Usa `Edit` para modificar el archivo, nunca `Write`.

---

---

## AGENTE AUDITOR

Recibes la lista de todos los archivos generados. Lee cada uno con `Read` y verifica:

### Checklist de auditoría

#### Consistencia de tipos
- [ ] Los nombres de interfaces en `domain/interfaces/api/` coinciden exactamente con los imports en los demás archivos
- [ ] Si `responseVoid = true`: no hay `BaseApiResponse` en la API class ni en el mock de respuesta
- [ ] Si `hasBodyTransformation = true`: la API class recibe `{ResourceName}Body`, el service recibe `{ResourceName}Input`, el adapter hace la transformación
- [ ] Si hay `enumFields`: el tipo/enum está definido en la interfaz y usado correctamente
- [ ] El `queryKeyEnum` en el hook coincide con la entrada añadida en `keys.ts`

#### Correctitud de patrones
- [ ] La API class tiene exactamente un `static async` método por operación
- [ ] Si `responseVoid = false`: el mock tiene `BaseApiResponse<T>` como wrapper
- [ ] Si `responseVoid = true`: el mock es del INPUT (no de respuesta) y el route retorna 204
- [ ] Si `generateService = true`: el service tiene `try/catch` con `NewRelic.noticeError`
- [ ] Si `generateAdapter = true` Y `responseVoid = false`: el adapter tiene `map{ResourceName}` que retorna `{ResourceName}Domain`
- [ ] Si `generateAdapter = true` Y `responseVoid = true`: el adapter usa `boolToString` + `toSnakeCaseBody` de `@/application/utils/events-amplitud.utils`
- [ ] Si `httpClient = coreClient`: el import es `@/infrastructure/api/core-api`, nunca `@kui/api-core/client`
- [ ] Si `httpClient = createBrowserClient`: tiene los 3 interceptores configurados

#### Orden de imports (simple-import-sort)
Dentro de cada archivo verifica que el orden sea:
1. `@kui/` imports (alfabético entre ellos)
2. `@/application/` imports (alfabético)
3. `@/domain/` imports (alfabético)
4. `@/infrastructure/` imports (alfabético)
5. *(línea en blanco)*
6. `../` o `./` imports relativos (alfabético)

No debe haber líneas en blanco entre los grupos 1-4. Sí debe haberla antes de los relativos.

#### Mock route
- [ ] El `if (fullPath.includes(...))` usa el segmento correcto del path
- [ ] Si `responseVoid = true`: el handler POST retorna `new NextResponse(null, { status: 204 })`
- [ ] Si `responseVoid = false` y POST: el handler importa el mock y retorna `NextResponse.json(mock)`

#### Calidad
- [ ] No hay `console.log` en los archivos generados
- [ ] No hay `alert()` en los archivos generados
- [ ] Los nombres de clase/función siguen PascalCase
- [ ] Los nombres de hooks siguen `useVerb{Resource}` pattern
- [ ] Todos los paths de archivo usan `{appPath}` del spec, nunca hardcodeado

### Formato del reporte

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔍 AUDITORÍA — {ResourceName}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Archivos revisados: {N}

✅ Sin issues — todos los archivos siguen los patrones del proyecto

(o si hay issues:)
⚠️  Issues encontrados ({N}):
  [CRÍTICO] ruta/archivo.ts:línea
  → descripción del problema

Tokens agente auditor: ~{N}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Si hay issues, corrígelos directamente con `Edit` antes de reportar. Solo reporta lo que no pudiste corregir.

---

### Reglas globales para todos los agentes

1. **Lee antes de modificar** — siempre usa `Read` antes de `Edit` en archivos existentes
2. **No sobrescribas** mock routes existentes — añade con `Edit`
3. **Sin comentarios** que expliquen qué hace el código
4. **Sin tests** a menos que el usuario los pida
5. **Sin `console.log`** ni `alert()` en código generado
6. Tipos `unknown` solo cuando genuinamente no se puede inferir el tipo
7. Todos los paths de archivo deben usar `{appPath}` del spec, nunca hardcodear `apps/funnel`
8. **Orden de imports** — respetar `simple-import-sort`: `@kui/` → `@/application/` → `@/domain/` → `@/infrastructure/` → (blank) → `../` → `./`
9. **`coreClient`** — importar siempre desde `@/infrastructure/api/core-api`, nunca desde `@kui/api-core/client`
