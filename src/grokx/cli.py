from __future__ import annotations

import argparse
import json
import sys
from typing import Sequence

from .admin import load_active_tokens, restart_grok2api, set_clearance_in_toml
from .client import build_client
from .config import Settings, load_settings, save_local_config
from .session_store import SessionStore


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="grokx", description="Portable CLI for a local grok2api service")
    sub = parser.add_subparsers(dest="command", required=True)

    ask_p = sub.add_parser("ask", help="Ask Grok a question")
    ask_p.add_argument("prompt")
    ask_p.add_argument("--model")
    ask_p.add_argument("--system")
    ask_p.add_argument("--session", help="Persist and reuse conversation context with a named session")
    ask_p.add_argument("--json", action="store_true")
    ask_p.add_argument("--no-stream", action="store_true", help="Wait for a full non-streaming JSON response")

    health_p = sub.add_parser("health", help="Check local grok2api health")
    health_p.add_argument("--with-chat", action="store_true")
    health_p.add_argument("--json", action="store_true")

    model_p = sub.add_parser("model", help="Inspect or change the default model")
    model_sub = model_p.add_subparsers(dest="model_command", required=True)
    model_sub.add_parser("current", help="Print the current default model")
    model_sub.add_parser("list", help="List available models from grok2api")
    model_set = model_sub.add_parser("set", help="Persist a new default model")
    model_set.add_argument("model")

    clearance_p = sub.add_parser("clearance", help="Manage local clearance")
    clearance_sub = clearance_p.add_subparsers(dest="clearance_command", required=True)
    clearance_set = clearance_sub.add_parser("set", help="Set cf_clearance in grok2api config")
    clearance_set.add_argument("cf_clearance")
    clearance_set.add_argument("--user-agent")
    clearance_set.add_argument("--restart", action="store_true")

    probe_p = sub.add_parser("probe", help="Probe account availability")
    probe_sub = probe_p.add_subparsers(dest="probe_command", required=True)
    probe_all = probe_sub.add_parser("all", help="Run read-only batch refresh on all active accounts")
    probe_all.add_argument("--concurrency", type=int, default=5)
    probe_all.add_argument("--json", action="store_true")

    session_p = sub.add_parser("session", help="Manage persistent chat sessions")
    session_sub = session_p.add_subparsers(dest="session_command", required=True)
    session_sub.add_parser("list", help="List saved session names")
    session_clear = session_sub.add_parser("clear", help="Delete a saved session")
    session_clear.add_argument("name")

    return parser


def _require(value: str, message: str) -> str:
    if not value:
        raise SystemExit(message)
    return value


def _run_probe_all(settings: Settings, *, concurrency: int) -> dict:
    if settings.grok2api_db_path is None:
        raise SystemExit("Missing GROKX_GROK2API_DB or GROKX_GROK2API_DIR")
    app_key = _require(settings.app_key, "Missing GROKX_APP_KEY or GROK_APP_APP_KEY")
    tokens = load_active_tokens(settings.grok2api_db_path)
    from urllib import request

    body = json.dumps({"tokens": tokens}).encode()
    req = request.Request(
        settings.base_url.removesuffix("/v1") + f"/admin/api/batch/refresh?concurrency={concurrency}",
        data=body,
        headers={"Authorization": f"Bearer {app_key}", "Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req, timeout=settings.timeout * 10) as resp:
        return json.loads(resp.read().decode())


def _build_session_messages(
    settings: Settings,
    session_name: str,
    *,
    prompt: str,
    system: str | None,
) -> tuple[SessionStore, list[dict[str, str]], str]:
    sessions_dir = settings.sessions_dir
    if sessions_dir is None:
        raise SystemExit("Missing grokx sessions directory")
    store = SessionStore(sessions_dir)
    state = store.load_session(session_name, turn_limit=settings.session_turn_limit)
    resolved_system = system if system is not None else state.system_prompt or None
    messages: list[dict[str, str]] = []
    if resolved_system:
        messages.append({"role": "system", "content": resolved_system})
    messages.extend(state.messages or [])
    messages.append({"role": "user", "content": prompt})
    return store, messages, resolved_system or ""


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    settings = load_settings()

    if args.command == "ask":
        client = build_client(settings)
        if args.session:
            store, messages, resolved_system = _build_session_messages(
                settings,
                args.session,
                prompt=args.prompt,
                system=args.system,
            )
            if args.json or args.no_stream:
                result = client.ask(model=args.model, messages=messages)
                store.append_turn(
                    args.session,
                    user_content=args.prompt,
                    assistant_content=result["text"],
                    model=args.model or settings.model,
                    system_prompt=resolved_system,
                )
                print(json.dumps(result["raw"], ensure_ascii=False) if args.json else result["text"])
            else:
                parts: list[str] = []
                for chunk in client.ask_stream(model=args.model, messages=messages):
                    parts.append(chunk)
                    print(chunk, end="", flush=True)
                store.append_turn(
                    args.session,
                    user_content=args.prompt,
                    assistant_content="".join(parts),
                    model=args.model or settings.model,
                    system_prompt=resolved_system,
                )
                print()
        elif args.json or args.no_stream:
            result = client.ask(args.prompt, model=args.model, system=args.system)
            print(json.dumps(result["raw"], ensure_ascii=False) if args.json else result["text"])
        else:
            for chunk in client.ask_stream(args.prompt, model=args.model, system=args.system):
                print(chunk, end="", flush=True)
            print()
        return 0

    if args.command == "health":
        result = build_client(settings).health(include_chat=args.with_chat)
        if args.json:
            print(json.dumps(result, ensure_ascii=False))
        else:
            print(f"health={result['health']} models_ok={result['models_ok']} model_count={result['model_count']} chat_ok={result['chat_ok']}")
        return 0

    if args.command == "model" and args.model_command == "current":
        print(settings.model)
        return 0

    if args.command == "model" and args.model_command == "list":
        for item in build_client(settings).list_models():
            model_id = item.get("id")
            if model_id:
                print(model_id)
        return 0

    if args.command == "model" and args.model_command == "set":
        if settings.config_path is None:
            raise SystemExit("Missing grokx config path")
        save_local_config(settings.config_path, {"model": args.model})
        print(args.model)
        return 0

    if args.command == "clearance" and args.clearance_command == "set":
        if settings.grok2api_config_path is None:
            raise SystemExit("Missing GROKX_GROK2API_CONFIG or GROKX_GROK2API_DIR")
        set_clearance_in_toml(settings.grok2api_config_path, cf_clearance=args.cf_clearance, user_agent=args.user_agent)
        if args.restart:
            restart_grok2api(settings.restart_cmd)
        print(str(settings.grok2api_config_path))
        return 0

    if args.command == "probe" and args.probe_command == "all":
        result = _run_probe_all(settings, concurrency=args.concurrency)
        if args.json:
            print(json.dumps(result, ensure_ascii=False))
        else:
            summary = result.get("summary", {})
            print(f"total={summary.get('total', 0)} ok={summary.get('ok', 0)} fail={summary.get('fail', 0)}")
        return 0

    if args.command == "session" and args.session_command == "list":
        sessions_dir = settings.sessions_dir
        if sessions_dir is None:
            raise SystemExit("Missing grokx sessions directory")
        for name in SessionStore(sessions_dir).list_sessions():
            print(name)
        return 0

    if args.command == "session" and args.session_command == "clear":
        sessions_dir = settings.sessions_dir
        if sessions_dir is None:
            raise SystemExit("Missing grokx sessions directory")
        SessionStore(sessions_dir).clear_session(args.name)
        print(args.name)
        return 0

    parser.error("Unknown command")
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
