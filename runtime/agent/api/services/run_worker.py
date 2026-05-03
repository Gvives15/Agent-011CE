from __future__ import annotations

import time
import uuid
from typing import Any, Dict

from api.schemas import Attachment, RunOptions
from api.services.costing import ModelPricing, compute_cost_usd
from api.services.openrouter_client import OpenRouterClient, OpenRouterError
from api.services.routing import decide_route
from api.services.run_manager import RunManager
from api.services.shell_actions import ShellPolicy, run_shell, validate_shell_command


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
    models: Dict[str, Dict[str, Any]],
    cfg: Any,
    run_manager: RunManager,
    openrouter: OpenRouterClient,
) -> None:
    if message.startswith("!shell "):
        cmd = message[len("!shell ") :].strip()
        action_id = f"act_{uuid.uuid4().hex}"
        approval_q = run_manager.create_pending_action(run_id, action_id)
        run_manager.emit(run_id, "proposed_action", {"run_id": run_id, "action_id": action_id, "type": "shell", "command": cmd, "risk": "high", "requires_confirmation": True})
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
            {"run_id": run_id, "action_id": action_id, "exit_code": res.returncode, "stdout": res.stdout[-4000:], "stderr": res.stderr[-4000:]},
        )
        run_manager.emit(run_id, "final", {"run_id": run_id, "status": "done"})
        return

    model_ids = {"logic": models["logic"]["id"], "vision": models["vision"]["id"], "ui": models["ui"]["id"]}
    route, model = decide_route(message=message, attachments=attachments, options=options, models=model_ids, enable_ui=False)

    if route == "error":
        run_manager.emit(run_id, "error", {"run_id": run_id, "error_class": "UI_MODEL_DISABLED", "message": "ui-tars no habilitado", "retryable": False})
        run_manager.emit(run_id, "final", {"run_id": run_id, "status": "error"})
        return

    run_manager.emit(run_id, "status", {"run_id": run_id, "phase": "routing", "route": route, "model": model})

    pricing = ModelPricing(
        input_usd_per_million_tokens=float(models[route]["input_usd_per_million_tokens"]) if route in models else 0.0,
        output_usd_per_million_tokens=float(models[route]["output_usd_per_million_tokens"]) if route in models else 0.0,
    )

    retries_left = int(cfg.max_retries_per_run)
    session_tokens_total = 0
    session_cost_usd = 0.0

    while True:
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
                    prompt_tokens = int(chunk.usage.get("prompt_tokens") or 0)
                    completion_tokens = int(chunk.usage.get("completion_tokens") or 0)
                    tokens_total = int(chunk.usage.get("total_tokens") or 0)
                    cost_usd = compute_cost_usd(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens, pricing=pricing)
                    session_tokens_total = max(session_tokens_total, tokens_total)
                    session_cost_usd = max(session_cost_usd, cost_usd)
                    run_manager.emit(
                        run_id,
                        "usage",
                        {
                            "run_id": run_id,
                            "tokens": {"prompt": prompt_tokens, "completion": completion_tokens, "total": tokens_total},
                            "cost_usd": cost_usd,
                            "session_tokens_total": session_tokens_total,
                            "session_cost_usd": session_cost_usd,
                        },
                    )
            run_manager.emit(run_id, "final", {"run_id": run_id, "status": "done"})
            return
        except OpenRouterError as e:
            run_manager.emit(run_id, "error", {"run_id": run_id, "error_class": _error_class(e.status_code), "message": str(e), "retryable": e.retryable})
            if not e.retryable or retries_left <= 0:
                run_manager.emit(run_id, "final", {"run_id": run_id, "status": "error"})
                return
            retries_left -= 1
            time.sleep(0.5)
