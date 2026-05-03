from __future__ import annotations

import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import requests
from dotenv import dotenv_values

from o11ce_cli.config import RuntimeEndpoints, compose_path, env_path, logs_dir, runtime_base_url, stack_dir, tmp_dir, workspace_dir, cache_dir


class ComposeNotFound(Exception):
    pass


@dataclass(frozen=True)
class ComposeBinary:
    mode: str
    argv_prefix: list[str]


def resolve_compose() -> ComposeBinary:
    docker = shutil.which("docker")
    if docker:
        try:
            subprocess.run([docker, "compose", "version"], check=True, capture_output=True, text=True)
            return ComposeBinary(mode="docker-compose-plugin", argv_prefix=[docker, "compose"])
        except Exception:
            pass
    dc = shutil.which("docker-compose")
    if dc:
        return ComposeBinary(mode="docker-compose", argv_prefix=[dc])
    raise ComposeNotFound("Docker Compose no encontrado (docker compose o docker-compose)")


def ensure_stack_layout(*, overwrite_compose: bool = False) -> None:
    stack_dir().mkdir(parents=True, exist_ok=True)
    (stack_dir() / "volumes").mkdir(parents=True, exist_ok=True)
    workspace_dir().mkdir(parents=True, exist_ok=True)
    logs_dir().mkdir(parents=True, exist_ok=True)
    cache_dir().mkdir(parents=True, exist_ok=True)
    tmp_dir().mkdir(parents=True, exist_ok=True)

    if overwrite_compose or not compose_path().exists():
        from importlib.resources import files

        data = files("o11ce_cli").joinpath("assets/compose.yml").read_text(encoding="utf-8")
        compose_path().write_text(data, encoding="utf-8")

    if not env_path().exists():
        env_path().write_text("OPENROUTER_API_KEY=\n", encoding="utf-8")


def compose_env() -> dict[str, str]:
    base = dict(os.environ)
    base.update({k: v for k, v in dotenv_values(env_path()).items() if v is not None})
    return base


def run_compose(args: list[str]) -> subprocess.CompletedProcess[str]:
    c = resolve_compose()
    return subprocess.run(
        c.argv_prefix + ["-f", str(compose_path())] + args,
        check=False,
        capture_output=True,
        text=True,
        cwd=str(stack_dir()),
        env=compose_env(),
    )


def up(*, wait_health: bool = True, timeout_seconds: int = 60) -> None:
    ensure_stack_layout()
    res = run_compose(["up", "-d"])
    if res.returncode != 0:
        raise RuntimeError(res.stderr.strip() or res.stdout.strip())

    if not wait_health:
        return

    endpoints = RuntimeEndpoints(base_url=runtime_base_url())
    deadline = time.time() + timeout_seconds
    last_err: Optional[str] = None
    while time.time() < deadline:
        try:
            r = requests.get(endpoints.health_url, timeout=2)
            if r.status_code == 200:
                return
            last_err = f"HTTP {r.status_code}"
        except Exception as e:
            last_err = str(e)
        time.sleep(1)
    raise RuntimeError(f"Runtime no respondió health a tiempo: {last_err}")


def down() -> None:
    ensure_stack_layout()
    res = run_compose(["down"])
    if res.returncode != 0:
        raise RuntimeError(res.stderr.strip() or res.stdout.strip())


def status() -> str:
    ensure_stack_layout()
    res = run_compose(["ps"])
    if res.returncode != 0:
        raise RuntimeError(res.stderr.strip() or res.stdout.strip())
    return res.stdout


def logs(*, follow: bool = False, tail: Optional[str] = None) -> str:
    ensure_stack_layout()
    args = ["logs"]
    if follow:
        args.append("-f")
    if tail is not None:
        args += ["--tail", tail]
    res = run_compose(args)
    if res.returncode != 0:
        raise RuntimeError(res.stderr.strip() or res.stdout.strip())
    return res.stdout
