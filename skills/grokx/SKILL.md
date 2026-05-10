---
name: grokx
description: Use the local grokx CLI to talk to a grok2api service from terminal workflows, scripts, and agent sessions. Use when the task needs `grokx ask`, persistent named sessions, side-branch questions, model probing, or grok2api health checks.
version: 0.1.0
author: Mabel
license: MIT
---

# grokx

`grokx` is a portable CLI for talking to a local `grok2api` service.

Use this skill when you want Grok available inside shell-driven workflows, especially for:

- one-shot prompts with `grokx ask`
- persistent named conversations with `--session`
- fresh resets with `grokx new` or `/new`
- temporary branch questions with `grokx side` or `/side`
- saved-session continuation with `grokx resume` or `/resume`
- model probing and default-model management
- local `grok2api` health checks

## Prerequisites

- `grokx` is installed and available on `PATH`, or you are inside this repo and can run the local editable install
- a `grok2api` service is running
- environment is configured through either:
  - `GROKX_BASE_URL` and `GROKX_API_KEY`
  - or `GROKX_GROK2API_DIR` pointing at a local `grok2api` checkout

Typical local target:

```bash
export GROKX_BASE_URL=http://127.0.0.1:8000/v1
export GROKX_API_KEY=your_grok2api_api_key
```

Recommended local discovery:

```bash
export GROKX_GROK2API_DIR=~/services/grok2api
```

## Core Commands

Ask Grok:

```bash
grokx ask "Review this plan"
grokx ask --model grok-4.20-expert "Review this plan"
grokx ask --no-stream "Return the final answer only"
grokx ask --json "Reply with OK"
```

Use persistent named context:

```bash
grokx ask --session repo-help "记住：这个仓库用 Python"
grokx ask --session repo-help "继续，帮我列出重构步骤"
```

Start fresh without carrying old context:

```bash
grokx new "从零开始审查这个问题"
grokx new --session repo-reset "重新开始，我们换个思路"
grokx /new --session repo-reset --force "清空旧上下文，开始新对话"
```

Ask a side question without mutating the main saved session:

```bash
grokx side
grokx side repo-help "只讨论一下测试策略，不要改主线程上下文"
grokx /side repo-help "先单独推演一下这个 edge case"
```

Resume a saved session:

```bash
grokx resume
grokx resume repo-help "继续，帮我把刚才的方案补完整"
grokx /resume repo-help "继续处理上一次的问题"
```

## Model Workflow

Inspect and manage the default model:

```bash
grokx model current
grokx model list
grokx model list --all
grokx model list --json
grokx model set grok-4.20-expert
```

Recommended pattern:

1. Run `grokx model list`
2. Confirm the model is chat-capable
3. Run `grokx model set <model>`

This CLI caches model probe results in the local `grokx` config.

## Health Workflow

Use health checks before debugging prompts:

```bash
grokx health
grokx health --with-chat
grokx health --probe-models
grokx health --with-chat --probe-models --json
```

## Sessions

List and clear saved sessions:

```bash
grokx session list
grokx session clear repo-help
```

Default local paths:

- config: `~/.config/grokx/config.json`
- sessions: `~/.config/grokx/sessions`

## Good Usage Patterns

Use `grokx ask` for one-shot analysis inside scripts:

```bash
cat plan.md | grokx ask "Review this plan and list the main risks"
```

Use `--session` when the prompt depends on prior turns:

```bash
grokx ask --session refactor-log "记住我们决定保留 sqlite"
grokx ask --session refactor-log "基于刚才的约束，重写迁移方案"
```

Use `side` when you want exploration without polluting the main thread:

```bash
grokx side refactor-log "单独推演一下回滚策略"
```

## Agent Guidance

For agent workflows:

- prefer `--no-stream` when the caller wants a single captured result
- prefer `--json` when downstream code parses the response
- prefer named `--session` values for durable task threads
- prefer `new` for hard resets and `side` for branch analysis
- run `grokx health` before assuming prompt or model failures

## Troubleshooting

If `grokx` fails:

1. Run `grokx health`
2. Confirm `grok2api` is reachable at `GROKX_BASE_URL`
3. Confirm `GROKX_API_KEY` is valid
4. Run `grokx model list --all` to inspect probe results

If named conversations behave unexpectedly, inspect and clear saved local sessions:

```bash
grokx session list
grokx session clear <name>
```
