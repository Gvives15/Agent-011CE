# Open-Peak V1 Spec (Implementable)

Fecha: 2026-05-03  
Estado: draft listo para implementación  
Objetivo: arquitectura cerrada para un agente con CLI tipo Gemini (Node.js), motor Python y streaming SSE vía OpenRouter

## 0. Alcance

### 0.1 Qué incluye V1

- CLI interactivo (REPL) en Node.js con streaming y comandos.
- Runtime del agente (Python) con API HTTP local y streaming SSE.
- Motor de decisiones por reglas (lógica vs visión) con overrides explícitos.
- Hardening aplicable para Docker/Compose (dev/browser/server).
- Gestión de errores, reintentos y guardrails de costo básicos.
- Persistencia mínima: logs estructurados, workspace, cache de sesión local.
- Modo /debug y manejo de archivos grandes para @archivos.
- Abort inteligente (Ctrl+C) y confirmación para acciones sensibles.

### 0.2 Qué NO incluye V1 (pasa a V2 o fuera de alcance)

- Multi-sesión (múltiples hilos persistentes).
- Integración con editor (VS Code / otros).
- Auto-instalación de dependencias en contenedor.
- Observabilidad avanzada (stack externo), multi-tenant, escalado horizontal.
- GPU como requisito (solo perfil optional-gpu documentado).

## 1. Objetivos operativos

- Reproducible: build + arranque con Compose en dev/server/browser.
- Seguro por defecto: sin root, mínima superficie, sin ejecución de acciones sensibles sin aprobación.
- Depurable: logs estructurados, /debug, health endpoint, errores claros.
- UX “Gemini-like”: respuesta en streaming, comandos rápidos, footer de estado.

## 2. Arquitectura de alto nivel

### 2.1 Componentes

- **open-peak-cli (Node.js)**: UI TUI/REPL y UX (input, streaming, comandos, confirmaciones, cache de sesión local).
- **agent-runtime (Python)**: orquestación, reglas de decisión, llamadas a OpenRouter, reintentos, costos, logging, artefactos.
- **browser-runtime (Python + Playwright, perfil browser)**: captura visual (screenshot) y navegación; solo habilitado en perfil `browser`.
- **config**: `.env` (secretos), `config/models.yml` y `config/runtime.yml` (no secretos).
- **persistencia**: `workspace/`, `logs/`, `cache/`, `tmp/`.

### 2.2 Diagrama (textual)

```text
Usuario
  |
  | (REPL, @archivos, /comandos)
  v
open-peak-cli (Node)
  |   \
  |    \ (approve/deny)         (Ctrl+C -> abort)
  |     \
  v      v
agent-runtime (Python HTTP)
  | \
  |  \ (si perfil browser + regla requiere)
  |   v
  | browser-runtime (captura/navegación)
  |
  v
OpenRouter
  |- deepseek/deepseek-chat (lógica)
  |- meta-llama/llama-3.2-11b-vision-instruct (visión)
  |- bytedance/ui-tars-72b (opcional, solo por override)
```

## 3. Contrato del CLI (Node.js)

### 3.1 Modos de ejecución

- **Host mode (default)**: CLI corre en el host y se conecta al runtime expuesto en `http://127.0.0.1:${RUNTIME_PORT}`.
- **In-container mode**: CLI corre dentro del contenedor y se conecta a `http://agent-runtime:${RUNTIME_PORT}` (red de Compose).

### 3.2 Entrada REPL

- Prompt principal acepta:
  - texto libre (mensaje al agente)
  - referencias `@path` a archivos dentro del workspace
  - comandos `/...`
- El CLI mantiene historial local y permite reenganche de sesión (cache).

### 3.3 Adjuntos con `@path`

Reglas de manejo (antes de enviar al runtime):

- El CLI resuelve `@path` relativo al workspace.
- Tipos soportados en V1:
  - texto (se envía contenido truncado según reglas)
  - imagen (`.png/.jpg/.jpeg/.webp`) se envía como “image attachment” (para visión)
