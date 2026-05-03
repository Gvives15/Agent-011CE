# Open-Peak V1 (Django Ninja) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementar completamente [open-peak-v1.md](file:///workspace/open-peak-v1.md) usando Django Ninja (no FastAPI): CLI Node.js tipo REPL con streaming SSE y runtime Python con API HTTP local, motor de reglas, abort, confirmación de acciones y Docker Compose con perfiles.

**Architecture:** Monorepo con `cli/` (Node) y dos servicios Python: `runtime/agent` (Django Ninja) y `runtime/browser` (Django Ninja + Playwright) como servicio separado. El CLI crea runs (`POST /v1/runs`) y consume eventos por SSE (`GET /v1/runs/{id}/events`).

**Tech Stack:** Node.js (ESM), Python 3.11+, Django, django-ninja, requests, Playwright, Docker Compose.

---

## Estructura objetivo

- `cli/`
  - `package.json`
  - `src/cli.mjs`
  - `src/sse.mjs`
  - `src/attachments.mjs`
  - `src/state.mjs`
- `runtime/agent/`
  - `requirements.txt`
  - `manage.py`
  - `open_peak_agent/` (settings/urls/wsgi)
  - `api/` (Django app con Ninja router)
  - `api/services/` (OpenRouter client, run manager, policies, logging)
  - `api/tests/`
- `runtime/browser/`
  - `requirements.txt`
  - `manage.py`
  - `open_peak_browser/`
  - `browser_api/` (Ninja router + Playwright)
- `config/models.yml`
- `config/runtime.yml`
- `docker/agent/Dockerfile`
- `docker/browser/Dockerfile`
- `docker-compose.yml`
- `.env.example`
- `workspace/`, `logs/`, `cache/`, `tmp/` (directorios runtime)

---

## Convenciones del contrato (V1)

- Endpoints runtime (agent):
  - `GET /v1/health`
  - `POST /v1/runs`
  - `GET /v1/runs/{id}/events` (SSE)
  - `POST /v1/runs/{id}/abort`
  - `POST /v1/runs/{id}/actions/{action_id}/approve`
- Tipos SSE cerrados: `status`, `token`, `message`, `usage`, `proposed_action`, `action_result`, `error`, `final`.
- Replay SSE: soportar `Last-Event-ID` con buffer en memoria de `N=1000` eventos o `60s`.
- Routing determinístico (reglas del spec V1) y override por `options`.

---

### Task 1: Base de repo + config + directorios

**Files:**
- Create: `.env.example`
- Create: `config/models.yml`
- Create: `config/runtime.yml`
- Create: `workspace/.gitkeep`
- Create: `logs/.gitkeep`
- Create: `cache/.gitkeep`
- Create: `tmp/.gitkeep`

- [ ] **Step 1: Crear `.env.example`**

```env
# Copiar a .env y completar
OPENROUTER_API_KEY=
RUNTIME_PORT=8000
BROWSER_PORT=8001
PROFILE=dev
ENABLE_BROWSER_AUTOMATION=false
ENABLE_VISION_STEPS=true
```

- [ ] **Step 2: Crear `config/models.yml`**

```yaml
models:
  logic:
    id: deepseek/deepseek-chat
    input_usd_per_million_tokens: 0.0
    output_usd_per_million_tokens: 0.0
  vision:
    id: meta-llama/llama-3.2-11b-vision-instruct
    input_usd_per_million_tokens: 0.0
    output_usd_per_million_tokens: 0.0
  ui:
    id: bytedance/ui-tars-72b
    input_usd_per_million_tokens: 0.0
    output_usd_per_million_tokens: 0.0
```

- [ ] **Step 3: Crear `config/runtime.yml`**

```yaml
runtime:
  sse:
    max_events: 1000
    max_age_seconds: 60
  attachments:
    max_attach_bytes: 1000000
    max_attach_lines: 2000
  openrouter:
    base_url: https://openrouter.ai/api/v1
    timeout_seconds: 60
    max_retries_per_run: 2
  safety:
    allowed_roots:
      - /workspace
      - /tmp
      - /cache
      - /logs
    deny_commands:
      - mkfs
      - dd
      - shutdown
      - reboot
```

---

### Task 2: agent-runtime (Django Ninja) scaffold + health endpoint

**Files:**
- Create: `runtime/agent/requirements.txt`
- Create: `runtime/agent/manage.py`
- Create: `runtime/agent/open_peak_agent/__init__.py`
- Create: `runtime/agent/open_peak_agent/settings.py`
- Create: `runtime/agent/open_peak_agent/urls.py`
- Create: `runtime/agent/open_peak_agent/wsgi.py`
- Create: `runtime/agent/api/__init__.py`
- Create: `runtime/agent/api/apps.py`
- Create: `runtime/agent/api/urls.py`
- Create: `runtime/agent/api/router.py`
- Test: `runtime/agent/api/tests/test_health.py`

- [ ] **Step 1: Crear `runtime/agent/requirements.txt`**

```txt
Django==5.0.6
django-ninja==1.1.0
PyYAML==6.0.1
requests==2.32.3
```

- [ ] **Step 2: Crear `manage.py`**

```python
#!/usr/bin/env python
import os
import sys


def main() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "open_peak_agent.settings")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Crear `open_peak_agent/settings.py`**

```python
from __future__ import annotations

import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-only-secret-key")
DEBUG = os.environ.get("DJANGO_DEBUG", "false").lower() == "true"
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "api",
]

MIDDLEWARE = []

ROOT_URLCONF = "open_peak_agent.urls"
WSGI_APPLICATION = "open_peak_agent.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.environ.get("SQLITE_PATH", str(BASE_DIR / "db.sqlite3")),
    }
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
```

- [ ] **Step 4: Crear routing Django + Ninja**

`runtime/agent/open_peak_agent/urls.py`

```python
from django.urls import path

from api.router import api


