# grokx Configuration

## Environment Variables

| Variable | Purpose |
|---|---|
| `GROKX_BASE_URL` | OpenAI-compatible base URL, default `http://127.0.0.1:8000/v1` |
| `GROKX_API_KEY` | API key for `/v1/*` requests |
| `GROKX_MODEL` | Default model |
| `GROKX_TIMEOUT` | Request timeout in seconds |
| `GROKX_CONFIG_PATH` | JSON config path for persistent local settings |
| `GROKX_SESSIONS_DIR` | Session storage directory |
| `GROKX_SESSION_TURN_LIMIT` | Number of recent turns replayed into the model |
| `GROKX_GROK2API_DIR` | Root directory of a local `grok2api` install |
| `GROKX_GROK2API_ENV` | Explicit path to the `grok2api` `.env` file |
| `GROKX_GROK2API_CONFIG` | Explicit path to `config.toml` |
| `GROKX_GROK2API_DB` | Explicit path to `accounts.db` |

## Typical Local Layout

```text
/path/to/grok2api/
  .env
  data/config.toml
  data/accounts.db
```

`grokx` can auto-discover:

- `~/services/grok2api`
- `./grok2api`
