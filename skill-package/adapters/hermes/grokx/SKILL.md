<!-- Synced from skill-package/core/SKILL.md. Platform-specific packaging details may be added below this banner. -->

---
name: grokx
description: Use the grokx CLI to talk to a local grok2api service from shell workflows, scripts, and agent sessions. Use when the task needs `grokx ask`, named sessions, side-thread questions, model probing, or grok2api health checks.
version: 1.0.0
author: Mabel
license: MIT
---

# grokx Core

`grokx` is a portable CLI for talking to a local `grok2api` service.

This core skill is the shared source for multiple agent platforms. Platform adapters should keep only platform-specific packaging and discovery details, while this file remains the source of truth for command behavior.

## Use Cases

Use `grokx` when you need:

- one-shot prompts with `grokx ask`
- persistent named conversations with `--session`
- fresh resets with `grokx new` or `/new`
- side-branch exploration with `grokx side` or `/side`
- saved-session continuation with `grokx resume` or `/resume`
- model probing and default-model management
- local `grok2api` health checks

## Prerequisites

- `grokx` is installed and available on `PATH`
- a reachable `grok2api` service exists
- configuration is provided through either:
  - `GROKX_BASE_URL` and `GROKX_API_KEY`
  - or `GROKX_GROK2API_DIR`

Recommended local discovery:

```bash
export GROKX_GROK2API_DIR=~/services/grok2api
```

Direct configuration:

```bash
export GROKX_BASE_URL=http://127.0.0.1:8000/v1
export GROKX_API_KEY=your_grok2api_api_key
```

## Core Commands

Ask Grok:

```bash
grokx ask "Review this plan"
grokx ask --model grok-4.20-expert "Review this plan"
grokx ask --no-stream "Return the final answer only"
grokx ask --json "Reply with OK"
```

Use named context:

```bash
grokx ask --session repo-help "记住：这个仓库用 Python"
grokx ask --session repo-help "继续，帮我列出重构步骤"
```

Start fresh:

```bash
grokx new "从零开始审查这个问题"
grokx new --session repo-reset "重新开始，我们换个思路"
grokx /new --session repo-reset --force "清空旧上下文，开始新对话"
```

Ask side questions without mutating the main thread:

```bash
grokx side repo-help "只讨论测试策略，不要改主线程上下文"
grokx /side repo-help "先单独推演一下这个 edge case"
```

Resume a saved session:

```bash
grokx resume
grokx resume repo-help "继续，帮我把刚才的方案补完整"
grokx /resume repo-help "继续处理上一次的问题"
```

## Model Workflow

```bash
grokx model current
grokx model list
grokx model list --all
grokx model list --json
grokx model set grok-4.20-expert
```

Recommended sequence:

1. Run `grokx model list`
2. Confirm the model is chat-capable
3. Run `grokx model set <model>`

The CLI caches probe results in the local `grokx` config.

## Health Workflow

```bash
grokx health
grokx health --with-chat
grokx health --probe-models
grokx health --with-chat --probe-models --json
```

## Sessions

```bash
grokx session list
grokx session clear repo-help
```

Default local paths:

- config: `~/.config/grokx/config.json`
- sessions: `~/.config/grokx/sessions`

## Agent Guidance

- prefer `--no-stream` when the caller wants a single captured result
- prefer `--json` when downstream code parses the response
- prefer named `--session` values for durable threads
- prefer `new` for hard resets
- prefer `side` for branch analysis
- run `grokx health` before assuming a prompt or model failure

## Troubleshooting

If `grokx` fails:

1. Run `grokx health`
2. Confirm `grok2api` is reachable at `GROKX_BASE_URL`
3. Confirm `GROKX_API_KEY` is valid
4. Run `grokx model list --all`

If named conversations behave unexpectedly:

```bash
grokx session list
grokx session clear <name>
```

## References

- For environment variables and path discovery, read `references/configuration.md`
- For packaging rules across platforms, read `references/platform-packaging.md`

## Platform Notes

This adapter targets Hermes Agent.

Preferred install locations:

- `~/.hermes/skills/grokx/`
- `~/.hermes/skills/autonomous-ai-agents/grokx/`

Hermes discovery is based on `SKILL.md`, so this directory can be copied directly into the Hermes skills tree.