urlpatterns = [
    path("", api.urls),
]
```

`runtime/agent/api/router.py`

```python
import os

from ninja import NinjaAPI

from api.urls import router as v1_router


api = NinjaAPI(title="open-peak-agent", version="v1")
api.add_router("/v1", v1_router)
```

`runtime/agent/api/urls.py`

```python
from ninja import Router

router = Router()


@router.get("/health")
def health(request):
    profile = os.environ.get("PROFILE", "dev")
    return {
        "status": "ok",
        "profile": profile,
        "models": {
            "logic": os.environ.get("LOGIC_MODEL", "deepseek/deepseek-chat"),
            "vision": os.environ.get("VISION_MODEL", "meta-llama/llama-3.2-11b-vision-instruct"),
            "ui": os.environ.get("UI_MODEL", "bytedance/ui-tars-72b"),
        },
        "browser": {"enabled": os.environ.get("ENABLE_BROWSER_AUTOMATION", "false").lower() == "true"},
        "version": "v1",
    }
```

- [ ] **Step 5: Test de health**

`runtime/agent/api/tests/test_health.py`

```python
from django.test import TestCase
from ninja.testing import TestClient

from api.router import api


class TestHealth(TestCase):
    def test_health(self):
        client = TestClient(api)
        resp = client.get("/v1/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["version"] == "v1"
```

- [ ] **Step 6: Run test**

Run: `cd runtime/agent && python manage.py test -v 2`
Expected: PASS

---

### Task 3: Modelo de run + buffer SSE + replay por Last-Event-ID

**Files:**
- Create: `runtime/agent/api/services/run_manager.py`
- Test: `runtime/agent/api/tests/test_sse_buffer.py`

- [ ] **Step 1: Test primero (buffer + replay)**

`runtime/agent/api/tests/test_sse_buffer.py`

```python
import time

from django.test import TestCase

from api.services.run_manager import RunManager


class TestSseBuffer(TestCase):
    def test_replay_since_event_id(self):
        mgr = RunManager(max_events=10, max_age_seconds=60)
        run = mgr.create_run()
        mgr.emit(run.id, "status", {"phase": "routing"})
        mgr.emit(run.id, "token", {"text": "a"})
        mgr.emit(run.id, "token", {"text": "b"})

        all_events = mgr.get_events(run.id, last_event_id=None)
        assert [e.event_type for e in all_events] == ["status", "token", "token"]

        last_id = all_events[0].event_id
        replay = mgr.get_events(run.id, last_event_id=last_id)
        assert [e.event_type for e in replay] == ["token", "token"]

    def test_eviction_by_age(self):
        mgr = RunManager(max_events=100, max_age_seconds=0)
        run = mgr.create_run()
        mgr.emit(run.id, "status", {"phase": "routing"})
        time.sleep(0.01)
        ev = mgr.get_events(run.id, last_event_id=None)
        assert ev == []
```

- [ ] **Step 2: Implementar `run_manager.py`**

`runtime/agent/api/services/run_manager.py`

```python
from __future__ import annotations

import queue
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass
from typing import Any, Deque, Dict, List, Optional


@dataclass(frozen=True)
class SseEvent:
    event_id: str
    event_type: str
    data: Dict[str, Any]
    ts: float


@dataclass
class RunState:
    id: str
    created_at: float
    abort_flag: threading.Event
    event_queue: "queue.Queue[SseEvent]"
    buffer: Deque[SseEvent]
    lock: threading.Lock
    next_event_seq: int
    final_emitted: bool
    pending_actions: Dict[str, "queue.Queue[bool]"]


class RunNotFound(Exception):
    pass


class RunManager:
    def __init__(self, max_events: int, max_age_seconds: int) -> None:
        self._runs: Dict[str, RunState] = {}
        self._lock = threading.Lock()
        self._max_events = max_events
        self._max_age_seconds = max_age_seconds

    def create_run(self) -> RunState:
        run_id = f"run_{uuid.uuid4().hex}"
        state = RunState(
            id=run_id,
            created_at=time.time(),
            abort_flag=threading.Event(),
            event_queue=queue.Queue(),
            buffer=deque(maxlen=self._max_events),
            lock=threading.Lock(),
            next_event_seq=1,
            final_emitted=False,
            pending_actions={},
        )
        with self._lock:
            self._runs[run_id] = state
        return state

    def get_run(self, run_id: str) -> RunState:
        with self._lock:
            state = self._runs.get(run_id)
        if state is None:
            raise RunNotFound(run_id)
        return state

    def emit(self, run_id: str, event_type: str, data: Dict[str, Any]) -> SseEvent:
        state = self.get_run(run_id)
        now = time.time()
        with state.lock:
            event_id = f"{run_id}:{state.next_event_seq}"
            state.next_event_seq += 1
            ev = SseEvent(event_id=event_id, event_type=event_type, data=data, ts=now)
            state.buffer.append(ev)
            state.event_queue.put(ev)
            if event_type == "final":
                state.final_emitted = True
        return ev

    def abort(self, run_id: str) -> None:
        state = self.get_run(run_id)
        state.abort_flag.set()

    def is_aborted(self, run_id: str) -> bool:
        state = self.get_run(run_id)
        return state.abort_flag.is_set()

    def get_events(self, run_id: str, last_event_id: Optional[str]) -> List[SseEvent]:
        state = self.get_run(run_id)
        now = time.time()
        cutoff = now - float(self._max_age_seconds)
        with state.lock:
            items = [e for e in list(state.buffer) if e.ts >= cutoff]
        if last_event_id is None:
            return items
        out: List[SseEvent] = []
        found = False
        for e in items:
            if found:
                out.append(e)
            elif e.event_id == last_event_id:
                found = True
        if not found:
            return items
        return out

    def create_pending_action(self, run_id: str, action_id: str) -> "queue.Queue[bool]":
        state = self.get_run(run_id)
        with state.lock:
            q: "queue.Queue[bool]" = queue.Queue(maxsize=1)
            state.pending_actions[action_id] = q
        return q

    def resolve_action(self, run_id: str, action_id: str, approved: bool) -> None:
        state = self.get_run(run_id)
        with state.lock:
            q = state.pending_actions.get(action_id)
        if q is None:
            return
        try:
            q.put_nowait(approved)
        except queue.Full:
            return
```

- [ ] **Step 3: Run tests**

Run: `cd runtime/agent && python manage.py test api.tests.test_sse_buffer -v 2`
Expected: PASS

---

### Task 4: Routing V1 + contrato `/v1/runs` (crear run y arrancar worker)

**Files:**
- Create: `runtime/agent/api/schemas.py`
- Modify: `runtime/agent/api/urls.py`
- Create: `runtime/agent/api/services/config_loader.py`
- Create: `runtime/agent/api/services/routing.py`
- Create: `runtime/agent/api/services/openrouter_client.py`
- Create: `runtime/agent/api/services/run_worker.py`
- Test: `runtime/agent/api/tests/test_routing.py`

- [ ] **Step 1: Schemas request/response**

`runtime/agent/api/schemas.py`

```python
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from ninja import Schema


AttachmentType = Literal["text", "image"]


class Attachment(Schema):
    type: AttachmentType
    path: str
    content: Optional[str] = None
    truncated: Optional[bool] = None
    mime: Optional[str] = None


class RunInput(Schema):
    message: str
    attachments: List[Attachment] = []


class RunOptions(Schema):
    profile: str = "dev"
    vision: str = "auto"
    preferred_model: str = "auto"
    enable_browser: bool = False


class CreateRunRequest(Schema):
    input: RunInput
    options: RunOptions


class CreateRunResponse(Schema):
    id: str
    events_url: str


class ApproveActionRequest(Schema):
    approved: bool


class ApproveActionResponse(Schema):
    action_id: str
    accepted: bool
```

- [ ] **Step 2: Tests de routing (reglas del spec V1)**

`runtime/agent/api/tests/test_routing.py`

```python
from django.test import TestCase

from api.schemas import Attachment, RunOptions
from api.services.routing import decide_route


class TestRouting(TestCase):
    def test_vision_never_forces_logic(self):
        route, model = decide_route(
            message="mirá la imagen",
            attachments=[Attachment(type="image", path="workspace/a.png", mime="image/png")],
            options=RunOptions(vision="never", preferred_model="auto", profile="dev", enable_browser=False),
            models={"logic": "L", "vision": "V", "ui": "U"},
            enable_ui=False,
        )
        assert route == "logic"
        assert model == "L"

    def test_image_forces_vision(self):
        route, model = decide_route(
            message="hola",
            attachments=[Attachment(type="image", path="workspace/a.png", mime="image/png")],
            options=RunOptions(vision="auto", preferred_model="auto", profile="dev", enable_browser=False),
            models={"logic": "L", "vision": "V", "ui": "U"},
            enable_ui=False,
        )
        assert route == "vision"
        assert model == "V"

    def test_ui_tars_requires_enable(self):
        route, model = decide_route(
            message="hola",
            attachments=[],
            options=RunOptions(vision="auto", preferred_model="ui-tars", profile="dev", enable_browser=False),
            models={"logic": "L", "vision": "V", "ui": "U"},
            enable_ui=False,
        )
        assert route == "error"
        assert model == ""
```

- [ ] **Step 3: Implementar routing**

`runtime/agent/api/services/routing.py`

```python
from __future__ import annotations

from typing import Dict, Tuple

from api.schemas import Attachment, RunOptions


def decide_route(
    message: str,
    attachments: list[Attachment],
    options: RunOptions,
    models: Dict[str, str],
    enable_ui: bool,
) -> Tuple[str, str]:
    if options.vision == "never":
        return "logic", models["logic"]

    if options.preferred_model == "ui-tars":
        if not enable_ui:
            return "error", ""
        return "ui", models["ui"]

    has_image = any(a.type == "image" for a in attachments)
    if has_image:
        return "vision", models["vision"]

    msg_lower = message.lower()
    if "analiz" in msg_lower and "imagen" in msg_lower:
        return "vision", models["vision"]
    if "mirá la imagen" in msg_lower or "mira la imagen" in msg_lower:
        return "vision", models["vision"]

    return "logic", models["logic"]
```

- [ ] **Step 4: Cargar config models/runtime**

`runtime/agent/api/services/config_loader.py`

```python
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

import yaml


@dataclass(frozen=True)
class RuntimeConfig:
    max_events: int
    max_age_seconds: int
    openrouter_base_url: str
    openrouter_timeout_seconds: int
    max_retries_per_run: int
    enable_browser_automation: bool
    enable_vision_steps: bool
    allow_roots: list[str]
    deny_commands: list[str]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def load_models() -> Dict[str, Dict[str, Any]]:
    p = _repo_root() / "config" / "models.yml"
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    return data["models"]


def load_runtime_config() -> RuntimeConfig:
    p = _repo_root() / "config" / "runtime.yml"
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    rt = data["runtime"]
    return RuntimeConfig(
        max_events=int(rt["sse"]["max_events"]),
        max_age_seconds=int(rt["sse"]["max_age_seconds"]),
        openrouter_base_url=str(rt["openrouter"]["base_url"]),
        openrouter_timeout_seconds=int(rt["openrouter"]["timeout_seconds"]),
        max_retries_per_run=int(rt["openrouter"]["max_retries_per_run"]),
        enable_browser_automation=os.environ.get("ENABLE_BROWSER_AUTOMATION", "false").lower() == "true",
        enable_vision_steps=os.environ.get("ENABLE_VISION_STEPS", "true").lower() == "true",
        allow_roots=[str(x) for x in rt["safety"]["allowed_roots"]],
        deny_commands=[str(x) for x in rt["safety"]["deny_commands"]],
    )
```

- [ ] **Step 5: Implementar `/v1/runs` (sin SSE aún)**

Modificar `runtime/agent/api/urls.py` para incluir el endpoint y crear un run vacío.

```python
import os

from ninja import Router

from api.schemas import CreateRunRequest, CreateRunResponse
from api.services.config_loader import load_models, load_runtime_config
from api.services.run_manager import RunManager

router = Router()

_cfg = load_runtime_config()
_models = load_models()

_run_manager = RunManager(max_events=_cfg.max_events, max_age_seconds=_cfg.max_age_seconds)


@router.get("/health")
def health(request):
    profile = os.environ.get("PROFILE", "dev")
    return {
        "status": "ok",
        "profile": profile,
        "models": {
            "logic": _models["logic"]["id"],
            "vision": _models["vision"]["id"],
            "ui": _models["ui"]["id"],
        },
        "browser": {"enabled": _cfg.enable_browser_automation},
        "version": "v1",
    }


@router.post("/runs", response=CreateRunResponse)
def create_run(request, payload: CreateRunRequest):
    run = _run_manager.create_run()
    return {"id": run.id, "events_url": f"/v1/runs/{run.id}/events"}
```

- [ ] **Step 6: Run tests**

Run: `cd runtime/agent && python manage.py test -v 2`
Expected: PASS

---

### Task 5: SSE `/v1/runs/{id}/events` + formato SSE + replay

**Files:**
- Modify: `runtime/agent/api/urls.py`
- Test: `runtime/agent/api/tests/test_sse_format.py`

- [ ] **Step 1: Test de formato SSE**

`runtime/agent/api/tests/test_sse_format.py`

```python
from django.test import TestCase
from ninja.testing import TestClient

from api.router import api
from api.urls import _run_manager


class TestSseFormat(TestCase):
    def test_sse_lines(self):
        run = _run_manager.create_run()
        _run_manager.emit(run.id, "status", {"run_id": run.id, "phase": "routing"})
        _run_manager.emit(run.id, "final", {"run_id": run.id, "status": "done"})

        client = TestClient(api)
        resp = client.get(f"/v1/runs/{run.id}/events")
        assert resp.status_code == 200
        body = resp.content.decode("utf-8")
        assert "event: status" in body
        assert "event: final" in body
        assert "id:" in body
        assert "\n\n" in body
```

- [ ] **Step 2: Implementar SSE endpoint**

En `runtime/agent/api/urls.py`, agregar:

```python
import json
import time

from django.http import HttpResponse, StreamingHttpResponse
from api.services.run_manager import RunNotFound


def _format_sse(event_type: str, event_id: str, data: dict) -> str:
    return f"event: {event_type}\nid: {event_id}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.get("/runs/{run_id}/events")
def run_events(request, run_id: str):
    last_id = request.headers.get("Last-Event-ID")
    try:
        _run_manager.get_run(run_id)
    except RunNotFound:
        return HttpResponse(status=404)

    def gen():
        replay = _run_manager.get_events(run_id, last_event_id=last_id)
        for ev in replay:
            yield _format_sse(ev.event_type, ev.event_id, ev.data)

        while True:
            if _run_manager.is_aborted(run_id):
                time.sleep(0.01)
            try:
                state = _run_manager.get_run(run_id)
                ev = state.event_queue.get(timeout=1.0)
                yield _format_sse(ev.event_type, ev.event_id, ev.data)
                if ev.event_type == "final":
                    break
            except Exception:
                continue

    resp = StreamingHttpResponse(gen(), content_type="text/event-stream")
    resp["Cache-Control"] = "no-cache"
    return resp
```

- [ ] **Step 3: Run tests**

Run: `cd runtime/agent && python manage.py test api.tests.test_sse_format -v 2`
Expected: PASS

---

### Task 6: Worker de run: streaming OpenRouter → eventos `token`/`usage` + reintentos

**Files:**
- Create: `runtime/agent/api/services/openrouter_client.py`
- Create: `runtime/agent/api/services/run_worker.py`
- Modify: `runtime/agent/api/urls.py`

- [ ] **Step 1: Implementar cliente OpenRouter (stream)**

`runtime/agent/api/services/openrouter_client.py`

```python
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Generator, Optional

import requests


@dataclass(frozen=True)
class OpenRouterChunk:
    delta_text: str
    usage: Optional[Dict[str, Any]]


class OpenRouterError(Exception):
    def __init__(self, status_code: int, message: str, retryable: bool) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.retryable = retryable


def _retryable(status: int) -> bool:
    if status in (401, 403):
        return False
    if status == 429:
        return True
    if 500 <= status <= 599:
        return True
    return False


class OpenRouterClient:
    def __init__(self, base_url: str, timeout_seconds: int) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds

    def stream_chat_completions(
        self,
        model: str,
        messages: list[dict],
        extra: Optional[dict] = None,
    ) -> Generator[OpenRouterChunk, None, None]:
        api_key = os.environ.get("OPENROUTER_API_KEY", "")
        if not api_key:
            raise OpenRouterError(401, "OPENROUTER_API_KEY missing", retryable=False)

        url = f"{self._base_url}/chat/completions"
        payload: Dict[str, Any] = {"model": model, "messages": messages, "stream": True}
        if extra:
            payload.update(extra)
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        with requests.post(url, headers=headers, json=payload, stream=True, timeout=self._timeout) as r:
            if r.status_code >= 400:
                raise OpenRouterError(r.status_code, r.text, retryable=_retryable(r.status_code))
            for raw in r.iter_lines(decode_unicode=True):
                if not raw:
                    continue
                if not raw.startswith("data:"):
                    continue
                data = raw[len("data:") :].strip()
                if data == "[DONE]":
                    break
                obj = json.loads(data)
                choice = obj.get("choices", [{}])[0]
                delta = choice.get("delta", {})
                text = delta.get("content") or ""
                usage = obj.get("usage")
                yield OpenRouterChunk(delta_text=text, usage=usage)
```

- [ ] **Step 2: Implementar worker + reintentos + abort**

`runtime/agent/api/services/run_worker.py`

```python
from __future__ import annotations

import time
import uuid
from typing import Any, Dict, Optional

from api.schemas import Attachment, RunOptions
from api.services.openrouter_client import OpenRouterClient, OpenRouterError
from api.services.routing import decide_route
from api.services.run_manager import RunManager


def _error_class(status_code: int) -> str:
    if status_code in (401, 403):
        return "OPENROUTER_AUTH"
    if status_code == 429:
        return "OPENROUTER_RATE_LIMIT"
    if 500 <= status_code <= 599:
        return "OPENROUTER_UPSTREAM"
    return "OPENROUTER_ERROR"


def run_worker(
    *,
    run_id: str,
    message: str,
    attachments: list[Attachment],
    options: RunOptions,
    models: Dict[str, str],
    cfg: Any,
    run_manager: RunManager,
    openrouter: OpenRouterClient,
) -> None:
    route, model = decide_route(
        message=message,
        attachments=attachments,
        options=options,
        models=models,
        enable_ui=False,
    )

    if route == "error":
        run_manager.emit(
            run_id,
            "error",
            {"run_id": run_id, "error_class": "UI_MODEL_DISABLED", "message": "ui-tars no habilitado", "retryable": False},
        )
        run_manager.emit(run_id, "final", {"run_id": run_id, "status": "error"})
        return

    run_manager.emit(run_id, "status", {"run_id": run_id, "phase": "routing", "route": route, "model": model})

    retries_left = int(cfg.max_retries_per_run)
    attempt = 0
    session_tokens_total = 0
    session_cost_usd = 0.0

    while True:
        attempt += 1
        if run_manager.is_aborted(run_id):
            run_manager.emit(run_id, "final", {"run_id": run_id, "status": "aborted"})
            return

        try:
            run_manager.emit(run_id, "status", {"run_id": run_id, "phase": "openrouter", "route": route, "model": model})
            messages = [{"role": "user", "content": message}]
            for chunk in openrouter.stream_chat_completions(model=model, messages=messages):
                if run_manager.is_aborted(run_id):
                    run_manager.emit(run_id, "final", {"run_id": run_id, "status": "aborted"})
                    return
                if chunk.delta_text:
                    run_manager.emit(run_id, "token", {"run_id": run_id, "text": chunk.delta_text})
                if chunk.usage:
                    tokens_total = int(chunk.usage.get("total_tokens") or 0)
                    session_tokens_total = max(session_tokens_total, tokens_total)
                    run_manager.emit(
                        run_id,
                        "usage",
                        {
                            "run_id": run_id,
                            "tokens": {"prompt": int(chunk.usage.get("prompt_tokens") or 0), "completion": int(chunk.usage.get("completion_tokens") or 0), "total": tokens_total},
                            "cost_usd": 0.0,
                            "session_tokens_total": session_tokens_total,
                            "session_cost_usd": session_cost_usd,
                        },
                    )
            run_manager.emit(run_id, "final", {"run_id": run_id, "status": "done"})
            return
        except OpenRouterError as e:
            err = {"run_id": run_id, "error_class": _error_class(e.status_code), "message": str(e), "retryable": e.retryable}
            run_manager.emit(run_id, "error", err)
            if not e.retryable or retries_left <= 0:
                run_manager.emit(run_id, "final", {"run_id": run_id, "status": "error"})
                return
            retries_left -= 1
            time.sleep(0.5)
```

- [ ] **Step 3: Conectar worker en `/v1/runs`**

En `runtime/agent/api/urls.py` dentro de `create_run`, lanzar `threading.Thread(..., daemon=True)`.

```python
import threading

from api.services.openrouter_client import OpenRouterClient
from api.services.run_worker import run_worker

_openrouter = OpenRouterClient(base_url=_cfg.openrouter_base_url, timeout_seconds=_cfg.openrouter_timeout_seconds)


@router.post("/runs", response=CreateRunResponse)
def create_run(request, payload: CreateRunRequest):
    run = _run_manager.create_run()
    t = threading.Thread(
        target=run_worker,
        kwargs={
            "run_id": run.id,
            "message": payload.input.message,
            "attachments": payload.input.attachments,
            "options": payload.options,
            "models": {"logic": _models["logic"]["id"], "vision": _models["vision"]["id"], "ui": _models["ui"]["id"]},
            "cfg": _cfg,
            "run_manager": _run_manager,
            "openrouter": _openrouter,
        },
        daemon=True,
    )
    t.start()
    return {"id": run.id, "events_url": f"/v1/runs/{run.id}/events"}
```

---

### Task 7: Abort endpoint `/v1/runs/{id}/abort`

**Files:**
- Modify: `runtime/agent/api/urls.py`

- [ ] **Step 1: Agregar endpoint**

```python
from ninja import Schema


class AbortResponse(Schema):
    id: str
    accepted: bool


@router.post("/runs/{run_id}/abort", response=AbortResponse)
def abort_run(request, run_id: str):
    _run_manager.abort(run_id)
    return {"id": run_id, "accepted": True}
```

---

### Task 8: Acciones sensibles (shell) con confirmación

**Nota:** Para V1, se implementa un trigger determinístico: si el mensaje empieza con `!shell `, el runtime NO llama al modelo: emite `proposed_action` y espera aprobación en `/approve`.

**Files:**
- Create: `runtime/agent/api/services/shell_actions.py`
- Modify: `runtime/agent/api/services/run_worker.py`
- Modify: `runtime/agent/api/urls.py`
- Test: `runtime/agent/api/tests/test_shell_action.py`

- [ ] **Step 1: Test end-to-end (propose → approve → action_result → final)**

`runtime/agent/api/tests/test_shell_action.py`

```python
import json

from django.test import TestCase
from ninja.testing import TestClient

from api.router import api


class TestShellAction(TestCase):
    def test_shell_action_flow(self):
        client = TestClient(api)
        resp = client.post(
            "/v1/runs",
            json={"input": {"message": "!shell echo hi", "attachments": []}, "options": {"profile": "dev", "vision": "auto", "preferred_model": "auto", "enable_browser": False}},
        )
        assert resp.status_code == 200
        run_id = resp.json()["id"]

        events = client.get(f"/v1/runs/{run_id}/events").content.decode("utf-8")
        assert "event: proposed_action" in events
```

- [ ] **Step 2: Implementar `shell_actions.py` (policy + ejecución)**

`runtime/agent/api/services/shell_actions.py`

```python
from __future__ import annotations

import os
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ShellPolicy:
    allow_roots: list[str]
    deny_commands: list[str]


def _is_path_allowed(path: str, allow_roots: list[str]) -> bool:
    p = Path(path).resolve()
    for root in allow_roots:
        if str(p).startswith(str(Path(root).resolve())):
            return True
    return False


def validate_shell_command(cmd: str, policy: ShellPolicy) -> None:
    parts = shlex.split(cmd)
    if not parts:
        raise ValueError("empty command")
    if parts[0] in policy.deny_commands:
        raise ValueError("command denied")

    for token in parts[1:]:
        if token.startswith("/"):
            if not _is_path_allowed(token, policy.allow_roots):
                raise ValueError("path denied")


def run_shell(cmd: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        shell=True,
        check=False,
        capture_output=True,
        text=True,
        cwd="/workspace",
        env={k: v for k, v in os.environ.items() if "KEY" not in k},
    )
```

- [ ] **Step 3: Integrar trigger `!shell` en `run_worker`**

En `runtime/agent/api/services/run_worker.py`, al principio:

```python
from api.services.shell_actions import ShellPolicy, run_shell, validate_shell_command


def run_worker(...):
    if message.startswith("!shell "):
        cmd = message[len("!shell ") :].strip()
        action_id = f"act_{uuid.uuid4().hex}"
        run_manager.emit(
            run_id,
            "proposed_action",
            {"run_id": run_id, "action_id": action_id, "type": "shell", "command": cmd, "risk": "high", "requires_confirmation": True},
        )
        approval_q = run_manager.create_pending_action(run_id, action_id)
        approved = approval_q.get()
        if not approved:
            run_manager.emit(run_id, "final", {"run_id": run_id, "status": "aborted"})
            return

        try:
            validate_shell_command(cmd, ShellPolicy(allow_roots=cfg.allow_roots, deny_commands=cfg.deny_commands))
        except Exception as e:
            run_manager.emit(run_id, "error", {"run_id": run_id, "error_class": "SHELL_DENIED", "message": str(e), "retryable": False})
            run_manager.emit(run_id, "final", {"run_id": run_id, "status": "error"})
            return

        res = run_shell(cmd)
        run_manager.emit(
            run_id,
            "action_result",
            {
                "run_id": run_id,
                "action_id": action_id,
                "exit_code": res.returncode,
                "stdout": res.stdout[-4000:],
                "stderr": res.stderr[-4000:],
            },
        )
        run_manager.emit(run_id, "final", {"run_id": run_id, "status": "done"})
        return
```

- [ ] **Step 4: Implementar `/approve`**

En `runtime/agent/api/urls.py`:

```python
from api.schemas import ApproveActionRequest, ApproveActionResponse


@router.post("/runs/{run_id}/actions/{action_id}/approve", response=ApproveActionResponse)
def approve_action(request, run_id: str, action_id: str, payload: ApproveActionRequest):
    _run_manager.resolve_action(run_id, action_id, approved=bool(payload.approved))
    return {"action_id": action_id, "accepted": True}
```

---

### Task 9: browser-runtime (Django Ninja + Playwright) como servicio separado

**Files:**
- Create: `runtime/browser/requirements.txt`
- Create: `runtime/browser/manage.py`
- Create: `runtime/browser/open_peak_browser/settings.py`
- Create: `runtime/browser/open_peak_browser/urls.py`
- Create: `runtime/browser/open_peak_browser/wsgi.py`
- Create: `runtime/browser/browser_api/router.py`
- Create: `runtime/browser/browser_api/urls.py`

- [ ] **Step 1: Crear requirements**

```txt
Django==5.0.6
django-ninja==1.1.0
playwright==1.44.0
```

- [ ] **Step 2: Endpoint mínimo de screenshot**

`runtime/browser/browser_api/urls.py`

```python
import time
import uuid
from pathlib import Path

from ninja import Router, Schema
from playwright.sync_api import sync_playwright


router = Router()


class ScreenshotRequest(Schema):
    url: str


@router.post("/screenshot")
def screenshot(request, payload: ScreenshotRequest):
    out_dir = Path("/workspace/.open-peak/artifacts")
    out_dir.mkdir(parents=True, exist_ok=True)
    name = f"screenshot_{int(time.time())}_{uuid.uuid4().hex}.png"
    out_path = out_dir / name
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(payload.url, wait_until="networkidle")
        page.screenshot(path=str(out_path), full_page=True)
        browser.close()
    return {"path": str(out_path), "mime": "image/png"}
```

---

### Task 10: CLI Node.js (REPL + SSE + @archivos + commands + abort)

**Files:**
- Create: `cli/package.json`
- Create: `cli/src/state.mjs`
- Create: `cli/src/sse.mjs`
- Create: `cli/src/attachments.mjs`
- Create: `cli/src/cli.mjs`

- [ ] **Step 1: `package.json`**

```json
{
  "name": "open-peak-cli",
  "private": true,
  "type": "module",
  "version": "0.1.0",
  "dependencies": {
    "eventsource": "2.0.2"
  }
}
```

- [ ] **Step 2: Cliente SSE y buffer**

`cli/src/sse.mjs`

```js
import EventSource from "eventsource";

export function openSse({ url, lastEventId, onEvent }) {
  const es = new EventSource(url, {
    headers: lastEventId ? { "Last-Event-ID": lastEventId } : undefined,
  });
  es.onmessage = () => {};
  const types = ["status","token","message","usage","proposed_action","action_result","error","final"];
  for (const t of types) {
    es.addEventListener(t, (e) => onEvent(t, e));
  }
  es.onerror = (e) => onEvent("error", { data: JSON.stringify({ message: "SSE_ERROR", raw: String(e) }) });
  return es;
}
```

- [ ] **Step 3: Adjuntos `@path` con truncado**

`cli/src/attachments.mjs`

```js
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";

const IMAGE_EXT = new Set([".png", ".jpg", ".jpeg", ".webp"]);

export function parseAttachments(inputLine) {
  const parts = inputLine.split(/\s+/);
  const paths = [];
  const rest = [];
  for (const p of parts) {
    if (p.startsWith("@")) paths.push(p.slice(1));
    else rest.push(p);
  }
  return { message: rest.join(" "), paths };
}

export function loadAttachment({ workspaceDir, relPath, maxBytes, maxLines }) {
  const full = path.resolve(workspaceDir, relPath);
  const ext = path.extname(full).toLowerCase();
  const buf = fs.readFileSync(full);
  if (IMAGE_EXT.has(ext)) {
    return { type: "image", path: `workspace/${relPath}`, mime: `image/${ext === ".jpg" ? "jpeg" : ext.slice(1)}` };
  }

  const text = buf.toString("utf-8");
  const lines = text.split("\n");
  const truncated = buf.byteLength > maxBytes || lines.length > maxLines;
  if (!truncated) return { type: "text", path: `workspace/${relPath}`, content: text, truncated: false };

  const head = lines.slice(0, 200);
  const tail = lines.slice(Math.max(0, lines.length - 50));
  const sha256 = crypto.createHash("sha256").update(buf).digest("hex");
  const content = [
    `# TRUNCATED attachment`,
    `# path=${relPath}`,
    `# total_lines=${lines.length}`,
    `# bytes=${buf.byteLength}`,
    `# sha256=${sha256}`,
    "",
    ...head,
    "",
    "# ...",
    "",
    ...tail,
  ].join("\n");
  return { type: "text", path: `workspace/${relPath}`, content, truncated: true };
}
```

- [ ] **Step 4: Estado + comandos + abort**

`cli/src/state.mjs`

```js
import fs from "node:fs";
import path from "node:path";

export function defaultState() {
  return {
    profile: "dev",
    preferredModel: "auto",
    vision: "auto",
    lastRunId: null,
    lastEventId: null,
    sessionTokensTotal: 0,
    sessionCostUsd: 0,
    eventRing: [],
  };
}

export function loadState(workspaceDir) {
  const p = path.join(workspaceDir, ".open-peak", "last_session.json");
  try {
    return JSON.parse(fs.readFileSync(p, "utf-8"));
  } catch {
    return defaultState();
  }
}

export function saveState(workspaceDir, state) {
  const dir = path.join(workspaceDir, ".open-peak");
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(dir, "last_session.json"), JSON.stringify({ ...state, last_updated_at: new Date().toISOString() }, null, 2));
}
```

- [ ] **Step 5: CLI principal**

`cli/src/cli.mjs`

```js
import readline from "node:readline";

