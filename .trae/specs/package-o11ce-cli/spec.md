# o11ce-cli (PyPI) V1 Spec

## Why
Hoy el agente requiere clonar/ejecutar el repo. Para que cualquiera pueda instalarlo en otra máquina con `pip install o11ce-cli`, necesitamos distribuir un CLI Python publicable en PyPI que además gestione el runtime vía Docker Compose.

## What Changes
- Agregar un paquete Python distribuible llamado `o11ce-cli` (módulo `o11ce_cli`) con entrypoint `o11ce`.
- Incluir en el paquete un template de Compose que corre el runtime (Django Ninja) como contenedores preconstruidos (imágenes publicadas).
- Implementar un CLI Python que:
  - gestione `up/down/status/logs` del stack vía Docker Compose
- Documentar flujo de build y publicación en PyPI (incluyendo `.pypirc`/Twine sin exponer secretos y prerequisito de imágenes Docker publicadas).

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

### Requirement: Configuración y secretos
El CLI SHALL manejar secretos sin exponerlos.

#### Details
- `OPENROUTER_API_KEY` SHALL almacenarse en el `.env` local del usuario o variables de entorno del proceso, pero nunca en logs.
- El CLI SHALL evitar imprimir variables con nombres que contengan `KEY`, `TOKEN` o `SECRET`.

### Requirement: Credenciales PyPI sin interacción
El proyecto SHALL soportar publicación a PyPI sin pegar credenciales en cada release, usando un archivo `.pypirc` local del desarrollador (o variables de entorno) y Twine.

#### Scenario: Configurar `.pypirc`
- **WHEN** el desarrollador crea `~/.pypirc` con `username=__token__` y `password=<token>`
- **THEN** `python -m twine upload dist/*` usa esas credenciales sin prompt interactivo
 
## MODIFIED Requirements

## MODIFIED Requirements

### Requirement: V1 distribution readiness
El alcance de V1 se amplía para incluir distribución instalable por pip, sin modificar el contrato HTTP+SSE del runtime.

## REMOVED Requirements
N/A
