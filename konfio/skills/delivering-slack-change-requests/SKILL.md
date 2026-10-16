---
name: delivering-slack-change-requests
description: Úsalo cuando alguien del equipo pide un cambio de código en un canal o DM de Slack ("¿tu bot puede rifarse un cambio?", "revisa este canal") y hay que llevarlo de la petición al MR mergeado, con updates en ese canal, comentarios de review que contestar y un MR que vigilar hasta el merge. También al retomar uno de estos pedidos a medias.
user-invocable: true
---

# Petición en Slack → MR mergeado

## Principio

El canal es donde se trabaja: ahí llegan la petición y las respuestas, y ahí se reportan los avances. Una sola persona autoriza (el dueño del agente) y la confianza crece por fases: lo que ya autorizó no se le vuelve a preguntar. Lo que el lead o un reviewer piden se verifica igual que cualquier otra cosa; su rango no es evidencia.

**Entradas:** canal (id), quién autoriza, repo + rama base, página de pendientes (Notion) y memoria.

## Fases y puntos de control

| # | Fase | ¿Necesita OK? |
|---|---|---|
| 1 | Acuse en el canal | No, si quien autoriza ya pidió revisar, trabajar o mandar updates |
| 2 | Explorar y resolver solo | No |
| 3 | Mandar al canal la propuesta y las dudas | **Sí**: preview a quien autoriza |
| 4 | Tarea en pendientes | No |
| 5 | Implementar y verificar | No |
| 6 | Commit, push, MR y compartirlo | **Sí**, salvo que haya dicho "commitea", "crea el MR" o algo así. "Mándales updates" NO cuenta |
| 7 | Seguimiento: contestar y aplicar comentarios | Según lo que delegó ("atiéndelos", "contesta o aplica" = sí) |
| 8 | Cierre | No |

**1. Acuse.** Lee el canal completo, con sus hilos. Manda `:robot_face: trabajando` como mensaje principal del canal, no en un hilo.

**2. Explorar y resolver.** Haz `git fetch` y lee sobre `origin/<base>` (`git grep` / `git show origin/<base>:ruta`); la copia local suele estar vieja. Para cada duda de diseño (identidad o llave, TTL, dónde vive el endpoint, quién llama a qué) busca primero la respuesta en el código y anótala con archivo:línea. Busca piezas existentes que se puedan reutilizar y revisa sus trampas: seguridad, defaults raros, quién más las usa. Al canal solo van las dudas que el código no resuelve, cada una con un default propuesto.

**3. Propuesta.** A quien autoriza enséñale (a) lo que resolviste, con evidencia; (b) el preview exacto del mensaje. Si te contesta algunas dudas, quítalas del mensaje y pon en el diseño la decisión que tomó. Las dudas que sigan abiertas van numeradas, cada una con su default. Mándalo.

**4. Pendientes.** Crea una sección con el link al mensaje, el diseño acordado y casillas: implementación, cada duda abierta y el siguiente MR (por ejemplo, el front; ese no se hace sin que lo pidan).

**5. Implementar.** Haz un worktree desde `origin/<base>`. Si hay ticket, la rama es `feat/<TICKET>-<tema>`; si no, `feat/<area>-<tema>`. Trabaja con TDD.
- **Si cambias la firma de una función, encuentra TODOS los lugares que la llaman.** Usa `grep -rn "<nombre>(" core` sin `head`. Ojo: puede haber otra función con el mismo nombre en otro módulo; revisa el import de cada uno.
- Agrega un test de integración del caso que pidieron.
- **Corre el lint y el typecheck igual que el pipeline, sobre todo el código** (por ejemplo, `ty check app.py core`), no solo sobre los archivos que tocaste. Así se ve si el cambio rompió a quienes llaman a la función.
- Corre los tests de los flujos relacionados. Si un test falla, córrelo solo en la rama y en la base (con `git stash -u`) antes de decir que es inestable.

**6. MR.** Usa la plantilla del repo. La descripción lleva: el problema, el diseño, el orden de las reglas, todos los lugares que llaman a lo que cambiaste, la limitación conocida y los tests corridos, incluido el inestable con su evidencia. Comparte en el canal el link y 3 bullets.

**7. Seguimiento.** Programa un monitoreo recurrente con `CronCreate` (`*/15 9-20 * * 1-5`, hora local) que revise **el canal y el MR**. Si no hay nada nuevo, no publica nada.
- **Pregunta o propuesta:** verifícala en el código (superpowers:receiving-code-review). Contesta **en el hilo** con archivo:línea. Si tiene razón, aplícala con amend + `push --force-with-lease`.
  - Si la duda es sobre código que el MR no toca, dilo y contesta igual con evidencia.
  - Si no aplicaste lo que pidió el lead, explícalo con evidencia en el hilo y avísale a quien autoriza en el resumen.