- Umbrales por defecto (configurables):
  - `MAX_ATTACH_BYTES=1_000_000` (1MB)
  - `MAX_ATTACH_LINES=2_000`
- Si el archivo supera el umbral, el CLI:
  - avisa y muestra tamaño/estimación
  - por defecto envía: primeras `200` líneas + últimas `50` líneas + metadatos (path, total_lines, sha256)
  - permite opciones interactivas: enviar rango, enviar solo resumen (si runtime lo soporta), cancelar

### 3.4 Slash commands (V1)

- `/help`: ayuda rápida.
- `/model <logic|vision|ui-tars|auto>`: set del “modelo preferido” para el próximo run (no persistente).
- `/profile <dev|browser|server>`: set del perfil activo (si el runtime lo permite; en server puede ser solo lectura).
- `/debug`: muestra diagnóstico (health + últimos eventos/logs).
- `/logs [n]`: imprime últimos `n` eventos SSE o logs recientes (n default: 100).
- `/reset`: limpia contexto local (cache de sesión) y comienza “sesión nueva”.
- `/exit`: salir.

### 3.5 Footer dinámico (estado)

El CLI muestra una barra persistente (una línea) con:

- `route`: `logic|vision|ui`
- `model`: id de modelo activo
- `usage`: tokens y costo estimado por sesión
- `sandbox`: `none|restricted` (en V1 usualmente `none`)
- `profile`: `dev|browser|server`
- `runtime`: `ok|degraded|down`

Fuente: evento SSE `usage` + `status` y `health`.

### 3.6 Abort inteligente

- `Ctrl+C` durante streaming:
  - el CLI envía `POST /v1/runs/{id}/abort`
  - el CLI vuelve a prompt sin reiniciar el proceso
  - el runtime cancela la llamada upstream y finaliza el run con estado `aborted`

### 3.7 Confirmación de acciones sensibles (Y/n)

- Cuando el runtime emite `proposed_action`, el CLI:
  - renderiza un bloque con la acción propuesta (tipo + comando/args + impacto)
  - espera input explícito `Y/n`
  - envía aprobación o rechazo al runtime

## 4. API del runtime (HTTP + SSE)

### 4.1 Base URL

- `http://127.0.0.1:${RUNTIME_PORT}` (host mode)
- `http://agent-runtime:${RUNTIME_PORT}` (in-container)

### 4.2 Endpoints

#### `GET /v1/health`

Response (200):

```json
{
  "status": "ok",
  "profile": "dev",
  "models": {
    "logic": "deepseek/deepseek-chat",
    "vision": "meta-llama/llama-3.2-11b-vision-instruct",
    "ui": "bytedance/ui-tars-72b"
  },
  "browser": { "enabled": false },
  "version": "v1"
}
```

#### `POST /v1/runs`

Request:

```json
{
  "input": {
    "message": "string",
    "attachments": [
      { "type": "text", "path": "workspace/...", "content": "string", "truncated": true },
      { "type": "image", "path": "workspace/...", "mime": "image/png" }
    ]
  },
  "options": {
    "profile": "dev",
    "vision": "auto",
    "preferred_model": "auto",
    "enable_browser": false
  }
}
```

Response (201):

```json
{
  "id": "run_...",
  "events_url": "/v1/runs/run_.../events"
}
```

#### `GET /v1/runs/{id}/events` (SSE)

- SSE unidireccional del runtime al CLI.
- Formato: `event: <type>`, `id: <event_id>`, `data: <json>`.
- Reconexion:
  - el CLI puede enviar `Last-Event-ID`
  - el runtime debe mantener un buffer en memoria de al menos `N=1000` eventos o `60s` (lo que sea menor) para replays

Event types (cerrados en V1):

- `status`: estado de run y/o etapa
- `token`: streaming de texto (delta)
- `message`: bloques estructurados (cuando corresponda)
- `usage`: tokens/costo acumulado
- `proposed_action`: acción sensible propuesta (requiere aprobación)
- `action_result`: resultado de acción
- `error`: error estructurado
- `final`: cierre del run

Payloads mínimos:

