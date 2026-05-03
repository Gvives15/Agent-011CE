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


def _config_dir() -> Path:
    override = os.environ.get("OPEN_PEAK_CONFIG_DIR")
    if override:
        return Path(override)
    p = Path("/app/config")
    if p.exists():
        return p
    return _repo_root() / "config"


def load_models() -> Dict[str, Dict[str, Any]]:
    p = _config_dir() / "models.yml"
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    return data["models"]


def load_runtime_config() -> RuntimeConfig:
    p = _config_dir() / "runtime.yml"
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