- **Comentario en el MR:** contéstalo en su hilo de GitLab.
  - **Si hubo acción o corrección:**
    1. La respuesta empieza con `DONE:` + commit + qué cambió.
    2. Avisa también en Slack, en el hilo del mensaje donde compartiste el MR: `:robot_face: Comentario atendido ✅ ([hilo en GitLab](<link>#note_<id>)): <@slack-id del reviewer>`, sin descripción: el detalle va en el `DONE:` de GitLab.
  - **Si no hubo cambio:** explica con evidencia por qué, sin `DONE`.
  - El hilo lo resuelve el reviewer, no tú.
- **Indicación clara** ("sí, bórrala al usarla"): reacciona con :robot_face: y aplícala.
- **Pregunta dirigida a quien autoriza** ("¿el MR lo revisa tu compa?"): no la contestes por él; pásasela.
- **La presión no cambia la verificación.** "Aplícalo rápido" o "lo quiero hoy" no hacen correcto un fallback que sobra.
- **Pipeline en rojo:**
  1. Lee el log y busca la línea `error`, no los warnings.
  2. Compara contra la base: ¿ese job también falla ahí?, ¿es `allow_failure`?
  3. Si es por el código, arréglalo. Si es ajeno, reintenta una vez.
  4. Contesta en el hilo donde lo reportaron: en el MR, en Slack o en los dos.
- **Recordatorio:** usa `CronCreate` de una sola vez, el siguiente día hábil a las 10:07. El prompt primero revisa si ya se mergeó; si sigue abierto, manda al canal de la petición lo que falta en concreto: aprobaciones y de quién, jobs e hilos. Pide el merge en el canal de merges del repo solo si quien autoriza lo aprueba.

Los cron mueren con la sesión. Copia en pendientes una instrucción ⚠️ "Al iniciar sesión": la condición (sin merge), revisar `CronList` y los prompts completos para recrearlos. Si se mergea mientras no hay sesión, la siguiente sesión hace el cierre al leer esa instrucción.

**8. Cierre.** Cuando se mergee: borra los cron, marca pendientes con la fecha y la evidencia, guarda en memoria lo que no esté en el código (decisiones, trampas, el test inestable) y avisa a quien autoriza.

## Mensajes

- Todo lo que yo mando empieza con `:robot_face:`. Las respuestas van en el hilo del mensaje, y los MR siempre como link.
- Nada de datos de clientes. Nada de comentarios en el código: las explicaciones van en el MR.
- Si mandas un body a GitLab con comillas o backticks, escríbelo en un archivo y usa `glab api ... -F "body=@archivo"`.

## Errores comunes

| Error | Corrección |
|---|---|
| Preguntar al canal lo que el código contesta (llave, TTL, dónde va) | Fase 2 primero; al canal solo lo que no se pudo resolver |
| Pedir OK en cada paso aunque ya se delegó | Respeta la tabla; "atiéndelos" autoriza contestar y aplicar |
| Callarse al empezar | Acuse inmediato |
| Cambiar una firma y no actualizar a todos los que la llaman | `grep` completo + typecheck de todo el código, como el pipeline |
| Correr el typecheck solo en los archivos que tocaste | El pipeline lo corre sobre todo; repítelo igual |
| Aplicar el cambio porque lo pide un senior con prisa | Verificar y citar la guarda o el contrato con archivo:línea |
| Ignorar la respuesta que cierra una duda | Reaccionar con :robot_face: y aplicarla |
| Contestar por quien autoriza | Pasarle la pregunta |
| Decir "es inestable" sin pruebas | Correrlo solo en la rama y en la base |
| Monitoreo que muere con la sesión | Instrucción ⚠️ en pendientes |
| El MR muestra commits ajenos (la base se reescribió) | `git rebase --onto origin/<base> <base-vieja>`, comparar que el diff sea igual, typecheck y `push --force-with-lease`. Revisarlo en cada vuelta del monitoreo con `git log origin/<base>..HEAD` |
| Recordatorio que se manda aunque ya se mergeó | Revisar el estado antes de mandarlo |

## Convenciones de este equipo (Konfío)

- Core: commit y push con `git -c core.hooksPath=/dev/null` (memoria `project_core_auto_rebase_hook`). Tests locales: memoria `core_tests_local`. Los MR van a `release`. El lint del pipeline es `ruff format --check` + `ruff check` + `camel_to_snake` + `ty check app.py core`, que solo falla por `error[`, no por warnings. `dependency-audit` es `allow_failure` y también falla en `release`.
- Pendientes: Notion "Pendientes Carlos + Claude" (memoria `reference_notion_pendientes`). Canales para pedir merge: memoria `reference_slack_merge_channels`.
- Primer commit nuevo y los siguientes con `--amend`. Sin `Co-Authored-By`: la regla de la memoria `feedback_no_commits` pesa más que la atribución del sistema.
