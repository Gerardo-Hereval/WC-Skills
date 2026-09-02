#!/usr/bin/env python3
"""
review-detectors.py — reglas deterministas del skill /review-commit.

Reglas que NO son juicio: se detectan con regex y emiten texto canonico exacto.
Cero tokens, cero variacion entre corridas, cero omisiones.

Principios de precision (importan mas que la cobertura):
  1. Solo se evaluan lineas AGREGADAS por el diff ('+'). Nunca contexto ni
     codigo preexistente: no se le reclama al autor lo que no toco.
  2. Los numeros de linea salen del parseo de hunks, no de una estimacion.
  3. Cada detector define exclusiones explicitas. Un falso positivo quema el
     review completo; preferimos perder un hallazgo a inventar uno.
  4. Multiples ocurrencias en un archivo = UN comentario en la primera, con las
     demas listadas en el cuerpo. No se inunda el MR.

Uso:
  review-detectors.py <diff.txt> [--json out.json] [--allow-jsdoc] [--allow-comments]

  --allow-jsdoc      exime la prosa JSDoc (@param, @returns, @example, @see...)
  --allow-comments   apaga por completo el detector de comentarios explicativos

Formatos de diff aceptados:
  - '=== FILE: <path> ===' seguido de hunks   (lo que produce gitlab-mr.py diff)
  - 'diff --git a/<path> b/<path>'            (lo que produce git show)
"""

import json
import re
import sys

# ---------------------------------------------------------------------------
# Comentarios canonicos. NO parafrasear: se publican tal cual.
# ---------------------------------------------------------------------------

C_UI_IN_UNIT = """:warning: **Pruebas de UI detectadas en Unit Tests**

Se detectaron aserciones o renderizados de componentes de UI dentro de esta prueba unitaria.

**Regla de Testing:** Las pruebas unitarias deben enfocarse exclusivamente en lógica de negocio, hooks y funciones puras. La validación de componentes visuales e interacciones de UI debe probarse únicamente en **Cypress**.

:bulb: *Por favor, remueve las pruebas de UI de este archivo o migra la validación a un spec de Cypress.*"""

C_CONSOLE = """:warning: **`console.log` en el código**

Se detectó salida de debug en las líneas que agrega este MR.

**Regla:** el código de instrumentación temporal no debe llegar a `main`. Si el log es intencional para observabilidad, debe pasar por el logger del proyecto, no por `console`.

:bulb: *Por favor, remueve el `console.log` o migra a logging estructurado.*"""

C_COMMENTED_CODE = """:warning: **Código comentado**

Se detectó código comentado en las líneas que agrega este MR.

**Regla:** el código muerto no se versiona — git ya conserva el historial. Un bloque comentado no dice por qué se dejó ahí ni bajo qué condición se retoma, así que nadie se atreve a borrarlo después.

:bulb: *Por favor, elimina el bloque. Si es trabajo pendiente, déjalo en un ticket en lugar de en el diff.*"""

C_EXPLANATORY = """:warning: **Comentario explicativo en el código**

Se detectaron comentarios en las líneas que agrega este MR.

**Regla:** el código debe explicarse solo. Un comentario que describe *qué* hace el código se desincroniza en el primer refactor y a partir de ahí miente. Y si hace falta explicar *por qué*, ese contexto pertenece al mensaje del commit, al MR o al ticket — donde queda fechado y atribuido — no al archivo, donde envejece sin que nadie lo note.

:bulb: *Por favor, elimina el comentario. Si el código no se entiende sin él, extrae una función con nombre descriptivo o renombra las variables involucradas: eso sí sobrevive al refactor.*"""

C_TODO = """:warning: **`TODO` sin ticket**

Se detectó un marcador `TODO`/`FIXME` sin referencia a un ticket.

**Regla:** un TODO sin ticket no se agenda y no se cierra — se vuelve deuda invisible que solo encuentra quien lea el archivo por casualidad.

:bulb: *Por favor, referencia el ticket (ej. `TODO(KNF-1234): ...`) o resuélvelo en este MR.*"""


# ---------------------------------------------------------------------------
# Deteccion
# ---------------------------------------------------------------------------

TEST_FILE = re.compile(r"\.(test|spec)\.(ts|tsx|js|jsx|mts|cts)$")
E2E_PATH = re.compile(r"(^|/)(cypress|e2e|playwright)(/|$)|-e2e/|\.cy\.[jt]sx?$")