```json
// status
{ "run_id": "run_...", "phase": "routing|openrouter|browser|finalize", "route": "logic", "model": "deepseek/deepseek-chat" }
```

```json
// token
{ "run_id": "run_...", "text": "..." }
```

```json
// usage
{
  "run_id": "run_...",
  "tokens": { "prompt": 0, "completion": 0, "total": 0 },
  "cost_usd": 0.0,
  "session_tokens_total": 0,
  "session_cost_usd": 0.0
}
```

```json
// proposed_action
{
  "run_id": "run_...",
  "action_id": "act_...",
  "type": "shell",
  "command": "rm -rf ...",
  "risk": "high",
  "requires_confirmation": true
}
```

```json
// error
{ "run_id": "run_...", "error_class": "OPENROUTER_429", "message": "string", "retryable": true }
```

#### `POST /v1/runs/{id}/abort`

- Semántica: cancelar upstream y marcar run como `aborted`.
- El runtime debe emitir `final` con estado `aborted`.

#### `POST /v1/runs/{id}/actions/{action_id}/approve`

Request:

```json
{ "approved": true }
```

Response (200):

```json
{ "action_id": "act_...", "accepted": true }
```

## 5. Motor de decisiones (reglas cerradas)

### 5.1 Inputs

- Mensaje del usuario.
- Adjuntos:
  - imagen → potencialmente requiere visión
  - texto → normalmente lógica
- Perfil activo: `dev|browser|server`.
- Flags/overrides: `vision`, `preferred_model`, `enable_browser`.

### 5.2 Overrides (precedencia)

Orden (de mayor a menor prioridad):

1. Override explícito del usuario en la request (`options.vision`, `options.preferred_model`).
2. Config de runtime (por perfil): `ENABLE_VISION_STEPS`, `ENABLE_BROWSER_AUTOMATION`.
3. Heurísticas determinísticas.

### 5.3 Reglas determinísticas (V1)

- Si `options.vision=never` → ruta `logic`.
- Si existe al menos un attachment `type=image` → ruta `vision` con `VISION_MODEL`.
- Si el mensaje contiene un request explícito de visión (“analizá esta captura”, “mirá la imagen”) → ruta `vision`.
- Si `options.preferred_model=ui-tars` → ruta `ui` (requiere habilitación explícita; si no, error claro).
- Caso contrario → ruta `logic` con `LOGIC_MODEL`.

Reglas de browser:

- Si la ruta requiere browser (p.ej. acción de navegación/captura) y `ENABLE_BROWSER_AUTOMATION=false` → abortar rama visual con error `BROWSER_DISABLED`.
- Si profile != `browser` y `enable_browser=true` → error `PROFILE_MISMATCH` (o elevar a `browser` si la política lo permite; default: no elevar automáticamente).

## 6. Seguridad operacional

### 6.1 Principios

- No ejecutar acciones sensibles sin confirmación explícita del usuario.
- Minimizar superficie: browser y automatización solo en perfil `browser`.
- No registrar secretos ni contenido sensible crudo innecesario.

### 6.2 Acciones sensibles (V1)

Tipos soportados por el contrato:

- `shell`: comandos de terminal dentro del contenedor (nunca en host).

Política V1:

- Toda acción `shell` requiere confirmación (Y/n).
- El runtime aplica denylist mínima antes de proponer o ejecutar:
  - rutas fuera de `/workspace`, `/tmp`, `/cache`, `/logs` (según mounts)
  - comandos destructivos sin guardrails (ej: `rm -rf /`, `mkfs`, `dd` a discos)

### 6.3 Sandbox status

- V1 reporta `sandbox=none` por defecto.
- El footer debe reflejar el estado actual (observable).

## 7. Hardening aplicable (Docker/Compose)

### 7.1 Reglas base

- Usuario no-root en runtime.
- Secrets solo vía `.env` y variables de entorno (nunca bakeados).
- Filesystem de solo lectura donde sea viable (especialmente server).
- Capacidades Linux minimizadas.

### 7.2 Settings mínimos por perfil (objetivo)

**dev**

