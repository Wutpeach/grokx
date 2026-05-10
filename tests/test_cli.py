import json

from grokx import cli
from grokx.config import Settings, load_local_config


class DummyClient:
    def __init__(self, responses=None, model_probes=None):
        self.calls = []
        self.responses = list(responses or ["OK"])
        self.model_probes = list(
            model_probes
            or [
                {"id": "grok-4.20-auto", "chat_ok": True, "error": ""},
                {"id": "grok-4.20-0309", "chat_ok": False, "error": "HTTP 400: unsupported model"},
            ]
        )

    def _next_text(self):
        return self.responses.pop(0) if self.responses else "OK"

    def ask(self, prompt=None, *, model=None, system=None, messages=None):
        self.calls.append(("ask", prompt, model, system, messages))
        return {"text": self._next_text(), "raw": {"id": "resp_1"}}

    def ask_stream(self, prompt=None, *, model=None, system=None, messages=None):
        self.calls.append(("stream", prompt, model, system, messages))
        for chunk in self._next_text():
            yield chunk

    def health(self, *, include_chat=False, include_model_probes=False):
        self.calls.append(("health", include_chat, include_model_probes))
        payload = {
            "health": "ok",
            "models_ok": True,
            "chat_ok": include_chat,
            "model_count": 3,
        }
        if include_model_probes:
            payload["usable_model_count"] = sum(1 for item in self.model_probes if item["chat_ok"])
            payload["model_probes"] = self.model_probes
        return payload

    def list_models(self):
        self.calls.append(("models",))
        return [
            {"id": "grok-4.20-auto"},
            {"id": "grok-4.20-0309"},
        ]

    def probe_models(self, models=None):
        self.calls.append(("probe_models", models))
        return list(self.model_probes)


def test_ask_command_prints_text(monkeypatch, capsys):
    dummy = DummyClient()
    monkeypatch.setattr(cli, "build_client", lambda settings: dummy)
    monkeypatch.setattr(cli, "load_settings", lambda: Settings(api_key="k"))

    exit_code = cli.main(["ask", "hello world"])

    assert exit_code == 0
    assert dummy.calls == [("stream", "hello world", None, None, None)]
    assert capsys.readouterr().out.strip() == "OK"


def test_ask_command_supports_no_stream(monkeypatch, capsys):
    dummy = DummyClient()
    monkeypatch.setattr(cli, "build_client", lambda settings: dummy)
    monkeypatch.setattr(cli, "load_settings", lambda: Settings(api_key="k"))

    exit_code = cli.main(["ask", "hello world", "--no-stream"])

    assert exit_code == 0
    assert dummy.calls == [("ask", "hello world", None, None, None)]
    assert capsys.readouterr().out.strip() == "OK"


def test_new_command_starts_fresh_named_session(monkeypatch, tmp_path, capsys):
    dummy = DummyClient(responses=["FIRST", "SECOND"])
    monkeypatch.setattr(cli, "build_client", lambda settings: dummy)
    monkeypatch.setattr(cli, "load_settings", lambda: Settings(api_key="k", sessions_dir=tmp_path / "sessions", session_turn_limit=12))

    assert cli.main(["ask", "hello world", "--no-stream", "--session", "demo"]) == 0
    capsys.readouterr()

    exit_code = cli.main(["new", "--session", "fresh", "brand new", "--no-stream"])

    assert exit_code == 0
    assert capsys.readouterr().out.strip() == "SECOND"
    assert dummy.calls[1] == (
        "ask",
        None,
        None,
        None,
        [
            {"role": "user", "content": "brand new"},
        ],
    )


def test_new_command_rejects_existing_session_without_force(monkeypatch, tmp_path, capsys):
    dummy = DummyClient(responses=["FIRST"])
    monkeypatch.setattr(cli, "build_client", lambda settings: dummy)
    monkeypatch.setattr(cli, "load_settings", lambda: Settings(api_key="k", sessions_dir=tmp_path / "sessions", session_turn_limit=12))

    assert cli.main(["ask", "hello world", "--no-stream", "--session", "demo"]) == 0
    capsys.readouterr()

    try:
        cli.main(["/new", "--session", "demo", "replace me", "--no-stream"])
    except SystemExit as exc:
        assert str(exc) == (
            "Session 'demo' already exists. "
            "Use `grokx resume demo \"...\"` to continue it or `grokx /new --session demo --force \"...\"` to replace it."
        )
    else:
        raise AssertionError("Expected SystemExit")


