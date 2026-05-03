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
from o11ce_cli.config import env_path, runtime_base_url, stack_dir
from o11ce_cli.runtime_client import RuntimeClient
from o11ce_cli.sse import iter_sse


console = Console()


@dataclass
class ChatState:
    profile: str
    vision: str
    preferred_model: str
    last_event_id: Optional[str]


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


def _print_help() -> None:
    console.print("/help /model <logic|vision|ui-tars|auto> /profile <dev|browser|server> /debug /logs [n] /reset /exit")


def _footer(*, route: str | None, model: str | None, profile: str, runtime: str, tokens: int | None, cost: float | None) -> None:
    tok = "?" if tokens is None else str(tokens)
    console.print(f"[route:{route or '?'}] [model:{model or '?'}] [usage:{tok} tok] [profile:{profile}] [runtime:{runtime}]")


def cmd_chat(_args: argparse.Namespace) -> int:
    ensure_stack_layout(overwrite_compose=False)

    env = dotenv_values(env_path())
    if not env.get("OPENROUTER_API_KEY") and not os.environ.get("OPENROUTER_API_KEY"):
        console.print("OPENROUTER_API_KEY faltante. Configuralo en env o en el .env del stack (o11ce init).")
        return 1

    client = RuntimeClient(base_url=runtime_base_url())
    state = ChatState(profile=os.environ.get("PROFILE", "dev"), vision="auto", preferred_model="auto", last_event_id=None)

    _print_help()

    while True:
        try:
            line = input("> ").strip()
        except EOFError:
            return 0
        except KeyboardInterrupt:
            console.print("")
            continue

        if not line:
            continue

        if line == "/exit":
            return 0
        if line == "/help":
            _print_help()
            continue
        if line.startswith("/profile "):
            state.profile = line.split(maxsplit=1)[1].strip() or "dev"
            continue
        if line.startswith("/model "):
            m = line.split(maxsplit=1)[1].strip()
            if m == "logic":
                state.preferred_model = "auto"
                state.vision = "never"
            elif m == "vision":
                state.preferred_model = "auto"
                state.vision = "always"
            elif m == "ui-tars":
                state.preferred_model = "ui-tars"
                state.vision = "auto"
            else:
                state.preferred_model = "auto"
                state.vision = "auto"
            continue
        if line == "/debug":
            try:
                console.print(client.health())
            except Exception as e:
                console.print(str(e))
            continue
        if line.startswith("/logs"):
            continue
        if line == "/reset":
            state.last_event_id = None
            continue

        options = {"profile": state.profile, "vision": state.vision, "preferred_model": state.preferred_model, "enable_browser": False}
        run = client.create_run(message=line, attachments=[], options=options)
        run_id = run["id"]
        events_url = f"{client.base_url.rstrip('/')}{run['events_url']}"

        route = None
        model = None
        runtime = "ok"
        tokens = None
        cost = None

        try:
            for ev in iter_sse(url=events_url, last_event_id=state.last_event_id):
                if ev.event_id:
                    state.last_event_id = ev.event_id
                if ev.event == "status":
                    route = ev.data.get("route")
                    model = ev.data.get("model")
                    _footer(route=route, model=model, profile=state.profile, runtime=runtime, tokens=tokens, cost=cost)
                elif ev.event == "token":
                    sys.stdout.write(ev.data.get("text", ""))
                    sys.stdout.flush()
                elif ev.event == "usage":
                    tokens = ev.data.get("session_tokens_total")
                    cost = ev.data.get("session_cost_usd")
                elif ev.event == "proposed_action":
                    cmd = ev.data.get("command", "")
                    console.print(f"\nproposed_action: {cmd}")
                    ans = input("Approve? (Y/n) ").strip().lower()
                    approved = ans == "" or ans == "y"
                    client.approve(run_id=run_id, action_id=ev.data["action_id"], approved=approved)
                elif ev.event == "action_result":
                    console.print(f"\nexit_code={ev.data.get('exit_code')}")
                    if ev.data.get("stdout"):
                        console.print(ev.data["stdout"])
                    if ev.data.get("stderr"):
                        console.print(ev.data["stderr"])
                elif ev.event == "error":
                    console.print(f"\nerror={ev.data.get('error_class')} {ev.data.get('message')}")
                elif ev.event == "final":
                    console.print("")
                    _footer(route=route, model=model, profile=state.profile, runtime=runtime, tokens=tokens, cost=cost)
                    break
        except KeyboardInterrupt:
            try:
                client.abort(run_id=run_id)
            except Exception:
                pass
            console.print("")
            continue

    return 0


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

    sub.add_parser("chat")
    return p


def main(argv: Optional[list[str]] = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.version:
        console.print(__version__)
        raise SystemExit(0)

    cmd = args.cmd or "chat"
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
    if cmd == "chat":
        raise SystemExit(cmd_chat(args))
    raise SystemExit(2)

