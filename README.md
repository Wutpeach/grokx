# grokx

`grokx` is a small CLI for talking to a `grok2api` service from a terminal.

It is designed for a simple workflow:

- keep `grok2api` as its own service
- install `grokx` as a separate CLI
- call `grokx ask ...` from a shell, scripts, Codex CLI, Claude CLI, or Hermes

## Features

- `grokx ask "..."` streams a reply from Grok
- `grokx ask --session <name> "..."` continues a named multi-turn conversation
- `grokx model current|list|set` inspects or changes the default model
- `grokx health` checks service health, model listing, and an optional chat round-trip
- `grokx clearance set <cf_clearance>` updates `grok2api` local clearance config
- `grokx probe all` runs a read-only batch refresh across the local account pool
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

Check the command:

```bash
grokx --help
```

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
| `GROKX_APP_KEY` | Admin key for `/admin/api/*` routes |
| `GROKX_GROK2API_DIR` | Root directory of a local `grok2api` install |
| `GROKX_GROK2API_ENV` | Explicit path to the `grok2api` `.env` file |
| `GROKX_GROK2API_CONFIG` | Explicit path to `config.toml` |
| `GROKX_GROK2API_DB` | Explicit path to `accounts.db` |
| `GROKX_RESTART_CMD` | Optional shell command to restart `grok2api` after config changes |

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

### Model Management

Show the current default model:

```bash
grokx model current
```

List models from `grok2api`:

```bash
grokx model list
```

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
grokx health --with-chat --json
```

### Clearance Management

Update `cf_clearance` in the local `grok2api` config:

```bash
grokx clearance set '<cf_clearance>'
```

Update clearance and user-agent together:

```bash
grokx clearance set '<cf_clearance>' --user-agent 'Mozilla/5.0 ...'
```

Restart `grok2api` after the config update:

```bash
grokx clearance set '<cf_clearance>' --restart
```

### Pool Probing

Run a read-only batch refresh across active accounts:

```bash
grokx probe all
grokx probe all --concurrency 5 --json
```

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

## License

MIT
