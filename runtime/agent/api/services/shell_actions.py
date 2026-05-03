from __future__ import annotations

import os
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ShellPolicy:
    allow_roots: list[str]
    deny_commands: list[str]


def _is_path_allowed(path: str, allow_roots: list[str]) -> bool:
    p = Path(path).resolve()
    for root in allow_roots:
        if str(p).startswith(str(Path(root).resolve())):
            return True
    return False


def validate_shell_command(cmd: str, policy: ShellPolicy) -> None:
    parts = shlex.split(cmd)
    if not parts:
        raise ValueError("empty command")
    if parts[0] in policy.deny_commands:
        raise ValueError("command denied")

    for token in parts[1:]:
        if token.startswith("/"):
            if not _is_path_allowed(token, policy.allow_roots):
                raise ValueError("path denied")


def run_shell(cmd: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if "KEY" not in k and "TOKEN" not in k and "SECRET" not in k}
    return subprocess.run(
        cmd,
        shell=True,
        check=False,
        capture_output=True,
        text=True,
        cwd="/workspace",
        env=env,
    )
