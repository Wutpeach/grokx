from __future__ import annotations

import json
from collections.abc import Iterator
from urllib import error, request

from .config import Settings


class GrokxClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.settings.api_key:
            headers["Authorization"] = f"Bearer {self.settings.api_key}"
        return headers

    def _json_request(self, url: str, payload: dict | None = None) -> dict:
        data = None if payload is None else json.dumps(payload).encode()
        req = request.Request(url, data=data, headers=self._headers(), method="POST" if payload is not None else "GET")
        try:
            with request.urlopen(req, timeout=self.settings.timeout) as resp:
                body = resp.read().decode() or "{}"
                return json.loads(body)
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", "replace")
            raise RuntimeError(f"HTTP {exc.code}: {body[:300]}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"Connection failed: {exc.reason}") from exc

    def _stream_request(self, url: str, payload: dict) -> Iterator[dict]:
        data = json.dumps(payload).encode()
        req = request.Request(url, data=data, headers=self._headers(), method="POST")
        try:
            with request.urlopen(req, timeout=self.settings.timeout) as resp:
                for raw_line in resp:
                    line = raw_line.decode("utf-8", "replace").strip()
                    if not line or line.startswith(":"):
                        continue
                    if not line.startswith("data:"):
                        continue
                    data_text = line.removeprefix("data:").strip()
                    if data_text == "[DONE]":
                        break
                    event = json.loads(data_text)
                    if "error" in event:
                        raise RuntimeError(event["error"].get("message", str(event["error"])))
                    yield event
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", "replace")
            raise RuntimeError(f"HTTP {exc.code}: {body[:300]}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"Connection failed: {exc.reason}") from exc

    def _chat_payload(
        self,
        prompt: str | None = None,
        *,
        model: str | None = None,
        system: str | None = None,
        stream: bool,
        messages: list[dict[str, str]] | None = None,
    ) -> dict:
        resolved_messages: list[dict[str, str]]
        if messages is not None:
            resolved_messages = list(messages)
        else:
            if prompt is None:
                raise ValueError("prompt is required when messages are not provided")
            resolved_messages = []
            if system:
                resolved_messages.append({"role": "system", "content": system})
            resolved_messages.append({"role": "user", "content": prompt})
        return {
            "model": model or self.settings.model,
            "stream": stream,
            "messages": resolved_messages,
        }

    def ask(
        self,
        prompt: str | None = None,
        *,
        model: str | None = None,
        system: str | None = None,
        messages: list[dict[str, str]] | None = None,
    ) -> dict:
        payload = self._chat_payload(prompt, model=model, system=system, stream=False, messages=messages)
        response = self._json_request(f"{self.settings.base_url}/chat/completions", payload)
        text = ((response.get("choices") or [{}])[0].get("message") or {}).get("content", "")
        return {"text": text, "raw": response}

    def ask_stream(
        self,
        prompt: str | None = None,
        *,
        model: str | None = None,
        system: str | None = None,
        messages: list[dict[str, str]] | None = None,
    ) -> Iterator[str]:
        payload = self._chat_payload(prompt, model=model, system=system, stream=True, messages=messages)
        for event in self._stream_request(f"{self.settings.base_url}/chat/completions", payload):
            choice = (event.get("choices") or [{}])[0]
            delta = choice.get("delta") or {}
            content = delta.get("content")
            if content:
                yield content

    def list_models(self) -> list[dict]:
        payload = self._json_request(f"{self.settings.base_url}/models")
        data = payload.get("data", [])
        return data if isinstance(data, list) else []

    def probe_model(self, model_id: str) -> dict:
        try:
            ask_result = self.ask("Reply with OK", model=model_id)
        except RuntimeError as exc:
            return {"id": model_id, "chat_ok": False, "error": str(exc)}
        text = ask_result["text"].strip()
        if not text:
            return {"id": model_id, "chat_ok": False, "error": "Empty response"}
        return {"id": model_id, "chat_ok": True, "error": ""}

    def probe_models(self, models: list[dict] | None = None) -> list[dict]:
        model_items = models if models is not None else self.list_models()
        results: list[dict] = []
        for item in model_items:
            model_id = item.get("id")
            if not model_id:
                continue
            result = dict(item)
            result.update(self.probe_model(model_id))
            results.append(result)
        return results

    def health(self, *, include_chat: bool = False, include_model_probes: bool = False) -> dict:
        base = self.settings.base_url.removesuffix("/v1")
        health_payload = self._json_request(f"{base}/health")
        models_payload = self._json_request(f"{self.settings.base_url}/models")
        model_items = models_payload.get("data", [])
        result = {
            "health": health_payload.get("status", "unknown"),
            "models_ok": isinstance(model_items, list),
            "model_count": len(model_items if isinstance(model_items, list) else []),
            "chat_ok": False,
        }
        if include_chat:
            ask_result = self.ask("Reply with exactly OK")
            result["chat_ok"] = ask_result["text"].strip() == "OK"
        if include_model_probes and isinstance(model_items, list):
            model_probes = self.probe_models(model_items)
            result["usable_model_count"] = sum(1 for item in model_probes if item.get("chat_ok"))
            result["model_probes"] = model_probes
        return result


def build_client(settings: Settings) -> GrokxClient:
    return GrokxClient(settings)
