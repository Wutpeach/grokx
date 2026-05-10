# grokx

`grokx` is a small CLI for talking to a `grok2api` service from a terminal.

It is designed for a simple workflow:

- keep `grok2api` as its own service
- install `grokx` as a separate CLI
- call `grokx ask ...` from a shell, scripts, Codex CLI, Claude CLI, or Hermes

## Features

- `grokx ask "..."` streams a reply from Grok
- `grokx ask --session <name> "..."` continues a named multi-turn conversation
- `grokx new` or `grokx /new` starts a fresh conversation without carrying over prior chat context
- `grokx side` or `grokx /side` asks a temporary branch question from a saved session without altering the main thread
- `grokx resume` or `grokx /resume` lists saved sessions and continues one without starting over
- `grokx model current|list|set` inspects or changes the default model
- `grokx model list` probes each listed model and shows chat-capable ones by default
- `grokx health` checks service health, model listing, and optional chat/model round-trips
- `grokx session list|clear` manages saved local sessions

## Install

### From GitHub

```bash
python -m pip install git+https://github.com/Wutpeach/grokx.git
```

### From a local checkout

```bash
git clone https://github.com/Wutpeach/grokx.git
cd grokx
python -m pip install .
```

### Editable install for development

```bash
git clone https://github.com/Wutpeach/grokx.git
cd grokx
python -m pip install -e .
```

### Development setup with uv

```bash
git clone https://github.com/Wutpeach/grokx.git
cd grokx
uv venv
uv sync --extra dev
source .venv/bin/activate
```

Check the command:

```bash
grokx --help
```

## Skill Install

This repo also ships a portable multi-platform skill bundle under:

```text
skill-package/
```

Current adapters:

- Hermes Agent
- Codex
- Claude Code
- OpenClaw-style workspace layout

Use the bundled installer:

```bash
bash skill-package/scripts/install.sh hermes
bash skill-package/scripts/install.sh codex
bash skill-package/scripts/install.sh claude
bash skill-package/scripts/install.sh openclaw
bash skill-package/scripts/install.sh all
```

Default install targets:

- Hermes: `~/.hermes/skills/grokx/`
- Codex: `~/.agents/skills/grokx/`
- Claude Code plugin: `~/.claude/plugins/local/grokx-skill/`
- OpenClaw: `~/.openclaw/workspace/skills/grokx/`

If you update the shared core skill content, resync the platform adapters with:

```bash
python3 skill-package/scripts/sync_from_core.py
```

To resync the project-local Codex skill in this repo, run `./scripts/sync_project_skill.sh`.

## Requirements

`grokx` talks to a running `grok2api` service.

The default target is:

```text
http://127.0.0.1:8000/v1
```

Typical local `grok2api` layout:

```text
/path/to/grok2api/
  .env
  data/config.toml
  data/accounts.db
```

`grokx` can auto-discover:

- `~/services/grok2api`
- `./grok2api`

## Quick Start

Set the minimum variables you need:

```bash
export GROKX_BASE_URL=http://127.0.0.1:8000/v1
export GROKX_API_KEY=your_grok2api_api_key
```

Ask a question:

```bash
grokx ask "Summarize the tradeoffs of this architecture"
```

Run a health check:

```bash
grokx health
```

List available models:

```bash
grokx model list
```

Show every listed model with probe status:

```bash
grokx model list --all
```

## Configuration

### Recommended local setup

Point `grokx` at your `grok2api` directory:

```bash
export GROKX_GROK2API_DIR=/absolute/path/to/grok2api
```

From that directory, `grokx` can derive:

- `.env`
- `data/config.toml`
- `data/accounts.db`
- `GROK_APP_API_KEY`
- `GROK_APP_APP_KEY`

### Environment Variables