def test_new_command_force_replaces_existing_session(monkeypatch, tmp_path, capsys):
    dummy = DummyClient(responses=["FIRST", "SECOND"])
    monkeypatch.setattr(cli, "build_client", lambda settings: dummy)
    monkeypatch.setattr(cli, "load_settings", lambda: Settings(api_key="k", sessions_dir=tmp_path / "sessions", session_turn_limit=12))

    assert cli.main(["ask", "hello world", "--no-stream", "--session", "demo"]) == 0
    capsys.readouterr()

    exit_code = cli.main(["new", "--session", "demo", "--force", "brand new", "--no-stream"])

    assert exit_code == 0
    assert capsys.readouterr().out.strip() == "SECOND"
    assert dummy.calls[1] == (
        "ask",
        None,
        None,
        None,
        [
            {"role": "user", "content": "brand new"},
        ],
    )


def test_ask_command_persists_and_reuses_named_session(monkeypatch, tmp_path, capsys):
    dummy = DummyClient(responses=["FIRST", "SECOND"])
    monkeypatch.setattr(cli, "build_client", lambda settings: dummy)
    monkeypatch.setattr(cli, "load_settings", lambda: Settings(api_key="k", sessions_dir=tmp_path / "sessions", session_turn_limit=12))

    first_exit = cli.main(["ask", "hello world", "--no-stream", "--session", "demo", "--system", "be helpful"])
    first_output = capsys.readouterr().out.strip()
    second_exit = cli.main(["ask", "follow up", "--no-stream", "--session", "demo"])
    second_output = capsys.readouterr().out.strip()

    assert first_exit == 0
    assert second_exit == 0
    assert first_output == "FIRST"
    assert second_output == "SECOND"
    assert dummy.calls[0] == (
        "ask",
        None,
        None,
        None,
        [
            {"role": "system", "content": "be helpful"},
            {"role": "user", "content": "hello world"},
        ],
    )
    assert dummy.calls[1] == (
        "ask",
        None,
        None,
        None,
        [
            {"role": "system", "content": "be helpful"},
            {"role": "user", "content": "hello world"},
            {"role": "assistant", "content": "FIRST"},
            {"role": "user", "content": "follow up"},
        ],
    )


def test_session_list_and_clear_commands(monkeypatch, tmp_path, capsys):
    dummy = DummyClient(responses=["OK"])
    settings = Settings(api_key="k", sessions_dir=tmp_path / "sessions", session_turn_limit=12)
    monkeypatch.setattr(cli, "build_client", lambda settings: dummy)
    monkeypatch.setattr(cli, "load_settings", lambda: settings)

    assert cli.main(["ask", "hello world", "--no-stream", "--session", "demo"]) == 0
    capsys.readouterr()

    assert cli.main(["session", "list"]) == 0
    assert capsys.readouterr().out.strip().splitlines() == ["demo"]

    assert cli.main(["session", "clear", "demo"]) == 0
    assert capsys.readouterr().out.strip() == "demo"

    assert cli.main(["session", "list"]) == 0
    assert capsys.readouterr().out.strip() == ""


def test_session_list_verbose_shows_summary(monkeypatch, tmp_path, capsys):
    dummy = DummyClient(responses=["FIRST"])
    settings = Settings(api_key="k", sessions_dir=tmp_path / "sessions", session_turn_limit=12)
    monkeypatch.setattr(cli, "build_client", lambda settings: dummy)
    monkeypatch.setattr(cli, "load_settings", lambda: settings)

    assert cli.main(["ask", "hello world", "--no-stream", "--session", "demo"]) == 0
    capsys.readouterr()

    assert cli.main(["session", "list", "--verbose"]) == 0
    assert capsys.readouterr().out.strip().splitlines()[0].startswith("demo\tturns=1\t")


