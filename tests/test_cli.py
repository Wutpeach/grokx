import json

from grokx import cli
from grokx.config import Settings


class DummyClient:
    def __init__(self, responses=None):
        self.calls = []
        self.responses = list(responses or ["OK"])

    def _next_text(self):
        return self.responses.pop(0) if self.responses else "OK"

    def ask(self, prompt=None, *, model=None, system=None, messages=None):
        self.calls.append(("ask", prompt, model, system, messages))
        return {"text": self._next_text(), "raw": {"id": "resp_1"}}

    def ask_stream(self, prompt=None, *, model=None, system=None, messages=None):
        self.calls.append(("stream", prompt, model, system, messages))
        for chunk in self._next_text():
            yield chunk

    def health(self, *, include_chat=False):
        self.calls.append(("health", include_chat))
        return {
            "health": "ok",
            "models_ok": True,
            "chat_ok": include_chat,
            "model_count": 3,
        }

    def list_models(self):
        self.calls.append(("models",))
        return [
            {"id": "grok-4.20-auto"},
            {"id": "grok-4.20-0309"},
        ]


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


def test_health_command_supports_json_output(monkeypatch, capsys):
    dummy = DummyClient()
    monkeypatch.setattr(cli, "build_client", lambda settings: dummy)
    monkeypatch.setattr(cli, "load_settings", lambda: Settings(api_key="k"))

    exit_code = cli.main(["health", "--with-chat", "--json"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["health"] == "ok"
    assert payload["chat_ok"] is True


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
    assert capsys.readouterr().out.strip().splitlines() == [
        "grok-4.20-auto",
        "grok-4.20-0309",
    ]


def test_model_set_command_persists_selected_model(tmp_path, monkeypatch, capsys):
    config_path = tmp_path / "config.json"
    monkeypatch.setenv("GROKX_CONFIG_PATH", str(config_path))
    monkeypatch.delenv("GROKX_MODEL", raising=False)

    exit_code = cli.main(["model", "set", "grok-4.20-expert"])

    assert exit_code == 0
    assert json.loads(config_path.read_text()) == {"model": "grok-4.20-expert"}
    assert capsys.readouterr().out.strip() == "grok-4.20-expert"