import { loadAttachment, parseAttachments } from "./attachments.mjs";
import { openSse } from "./sse.mjs";
import { loadState, saveState } from "./state.mjs";

const workspaceDir = process.env.WORKSPACE_DIR || process.cwd();
const runtimeBase = process.env.RUNTIME_BASE || `http://127.0.0.1:${process.env.RUNTIME_PORT || "8000"}`;

const MAX_ATTACH_BYTES = Number(process.env.MAX_ATTACH_BYTES || "1000000");
const MAX_ATTACH_LINES = Number(process.env.MAX_ATTACH_LINES || "2000");

let state = loadState(workspaceDir);
let active = { runId: null, es: null };

function printFooter() {
  process.stdout.write(
    `\n[route:${state.route || "?"}] [model:${state.model || "?"}] [usage:${state.sessionTokensTotal} tok] [profile:${state.profile}] [runtime:${state.runtime || "?"}]\n`
  );
}

async function postJson(url, body) {
  const r = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  const t = await r.text();
  if (!r.ok) throw new Error(`HTTP ${r.status}: ${t}`);
  return JSON.parse(t);
}

async function handleLine(line) {
  const trimmed = line.trim();
  if (!trimmed) return;

  if (trimmed === "/exit") process.exit(0);
  if (trimmed === "/help") {
    console.log("/help /model <logic|vision|ui-tars|auto> /profile <dev|browser|server> /debug /logs [n] /reset /exit");
    return;
  }
  if (trimmed.startsWith("/model ")) {
    state.preferredModel = trimmed.split(/\s+/)[1] || "auto";
    saveState(workspaceDir, state);
    return;
  }
  if (trimmed.startsWith("/profile ")) {
    state.profile = trimmed.split(/\s+/)[1] || "dev";
    saveState(workspaceDir, state);
    return;
  }
  if (trimmed === "/reset") {
    state = { ...state, lastRunId: null, lastEventId: null, eventRing: [] };
    saveState(workspaceDir, state);
    return;
  }
  if (trimmed.startsWith("/logs")) {
    const n = Number(trimmed.split(/\s+/)[1] || "100");
    const tail = state.eventRing.slice(Math.max(0, state.eventRing.length - n));
    for (const e of tail) console.log(e);
    return;
  }
  if (trimmed === "/debug") {
    const r = await fetch(`${runtimeBase}/v1/health`);
    console.log("health:", await r.text());
    console.log("events_tail:", state.eventRing.slice(Math.max(0, state.eventRing.length - 100)));
    return;
  }

  const { message, paths } = parseAttachments(trimmed);
  const attachments = paths.map((p) => loadAttachment({ workspaceDir, relPath: p, maxBytes: MAX_ATTACH_BYTES, maxLines: MAX_ATTACH_LINES }));

  const resp = await postJson(`${runtimeBase}/v1/runs`, {
    input: { message, attachments },
    options: { profile: state.profile, vision: state.vision, preferred_model: state.preferredModel, enable_browser: false },
  });

  active.runId = resp.id;
  state.lastRunId = resp.id;
  saveState(workspaceDir, state);

  const eventsUrl = `${runtimeBase}${resp.events_url}`;
  active.es = openSse({
    url: eventsUrl,
    lastEventId: state.lastEventId,
    onEvent: async (type, e) => {
      const raw = e.data;
      state.eventRing.push(`[${type}] ${raw}`);
      if (state.eventRing.length > 1000) state.eventRing.shift();

      if (e.lastEventId) state.lastEventId = e.lastEventId;
      if (type === "status") {
        const d = JSON.parse(raw);
        state.route = d.route;
        state.model = d.model;
        state.runtime = "ok";
        printFooter();
      } else if (type === "token") {
        const d = JSON.parse(raw);
        process.stdout.write(d.text);
      } else if (type === "usage") {
        const d = JSON.parse(raw);
        state.sessionTokensTotal = d.session_tokens_total || state.sessionTokensTotal;
        state.sessionCostUsd = d.session_cost_usd || state.sessionCostUsd;
      } else if (type === "proposed_action") {
        const d = JSON.parse(raw);
        console.log(`\nproposed_action (${d.risk}): ${d.command}`);
        rl.question("Approve? (Y/n) ", async (ans) => {
          const approved = ans.trim() === "" || ans.trim().toLowerCase() === "y";
          await postJson(`${runtimeBase}/v1/runs/${d.run_id}/actions/${d.action_id}/approve`, { approved });
        });
      } else if (type === "final") {
        console.log("\n");
        printFooter();
        saveState(workspaceDir, state);
        active.es?.close();
        active.es = null;
      }
    },
  });
}

