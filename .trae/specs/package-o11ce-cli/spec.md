# o11ce-cli (PyPI) V1 Spec

## Why
Hoy el agente requiere clonar/ejecutar el repo. Para que cualquiera pueda instalarlo en otra máquina con `pip install o11ce-cli`, necesitamos distribuir un CLI Python publicable en PyPI que además gestione el runtime vía Docker Compose.

## What Changes
- Agregar un paquete Python distribuible llamado `o11ce-cli` (módulo `o11ce_cli`) con entrypoint `o11ce`.
- Incluir en el paquete un template de Compose que corre el runtime (Django Ninja) como contenedores preconstruidos (imágenes publicadas).
- Implementar un CLI Python que:
  - gestione `up/down/status/logs` del stack vía Docker Compose
  - inicie un chat interactivo que cree runs y consuma SSE del runtime
  - soporte confirmación de acciones sensibles (`proposed_action`) y abort (`Ctrl+C`)
- Documentar flujo de build y publicación en PyPI (y prerequisito: publicar imágenes Docker del runtime).

## Impact
- Affected specs: V1 runtime API (se consume tal cual; no se modifica), distribución/instalación, UX de CLI.
- Affected code: nuevo paquete `o11ce_cli/` (Python) y assets embebidos (compose), sin romper el runtime existente.

## ADDED Requirements

### Requirement: Paquete instalable desde PyPI
El sistema SHALL proveer un paquete `o11ce-cli` instalable con `pip install o11ce-cli` que exponga el comando `o11ce` en PATH.

#### Scenario: Instalación exitosa
- **WHEN** el usuario ejecuta `pip install o11ce-cli`
- **THEN** `python -m pip show o11ce-cli` muestra el paquete instalado
- **AND** `o11ce --help` funciona y retorna exit code `0`

### Requirement: Gestión del runtime por Docker Compose
El comando `o11ce` SHALL poder levantar y bajar el runtime (agent-runtime y, opcionalmente, browser-runtime) usando Docker Compose.

#### Details
- El paquete SHALL incluir un archivo Compose template embebido (por ejemplo `o11ce_cli/assets/compose.yml`) que use imágenes publicadas (no build local).
- El CLI SHALL crear un directorio de trabajo en el home del usuario para:
  - `.env` local del stack (incluyendo `OPENROUTER_API_KEY`)
  - volúmenes bind para `workspace/`, `logs/`, `cache/`, `tmp/`
  - `compose.yml` efectivo (copia del template con overrides mínimos si aplica)
- El CLI SHALL invocar Docker Compose mediante `subprocess` usando preferencia:
  1) `docker compose` (plugin)
  2) `docker-compose` (binario legacy)
- Si Docker no está disponible, el CLI SHALL terminar con error claro y exit code no-cero.

#### Scenario: Levantar runtime (dev)
- **WHEN** el usuario ejecuta `o11ce up`
- **THEN** el CLI inicia los contenedores del runtime
- **AND** el CLI espera a que `GET /v1/health` responda `200`
- **AND** retorna exit code `0`

#### Scenario: Bajar runtime
- **WHEN** el usuario ejecuta `o11ce down`
- **THEN** el CLI detiene los contenedores del stack
- **AND** retorna exit code `0`

### Requirement: Chat interactivo (cliente HTTP+SSE)
El comando `o11ce chat` SHALL iniciar un REPL interactivo que envía mensajes al runtime y muestra la respuesta por streaming SSE.

#### Details
- Base URL default: `http://127.0.0.1:8000` (configurable por env/flag).
- El chat SHALL usar:
  - `POST /v1/runs` para crear un run
  - `GET /v1/runs/{id}/events` para consumir SSE
- El chat SHALL mostrar el stream de `token` incrementalmente.
- El chat SHALL mantener un “footer” mínimo con:
  - route, model, profile, runtime status, tokens/costo acumulado (si `usage` presente)
- El chat SHALL soportar comandos mínimos:
  - `/help`, `/debug`, `/logs [n]`, `/reset`, `/exit`
  - `/model <logic|vision|ui-tars|auto>` (mapea a `options.vision` + `options.preferred_model`)
  - `/profile <dev|browser|server>` (mapea a `options.profile`)

#### Scenario: Streaming exitoso
- **WHEN** el usuario escribe un mensaje en el REPL
- **THEN** el CLI crea un run y abre SSE
- **AND** imprime `token` events incrementalmente
- **AND** finaliza al recibir `final`

### Requirement: Confirmación de acciones sensibles
Cuando el runtime emite `proposed_action`, el CLI SHALL pedir confirmación explícita al usuario y responder con `POST /v1/runs/{id}/actions/{action_id}/approve`.

#### Scenario: Aprobar acción
- **WHEN** el CLI recibe `proposed_action` con `requires_confirmation=true`
- **AND** el usuario responde “Y”
- **THEN** el CLI envía `{ "approved": true }`
- **AND** renderiza `action_result` si llega

### Requirement: Abort inteligente (Ctrl+C)
Durante streaming, `Ctrl+C` SHALL abortar el run actual sin cerrar el proceso del CLI.

#### Scenario: Abort
- **WHEN** el usuario presiona `Ctrl+C` durante un run activo
- **THEN** el CLI llama `POST /v1/runs/{id}/abort`
- **AND** vuelve al prompt

### Requirement: Configuración y secretos
El CLI SHALL manejar secretos sin exponerlos.

#### Details
- `OPENROUTER_API_KEY` SHALL almacenarse en el `.env` local del usuario o variables de entorno del proceso, pero nunca en logs.
- El CLI SHALL evitar imprimir variables con nombres que contengan `KEY`, `TOKEN` o `SECRET`.

## MODIFIED Requirements

### Requirement: V1 distribution readiness
El alcance de V1 se amplía para incluir distribución instalable por pip, sin modificar el contrato HTTP+SSE del runtime.

## REMOVED Requirements
N/A