- `read_only: false` (para facilitar iteración)
- mounts: `workspace` rw, `logs` rw, `cache` rw, `tmp` rw

**server**

- `read_only: true`
- `cap_drop: [ALL]`
- `security_opt: ["no-new-privileges:true"]`
- `pids_limit: 512`
- límites de recursos: `mem_limit`, `cpus` (valores definidos por runtime config)
- mounts: `workspace` rw (solo si se requiere), `logs` rw, `tmp` tmpfs, `cache` opcional rw

**browser**

- mantiene hardening base, pero permite recursos necesarios para Chromium/Playwright:
  - `shm_size` o configuración equivalente
  - `tmp` rw y suficiente
- browser y visión habilitados solo si config lo permite

### 7.3 Matriz de mounts (default)

- `/workspace`: rw
- `/logs`: rw
- `/cache`: rw
- `/tmp`: tmpfs (server) / rw (dev/browser)

## 8. Gestión de errores y reintentos

### 8.1 Matriz de errores (OpenRouter)

- 401/403: `OPENROUTER_AUTH` → fail fast (no reintentar).
- 429: `OPENROUTER_RATE_LIMIT` → 1 reintento con backoff corto; si persiste, error claro.
- 5xx: `OPENROUTER_UPSTREAM` → 1 reintento; si persiste, abort.
- timeout: `OPENROUTER_TIMEOUT` → 1 reintento; si persiste, abort.
- respuesta inválida: `OPENROUTER_INVALID_RESPONSE` → 0–1 reintento según causa; default 0.

### 8.2 Guardrails de ejecución

- Máx reintentos por run: 2 total.
- Máx duración por run (wall clock): configurable; default `MODEL_TIMEOUT_MS` + margen.

## 9. Gestión de costos (V1)

### 9.1 Fuente de tokens

Orden:

1. `usage` del response del proveedor (si viene).
2. Estimación (fallback): aproximación simple por longitud de texto.

### 9.2 Precios por modelo (config)

`config/models.yml` debe permitir definir:

- `input_usd_per_million_tokens`
- `output_usd_per_million_tokens`

El runtime calcula:

- costo por run (prompt + completion)
- acumulado por sesión (para footer)

### 9.3 Emisión al CLI

- Luego de cada chunk o al finalizar:
  - emitir evento `usage` con tokens y costo acumulado

## 10. Persistencia y logging

### 10.1 Cache de sesión local (CLI)

- Ruta default: `workspace/.open-peak/last_session.json` (si existe workspace montado).
- Schema mínimo:
  - `session_id`, `last_run_id`, `profile`, `preferred_model`, `history_tail` (últimos mensajes), `last_updated_at`.

### 10.2 Logs estructurados (runtime)

- Formato: JSONL.
- Campos mínimos:
  - `ts`, `run_id`, `session_id`, `route`, `model`, `phase`, `latency_ms`, `error_class`, `retry_count`
  - `tokens_prompt`, `tokens_completion`, `tokens_total`, `cost_usd`
- Sanitización:
  - nunca loguear `OPENROUTER_API_KEY`
  - truncar prompts/attachments por default (guardar hashes cuando sea útil)

### 10.3 `/debug`

El CLI `/debug` debe mostrar:

- `GET /v1/health`
- resumen de config efectiva (sin secretos)
- últimos `N=100` eventos SSE (si disponibles)
- últimos `N=200` logs (si el runtime expone endpoint o el CLI accede a logs montados)

## 11. Validación (Acceptance V1)

V1 se considera operativa cuando:

- build de imagen base no falla y el proceso corre como usuario no-root.
- `compose` levanta perfil `dev` y expone `GET /v1/health`.
- el CLI recibe streaming vía SSE (`token` events) en una tarea simple.
- `Ctrl+C` aborta un run y el runtime emite `final` con estado `aborted`.
- una acción `shell` propuesta se bloquea hasta aprobación y se registra el resultado.
- `@archivo` grande dispara warning y truncado por defecto.
- `/debug` muestra health + eventos/logs recientes.
- logs JSONL se escriben en `logs/` y un artefacto mínimo se escribe en `workspace/`.
