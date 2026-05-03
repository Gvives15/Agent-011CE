from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional


def _log_path() -> Path:
    override = os.environ.get("OPEN_PEAK_LOG_PATH")
    if override:
        return Path(override)
    ws_logs = Path("/workspace/logs/runtime.jsonl")
    if ws_logs.parent.exists():
        return ws_logs
    return Path("/logs/runtime.jsonl")


def write_event(*, run_id: str, event_type: str, data: Dict[str, Any], route: Optional[str] = None, model: Optional[str] = None, phase: Optional[str] = None, error_class: Optional[str] = None) -> None:
    p = _log_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    entry: Dict[str, Any] = {
        "ts": time.time(),
        "run_id": run_id,
        "route": route,
        "model": model,
        "phase": phase,
        "event_type": event_type,
        "error_class": error_class,
    }
    if event_type == "usage":
        entry.update(
            {
                "tokens_prompt": data.get("tokens", {}).get("prompt"),
                "tokens_completion": data.get("tokens", {}).get("completion"),
                "tokens_total": data.get("tokens", {}).get("total"),
                "cost_usd": data.get("cost_usd"),
            }
        )
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