| Variable | Purpose |
|---|---|
| `GROKX_BASE_URL` | OpenAI-compatible base URL, default `http://127.0.0.1:8000/v1` |
| `GROKX_API_KEY` | API key for `/v1/*` requests |
| `GROKX_MODEL` | Default model, default `grok-4.20-auto` |
| `GROKX_TIMEOUT` | Request timeout in seconds |
| `GROKX_CONFIG_PATH` | JSON config path for persistent CLI settings |
| `GROKX_SESSIONS_DIR` | Session storage directory, default `~/.config/grokx/sessions` |
| `GROKX_SESSION_TURN_LIMIT` | Number of recent turns replayed into the model, default `12` |
| `GROKX_GROK2API_DIR` | Root directory of a local `grok2api` install |
| `GROKX_GROK2API_ENV` | Explicit path to the `grok2api` `.env` file |
| `GROKX_GROK2API_CONFIG` | Explicit path to `config.toml` |
| `GROKX_GROK2API_DB` | Explicit path to `accounts.db` |

## Usage

### Ask Grok

```bash
grokx ask "Review this plan"
```

Streaming is the default behavior. Use `--no-stream` to wait for a full reply:

```bash
grokx ask "Review this plan" --no-stream
```

Use a specific model:

```bash
grokx ask "Review this plan" --model grok-4.20-expert
```

Return raw JSON:

```bash
grokx ask "Reply with OK" --json
```

### Persistent Sessions

Create or continue a named conversation:

```bash
grokx ask "记住：这个仓库用 Python" --session repo-help --system "你是一个严谨的代码助手"
grokx ask "继续，帮我列出重构步骤" --session repo-help
```

Session data is stored under `~/.config/grokx/sessions` unless you override it with `GROKX_SESSIONS_DIR`.

Manage saved sessions:

```bash
grokx session list
grokx session clear repo-help
```

Start a fresh conversation in the same repo without reusing previous chat context:

```bash
grokx new "从零开始审查这个问题"
grokx new --session repo-reset "重新开始，我们换个思路"
grokx /new --session repo-reset --force "清空旧上下文，开始新对话"
```

Resume from the saved-session list without starting a new conversation:

```bash
grokx resume
grokx resume repo-help "继续，帮我把刚才的方案补完整"
grokx /resume repo-help "继续处理上一次的问题"
```

Ask a side question from an existing session without writing that branch back into the main conversation:

```bash
grokx side
grokx side repo-help "只讨论一下测试策略，不要改主线程上下文"
grokx /side repo-help "先单独推演一下这个 edge case"
```

### Model Management

Show the current default model:

```bash
grokx model current
```

List models from `grok2api`:

```bash
grokx model list
```

By default, `grokx model list` only prints models that successfully complete a chat request.
Use `--all` to include failures with their probe status, or `--json` for structured output:

```bash
grokx model list --all
grokx model list --json
```

`grokx model list` also refreshes a local probe cache. After that, `grokx model set <model>` only accepts models that are present in the cache and marked chat-capable, which keeps known-bad models out of your default selection.

Persist a new default model:

```bash
grokx model set grok-4.20-expert
```

By default, this is stored in:

```text
~/.config/grokx/config.json
```

### Health Checks

```bash
grokx health
grokx health --with-chat
grokx health --probe-models
grokx health --with-chat --probe-models
grokx health --with-chat --json
```

When you use `--probe-models`, the probe results are written into the local `grokx` config so later `model set` calls can reject models that previously failed.

## Typical Workflows

### Use from a shell

```bash
grokx ask "Give me a second opinion on this approach"
```

### Use with stdin

```bash
cat plan.md | grokx ask "Review this plan and list the main risks"
```

### Use from another agent CLI

Call `grokx ask ...` as a subprocess from Codex CLI, Claude CLI, Hermes, or any shell-driven workflow.

## Development

Run tests:

```bash
pytest -q
```

Build a wheel:

```bash
python -m build
```

If you use `uv`, a typical local development loop is:

```bash
cd grokx
source .venv/bin/activate
pytest -q
```

## License

MIT
