from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_BASE_URL = "http://127.0.0.1:8000/v1"
DEFAULT_MODEL = "grok-4.20-auto"
DEFAULT_TIMEOUT = 180.0
DISCOVERY_DIRS = [
    Path.home() / "services" / "grok2api",
    Path.cwd() / "grok2api",
]


@dataclass
class Settings:
    base_url: str = DEFAULT_BASE_URL
    api_key: str = ""
    model: str = DEFAULT_MODEL
    timeout: float = DEFAULT_TIMEOUT
    app_key: str = ""
    grok2api_dir: Path | None = None
    grok2api_env_path: Path | None = None
    grok2api_config_path: Path | None = None
    grok2api_db_path: Path | None = None
    restart_cmd: str = ""
    config_path: Path | None = None
    sessions_dir: Path | None = None
    session_turn_limit: int = 12


def _read_dotenv(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def _discover_grok2api_dir() -> Path | None:
    explicit = os.getenv("GROKX_GROK2API_DIR")
    if explicit:
        path = Path(explicit).expanduser()
        return path if path.exists() else path
    for candidate in DISCOVERY_DIRS:
        if candidate.exists():
            return candidate
    return None


def _resolve_config_path() -> Path:
    explicit = os.getenv("GROKX_CONFIG_PATH")
    if explicit:
        return Path(explicit).expanduser()
    xdg_config_home = os.getenv("XDG_CONFIG_HOME")
    base_dir = Path(xdg_config_home).expanduser() if xdg_config_home else Path.home() / ".config"
    return base_dir / "grokx" / "config.json"


def _read_local_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def save_local_config(path: Path, patch: dict[str, Any]) -> dict[str, Any]:
    current = _read_local_config(path)
    current.update(patch)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(current, ensure_ascii=False, indent=2) + "\n")
    return current


def load_local_config(path: Path) -> dict[str, Any]:
    return _read_local_config(path)


def _load_model(local_config: dict[str, Any]) -> str:
    local_model = local_config.get("model")
    if isinstance(local_model, str) and local_model.strip():
        return local_model.strip()
    env_model = os.getenv("GROKX_MODEL", "").strip()
    return env_model or DEFAULT_MODEL


def load_settings() -> Settings:
    grok2api_dir = _discover_grok2api_dir()
    grok2api_env_path = Path(os.getenv("GROKX_GROK2API_ENV", "")).expanduser() if os.getenv("GROKX_GROK2API_ENV") else None
    if grok2api_env_path is None and grok2api_dir is not None:
        grok2api_env_path = grok2api_dir / ".env"

    dotenv = _read_dotenv(grok2api_env_path) if grok2api_env_path else {}
    config_path = _resolve_config_path()
    local_config = _read_local_config(config_path)
    sessions_dir = Path(os.getenv("GROKX_SESSIONS_DIR", "")).expanduser() if os.getenv("GROKX_SESSIONS_DIR") else config_path.parent / "sessions"

    def _resolve_local_path(value: str | None) -> Path | None:
        if not value:
            return None
        path = Path(value).expanduser()
        if path.is_absolute() or grok2api_dir is None:
            return path
        return grok2api_dir / path

    grok2api_config_path = os.getenv("GROKX_GROK2API_CONFIG") or dotenv.get("CONFIG_LOCAL_PATH")
    if not grok2api_config_path and grok2api_dir is not None:
        grok2api_config_path = str(grok2api_dir / "data" / "config.toml")

    grok2api_db_path = os.getenv("GROKX_GROK2API_DB") or dotenv.get("ACCOUNT_LOCAL_PATH")
    if not grok2api_db_path and grok2api_dir is not None:
        grok2api_db_path = str(grok2api_dir / "data" / "accounts.db")

    return Settings(
        base_url=os.getenv("GROKX_BASE_URL", DEFAULT_BASE_URL),
        api_key=os.getenv("GROKX_API_KEY") or dotenv.get("GROK_APP_API_KEY", ""),
        model=_load_model(local_config),
        timeout=float(os.getenv("GROKX_TIMEOUT", str(DEFAULT_TIMEOUT))),
        app_key=os.getenv("GROKX_APP_KEY") or dotenv.get("GROK_APP_APP_KEY", ""),
        grok2api_dir=grok2api_dir,
        grok2api_env_path=grok2api_env_path,
        grok2api_config_path=_resolve_local_path(grok2api_config_path),
        grok2api_db_path=_resolve_local_path(grok2api_db_path),
        restart_cmd=os.getenv("GROKX_RESTART_CMD", ""),
        config_path=config_path,
        sessions_dir=sessions_dir,
        session_turn_limit=max(1, int(os.getenv("GROKX_SESSION_TURN_LIMIT", "12"))),
    )
