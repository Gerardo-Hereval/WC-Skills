---
name: add-storyblok-component
description: >
  Descarga un componente de Storyblok y lo agrega al block-library con las
  convenciones del proyecto (nombre de archivo, component_group_name, carpeta
  correcta). Crea el grupo en component-groups.json si no existe.
  Uso: /add-storyblok-component <storyblok-url-or-component-id>
user-invocable: true
allowed-tools:
  - Bash
  - Read
  - Edit
  - Write
  - AskUserQuestion
---

# /add-storyblok-component

Argumento recibido: `$ARGUMENTS`

---

## PASO 1 — Extraer IDs

Analiza `$ARGUMENTS`:

- Si es una URL de Storyblok (`https://app.storyblok.com/#/me/spaces/:spaceId/components/:componentId`):
  - Extrae `spaceId` y `componentId` de la URL
- Si son dos números separados por espacio o coma (`spaceId componentId`):
  - Úsalos directamente
- Si es solo un número:
  - Úsalo como `componentId` y lee el `spaceId` del nombre de archivo de cualquier componente existente en `data/components/` que aún tenga el sufijo `-XXXXXX.json` (archivos legacy)

---

## PASO 2 — Descargar el componente

Verifica si la variable de entorno `STORYBLOK_TOKEN` está disponible:

```bash
echo $STORYBLOK_TOKEN
```

**Si el token está disponible**, descarga el componente directamente a un directorio temporal:

```bash
./node_modules/.bin/ts-node -r tsconfig-paths/register scripts/download-component.ts "<spaceId>" "<componentId>" "$STORYBLOK_TOKEN" "./tmp-download"
```

**Si el token NO está disponible**, muestra este mensaje al usuario:

```
Por favor corre en tu terminal (con STORYBLOK_TOKEN exportado):

./node_modules/.bin/ts-node -r tsconfig-paths/register scripts/download-component.ts "<spaceId>" "<componentId>" "$STORYBLOK_TOKEN" "./tmp-download"

Cuando termines, dime el nombre del archivo descargado o simplemente escribe "listo".
```

Espera confirmación antes de continuar.

---

## PASO 3 — Leer el componente descargado

Lee el archivo JSON descargado en `./tmp-download/component-<componentId>.json`.

Extrae:
- `name` del componente
- `component_group_uuid` (si existe)

---

## PASO 4 — Determinar la carpeta destino

Lee `data/components/component-groups.json` para mostrar los grupos disponibles.

Pregunta al usuario:

```
¿En qué grupo/carpeta debe ir el componente "<name>"?

Grupos disponibles: [lista de grupos del component-groups.json]

Si es un grupo nuevo, indícame también el parent_name (grupo padre).
```

Con la respuesta, determina la ruta de destino:
- `atoms` → `data/components/atoms/`
- `molecules` → `data/components/molecules/`
- `konfio-app-web` → `data/components/templates/konfio-app-web/`
- `on-boarding` → `data/components/templates/konfio-app-web/on-boarding/`
- `funnel` → `data/components/templates/konfio-app-web/funnel/`
- `konfio-app-mobile` → `data/components/templates/konfio-app-mobile/`
- `konfio-mx` → `data/components/templates/konfio-mx/`
- Subgrupos nuevos → dentro de la ruta de su parent

### Regla de ubicación por tipo de componente (OBLIGATORIO)

La validación del proyecto aplica convenciones de nombres según el directorio:

| Directorio destino | Sufijo requerido en el archivo |
|---|---|
| `konfio-app-web/` (y subdirectorios) | debe terminar en `-page` |
| `konfio-app-mobile/` (y subdirectorios) | debe terminar en `-screen` |
| `konfio-mx/` (y subdirectorios) | debe terminar en `-page` |

**Si el componente es anidable (`is_nestable: true`) y NO es una página/pantalla raíz:**
- NO debe ir en `konfio-app-web/`, `konfio-app-mobile/` ni `konfio-mx/`
- Debe colocarse en `molecules/` (con `component_group_name: "molecules"`) aunque sea específico de un dominio
- Solo van en esos directorios los componentes con `is_nestable: false` que representan páginas o pantallas completas

---

## PASO 5 — Crear el grupo si no existe

Si el grupo indicado NO está en `component-groups.json`:

1. Agrégalo al array `component_groups` con su `parent_name`
2. Crea el directorio físico si no existe

---

## PASO 6 — Ajustar y mover el archivo

Transforma el JSON descargado aplicando estas reglas:

1. **Eliminar** el campo `component_group_uuid` (si existe)
2. **Agregar** `"component_group_name": "<nombre-del-grupo>"` al final del JSON (antes del cierre `}`)
3. **Eliminar** `component_denylist` de cualquier campo tipo `bloks` (si está vacío)
4. **Nombre del archivo**: `<name>.json` — solo el nombre del componente en kebab-case, **sin** el spaceId (ej. `credit-detail-card.json`, NO `credit-detail-card-1023897.json`)
5. **`display_name`**: Reemplaza el valor `null` por el nombre del componente en Title Case (ej. `"Credit Detail Card"`). Convierte cada palabra del nombre kebab-case a mayúscula inicial.
6. **Mover** el archivo al directorio destino determinado en el Paso 4

### Limpieza de metadatos de entorno (OBLIGATORIO)

Elimina todos los campos que son específicos del entorno de Storyblok y que provocan fallos en el CI:

**Top-level** — eliminar si existen:
- `id` (el numérico de Storyblok, ej. `177949904650601`)
- `created_at`
- `updated_at`
- `internal_tags_list`
- `internal_tag_ids`

**Dentro de cada campo del `schema`** — eliminar si existe:
- `id` (el string de Storyblok, ej. `"luvbYMnSR5KRZ7cE0Fciyg"`)

**Dentro de cada entrada de `options`** en campos tipo `option` — eliminar si existe:
- `_uid`

### Regla de `is_root`

- Si `is_nestable: true` → `is_root` **debe ser `false`** (es un bloque anidable, no un content type raíz)
- Si `is_nestable: false` → `is_root` puede quedarse como `true` (es una página/content type raíz)
- Si el componente exportado tiene `is_root: true` e `is_nestable: true`, corrige `is_root` a `false`

---

## PASO 7 — Limpiar y confirmar

1. Elimina el archivo temporal en `./tmp-download/component-<componentId>.json`
2. Si el directorio `./tmp-download/` quedó vacío, elimínalo también
3. Muestra un resumen:

```
✅ Componente agregado:
   Nombre:   <name>
   Archivo:  <ruta-final>
   Grupo:    <component_group_name>

Próximos pasos:
1. Revisa el archivo y valida que el schema sea correcto
2. Corre: pnpm run validate:components
3. Abre un MR — el CI lo desplegará automáticamente a Storyblok
```
