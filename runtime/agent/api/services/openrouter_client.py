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
        *,
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
