# Tasks

- [x] Task 1: Definir el paquete `o11ce-cli` y su estructura
  - [x] Crear estructura `o11ce_cli/` con `__init__.py` y módulos `main.py`, `compose.py`, `runtime_client.py`, `sse.py`, `config.py`
  - [x] Crear `pyproject.toml` con metadata, dependencias y `project.scripts` para `o11ce`
  - [x] Crear `README.md` mínimo para PyPI (instalación, comandos, variables)

- [x] Task 2: Implementar gestión de Docker Compose (up/down/status/logs)
  - [x] Incluir template de Compose embebido que use imágenes publicadas del runtime
  - [x] Implementar resolución de binario compose (`docker compose` vs `docker-compose`)
  - [x] Implementar `o11ce up` con health-check `GET /v1/health`
  - [x] Implementar `o11ce down` y `o11ce status`

- [x] Task 3: Persistencia local (V1 mínima) y guardrails
  - [x] Crear directorio de trabajo del usuario (workspace/logs/cache/tmp y `.env`)
  - [x] Sanitizar logs/salidas para no exponer secretos

- [x] Task 4: Tests y validación local
  - [x] Tests unitarios: parse de comandos, resolución compose, y generación del stack dir/compose.yml
  - [x] Smoke test local (sin Docker): ejecutar `o11ce status` y verificar error claro cuando Docker no está disponible

- [x] Task 5: Build y publicación (documentación + pipeline manual)
  - [x] Documentar pasos `python -m build` y `twine upload`
  - [x] Documentar prerequisito de publicar imágenes Docker del runtime y versión/tagging alineado con el paquete
  - [x] Documentar configuración recomendada de `.pypirc` con `__token__` (sin copiar tokens en el repo)

# Task Dependencies

- Task 2 depende de Task 1
- Task 3 depende de Task 2
- Task 4 depende de Task 2 y Task 3
- Task 5 depende de Task 1 (y coordinación externa para imágenes Docker)
