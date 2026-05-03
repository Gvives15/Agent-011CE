# o11ce-cli

`o11ce-cli` instala el comando `o11ce` para:

- levantar/bajar el runtime vía Docker Compose (`o11ce up`, `o11ce down`, `o11ce status`)
- chatear con streaming SSE contra el runtime (`o11ce chat`)

## Requisitos

- Python 3.11+
- Docker + Docker Compose (plugin `docker compose` o binario `docker-compose`)

## Instalación

```bash
pip install o11ce-cli
```

## Configuración

El runtime requiere `OPENROUTER_API_KEY`.

- Opción A: exportar variable en tu shell:

```bash
export OPENROUTER_API_KEY="..."
```

- Opción B: guardar el secreto en el `.env` del stack:

```bash
o11ce init
```

Esto crea un directorio local en tu home con `.env`, `compose.yml` y volúmenes (`workspace/ logs/ cache/ tmp/`).

## Uso

Levantar runtime:

```bash
o11ce up
```

Chat:

```bash
o11ce chat
```

Bajar runtime:

```bash
o11ce down
```

## Comandos del chat (V1)

- `/help`
- `/model <logic|vision|ui-tars|auto>`
- `/profile <dev|browser|server>`
- `/debug`
- `/logs [n]`
- `/reset`
- `/exit`

## Imágenes Docker

El compose embebido usa imágenes publicadas y puede sobrescribirse:

- `O11CE_AGENT_IMAGE`
- `O11CE_BROWSER_IMAGE`

Ejemplo:

```bash
export O11CE_AGENT_IMAGE="ghcr.io/o11ce/open-peak-agent:0.1.0"
```
