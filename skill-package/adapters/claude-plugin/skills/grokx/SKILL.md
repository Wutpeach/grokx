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

- do not use `grokx` when local tools can answer the question directly
- do not use `grokx` for trivial edits, formatting, or straightforward fact lookup from the local workspace
- prefer `--no-stream` when the caller wants a single captured result
- prefer `--json` when downstream code parses the response
- prefer `ask --session <name>` when the target session is already known
- prefer `resume` when the agent needs to rediscover, list, or reattach to an existing saved session
- prefer named `--session` values for durable threads
- prefer `new` for hard resets
- prefer `side` for branch analysis from an existing saved session
- run `grokx health` before assuming a prompt or model failure

## Prompt Packaging

Before asking Grok for design review, debugging help, or implementation critique, compress the request into a structured prompt instead of dumping raw transcript.

Default packaging shape:

- background
- current objective
- confirmed constraints
- relevant implementation details
- the concrete question Grok should answer

Additional rules:

- do not paste the full shell transcript or full agent conversation unless the task explicitly requires it
- include file paths, function names, or short code excerpts when the question depends on code context
- ask for a bounded output shape when possible, such as risks, options, tradeoffs, or next steps
- prefer one dense well-scoped prompt over several underspecified follow-ups

## Agent Workflow

When an agent uses `grokx` for design review, troubleshooting, or iterative planning, treat Grok consultation as a managed session workflow rather than a series of unrelated one-shot prompts.

### 1. Create a stable main session

For the first Grok consultation on a task, create or choose a durable main session name and keep reusing it for the same task.

Recommended naming shape:

```text
grokx-<repo-or-project>-<task-slug>-main
```

Examples:

```bash
grokx ask --session grokx-myrepo-auth-main --no-stream "Review this implementation plan"
grokx ask --session grokx-myrepo-auth-main --no-stream "Here is the error we hit. Suggest likely causes."
```

Do not switch session names casually during the same task. Reuse the same main session until you intentionally roll the context forward.

### 2. Use `side` for temporary branches

When the agent wants a narrow exploration that should not pollute the main consultation record, use `grokx side`.

`side` only works from an existing saved session. It is not a shortcut for starting a new thread.

Typical cases:

- compare one alternative design
- test an edge-case hypothesis
- ask a narrow debugging question
- challenge the current direction without changing the main thread

Example:

```bash
grokx side grokx-myrepo-auth-main --no-stream "Assume the root cause is state leakage. What evidence would support that?"
```

### 3. Watch for context saturation

Do not keep extending the same Grok session forever. Grok still depends on a bounded replay window, and the highest-quality answers usually come from dense, well-curated context rather than a long raw transcript.

Evaluate whether to roll forward into a new session when any of these are true:

- the main consultation has reached roughly 5 to 8 substantial Grok turns
- the task has accumulated enough detail that older context is becoming important again
- Grok starts repeating itself, drifting, or missing previously established constraints
- the discussion has shifted from broad exploration to converging on a final solution
- the agent has already tried several alternatives and needs a cleaner decision-focused context

Do not treat 5 or 10 turns as a rigid limit. The real signal is context quality, not a fixed count.

### 4. Roll forward with a structured summary

When context saturation is approaching, create a structured summary first, then start a fresh session with that summary as the new anchor context.

The roll-forward summary should include:

- project or task background
- current objective
- confirmed constraints
- relevant implementation details
- options already considered
- why rejected options failed
- the strongest remaining candidate solution
- unresolved questions that Grok should focus on next

The summary should be compressed, factual, and decision-oriented. Do not dump the whole transcript back into the next session.

Example pattern:

```bash
grokx new --session grokx-myrepo-auth-main-r2 --no-stream "Context summary:
Project: auth refactor for myrepo.
Goal: make token refresh race-safe.
Constraints: cannot change external API; Redis is available; background workers are not.
Tried: optimistic locking only, rejected because concurrent refreshes still duplicate writes.
Tried: per-user in-memory lock, rejected because app runs on multiple instances.
Current best option: Redis-based short TTL lock plus idempotent refresh write path.
Open questions: failure recovery, lock expiry tuning, and whether a compare-and-swap write is still needed.
Please critique this candidate design and identify the main failure modes."
```

### 5. Keep session lineage explicit

When rolling forward, use a visible lineage in the session name rather than overwriting the old thread immediately.

Recommended progression:

```text
grokx-myrepo-auth-main
grokx-myrepo-auth-main-r2
grokx-myrepo-auth-main-r3
```

This preserves the research trail while letting the active consultation move into a cleaner context window.

Only use `grokx new --force` on an existing session name when the old thread is no longer useful and the agent intentionally wants to replace it.

### 6. Default decision policy for agents

Use this decision order:

1. If local tools can answer the question directly, do not call `grokx`.
2. If the task has no existing Grok consultation thread, start or select a main named session.
3. If the target session is already known and the task is continuing the same line of reasoning, use `ask --session <name>`.
4. If the agent needs to find or reattach to an older saved thread, use `resume`.
5. If the question is exploratory and should not modify the main consultation history, use `side`.
6. If the main consultation context is getting diluted, summarize and `new` a successor session.
7. If the entire previous line of thought should be discarded, use `new --force`.

## Output Consumption

Use output mode intentionally:

- prefer `--no-stream` when the agent needs one complete answer to inspect or quote
- prefer `--json` when another tool, script, or parser will consume the result
- prefer plain streaming output only for interactive human reading or live monitoring
- if the agent needs both persistence and machine-readable output, combine `--session` with `--no-stream` or `--json`

## Troubleshooting

If `grokx` fails:

1. Run `grokx health`
2. Run `grokx session list` if the failure involves saved context or missing session state
3. Run `grokx model list --all` if the failure may involve model availability or chat capability
4. Confirm `grok2api` is reachable at `GROKX_BASE_URL`
5. Confirm `GROKX_API_KEY` is valid

If named conversations behave unexpectedly:

```bash
grokx session list
grokx session clear <name>
```

## References

- For environment variables and path discovery, read `references/configuration.md`
- For packaging rules across platforms, read `references/platform-packaging.md`

## Platform Notes

This adapter targets Claude Code plugin packaging.

Expected plugin structure:

```text
.claude-plugin/plugin.json
skills/grokx/SKILL.md
```

Project-local alternative:

```text
.claude/skills/grokx/SKILL.md
```