# Senales de DOM/render. Deliberadamente NO incluye '@testing-library/react':
# renderHook() vive en esa libreria y es EL patron correcto para probar hooks.
# Marcar el import produciria falsos positivos sobre tests legitimos.
UI_SIGNALS = [
    (re.compile(r"\brender\s*\("), "render()"),
    (re.compile(r"\bscreen\s*\."), "screen.*"),
    (re.compile(r"\b(getBy|queryBy|findBy|getAllBy|queryAllBy|findAllBy)[A-Z]\w*\s*\("), "queries del DOM"),
    (re.compile(r"\bfireEvent\s*\."), "fireEvent"),
    (re.compile(r"\buserEvent\s*\."), "userEvent"),
    (re.compile(r"\.toBeInTheDocument\s*\("), "toBeInTheDocument()"),
    (re.compile(r"\.toBeVisible\s*\("), "toBeVisible()"),
    (re.compile(r"\.toHaveTextContent\s*\("), "toHaveTextContent()"),
    (re.compile(r"\.toHaveClass\s*\("), "toHaveClass()"),
    (re.compile(r"\bcontainer\.querySelector\s*\("), "querySelector()"),
]

CONSOLE = re.compile(r"\bconsole\s*\.\s*(log|debug|dir|trace)\s*\(")

# Un comentario cuenta como "codigo comentado" solo si ademas parece codigo.
COMMENT_START = re.compile(r"^\s*(//|/\*|\*(?!/)|#)")
CODE_INSIDE = re.compile(
    r"(;\s*$)|(=>)|(\bfunction\b)|(\bconst\s+\w+\s*=)|(\blet\s+\w+\s*=)|(\bvar\s+\w+\s*=)"
    r"|(\bimport\s+.*\bfrom\b)|(\breturn\b\s+\S)|(\bif\s*\()|(\bfor\s*\()|(\bwhile\s*\()"
    r"|(\}\s*\)?\s*;?\s*$)|(\bawait\s+\w)|(\bexpect\s*\()|(\bit\s*\()|(\bdescribe\s*\()"
    r"|(\bconsole\s*\.)|(\bdef\s+\w+\s*\()|(\bclass\s+\w+)"
)
# DIRECTIVAS FUNCIONALES: parecen comentarios pero el toolchain las lee.
# Borrarlas cambia el comportamiento del build, del lint o de los tipos.
# NUNCA se marcan, ni como codigo muerto ni como comentario explicativo.
DIRECTIVE = re.compile(
    # linters y type-checkers
    r"eslint-|eslint\s|@ts-|tslint:|biome-ignore|oxlint-|deno-lint-|jshint|jscs"
    r"|noinspection|\$Flow|stylelint-|prettier-ignore"
    # cobertura
    r"|istanbul\s+ignore|c8\s+ignore|v8\s+ignore|node:coverage"
    # bundlers (borrarlas rompe el build)
    r"|webpack[A-Za-z]|@vite-|vite-ignore|@rollup|magic-comment"
    # tipos funcionales en JS
    r"|@type\b|@satisfies|@template|@overload|@deprecated"
    # pragmas y metadata
    r"|^\s*#!|@jsx|sourceMappingURL|#\s*(region|endregion)|@flow\b|@format"
    # legal / generado: se conserva por obligacion, no por gusto
    r"|SPDX|Copyright|Licen[sc]e|auto[- ]?generated|autogenerated|DO NOT EDIT"
    r"|@generated|Code generated by",
    re.I,
)

# Archivos donde un comentario es prosa evitable. Se excluyen a proposito
# yaml/sh/dockerfile/env: ahi comentar es idiomatico y a veces obligatorio.
CODE_FILE = re.compile(
    r"\.(ts|tsx|js|jsx|mjs|cjs|mts|cts|py|java|kt|kts|go|rb|php|cs|swift|rs|scala|dart)$"
)

TODO = re.compile(r"\b(TODO|FIXME|XXX|HACK)\b", re.I)
TICKET = re.compile(r"[A-Z]{2,}-\d+|#\d+|\bhttps?://")

# Prosa de documentacion. Solo se exime con --allow-jsdoc.
JSDOC_TAG = re.compile(r"@(param|returns?|example|see|description|throws|yields|author|since)\b")


