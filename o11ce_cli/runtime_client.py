from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests


@dataclass(frozen=True)
class RuntimeClient:
    base_url: str

    def _url(self, path: str) -> str:
        return f"{self.base_url.rstrip('/')}{path}"

    def health(self) -> Dict[str, Any]:
        r = requests.get(self._url("/v1/health"), timeout=10)
        r.raise_for_status()
        return r.json()

    def create_run(self, *, message: str, attachments: Optional[list[dict]] = None, options: Optional[dict] = None) -> Dict[str, Any]:
        payload = {"input": {"message": message, "attachments": attachments or []}, "options": options or {}}
        r = requests.post(self._url("/v1/runs"), json=payload, timeout=30)
        r.raise_for_status()
        return r.json()

    def abort(self, *, run_id: str) -> None:
        r = requests.post(self._url(f"/v1/runs/{run_id}/abort"), json={}, timeout=10)
        if r.status_code >= 400:
            raise RuntimeError(r.text)

    def approve(self, *, run_id: str, action_id: str, approved: bool) -> None:
        r = requests.post(self._url(f"/v1/runs/{run_id}/actions/{action_id}/approve"), json={"approved": approved}, timeout=10)
        if r.status_code >= 400:
            raise RuntimeError(r.text)
