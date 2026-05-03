from __future__ import annotations

import queue
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass
from typing import Any, Deque, Dict, List, Optional

from api.services.jsonl_logger import write_event


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
        if event_type in {"status", "usage", "error", "proposed_action", "action_result", "final"}:
            write_event(
                run_id=run_id,
                event_type=event_type,
                data=data,
                route=data.get("route"),
                model=data.get("model"),
                phase=data.get("phase"),
                error_class=data.get("error_class"),
            )
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
