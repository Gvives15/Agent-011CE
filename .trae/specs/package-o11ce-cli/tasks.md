# Tasks

- [x] Task 1: Definir el paquete `o11ce-cli` y su estructura
  - [x] Crear estructura `o11ce_cli/` con `__init__.py` y módulos `main.py`, `compose.py`, `runtime_client.py`, `sse.py`, `config.py`
  - [x] Crear `pyproject.toml` con metadata, dependencias y `project.scripts` para `o11ce`
  - [x] Crear `README.md` mínimo para PyPI (instalación, comandos, variables)

- [ ] Task 2: Implementar gestión de Docker Compose (up/down/status/logs)
  - [ ] Incluir template de Compose embebido que use imágenes publicadas del runtime
  - [ ] Implementar resolución de binario compose (`docker compose` vs `docker-compose`)
  - [ ] Implementar `o11ce up` con health-check `GET /v1/health`
  - [ ] Implementar `o11ce down` y `o11ce status`

- [ ] Task 3: Implementar `o11ce chat` (cliente HTTP+SSE) con UX mínima V1
  - [ ] Implementar REPL con comandos `/help /model /profile /debug /logs /reset /exit`
  - [ ] Implementar `POST /v1/runs` y consumo SSE de `/events`
  - [ ] Implementar confirmación de `proposed_action` (Y/n) y render de `action_result`
  - [ ] Implementar abort con Ctrl+C (`POST /v1/runs/{id}/abort`)

- [ ] Task 4: Persistencia local (V1 mínima) y guardrails
  - [ ] Crear directorio de trabajo del usuario (workspace/logs/cache/tmp y `.env`)
  - [ ] Guardar cache de sesión mínima (last_session) para reenganche local
  - [ ] Sanitizar logs/salidas para no exponer secretos

- [ ] Task 5: Tests y validación local
  - [ ] Tests unitarios: parse de comandos, resolución compose, formateo SSE, mapeo `/model`→options
  - [ ] Smoke test local (sin Docker): ejecutar `o11ce chat` apuntando a un runtime ya corriendo y verificar streaming de eventos

- [ ] Task 6: Build y publicación (documentación + pipeline manual)
  - [ ] Documentar pasos `python -m build` y `twine upload`
  - [ ] Documentar prerequisito de publicar imágenes Docker del runtime y versión/tagging alineado con el paquete

# Task Dependencies

- Task 3 depende de Task 1
- Task 2 depende de Task 1
- Task 4 depende de Task 2 y Task 3
- Task 5 depende de Task 2 y Task 3
- Task 6 depende de Task 1 (y coordinación externa para imágenes Docker)