process.on("SIGINT", async () => {
  if (active.runId) {
    try {
      await postJson(`${runtimeBase}/v1/runs/${active.runId}/abort`, {});
    } catch {}
    if (active.es) active.es.close();
    active.runId = null;
    active.es = null;
    process.stdout.write("\n");
    return;
  }
  process.exit(0);
});

const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
rl.setPrompt("> ");
rl.prompt();
rl.on("line", async (line) => {
  try {
    await handleLine(line);
  } catch (e) {
    console.error(String(e));
  } finally {
    rl.prompt();
  }
});
```

---

### Task 11: Docker/Compose (dev/server/browser) + hardening mínimo

**Files:**
- Create: `docker/agent/Dockerfile`
- Create: `docker/browser/Dockerfile`
- Create: `docker-compose.yml`

- [ ] **Step 1: Dockerfile agent (no-root)**

`docker/agent/Dockerfile`

```Dockerfile
FROM python:3.11-slim

RUN useradd -m -u 10001 appuser
WORKDIR /app

COPY runtime/agent/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY runtime/agent /app

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

USER appuser
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
```

- [ ] **Step 2: Dockerfile browser (Playwright)**

`docker/browser/Dockerfile`

```Dockerfile
FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

RUN useradd -m -u 10002 appuser
WORKDIR /app