def parse_diff(text):
    """-> {path: [(new_line, contenido_sin_el_+), ...]} solo de lineas agregadas."""
    files, path, new_line = {}, None, None
    for raw in text.splitlines():
        m = re.match(r"^=== FILE: (.+?) ===", raw)
        if m:
            path, new_line = m.group(1), None
            files.setdefault(path, [])
            continue
        m = re.match(r"^diff --git a/.+? b/(.+)$", raw)
        if m:
            path, new_line = m.group(1), None
            files.setdefault(path, [])
            continue
        if path is None:
            continue
        m = re.match(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@", raw)
        if m:
            new_line = int(m.group(1))
            continue
        if new_line is None:
            continue
        if raw.startswith("+++") or raw.startswith("---"):
            continue
        if raw.startswith("+"):
            files[path].append((new_line, raw[1:]))
            new_line += 1
        elif raw.startswith("-"):
            pass                      # no avanza: la linea no existe en el archivo nuevo
        else:
            new_line += 1             # contexto
    return files


def scan(files, allow_comments=False, allow_jsdoc=False):
    out = []

    def emit(path, hits, tipo, sev, titulo, body, detalle):
        """Un comentario por archivo, anclado en la primera ocurrencia."""
        first = hits[0][0]
        extra = ""
        if len(hits) > 1:
            otras = ", ".join(str(l) for l, _ in hits[1:])
            extra = f"\n\n<sub>Otras ocurrencias en este archivo: líneas {otras}.</sub>"
        out.append({
            "file": path, "line": first, "body": body + extra,
            "detector": tipo, "severidad": sev, "titulo": titulo,
            "evidencia": [f"{path}:{l} — {d}" for l, d in [(h[0], detalle(h[1])) for h in hits]][:6],
            "ocurrencias": len(hits),
        })

    for path, added in files.items():
        if not added:
            continue

        # 1. UI en unit tests
        if TEST_FILE.search(path) and not E2E_PATH.search(path):
            hits = []
            for ln, txt in added:
                if COMMENT_START.match(txt):
                    continue
                for rx, label in UI_SIGNALS:
                    if rx.search(txt):
                        hits.append((ln, label))
                        break
            if hits:
                emit(path, hits, "ui-in-unit-test", "Alta",
                     "Pruebas de UI en unit test", C_UI_IN_UNIT, lambda s: s)

        # 2. console.log
        hits = [(ln, txt.strip()[:70]) for ln, txt in added
                if CONSOLE.search(txt) and not COMMENT_START.match(txt)]
        if hits:
            emit(path, hits, "console-log", "Media",
                 "console.log en el código", C_CONSOLE, lambda s: s)

        # 3. codigo comentado
        hits = [(ln, txt.strip()[:70]) for ln, txt in added
                if COMMENT_START.match(txt) and CODE_INSIDE.search(txt)
                and not DIRECTIVE.search(txt)]
        dead_lines = {ln for ln, _ in hits}
        if hits:
            emit(path, hits, "commented-code", "Media",
                 "Código comentado", C_COMMENTED_CODE, lambda s: s)

        # 5. comentario explicativo (politica: el codigo se explica solo).
        #    Excluye lo ya marcado como codigo muerto para no duplicar comentario.
        if CODE_FILE.search(path) and not allow_comments:
            hits = []
            for ln, txt in added:
                if ln in dead_lines or not COMMENT_START.match(txt):
                    continue
                if DIRECTIVE.search(txt):
                    continue
                if allow_jsdoc and JSDOC_TAG.search(txt):
                    continue
                cuerpo = re.sub(r"^\s*(//+|/\*+|\*+/?|#+)\s*", "", txt).strip()
                if len(cuerpo) < 3:          # '// ' sueltos, cierres de bloque
                    continue
                hits.append((ln, cuerpo[:70]))
            if hits:
                emit(path, hits, "explanatory-comment", "Media",
                     "Comentario explicativo", C_EXPLANATORY, lambda s: s)

        # 4. TODO sin ticket.
        #    Solo aplica si se permiten comentarios: bajo politica de cero
        #    comentarios un TODO es un comentario y lo cubre el detector 5.
        #    Emitir ambos daria dos mensajes contradictorios sobre la misma linea
        #    ("agregale ticket" vs "borralo").
        if allow_comments or not CODE_FILE.search(path):
            hits = [(ln, txt.strip()[:70]) for ln, txt in added
                    if TODO.search(txt) and COMMENT_START.match(txt)
                    and not TICKET.search(txt)]
            if hits:
                emit(path, hits, "todo-without-ticket", "Baja",
                     "TODO sin ticket", C_TODO, lambda s: s)

    orden = {"Alta": 0, "Media": 1, "Baja": 2}
    out.sort(key=lambda f: (orden[f["severidad"]], f["file"]))
    return out


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    with open(sys.argv[1], encoding="utf-8", errors="replace") as f:
        findings = scan(parse_diff(f.read()),
                        allow_comments="--allow-comments" in sys.argv,
                        allow_jsdoc="--allow-jsdoc" in sys.argv)

    if not findings:
        print("Detectores deterministas: 0 hallazgos.")
    else:
        print(f"Detectores deterministas: {len(findings)} hallazgo(s).\n")
        for i, f in enumerate(findings, 1):
            print(f"{i}. [{f['severidad']}] {f['titulo']}  ({f['detector']})")
            print(f"   {f['file']}:{f['line']}   ocurrencias={f['ocurrencias']}")
            for e in f["evidencia"]:
                print(f"     - {e}")
            print()

    if "--json" in sys.argv:
        dest = sys.argv[sys.argv.index("--json") + 1]
        with open(dest, "w") as fh:
            json.dump({"findings": findings}, fh, indent=2, ensure_ascii=False)
        print(f"-> {dest}")


if __name__ == "__main__":
    main()
