from __future__ import annotations

import json
import os
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

try:
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class SessionState:
    name: str
    system_prompt: str = ""
    created_at: str = ""
    updated_at: str = ""
    last_model: str = ""
    turns: int = 0
    messages: list[dict[str, str]] | None = None


class SessionStore:
    def __init__(self, root_dir: Path):
        self.root_dir = Path(root_dir).expanduser()
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def _normalize_name(self, name: str) -> str:
        candidate = (name or "").strip()
        if not candidate:
            raise ValueError("session name cannot be empty")
        if candidate in {".", ".."} or "/" in candidate or "\\" in candidate:
            raise ValueError(f"invalid session name: {name}")
        return candidate

    def _session_path(self, name: str) -> Path:
        return self.root_dir / f"{self._normalize_name(name)}.jsonl"

    def _meta_path(self, name: str) -> Path:
        return self.root_dir / f"{self._normalize_name(name)}.meta.json"

    def _lock_path(self, name: str) -> Path:
        return self.root_dir / f"{self._normalize_name(name)}.lock"

    @contextmanager
    def _locked(self, name: str) -> Iterator[None]:
        lock_path = self._lock_path(name)
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with lock_path.open("a+", encoding="utf-8") as handle:
            if fcntl is not None:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                if fcntl is not None:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def _read_meta(self, name: str) -> dict:
        path = self._meta_path(name)
        if not path.exists():
            return {}
        try:
            payload = json.loads(path.read_text())
        except json.JSONDecodeError:
            return {}
        return payload if isinstance(payload, dict) else {}

    def _write_meta(self, name: str, payload: dict) -> None:
        path = self._meta_path(name)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")

    def list_sessions(self) -> list[str]:
        names: set[str] = set()
        for path in self.root_dir.glob("*.jsonl"):
            names.add(path.stem)
        for path in self.root_dir.glob("*.meta.json"):
            names.add(path.name.removesuffix(".meta.json"))
        return sorted(names)

    def load_session(self, name: str, *, turn_limit: int | None = None) -> SessionState:
        with self._locked(name):
            meta = self._read_meta(name)
            path = self._session_path(name)
            records: list[dict] = []
            if path.exists():
                for line in path.read_text().splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        payload = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if isinstance(payload, dict):
                        records.append(payload)

        if turn_limit and records:
            last_turn = max(int(item.get("turn", 0)) for item in records)
            min_turn = max(1, last_turn - turn_limit + 1)
            records = [item for item in records if int(item.get("turn", 0)) >= min_turn]

        messages = []
        for item in records:
            role = item.get("role")
            content = item.get("content")
            if isinstance(role, str) and isinstance(content, str):
                messages.append({"role": role, "content": content})

        return SessionState(
            name=name,
            system_prompt=str(meta.get("system_prompt") or ""),
            created_at=str(meta.get("created_at") or ""),
            updated_at=str(meta.get("updated_at") or ""),
            last_model=str(meta.get("last_model") or ""),
            turns=int(meta.get("turns") or 0),
            messages=messages,
        )

    def append_turn(
        self,
        name: str,
        *,
        user_content: str,
        assistant_content: str,
        model: str,
        system_prompt: str | None = None,
    ) -> SessionState:
        timestamp = _utc_now()
        with self._locked(name):
            meta = self._read_meta(name)
            created_at = str(meta.get("created_at") or timestamp)
            turn = int(meta.get("turns") or 0) + 1
            if system_prompt is None:
                resolved_system = str(meta.get("system_prompt") or "")
            else:
                resolved_system = system_prompt
            meta = {
                "name": name,
                "created_at": created_at,
                "updated_at": timestamp,
                "system_prompt": resolved_system,
                "last_model": model,
                "turns": turn,
            }
            self._write_meta(name, meta)
            path = self._session_path(name)
            entries = [
                {
                    "id": f"{name}-u-{turn}",
                    "ts": timestamp,
                    "role": "user",
                    "content": user_content,
                    "turn": turn,
                    "model": model,
                },
                {
                    "id": f"{name}-a-{turn}",
                    "ts": timestamp,
                    "role": "assistant",
                    "content": assistant_content,
                    "turn": turn,
                    "model": model,
                },
            ]
            with path.open("a", encoding="utf-8") as handle:
                for entry in entries:
                    handle.write(json.dumps(entry, ensure_ascii=False) + "\n")

        return SessionState(
            name=name,
            system_prompt=resolved_system,
            created_at=created_at,
            updated_at=timestamp,
            last_model=model,
            turns=turn,
            messages=None,
        )

    def clear_session(self, name: str) -> None:
        with self._locked(name):
            for path in (self._session_path(name), self._meta_path(name)):
                if path.exists():
                    path.unlink()
            lock_path = self._lock_path(name)
            if lock_path.exists() and os.path.getsize(lock_path) == 0:
                lock_path.unlink()
