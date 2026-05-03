from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RuntimeEndpoints:
    base_url: str

    @property
    def health_url(self) -> str:
        return f"{self.base_url.rstrip('/')}/v1/health"


def home_dir() -> Path:
    override = os.environ.get("O11CE_HOME")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".o11ce"


def stack_dir() -> Path:
    return home_dir() / "stack"


def env_path() -> Path:
    return stack_dir() / ".env"


def compose_path() -> Path:
    return stack_dir() / "compose.yml"


def volumes_dir() -> Path:
    return stack_dir() / "volumes"


def workspace_dir() -> Path:
    return volumes_dir() / "workspace"


def logs_dir() -> Path:
    return volumes_dir() / "logs"


def cache_dir() -> Path:
    return volumes_dir() / "cache"


def tmp_dir() -> Path:
    return volumes_dir() / "tmp"


def runtime_base_url() -> str:
    return os.environ.get("O11CE_RUNTIME_BASE_URL", "http://127.0.0.1:8000")
