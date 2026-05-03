from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Generator, Optional

import requests


@dataclass(frozen=True)
class SseEvent:
    event: str
    data: Dict[str, Any]
    event_id: Optional[str]


def iter_sse(*, url: str, last_event_id: Optional[str] = None) -> Generator[SseEvent, None, None]:
    headers = {}
    if last_event_id:
        headers["Last-Event-ID"] = last_event_id

    with requests.get(url, stream=True, headers=headers, timeout=60) as r:
        r.raise_for_status()
        current_event = None
        current_id = None
        for raw in r.iter_lines(decode_unicode=True):
            if raw is None:
                continue
            line = raw.strip()
            if not line:
                continue
            if line.startswith("event:"):
                current_event = line.split(":", 1)[1].strip()
                continue
            if line.startswith("id:"):
                current_id = line.split(":", 1)[1].strip()
                continue
            if line.startswith("data:"):
                data_str = line.split(":", 1)[1].strip()
                payload = json.loads(data_str) if data_str else {}
                yield SseEvent(event=current_event or "message", data=payload, event_id=current_id)
