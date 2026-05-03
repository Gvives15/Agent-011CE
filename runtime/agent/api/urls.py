from __future__ import annotations

import json
import os
import threading
import time
from typing import Any, Dict

from django.http import HttpResponse, StreamingHttpResponse
from ninja import Router

from api.schemas import AbortResponse, ApproveActionRequest, ApproveActionResponse, CreateRunRequest, CreateRunResponse
from api.services.config_loader import load_models, load_runtime_config
from api.services.openrouter_client import OpenRouterClient
from api.services.run_manager import RunManager, RunNotFound
from api.services.run_worker import run_worker

router = Router()

_cfg = load_runtime_config()
_models = load_models()
_run_manager = RunManager(max_events=_cfg.max_events, max_age_seconds=_cfg.max_age_seconds)
_openrouter = OpenRouterClient(base_url=_cfg.openrouter_base_url, timeout_seconds=_cfg.openrouter_timeout_seconds)


def _format_sse(*, event_type: str, event_id: str, data: Dict[str, Any]) -> str:
    return f"event: {event_type}\nid: {event_id}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.get("/health")
def health(request):
    profile = os.environ.get("PROFILE", "dev")
    return {
        "status": "ok",
        "profile": profile,
        "models": {"logic": _models["logic"]["id"], "vision": _models["vision"]["id"], "ui": _models["ui"]["id"]},
        "browser": {"enabled": _cfg.enable_browser_automation},
        "version": "v1",
    }


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
            "models": _models,
            "cfg": _cfg,
            "run_manager": _run_manager,
            "openrouter": _openrouter,
        },
        daemon=True,
    )
    t.start()
    return {"id": run.id, "events_url": f"/v1/runs/{run.id}/events"}


@router.get("/runs/{run_id}/events")
def run_events(request, run_id: str):
    last_id = request.headers.get("Last-Event-ID")
    try:
        state = _run_manager.get_run(run_id)
    except RunNotFound:
        return HttpResponse(status=404)

    def gen():
        replay = _run_manager.get_events(run_id, last_event_id=last_id)
        for ev in replay:
            yield _format_sse(event_type=ev.event_type, event_id=ev.event_id, data=ev.data)
            if ev.event_type == "final":
                return

        while True:
            try:
                ev = state.event_queue.get(timeout=1.0)
                yield _format_sse(event_type=ev.event_type, event_id=ev.event_id, data=ev.data)
                if ev.event_type == "final":
                    break
            except Exception:
                continue

    resp = StreamingHttpResponse(gen(), content_type="text/event-stream")
    resp["Cache-Control"] = "no-cache"
    return resp


@router.post("/runs/{run_id}/abort", response=AbortResponse)
def abort_run(request, run_id: str):
    _run_manager.abort(run_id)
    return {"id": run_id, "accepted": True}


@router.post("/runs/{run_id}/actions/{action_id}/approve", response=ApproveActionResponse)
def approve_action(request, run_id: str, action_id: str, payload: ApproveActionRequest):
    _run_manager.resolve_action(run_id, action_id, approved=bool(payload.approved))
    return {"action_id": action_id, "accepted": True}

