from __future__ import annotations

import re
import sqlite3
import subprocess
from pathlib import Path


def _replace_key(text: str, key: str, value: str) -> str:
    pattern = rf'(^\s*{re.escape(key)}\s*=\s*")[^"]*(")'
    replaced, count = re.subn(pattern, rf'\1{value}\2', text, flags=re.MULTILINE)
    if count == 0:
        raise ValueError(f"Could not find `{key}` in config file")
    return replaced


def set_clearance_in_toml(path: Path, *, cf_clearance: str, user_agent: str | None) -> None:
    text = path.read_text()
    text = _replace_key(text, "cf_clearance", cf_clearance)
    if user_agent is not None:
        text = _replace_key(text, "user_agent", user_agent)
    path.write_text(text)


def restart_grok2api(command: str) -> None:
    if not command:
        return
    subprocess.run(command, shell=True, check=True)


def load_active_tokens(db_path: Path) -> list[str]:
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        return [row[0] for row in cur.execute("select token from accounts where status='active' order by updated_at desc")]
    finally:
        conn.close()