COPY runtime/browser/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY runtime/browser /app

EXPOSE 8001
USER appuser
CMD ["python", "manage.py", "runserver", "0.0.0.0:8001"]
```

- [ ] **Step 3: docker-compose con perfiles**

`docker-compose.yml`

```yaml
services:
  agent-runtime:
    build:
      context: .
      dockerfile: docker/agent/Dockerfile
    environment:
      - OPENROUTER_API_KEY=${OPENROUTER_API_KEY}
      - PROFILE=${PROFILE:-dev}
      - ENABLE_BROWSER_AUTOMATION=${ENABLE_BROWSER_AUTOMATION:-false}
      - ENABLE_VISION_STEPS=${ENABLE_VISION_STEPS:-true}
    ports:
      - "${RUNTIME_PORT:-8000}:8000"
    volumes:
      - ./workspace:/workspace:rw
      - ./logs:/logs:rw
      - ./cache:/cache:rw
      - ./tmp:/tmp:rw
      - ./config:/app/config:ro
    profiles: ["dev", "server", "browser"]

  browser-runtime:
    build:
      context: .
      dockerfile: docker/browser/Dockerfile
    ports:
      - "${BROWSER_PORT:-8001}:8001"
    volumes:
      - ./workspace:/workspace:rw
      - ./tmp:/tmp:rw
    shm_size: "1gb"
    profiles: ["browser"]
```

---

## Plan self-review (cobertura spec V1)

- SSE: endpoint, tipos cerrados, replay con Last-Event-ID y buffer (Task 3 + Task 5).
- Abort: Ctrl+C CLI → `/abort` y runtime marca final aborted (Task 7 + CLI).
- Acciones sensibles: `proposed_action` + confirmación + `action_result` (Task 8 + CLI).
- @archivos grandes: truncado por bytes/líneas y metadata/sha256 (CLI Task 10).
- /debug y /logs: en CLI (Task 10).
- Hardening: no-root + perfiles compose (Task 11).

---

## Ejecución

Plan completo y guardado en `docs/superpowers/plans/2026-05-03-open-peak-v1-django-ninja.md`. Dos opciones de ejecución:

1. **Subagent-Driven (recomendado)** - despacho un sub-agente por task y reviso entre tasks.
2. **Inline Execution** - ejecuto tasks en esta sesión, con checkpoints.
