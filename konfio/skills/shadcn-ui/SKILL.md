---
name: shadcn-ui
description: >
  Implementar, refactorizar o auditar componentes de UI en @kui/design-system
  usando shadcn/ui y Tailwind. Usar cuando el componente es reusable y vive en
  packages/design-system/src/ui/ (atoms, molecules, organisms). Para componentes
  app-local usa figma-to-code.
user-invocable: true
allowed-tools:
  - Bash
  - Read
  - Edit
  - Write
  - Agent
  - AskUserQuestion
---

# /shadcn-ui

Lee el skill completo en:

`packages/design-system/docs/skills/shadcn-ui/SKILL.md`

Ese archivo contiene el workflow completo: boundary de decisión, alineación con NDS tokens, reglas de Atomic Design, modelo de ejecución con sub-agentes (orchestrator → executors → auditor), validación CSS contra Figma y guardrails.

Sigue las instrucciones de ese archivo exactamente.
