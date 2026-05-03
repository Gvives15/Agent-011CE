# o11ce-cli

`o11ce-cli` instala el comando `o11ce` para:

- levantar/bajar el runtime vía Docker Compose (`o11ce up`, `o11ce down`, `o11ce status`)

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
o11ce status
```

Bajar runtime:

```bash
o11ce down
```

## Imágenes Docker

El compose embebido usa imágenes publicadas y puede sobrescribirse:

- `O11CE_AGENT_IMAGE`
- `O11CE_BROWSER_IMAGE`

Ejemplo:

```bash
export O11CE_AGENT_IMAGE="ghcr.io/o11ce/open-peak-agent:0.1.0"
```

## Build y publicación en PyPI

Prerequisitos:

- Tener cuenta en PyPI
- Tener token de API de PyPI

### Configurar credenciales (recomendado)

Crear `~/.pypirc`:

```ini
[pypi]
username = __token__
password = <TU_TOKEN_DE_PYPI>
```

### Construir

```bash
python -m pip install -U build
python -m build
```

### Subir

```bash
python -m pip install -U twine
python -m twine upload dist/*
```
