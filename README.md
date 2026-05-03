# Agent-011CE / Open‑Peak Agent

Starter repo para construir un agente tipo Trae con OpenRouter como gateway, DeepSeek‑V3 como modelo lógico principal, Llama 3.2 Vision como visión por defecto y UI‑TARS como ruta visual avanzada opcional.

El objetivo es tener un sistema seguro por defecto, reproducible en local y server, y con una UX de terminal estilo Gemini CLI pero diseñada específicamente para este stack (CLI Node.js + runtime Python con streaming SSE).

## Docs

- Spec V1 (implementable): [open-peak-v1.md](docs/specs/open-peak-v1.md)
- Spec V2 (delta profesional): [open-peak-v2.md](docs/specs/open-peak-v2.md)
- Spec base histórica (contexto y decisiones iniciales): [2026-05-02-open-peak-stack-design.md](docs/specs/2026-05-02-open-peak-stack-design.md)
- Plan de trabajo para escribir/validar specs por versión: [2026-05-03-open-peak-v1-v2-spec-plan.md](docs/plans/2026-05-03-open-peak-v1-v2-spec-plan.md)

## Arquitectura (resumen)

- open-peak-cli (Node.js): REPL, `@archivos`, `/comandos`, footer de estado/costos, abort inteligente (Ctrl+C) y confirmación `Y/n` para acciones sensibles.
- agent-runtime (Python): API HTTP local + streaming SSE, motor de decisiones por reglas (lógica vs visión), llamadas a OpenRouter, retries/guardrails, logs y artefactos.
- browser-runtime (perfil browser): automatización/captura visual (Playwright) habilitada solo cuando corresponde.

## Modelos (OpenRouter)

- Lógico: `deepseek/deepseek-chat`
- Visión default: `meta-llama/llama-3.2-11b-vision-instruct`
- Visión avanzada opcional: `bytedance/ui-tars-72b`

## Seguridad (principios)

- Nunca subir secretos: la API key de OpenRouter vive en `.env` (no versionado).
- El runtime corre en contenedor con usuario no-root y hardening por perfil (ver V1).
- Acciones sensibles nunca se ejecutan sin confirmación explícita del usuario (`Y/n`).

## Estructura del repo

```
docs/
  specs/           Specs V1/V2 y spec base
  plans/           Planes de trabajo
config/            (skeleton) Config no sensible (models.yml/runtime.yml) en V1
scripts/           (skeleton) Healthcheck / verify-openrouter / bootstrap en V1
app/               (skeleton) Código del runtime (agent/browser/prompts) en V1
logs/              Logs (no se versionan; se mantiene .gitkeep)
workspace/         Workspace persistente (no se versiona; se mantiene .gitkeep)
cache/             Cachés tolerables (no se versiona; se mantiene .gitkeep)
tmp/               Temporales (no se versiona; se mantiene .gitkeep)
```

## Estado del proyecto

Este repo arranca como documentación + skeleton. La implementación operativa (Dockerfile/Compose/config/scripts/runtime/CLI) se hará siguiendo:

- Spec V1 para “operatividad mínima” (SSE, reglas, hardening, validación)
- Spec V2 para “salto profesional” (multi-sesión, editor in-place, auto-deps, budgets/policies avanzadas)

