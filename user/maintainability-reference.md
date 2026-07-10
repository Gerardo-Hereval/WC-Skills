# Maintainability reference (thermo-nuclear)

Companion to `/review-commit`. Use when drafting structural comments or calibrating severity. The operational workflow lives in `~/.claude/commands/review-commit.md`.

## What to flag aggressively

Escalate when you see:

- A complicated implementation where a cleaner reframing could delete whole categories of complexity
- Refactors that move code around but fail to reduce the number of concepts a reader must hold
- A file crossing 1000 lines due to the PR, especially if the new code could be split out
- New conditionals bolted onto unrelated code paths
- One-off booleans, nullable modes, or flags that complicate existing control flow
- Feature-specific logic leaking into general-purpose modules
- Generic "magic" handling that hides simple structure
- Thin wrappers or identity abstractions that add indirection without simplifying anything
- Unnecessary casts, `any`, `unknown`, or optional params that muddy the real contract
- Copy-pasted logic instead of extracted helpers
- Narrow edge-case handling in the middle of an already busy function
- Refactors that pass tests but make the code less modular or less readable
- "Temporary" branching likely to become permanent debt
- Bespoke helpers where the codebase already has a canonical utility
- Logic in the wrong layer/package when a clearer canonical home exists
- Sequential async flow where independent work could stay simpler in parallel
- Partial-update logic that leaves state less atomic than necessary

## Comment phrase bank (ES)

Adapt as questions to the author (skill convention):

- `este archivo cruza 1k líneas con este PR. ¿podemos descomponerlo primero?`
- `esto mete otro special-case en un flujo ya cargado. ¿lo movemos detrás de su propia abstracción?`
- `funciona, pero vuelve más spaghetti el código alrededor. ¿mantenemos el comportamiento y reestructuramos?`
- `parece feature logic filtrándose a un path compartido. ¿lo aislamos?`
- `esta abstracción no parece pagar su costo. ¿dejamos el flujo directo?`
- `¿por qué necesitamos cast / optional aquí? ¿podemos hacer el boundary más explícito?`
- `esto parece un helper a medida de algo que ya tenemos. ¿reusamos el canónico?`
- `creo que hay un code-judo move que lo simplifica mucho. ¿reencuadramos para que desaparezcan estas ramas?`
- `este refactor mueve complejidad, pero no la borra. ¿hay forma de simplificar el modelo en sí?`

## English originals (for calibration)

- `this pushes the file past 1k lines. can we decompose this first?`
- `this adds another special-case branch into an already busy flow. can we move this behind its own abstraction?`
- `this works, but it makes the surrounding code more spaghetti. let's keep the behavior and restructure the implementation.`
- `this feels like feature logic leaking into a shared path. can we isolate it?`
- `this abstraction seems unnecessary. can we just keep the direct flow?`
- `why does this need a cast / optional here? can we make the boundary more explicit instead?`
- `this looks like a bespoke helper for something we already have elsewhere. can we reuse the canonical one?`
- `i think there's a code-judo move here that makes this much simpler. can we reframe this so these branches disappear?`
- `this refactor moves complexity around, but doesn't really delete it. is there a way to make the model itself simpler?`

## Preferred remedies (short list)

- Delete a whole layer of indirection rather than polishing it
- Reframe the state model so conditionals disappear instead of getting centralized
- Change the ownership boundary so the feature becomes a natural extension of an existing abstraction
- Turn special-case logic into a simpler default flow with fewer exceptions
- Extract a helper or pure function; split a large file
- Replace condition chains with a typed model or explicit dispatcher
- Separate orchestration from business logic
- Collapse duplicate branches; delete wrappers that do not clarify the API
- Reuse the existing canonical helper; move logic to the owning package/layer
- Parallelize independent work when that also simplifies orchestration
- Restructure related updates into a more atomic flow
