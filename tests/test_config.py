from pathlib import Path

from grokx.config import Settings, load_settings


def test_load_settings_reads_values_from_grok2api_dir(tmp_path, monkeypatch):
    grok2api_dir = tmp_path / "grok2api"
    data_dir = grok2api_dir / "data"
    data_dir.mkdir(parents=True)
    (grok2api_dir / ".env").write_text(
        "GROK_APP_API_KEY=test-api-key\n"
        "GROK_APP_APP_KEY=test-app-key\n"
        "CONFIG_LOCAL_PATH=/custom/config.toml\n"
        "ACCOUNT_LOCAL_PATH=/custom/accounts.db\n"
    )
    (data_dir / "config.toml").write_text('cf_clearance = "old"\n')
    (data_dir / "accounts.db").write_text("")

    monkeypatch.setenv("GROKX_GROK2API_DIR", str(grok2api_dir))

    settings = load_settings()

    assert isinstance(settings, Settings)
    assert settings.api_key == "test-api-key"
    assert settings.app_key == "test-app-key"
    assert settings.grok2api_config_path == Path("/custom/config.toml")
    assert settings.grok2api_db_path == Path("/custom/accounts.db")


def test_load_settings_resolves_relative_paths_from_grok2api_dir(tmp_path, monkeypatch):
    grok2api_dir = tmp_path / "grok2api"
    grok2api_dir.mkdir(parents=True)
    (grok2api_dir / ".env").write_text(
        "ACCOUNT_LOCAL_PATH=./data/accounts.db\n"
        "CONFIG_LOCAL_PATH=./data/config.toml\n"
    )

    monkeypatch.setenv("GROKX_GROK2API_DIR", str(grok2api_dir))

    settings = load_settings()

    assert settings.grok2api_db_path == grok2api_dir / "data" / "accounts.db"
    assert settings.grok2api_config_path == grok2api_dir / "data" / "config.toml"


def test_load_settings_defaults_to_localhost_and_default_model(tmp_path, monkeypatch):
    monkeypatch.delenv("GROKX_BASE_URL", raising=False)
    monkeypatch.delenv("GROKX_MODEL", raising=False)
    monkeypatch.delenv("GROKX_GROK2API_DIR", raising=False)
    monkeypatch.setenv("GROKX_CONFIG_PATH", str(tmp_path / "config.json"))

    settings = load_settings()

    assert settings.base_url == "http://127.0.0.1:8000/v1"
    assert settings.model == "grok-4.20-auto"
    assert settings.sessions_dir == settings.config_path.parent / "sessions"


def test_load_settings_prefers_saved_model_over_env_model(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    config_path.write_text('{"model": "grok-4.20-0309"}')

    monkeypatch.setenv("GROKX_CONFIG_PATH", str(config_path))
    monkeypatch.setenv("GROKX_MODEL", "grok-4.20-auto")
    monkeypatch.delenv("GROKX_GROK2API_DIR", raising=False)

    settings = load_settings()

    assert settings.config_path == config_path
    assert settings.model == "grok-4.20-0309"


def test_load_settings_supports_explicit_sessions_dir(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    sessions_dir = tmp_path / "custom-sessions"

    monkeypatch.setenv("GROKX_CONFIG_PATH", str(config_path))
    monkeypatch.setenv("GROKX_SESSIONS_DIR", str(sessions_dir))
    monkeypatch.delenv("GROKX_GROK2API_DIR", raising=False)

    settings = load_settings()

    assert settings.sessions_dir == sessions_dir


def test_load_settings_reads_saved_base_url_and_api_key(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    config_path.write_text('{"base_url": "https://example.com/v1", "api_key": "saved-key"}')

    monkeypatch.setenv("GROKX_CONFIG_PATH", str(config_path))
    monkeypatch.delenv("GROKX_BASE_URL", raising=False)
    monkeypatch.delenv("GROKX_API_KEY", raising=False)
    monkeypatch.delenv("GROKX_GROK2API_DIR", raising=False)

    settings = load_settings()

    assert settings.base_url == "https://example.com/v1"
    assert settings.api_key == "saved-key"


def test_load_settings_prefers_env_base_url_and_api_key_over_saved_values(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    config_path.write_text('{"base_url": "https://saved.example/v1", "api_key": "saved-key"}')

    monkeypatch.setenv("GROKX_CONFIG_PATH", str(config_path))
    monkeypatch.setenv("GROKX_BASE_URL", "https://env.example/v1")
    monkeypatch.setenv("GROKX_API_KEY", "env-key")
    monkeypatch.delenv("GROKX_GROK2API_DIR", raising=False)

    settings = load_settings()

    assert settings.base_url == "https://env.example/v1"
    assert settings.api_key == "env-key"
