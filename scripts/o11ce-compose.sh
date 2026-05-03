#!/usr/bin/env sh
set -eu

PWD_DIR="$(pwd)"
HOME_DIR="${HOME:-}"

pick_compose() {
  if [ -f "$PWD_DIR/compose.yml" ]; then echo "$PWD_DIR/compose.yml"; return; fi
  if [ -f "$PWD_DIR/docker-compose.yml" ]; then echo "$PWD_DIR/docker-compose.yml"; return; fi
  if [ -n "$HOME_DIR" ] && [ -f "$HOME_DIR/.o11ce/stack/compose.yml" ]; then echo "$HOME_DIR/.o11ce/stack/compose.yml"; return; fi
  return 1
}

COMPOSE_FILE="$(pick_compose || true)"
if [ -z "${COMPOSE_FILE:-}" ]; then
  echo "No se encontró compose.yml. Busqué: ./compose.yml, ./docker-compose.yml, ~/.o11ce/stack/compose.yml" >&2
  exit 2
fi

WORKDIR="$(dirname "$COMPOSE_FILE")"

run_cmd() {
  cd "$WORKDIR"
  "$@"
}

if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
  run_cmd docker compose -f "$COMPOSE_FILE" "$@"
  exit $?
fi

if command -v docker-compose >/dev/null 2>&1; then
  run_cmd docker-compose -f "$COMPOSE_FILE" "$@"
  exit $?
fi

echo "Docker Compose no encontrado (docker compose o docker-compose)" >&2
exit 2

