from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from typing import Any
from typing import Sequence

from .client import build_client
from .config import Settings, load_local_config, load_settings, save_local_config
from .session_store import SessionStore


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="grokx", description="Portable CLI for a local grok2api service")
    sub = parser.add_subparsers(dest="command", required=True)

    ask_p = sub.add_parser("ask", help="Ask Grok a question")
    ask_p.add_argument("prompt", help="Prompt text to send")
    ask_p.add_argument("--model", help="Override the default model for this request")
    ask_p.add_argument("--system", help="Optional system prompt for this request")
    ask_p.add_argument("--session", help="Persist and reuse conversation context with a named session")
    ask_p.add_argument("--json", action="store_true", help="Print the raw JSON response")
    ask_p.add_argument("--no-stream", action="store_true", help="Wait for a full non-streaming JSON response")

    def _add_new_parser(name: str, help_text: str) -> None:
        new_p = sub.add_parser(name, help=help_text)
        new_p.add_argument("prompt", help="Prompt text to send")
        new_p.add_argument("--session", help="Create and use a fresh named session")
        new_p.add_argument("--model", help="Override the default model for this request")
        new_p.add_argument("--system", help="Optional system prompt for this request")
        new_p.add_argument("--json", action="store_true", help="Print the raw JSON response")
        new_p.add_argument("--no-stream", action="store_true", help="Wait for a full non-streaming JSON response")
        new_p.add_argument("--force", action="store_true", help="Replace an existing session with the same name")

    _add_new_parser("new", "Start a fresh chat session")
    _add_new_parser("/new", argparse.SUPPRESS)

    def _add_side_parser(name: str, help_text: str) -> None:
        side_p = sub.add_parser(name, help=help_text)
        side_p.add_argument("prompt", nargs="?", help="Prompt text to send")
        side_p.add_argument("--list", action="store_true", help="List saved sessions with summary details")
        side_p.add_argument("--session", help="Existing session name")
        side_p.add_argument("--model", help="Override the default model for this request")
        side_p.add_argument("--system", help="Optional system prompt for this request")
        side_p.add_argument("--json", action="store_true", help="Print JSON when listing or when returning a response")
        side_p.add_argument("--no-stream", action="store_true", help="Wait for a full non-streaming JSON response")

    _add_side_parser("side", "Ask a temporary side question from a saved session without mutating it")
    _add_side_parser("/side", argparse.SUPPRESS)

    def _add_resume_parser(name: str, help_text: str) -> None:
        resume_p = sub.add_parser(name, help=help_text)
        resume_p.add_argument("prompt", nargs="?", help="Prompt text to send")
        resume_p.add_argument("--list", action="store_true", help="List saved sessions with summary details")
        resume_p.add_argument("--session", help="Existing session name")
        resume_p.add_argument("--model", help="Override the default model for this request")
        resume_p.add_argument("--system", help="Optional system prompt for this request")
        resume_p.add_argument("--json", action="store_true", help="Print JSON when listing or when returning a response")
        resume_p.add_argument("--no-stream", action="store_true", help="Wait for a full non-streaming JSON response")

    _add_resume_parser("resume", "Resume a saved chat session")
    _add_resume_parser("/resume", argparse.SUPPRESS)

    health_p = sub.add_parser("health", help="Check local grok2api health")
    health_p.add_argument("--with-chat", action="store_true")
    health_p.add_argument("--probe-models", action="store_true")
    health_p.add_argument("--json", action="store_true")

    model_p = sub.add_parser("model", help="Inspect or change the default model")
    model_sub = model_p.add_subparsers(dest="model_command", required=True)
    model_sub.add_parser("current", help="Print the current default model")
    model_list = model_sub.add_parser("list", help="List chat-capable models from grok2api")
    model_list.add_argument("--all", action="store_true", help="Include models that fail a chat probe")
    model_list.add_argument("--json", action="store_true")
    model_set = model_sub.add_parser("set", help="Persist a new default model")
    model_set.add_argument("model")

    config_p = sub.add_parser("config", help="Inspect or persist CLI connection settings")
    config_sub = config_p.add_subparsers(dest="config_command", required=True)
    config_sub.add_parser("show", help="Print the effective base URL and API key status")
    config_base = config_sub.add_parser("set-base-url", help="Persist a new default base URL")
    config_base.add_argument("base_url")
    config_api = config_sub.add_parser("set-api-key", help="Persist a new default API key")
    config_api.add_argument("api_key")

    session_p = sub.add_parser("session", help="Manage persistent chat sessions")
    session_sub = session_p.add_subparsers(dest="session_command", required=True)
    session_list = session_sub.add_parser("list", help="List saved sessions")
    session_list.add_argument("--verbose", action="store_true", help="Show summary details instead of names only")
    session_list.add_argument("--json", action="store_true", help="Print saved session summaries as JSON")
    session_clear = session_sub.add_parser("clear", help="Delete a saved session")
    session_clear.add_argument("name")

    return parser


