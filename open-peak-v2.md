# Open-Peak V2 Spec (Extensión Profesional)

Fecha: 2026-05-03  
Estado: draft (delta sobre V1)  
Base: este documento extiende [open-peak-v1.md](file:///workspace/docs/specs/open-peak-v1.md) sin romper compatibilidad

## 0. Alcance

### 0.1 Objetivo

V2 agrega potencia y refinamiento manteniendo el contrato V1 (CLI + runtime SSE), con foco en:

- productividad (multi-sesión, edición in-place)
- automatización controlada (auto-deps con permiso)
- costos y policies más robustas (budgets, breakdown, allowlists)

### 0.2 Compatibilidad

- Se mantienen los endpoints V1 y los event types SSE V1.
- V2 solo agrega nuevos endpoints, nuevos event types opcionales y nuevos comandos `/...`.
- Un CLI V1 debe poder conectarse a un runtime V2 (y viceversa con degradación graciosa cuando falte feature).

## 1. Multi-sesión (hilos persistentes)

### 1.1 Concepto

Una “sesión” representa un hilo de conversación persistente con:

- historial (mensajes)
- metadatos (modelo preferido, perfil, tags)
- artefactos y runs asociados

### 1.2 Storage

Ubicación default (portable host + contenedor si workspace está montado):

- `workspace/.open-peak/sessions/`

Archivos:

- `index.json` (lista de sesiones)
- `{session_id}.json` (detalle)

Schema mínimo de `index.json`:

```json
{
  "active_session_id": "sess_...",
  "sessions": [
    { "id": "sess_...", "name": "string", "created_at": "iso8601", "updated_at": "iso8601" }
  ]
}
```

Schema mínimo de sesión:

```json
{
  "id": "sess_...",
  "name": "string",
  "profile": "dev",
  "preferred_model": "auto",
  "history": [
    { "role": "user", "content": "..." },
    { "role": "assistant", "content": "..." }
  ],
  "runs": ["run_..."],
  "created_at": "iso8601",
  "updated_at": "iso8601"
}
```

### 1.3 Comandos CLI

- `/sessions`: lista sesiones (id, name, updated_at).
- `/new [name]`: crea sesión y la activa.
- `/switch <session_id|name>`: activa otra sesión.
- `/rename <session_id> <name>`: renombra.
- `/delete <session_id>`: borra (con confirmación).

### 1.4 Reglas de retención y tamaño

- `MAX_SESSIONS` (default 20) y `MAX_HISTORY_MESSAGES` (default 200) configurables.
- Si se excede, el CLI debe ofrecer:
  - archivar sesiones inactivas
  - truncar historial manteniendo un “summary” (si está habilitado)

## 2. Edición de código in-place (integración con editor)

### 2.1 Objetivo

Permitir que el agente “salte” a la ubicación exacta del archivo/línea sin navegar manualmente, pero siempre bajo control del usuario.

### 2.2 Modelo de acción (propuesta + confirmación)

Se extiende el sistema de `proposed_action`:

- Nuevo `type`: `open_in_editor`
- Payload:

```json
{
  "run_id": "run_...",
  "action_id": "act_...",
  "type": "open_in_editor",
  "file": "workspace/path/to/file.py",
  "line": 123,
  "col": 1,
  "editor": "vscode",
  "requires_confirmation": true
}
```

### 2.3 Implementación objetivo (cross-platform)

- Default V2: VS Code
  - Host: `code -g file:line:col` si está disponible
  - Fallback: deep link `vscode://file/...:line:col` si corresponde
- Política:
  - nunca ejecutar sin confirmación
  - si no hay editor disponible, retornar error claro y sugerir instalación/config

## 3. Auto-instalación de dependencias (con permiso)

### 3.1 Objetivo

Reducir fricción cuando el agente propone código que requiere una librería nueva, sin perder control ni romper reproducibilidad.

### 3.2 Detección

Casos típicos:

- Python: `ModuleNotFoundError`, `ImportError`
- Node: error de `Cannot find module`

### 3.3 Propuesta de acción

Nuevo `proposed_action`:

- `type`: `install_dependency`
- Payload mínimo:

```json
{
  "run_id": "run_...",
  "action_id": "act_...",
  "type": "install_dependency",
  "ecosystem": "python",
  "package": "requests",
  "command": "pip install requests==2.32.0",
  "requires_confirmation": true
}
```

### 3.4 Política de ejecución

- Solo dentro del contenedor (nunca en host).
- Reglas:
  - siempre confirmación
  - allowlist opcional (por perfil) de registries/comandos permitidos
  - registrar resultado en logs + artefacto `workspace/.open-peak/actions/{action_id}.json`
- Reproducibilidad:
  - si existe un lock (p. ej. `requirements.txt`/`pyproject.toml` o `package-lock.json`), el runtime debe proponer actualizarlo (acción separada) en lugar de “solo instalar”.

## 4. Costos avanzados (budgets y reportes)

### 4.1 Presupuestos

Config propuesta (runtime):

- `BUDGET_USD_PER_SESSION` (default 5.0)
- `BUDGET_TOKENS_PER_SESSION` (default 500_000)
- `BUDGET_USD_PER_RUN` (default 1.0)

Comportamiento:

- cuando se supera un budget:
  - emitir evento `status` con `degraded=true`
  - bloquear runs nuevos hasta confirmación explícita del usuario

### 4.2 Breakdown

- El runtime acumula por:
  - `route` (logic/vision/ui)
  - `model`
  - `run_id`

Se agrega endpoint:

- `GET /v1/costs` → resumen por sesión + breakdown por modelo/route

### 4.3 Export

Comando CLI:

- `/costs export [path]` → export JSON/CSV a workspace

## 5. Policies granulares de acciones

### 5.1 Niveles

- `deny`: nunca permitir
- `confirm`: requiere confirmación (default)
- `allow`: permitido sin prompt (solo para acciones “safe”)

### 5.2 Config

`config/runtime.yml` define:

- allowlist de comandos safe (ej: `ls`, `cat`, `python -m pytest -q` en rutas del workspace)
- denylist fuerte (siempre)
- reglas por perfil (server más estricto)

### 5.3 Eventos SSE

Se mantiene `proposed_action`, pero se agrega campo:

- `policy_applied`: `deny|confirm|allow`

## 6. Validación (Acceptance V2)

V2 se considera operativa cuando, además de pasar V1:

- se pueden crear/listar/cambiar sesiones y persisten en `workspace/.open-peak/sessions`.
- `/switch` cambia el contexto efectivo (history/runs asociados) sin mezclar hilos.
- `open_in_editor` se propone y requiere confirmación; si VS Code está disponible, abre en `file:line:col`.
- `install_dependency` se propone, requiere confirmación y registra artefacto; no corre en host.
- budgets bloquean runs cuando se exceden y el CLI lo refleja en el footer/estado.
- `GET /v1/costs` devuelve breakdown consistente con `usage` emitido por SSE.