def test_session_list_json_shows_summary_payload(monkeypatch, tmp_path, capsys):
    dummy = DummyClient(responses=["FIRST"])
    settings = Settings(api_key="k", sessions_dir=tmp_path / "sessions", session_turn_limit=12)
    monkeypatch.setattr(cli, "build_client", lambda settings: dummy)
    monkeypatch.setattr(cli, "load_settings", lambda: settings)

    assert cli.main(["ask", "hello world", "--no-stream", "--session", "demo"]) == 0
    capsys.readouterr()

    assert cli.main(["session", "list", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload[0]["name"] == "demo"
    assert payload[0]["turns"] == 1


def test_resume_lists_saved_sessions(monkeypatch, tmp_path, capsys):
    dummy = DummyClient(responses=["FIRST", "SECOND"])
    settings = Settings(api_key="k", sessions_dir=tmp_path / "sessions", session_turn_limit=12)
    monkeypatch.setattr(cli, "build_client", lambda settings: dummy)
    monkeypatch.setattr(cli, "load_settings", lambda: settings)

    assert cli.main(["ask", "hello world", "--no-stream", "--session", "demo"]) == 0
    capsys.readouterr()
    assert cli.main(["ask", "another one", "--no-stream", "--session", "alpha"]) == 0
    capsys.readouterr()

    assert cli.main(["resume"]) == 0
    captured = capsys.readouterr()
    lines = captured.out.strip().splitlines()
    assert len(lines) == 2
    assert any(line.startswith("demo\tturns=1\t") for line in lines)
    assert any(line.startswith("alpha\tturns=1\t") for line in lines)
    assert "Prefer `grokx resume --list` or `grokx session list --verbose`." in captured.err


def test_resume_list_flag_lists_saved_sessions(monkeypatch, tmp_path, capsys):
    dummy = DummyClient(responses=["FIRST"])
    settings = Settings(api_key="k", sessions_dir=tmp_path / "sessions", session_turn_limit=12)
    monkeypatch.setattr(cli, "build_client", lambda settings: dummy)
    monkeypatch.setattr(cli, "load_settings", lambda: settings)

    assert cli.main(["ask", "hello world", "--no-stream", "--session", "demo"]) == 0
    capsys.readouterr()

    assert cli.main(["resume", "--list"]) == 0
    captured = capsys.readouterr()
    assert captured.out.strip().splitlines()[0].startswith("demo\tturns=1\t")
    assert captured.err.strip() == ""


def test_resume_list_flag_rejects_name_or_prompt(monkeypatch, tmp_path):
    settings = Settings(api_key="k", sessions_dir=tmp_path / "sessions", session_turn_limit=12)
    monkeypatch.setattr(cli, "load_settings", lambda: settings)

    try:
        cli.main(["resume", "--list", "demo"])
    except SystemExit as exc:
        assert str(exc) == "Cannot combine `grokx resume --list` with a session name or prompt."
    else:
        raise AssertionError("Expected SystemExit")


def test_resume_command_continues_named_session(monkeypatch, tmp_path, capsys):
    dummy = DummyClient(responses=["FIRST", "SECOND"])
    monkeypatch.setattr(cli, "build_client", lambda settings: dummy)
    monkeypatch.setattr(cli, "load_settings", lambda: Settings(api_key="k", sessions_dir=tmp_path / "sessions", session_turn_limit=12))

    assert cli.main(["ask", "hello world", "--no-stream", "--session", "demo", "--system", "be helpful"]) == 0
    capsys.readouterr()

    exit_code = cli.main(["resume", "demo", "follow up", "--no-stream"])

    assert exit_code == 0
    assert capsys.readouterr().out.strip() == "SECOND"
    assert dummy.calls[1] == (
        "ask",
        None,
        None,
        None,
        [
            {"role": "system", "content": "be helpful"},
            {"role": "user", "content": "hello world"},
            {"role": "assistant", "content": "FIRST"},
            {"role": "user", "content": "follow up"},
        ],
    )


def test_resume_command_supports_session_flag(monkeypatch, tmp_path, capsys):
    dummy = DummyClient(responses=["FIRST", "SECOND"])
    monkeypatch.setattr(cli, "build_client", lambda settings: dummy)
    monkeypatch.setattr(cli, "load_settings", lambda: Settings(api_key="k", sessions_dir=tmp_path / "sessions", session_turn_limit=12))

    assert cli.main(["ask", "hello world", "--no-stream", "--session", "demo"]) == 0
    capsys.readouterr()

    assert cli.main(["resume", "demo", "follow up", "--session", "demo", "--no-stream"]) == 0
    assert capsys.readouterr().out.strip() == "SECOND"


def test_resume_command_rejects_conflicting_session_selectors(monkeypatch, tmp_path):
    settings = Settings(api_key="k", sessions_dir=tmp_path / "sessions", session_turn_limit=12)
    monkeypatch.setattr(cli, "load_settings", lambda: settings)

    try:
        cli.main(["resume", "demo", "follow up", "--session", "alpha"])
    except SystemExit as exc:
        assert str(exc) == (
            "Conflicting session selectors for `grokx resume`. "
            "Use either the positional session name or `--session`, not both."
        )
    else:
        raise AssertionError("Expected SystemExit")


def test_slash_resume_alias_continues_named_session(monkeypatch, tmp_path, capsys):
    dummy = DummyClient(responses=["FIRST", "SECOND"])
    monkeypatch.setattr(cli, "build_client", lambda settings: dummy)
    monkeypatch.setattr(cli, "load_settings", lambda: Settings(api_key="k", sessions_dir=tmp_path / "sessions", session_turn_limit=12))

    assert cli.main(["ask", "hello world", "--no-stream", "--session", "demo"]) == 0
    capsys.readouterr()

    exit_code = cli.main(["/resume", "demo", "follow up", "--no-stream"])

    assert exit_code == 0
    assert capsys.readouterr().out.strip() == "SECOND"


def test_side_lists_saved_sessions(monkeypatch, tmp_path, capsys):
    dummy = DummyClient(responses=["FIRST"])
    settings = Settings(api_key="k", sessions_dir=tmp_path / "sessions", session_turn_limit=12)
    monkeypatch.setattr(cli, "build_client", lambda settings: dummy)
    monkeypatch.setattr(cli, "load_settings", lambda: settings)

    assert cli.main(["ask", "hello world", "--no-stream", "--session", "demo"]) == 0
    capsys.readouterr()

    assert cli.main(["side"]) == 0
    captured = capsys.readouterr()
    assert captured.out.strip().splitlines()[0].startswith("demo\tturns=1\t")
    assert "Prefer `grokx side --list` or `grokx session list --verbose`." in captured.err


def test_side_list_flag_lists_saved_sessions(monkeypatch, tmp_path, capsys):
    dummy = DummyClient(responses=["FIRST"])
    settings = Settings(api_key="k", sessions_dir=tmp_path / "sessions", session_turn_limit=12)
    monkeypatch.setattr(cli, "build_client", lambda settings: dummy)
    monkeypatch.setattr(cli, "load_settings", lambda: settings)

    assert cli.main(["ask", "hello world", "--no-stream", "--session", "demo"]) == 0
    capsys.readouterr()

    assert cli.main(["side", "--list"]) == 0
    captured = capsys.readouterr()
    assert captured.out.strip().splitlines()[0].startswith("demo\tturns=1\t")
    assert captured.err.strip() == ""


def test_side_list_flag_rejects_name_or_prompt(monkeypatch, tmp_path):
    settings = Settings(api_key="k", sessions_dir=tmp_path / "sessions", session_turn_limit=12)
    monkeypatch.setattr(cli, "load_settings", lambda: settings)

    try:
        cli.main(["side", "--list", "demo"])
    except SystemExit as exc:
        assert str(exc) == "Cannot combine `grokx side --list` with a session name or prompt."
    else:
        raise AssertionError("Expected SystemExit")


def test_side_command_uses_saved_context_without_mutating_session(monkeypatch, tmp_path, capsys):
    dummy = DummyClient(responses=["FIRST", "SECOND", "THIRD"])
    settings = Settings(api_key="k", sessions_dir=tmp_path / "sessions", session_turn_limit=12)
    monkeypatch.setattr(cli, "build_client", lambda settings: dummy)
    monkeypatch.setattr(cli, "load_settings", lambda: settings)

    assert cli.main(["ask", "hello world", "--no-stream", "--session", "demo", "--system", "be helpful"]) == 0
    capsys.readouterr()

    exit_code = cli.main(["side", "demo", "temporary branch", "--no-stream"])

    assert exit_code == 0
    assert capsys.readouterr().out.strip() == "SECOND"
    assert dummy.calls[1] == (
        "ask",
        None,
        None,
        None,
        [
            {"role": "system", "content": "be helpful"},
            {"role": "user", "content": "hello world"},
            {"role": "assistant", "content": "FIRST"},
            {"role": "user", "content": "temporary branch"},
        ],
    )

    resume_exit_code = cli.main(["resume", "demo", "follow up", "--no-stream"])

    assert resume_exit_code == 0
    assert capsys.readouterr().out.strip() == "THIRD"
    assert dummy.calls[2] == (
        "ask",
        None,
        None,
        None,
        [
            {"role": "system", "content": "be helpful"},
            {"role": "user", "content": "hello world"},
            {"role": "assistant", "content": "FIRST"},
            {"role": "user", "content": "follow up"},
        ],
    )


def test_side_command_supports_session_flag(monkeypatch, tmp_path, capsys):
    dummy = DummyClient(responses=["FIRST", "SECOND"])
    settings = Settings(api_key="k", sessions_dir=tmp_path / "sessions", session_turn_limit=12)
    monkeypatch.setattr(cli, "build_client", lambda settings: dummy)
    monkeypatch.setattr(cli, "load_settings", lambda: settings)

    assert cli.main(["ask", "hello world", "--no-stream", "--session", "demo"]) == 0
    capsys.readouterr()

    assert cli.main(["side", "demo", "temporary branch", "--session", "demo", "--no-stream"]) == 0
    assert capsys.readouterr().out.strip() == "SECOND"


def test_side_command_rejects_conflicting_session_selectors(monkeypatch, tmp_path):
    settings = Settings(api_key="k", sessions_dir=tmp_path / "sessions", session_turn_limit=12)
    monkeypatch.setattr(cli, "load_settings", lambda: settings)

    try:
        cli.main(["side", "demo", "temporary branch", "--session", "alpha"])
    except SystemExit as exc:
        assert str(exc) == (
            "Conflicting session selectors for `grokx side`. "
            "Use either the positional session name or `--session`, not both."
        )
    else:
        raise AssertionError("Expected SystemExit")


def test_slash_side_alias_works(monkeypatch, tmp_path, capsys):
    dummy = DummyClient(responses=["FIRST", "SECOND"])
    settings = Settings(api_key="k", sessions_dir=tmp_path / "sessions", session_turn_limit=12)
    monkeypatch.setattr(cli, "build_client", lambda settings: dummy)
    monkeypatch.setattr(cli, "load_settings", lambda: settings)

    assert cli.main(["ask", "hello world", "--no-stream", "--session", "demo"]) == 0
    capsys.readouterr()

    exit_code = cli.main(["/side", "demo", "temporary branch", "--no-stream"])

    assert exit_code == 0
    assert capsys.readouterr().out.strip() == "SECOND"


def test_health_command_supports_json_output(monkeypatch, capsys):
    dummy = DummyClient()
    monkeypatch.setattr(cli, "build_client", lambda settings: dummy)
    monkeypatch.setattr(cli, "load_settings", lambda: Settings(api_key="k"))

    exit_code = cli.main(["health", "--with-chat", "--probe-models", "--json"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["health"] == "ok"
    assert payload["chat_ok"] is True
    assert payload["usable_model_count"] == 1


def test_model_current_command_prints_selected_model(monkeypatch, capsys):
    monkeypatch.setattr(cli, "load_settings", lambda: Settings(model="grok-4.20-0309"))

    exit_code = cli.main(["model", "current"])

    assert exit_code == 0
    assert capsys.readouterr().out.strip() == "grok-4.20-0309"


def test_model_list_command_prints_available_models(monkeypatch, capsys):
    dummy = DummyClient()
    monkeypatch.setattr(cli, "build_client", lambda settings: dummy)
    monkeypatch.setattr(cli, "load_settings", lambda: Settings(api_key="k"))

    exit_code = cli.main(["model", "list"])

    assert exit_code == 0
    assert dummy.calls == [("probe_models", None)]
    assert capsys.readouterr().out.strip().splitlines() == ["grok-4.20-auto"]


def test_model_list_caches_probe_results(tmp_path, monkeypatch, capsys):
    dummy = DummyClient()
    config_path = tmp_path / "config.json"
    monkeypatch.setenv("GROKX_CONFIG_PATH", str(config_path))
    monkeypatch.setattr(cli, "build_client", lambda settings: dummy)
    monkeypatch.setattr(cli, "load_settings", lambda: Settings(api_key="k", config_path=config_path))

    exit_code = cli.main(["model", "list"])

    assert exit_code == 0
    assert load_local_config(config_path)["model_probes"] == dummy.model_probes
    assert capsys.readouterr().out.strip().splitlines() == ["grok-4.20-auto"]


def test_model_list_all_shows_probe_failures(monkeypatch, capsys):
    dummy = DummyClient()
    monkeypatch.setattr(cli, "build_client", lambda settings: dummy)
    monkeypatch.setattr(cli, "load_settings", lambda: Settings(api_key="k"))

    exit_code = cli.main(["model", "list", "--all"])

    assert exit_code == 0
    assert capsys.readouterr().out.strip().splitlines() == [
        "grok-4.20-auto\tok",
        "grok-4.20-0309\tfail: HTTP 400: unsupported model",
    ]


def test_model_set_command_persists_selected_model(tmp_path, monkeypatch, capsys):
    config_path = tmp_path / "config.json"
    monkeypatch.setenv("GROKX_CONFIG_PATH", str(config_path))
    monkeypatch.delenv("GROKX_MODEL", raising=False)
    config_path.write_text(
        json.dumps(
            {
                "model_probes": [
                    {"id": "grok-4.20-expert", "chat_ok": True, "error": ""},
                ]
            }
        )
    )

    exit_code = cli.main(["model", "set", "grok-4.20-expert"])

    assert exit_code == 0
    assert json.loads(config_path.read_text()) == {
        "model_probes": [
            {"id": "grok-4.20-expert", "chat_ok": True, "error": ""},
        ],
        "model": "grok-4.20-expert",
    }
    assert capsys.readouterr().out.strip() == "grok-4.20-expert"


def test_health_probe_models_caches_results(tmp_path, monkeypatch, capsys):
    dummy = DummyClient()
    config_path = tmp_path / "config.json"
    monkeypatch.setenv("GROKX_CONFIG_PATH", str(config_path))
    monkeypatch.setattr(cli, "build_client", lambda settings: dummy)
    monkeypatch.setattr(cli, "load_settings", lambda: Settings(api_key="k", config_path=config_path))

    exit_code = cli.main(["health", "--probe-models"])

    assert exit_code == 0
    assert load_local_config(config_path)["model_probes"] == dummy.model_probes


def test_model_set_rejects_model_missing_from_cache(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    monkeypatch.setenv("GROKX_CONFIG_PATH", str(config_path))
    monkeypatch.delenv("GROKX_MODEL", raising=False)

    try:
        cli.main(["model", "set", "grok-4.20-expert"])
    except SystemExit as exc:
        assert str(exc) == (
            "Model 'grok-4.20-expert' is not in the cached usable-model set. "
            "Run `grokx health --probe-models` or `grokx model list` first."
        )
    else:
        raise AssertionError("Expected SystemExit")


def test_model_set_rejects_cached_failed_model(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    monkeypatch.setenv("GROKX_CONFIG_PATH", str(config_path))
    monkeypatch.delenv("GROKX_MODEL", raising=False)
    config_path.write_text(
        json.dumps(
            {
                "model_probes": [
                    {"id": "grok-4.20-expert", "chat_ok": False, "error": "HTTP 400: unsupported model"},
                ]
            }
        )
    )

    try:
        cli.main(["model", "set", "grok-4.20-expert"])
    except SystemExit as exc:
        assert str(exc) == "Model 'grok-4.20-expert' failed the last chat probe: HTTP 400: unsupported model"
    else:
        raise AssertionError("Expected SystemExit")


def test_config_show_prints_effective_connection_settings(monkeypatch, capsys):
    monkeypatch.setattr(
        cli,
        "load_settings",
        lambda: Settings(base_url="https://example.com/v1", api_key="secret"),
    )

    exit_code = cli.main(["config", "show"])

    assert exit_code == 0
    assert json.loads(capsys.readouterr().out) == {
        "base_url": "https://example.com/v1",
        "api_key_configured": True,
    }


def test_config_set_base_url_persists_value(tmp_path, monkeypatch, capsys):
    config_path = tmp_path / "config.json"
    monkeypatch.setenv("GROKX_CONFIG_PATH", str(config_path))
    monkeypatch.setattr(cli, "load_settings", lambda: Settings(config_path=config_path))

    exit_code = cli.main(["config", "set-base-url", "https://example.com/v1"])

    assert exit_code == 0
    assert json.loads(config_path.read_text()) == {"base_url": "https://example.com/v1"}
    assert capsys.readouterr().out.strip() == "https://example.com/v1"


def test_config_set_api_key_persists_value(tmp_path, monkeypatch, capsys):
    config_path = tmp_path / "config.json"
    monkeypatch.setenv("GROKX_CONFIG_PATH", str(config_path))
    monkeypatch.setattr(cli, "load_settings", lambda: Settings(config_path=config_path))

    exit_code = cli.main(["config", "set-api-key", "secret-key"])

    assert exit_code == 0
    assert json.loads(config_path.read_text()) == {"api_key": "secret-key"}
    assert capsys.readouterr().out.strip() == "api_key_configured=true"