def _require(value: str, message: str) -> str:
    if not value:
        raise SystemExit(message)
    return value


def _read_cached_model_probes(settings: Settings) -> list[dict[str, Any]]:
    if settings.config_path is None:
        return []
    local_config = load_local_config(settings.config_path)
    cached = local_config.get("model_probes")
    return cached if isinstance(cached, list) else []


def _cache_model_probes(settings: Settings, model_probes: list[dict[str, Any]]) -> None:
    if settings.config_path is None:
        return
    save_local_config(settings.config_path, {"model_probes": model_probes})


def _find_cached_model(model_probes: list[dict[str, Any]], model_id: str) -> dict[str, Any] | None:
    for item in model_probes:
        if item.get("id") == model_id:
            return item
    return None


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


def _require_sessions_dir(settings: Settings) -> SessionStore:
    sessions_dir = settings.sessions_dir
    if sessions_dir is None:
        raise SystemExit("Missing grokx sessions directory")
    return SessionStore(sessions_dir)


def _generate_session_name(store: SessionStore) -> str:
    base = datetime.now(timezone.utc).strftime("chat-%Y%m%d-%H%M%S")
    existing = set(store.list_sessions())
    if base not in existing:
        return base
    suffix = 2
    while f"{base}-{suffix}" in existing:
        suffix += 1
    return f"{base}-{suffix}"


def _session_summary_payload(store: SessionStore) -> list[dict[str, str | int]]:
    return [
        {
            "name": state.name,
            "created_at": state.created_at,
            "updated_at": state.updated_at,
            "last_model": state.last_model,
            "turns": state.turns,
        }
        for state in store.list_session_states()
    ]


def _print_session_summaries(store: SessionStore, *, as_json: bool) -> None:
    payload = _session_summary_payload(store)
    if as_json:
        print(json.dumps(payload, ensure_ascii=False))
        return
    for item in payload:
        print(
            f"{item['name']}\tturns={item['turns']}\tupdated_at={item['updated_at'] or '-'}\tmodel={item['last_model'] or '-'}"
        )


def _print_session_names(store: SessionStore) -> None:
    for name in store.list_sessions():
        print(name)


def _validate_list_mode(command_name: str, *, list_requested: bool, session_name: str | None, prompt: str | None) -> None:
    if list_requested and (session_name or prompt):
        raise SystemExit(f"Cannot combine `grokx {command_name} --list` with `--session` or a prompt.")


def _run_saved_session_prompt(
    settings: Settings,
    *,
    session_name: str,
    prompt: str,
    model: str | None,
    system: str | None,
    as_json: bool,
    no_stream: bool,
) -> None:
    store, messages, resolved_system = _build_session_messages(
        settings,
        session_name,
        prompt=prompt,
        system=system,
    )
    client = build_client(settings)
    if as_json or no_stream:
        result = client.ask(model=model, messages=messages)
        store.append_turn(
            session_name,
            user_content=prompt,
            assistant_content=result["text"],
            model=model or settings.model,
            system_prompt=resolved_system,
        )
        print(json.dumps(result["raw"], ensure_ascii=False) if as_json else result["text"])
        return

    parts: list[str] = []
    for chunk in client.ask_stream(model=model, messages=messages):
        parts.append(chunk)
        print(chunk, end="", flush=True)
    store.append_turn(
        session_name,
        user_content=prompt,
        assistant_content="".join(parts),
        model=model or settings.model,
        system_prompt=resolved_system,
    )
    print()


