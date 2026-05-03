from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from typing import Optional

from dotenv import dotenv_values
from rich.console import Console

from o11ce_cli import __version__
from o11ce_cli.compose import ComposeNotFound, ensure_stack_layout, logs as compose_logs, down as compose_down, status as compose_status, up as compose_up
from o11ce_cli.config import env_path, stack_dir


console = Console()


def _mask_if_secret(key: str, value: str) -> str:
    k = key.upper()
    if "KEY" in k or "TOKEN" in k or "SECRET" in k:
        return "***"
    return value


def cmd_init(_args: argparse.Namespace) -> int:
    ensure_stack_layout(overwrite_compose=False)
    console.print(f"Stack dir: {stack_dir()}")
    console.print(f"Env file: {env_path()}")
    return 0


def cmd_up(args: argparse.Namespace) -> int:
    try:
        compose_up(wait_health=True, timeout_seconds=args.timeout)
        console.print("runtime: ok")
        return 0
    except ComposeNotFound as e:
        console.print(str(e))
        return 2
    except Exception as e:
        console.print(str(e))
        return 1


def cmd_down(_args: argparse.Namespace) -> int:
    try:
        compose_down()
        console.print("down: ok")
        return 0
    except ComposeNotFound as e:
        console.print(str(e))
        return 2
    except Exception as e:
        console.print(str(e))
        return 1


def cmd_status(_args: argparse.Namespace) -> int:
    try:
        out = compose_status()
        console.print(out.rstrip())
        return 0
    except ComposeNotFound as e:
        console.print(str(e))
        return 2
    except Exception as e:
        console.print(str(e))
        return 1


def cmd_logs(args: argparse.Namespace) -> int:
    try:
        out = compose_logs(follow=args.follow, tail=args.tail)
        console.print(out.rstrip())
        return 0
    except ComposeNotFound as e:
        console.print(str(e))
        return 2
    except Exception as e:
        console.print(str(e))
        return 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="o11ce")
    p.add_argument("--version", action="store_true")
    sub = p.add_subparsers(dest="cmd", required=False)

    sub.add_parser("init")

    up = sub.add_parser("up")
    up.add_argument("--timeout", type=int, default=60)

    sub.add_parser("down")
    sub.add_parser("status")

    logs = sub.add_parser("logs")
    logs.add_argument("-f", "--follow", action="store_true")
    logs.add_argument("--tail", default=None)
    return p


def main(argv: Optional[list[str]] = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.version:
        console.print(__version__)
        raise SystemExit(0)

    cmd = args.cmd
    if cmd == "init":
        raise SystemExit(cmd_init(args))
    if cmd == "up":
        raise SystemExit(cmd_up(args))
    if cmd == "down":
        raise SystemExit(cmd_down(args))
    if cmd == "status":
        raise SystemExit(cmd_status(args))
    if cmd == "logs":
        raise SystemExit(cmd_logs(args))
    parser.print_help()
    raise SystemExit(0)
