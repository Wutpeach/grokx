# Platform Packaging

## Hermes Agent

- install location: `~/.hermes/skills/<category-or-flat>/grokx/SKILL.md`
- core artifact: `SKILL.md`

## Codex

- install location: `~/.agents/skills/grokx/SKILL.md`
- compatible fallback location in some setups: `~/.codex/skills/grokx/SKILL.md`
- optional UI metadata: `agents/openai.yaml`

## Claude Code

- project-local skill: `.claude/skills/grokx/SKILL.md`
- plugin-packaged skill: plugin root `skills/grokx/SKILL.md`
- plugin manifest: `.claude-plugin/plugin.json`

## OpenCode / OpenClaw-family layout

- personal skill location used by OpenCode-style discovery: `~/.config/opencode/skills/grokx/SKILL.md`
- project skill location: `.opencode/skills/grokx/SKILL.md`
- OpenClaw migration docs indicate historical skill sources such as:
  - `~/.openclaw/skills/`
  - `workspace/skills/`
  - `~/.agents/skills/`
  - `workspace/.agents/skills/`

For a portable package, a conservative adapter is `workspace/skills/grokx/SKILL.md`.