def _run_side_session_prompt(
    settings: Settings,
    *,
    session_name: str,
    prompt: str,
    model: str | None,
    system: str | None,
    as_json: bool,
    no_stream: bool,
) -> None:
    _, messages, _ = _build_session_messages(
        settings,
        session_name,
        prompt=prompt,
        system=system,
    )
    client = build_client(settings)
    if as_json or no_stream:
        result = client.ask(model=model, messages=messages)
        print(json.dumps(result["raw"], ensure_ascii=False) if as_json else result["text"])
        return

    for chunk in client.ask_stream(model=model, messages=messages):
        print(chunk, end="", flush=True)
    print()


def _run_new_session_prompt(
    settings: Settings,
    *,
    requested_session: str | None,
    prompt: str,
    model: str | None,
    system: str | None,
    as_json: bool,
    no_stream: bool,
    force: bool,
) -> None:
    store = _require_sessions_dir(settings)
    session_name = requested_session or _generate_session_name(store)
    existing_sessions = set(store.list_sessions())
    if session_name in existing_sessions:
        if not force:
            raise SystemExit(
                f"Session {session_name!r} already exists. "
                f"Use `grokx resume {session_name} \"...\"` to continue it or `grokx /new --session {session_name} --force \"...\"` to replace it."
            )
        store.clear_session(session_name)
    if requested_session is None:
        print(f"new_session={session_name}", file=sys.stderr)
    _run_saved_session_prompt(
        settings,
        session_name=session_name,
        prompt=prompt,
        model=model,
        system=system,
        as_json=as_json,
        no_stream=no_stream,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    settings = load_settings()

    if args.command == "ask":
        if args.session:
            _run_saved_session_prompt(
                settings,
                session_name=args.session,
                prompt=args.prompt,
                model=args.model,
                system=args.system,
                as_json=args.json,
                no_stream=args.no_stream,
            )
        elif args.json or args.no_stream:
            result = build_client(settings).ask(args.prompt, model=args.model, system=args.system)
            print(json.dumps(result["raw"], ensure_ascii=False) if args.json else result["text"])
        else:
            for chunk in build_client(settings).ask_stream(args.prompt, model=args.model, system=args.system):
                print(chunk, end="", flush=True)
            print()
        return 0

    if args.command in {"new", "/new"}:
        _run_new_session_prompt(
            settings,
            requested_session=args.session,
            prompt=args.prompt,
            model=args.model,
            system=args.system,
            as_json=args.json,
            no_stream=args.no_stream,
            force=args.force,
        )
        return 0

    if args.command in {"side", "/side"}:
        store = _require_sessions_dir(settings)
        _validate_list_mode("side", list_requested=args.list, session_name=args.session, prompt=args.prompt)
        if args.list:
            _print_session_summaries(store, as_json=args.json)
            return 0
        session_name = args.session
        if not session_name:
            raise SystemExit("Missing session name. Use `grokx side --session <name> \"...\"` or `grokx side --list`.")
        if session_name not in store.list_sessions():
            raise SystemExit(f"Unknown session {session_name!r}. Run `grokx side --list` to see saved sessions.")
        if not args.prompt:
            raise SystemExit(
                f"Missing prompt. Use `grokx side --session {session_name} \"...\"` "
                "to ask a temporary side question."
            )
        _run_side_session_prompt(
            settings,
            session_name=session_name,
            prompt=args.prompt,
            model=args.model,
            system=args.system,
            as_json=args.json,
            no_stream=args.no_stream,
        )
        return 0

    if args.command in {"resume", "/resume"}:
        store = _require_sessions_dir(settings)
        _validate_list_mode("resume", list_requested=args.list, session_name=args.session, prompt=args.prompt)
        if args.list:
            _print_session_summaries(store, as_json=args.json)
            return 0
        session_name = args.session
        if not session_name:
            raise SystemExit(
                "Missing session name. Use `grokx resume --session <name> \"...\"` or `grokx resume --list`."
            )
        if session_name not in store.list_sessions():
            raise SystemExit(f"Unknown session {session_name!r}. Run `grokx resume --list` to see saved sessions.")
        if not args.prompt:
            raise SystemExit(
                f"Missing prompt. Use `grokx resume --session {session_name} \"...\"` "
                "to continue this session."
            )
        _run_saved_session_prompt(
            settings,
            session_name=session_name,
            prompt=args.prompt,
            model=args.model,
            system=args.system,
            as_json=args.json,
            no_stream=args.no_stream,
        )
        return 0

    if args.command == "health":
        result = build_client(settings).health(
            include_chat=args.with_chat,
            include_model_probes=args.probe_models,
        )
        if args.probe_models and "model_probes" in result:
            _cache_model_probes(settings, result["model_probes"])
        if args.json:
            print(json.dumps(result, ensure_ascii=False))
        else:
            parts = [
                f"health={result['health']}",
                f"models_ok={result['models_ok']}",
                f"model_count={result['model_count']}",
                f"chat_ok={result['chat_ok']}",
            ]
            if args.probe_models:
                parts.append(f"usable_model_count={result.get('usable_model_count', 0)}")
            print(" ".join(parts))
        return 0

    if args.command == "model" and args.model_command == "current":
        print(settings.model)
        return 0

    if args.command == "model" and args.model_command == "list":
        results = build_client(settings).probe_models()
        _cache_model_probes(settings, results)
        if args.json:
            print(json.dumps(results, ensure_ascii=False))
            return 0
        for item in results:
            model_id = item.get("id")
            if not model_id:
                continue
            if args.all:
                status = "ok" if item.get("chat_ok") else f"fail: {item.get('error', 'Unknown error')}"
                print(f"{model_id}\t{status}")
            elif item.get("chat_ok"):
                print(model_id)
        return 0

    if args.command == "model" and args.model_command == "set":
        if settings.config_path is None:
            raise SystemExit("Missing grokx config path")
        cached_model_probes = _read_cached_model_probes(settings)
        cached_model = _find_cached_model(cached_model_probes, args.model)
        if cached_model is None:
            raise SystemExit(
                f"Model {args.model!r} is not in the cached usable-model set. "
                "Run `grokx health --probe-models` or `grokx model list` first."
            )
        if not cached_model.get("chat_ok"):
            error_message = cached_model.get("error", "Unknown error")
            raise SystemExit(f"Model {args.model!r} failed the last chat probe: {error_message}")
        save_local_config(settings.config_path, {"model": args.model})
        print(args.model)
        return 0

    if args.command == "config" and args.config_command == "show":
        payload = {
            "base_url": settings.base_url,
            "api_key_configured": bool(settings.api_key),
        }
        print(json.dumps(payload, ensure_ascii=False))
        return 0

    if args.command == "config" and args.config_command == "set-base-url":
        if settings.config_path is None:
            raise SystemExit("Missing grokx config path")
        save_local_config(settings.config_path, {"base_url": args.base_url})
        print(args.base_url)
        return 0

    if args.command == "config" and args.config_command == "set-api-key":
        if settings.config_path is None:
            raise SystemExit("Missing grokx config path")
        save_local_config(settings.config_path, {"api_key": args.api_key})
        print("api_key_configured=true")
        return 0

    if args.command == "session" and args.session_command == "list":
        store = _require_sessions_dir(settings)
        if args.json or args.verbose:
            _print_session_summaries(store, as_json=args.json)
        else:
            _print_session_names(store)
        return 0

    if args.command == "session" and args.session_command == "clear":
        _require_sessions_dir(settings).clear_session(args.name)
        print(args.name)
        return 0

    parser.error("Unknown command")
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
