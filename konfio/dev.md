# /dev — Levantar servicios

Levanta uno o todos los servicios del monorepo en segundo plano y reporta la URL cuando esté listo.

Si se pasa un nombre de app (ej. `/dev funnel`), levanta solo ese servicio.
Si no se pasa argumento, levanta todos con `turbo run dev`.

---

## Apps disponibles y sus puertos

| App      | Filtro pnpm       | Puerto por defecto |
|----------|-------------------|--------------------|
| funnel   | `funnel`          | 3000               |
| todas    | —                 | según cada app     |

## Comandos

**Un solo servicio:**
```bash
pnpm --filter <app> dev
```
Ejemplo: `pnpm --filter funnel dev`

**Todos los servicios:**
```bash
pnpm dev
```

Ambos se ejecutan desde la raíz `/Users/carlos.heredia/Documents/porjects/konfio-app-web/`.

## Instrucciones para Claude

1. Corre el comando con `run_in_background: true` desde la raíz del monorepo.
2. Espera a que el output muestre `Ready` o `Local:` para confirmar que levantó.
3. Reporta la URL al usuario.
4. Si hay error de compilación, muéstralo directamente.
