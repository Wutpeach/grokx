# grokx Skill Package

This directory packages `grokx` as a portable multi-platform skill bundle.

## Layout

```text
skill-package/
  core/
  adapters/
    hermes/
    codex/
    claude-plugin/
    openclaw/
  scripts/
```

## Install

```bash
bash skill-package/scripts/install.sh hermes
bash skill-package/scripts/install.sh codex
bash skill-package/scripts/install.sh claude
bash skill-package/scripts/install.sh openclaw
bash skill-package/scripts/install.sh all
```

## Notes

- Hermes adapter installs to `~/.hermes/skills/grokx/`
- Codex adapter installs to `~/.agents/skills/grokx/`
- Claude adapter installs as a local plugin under `~/.claude/plugins/local/grokx-skill/`
- OpenClaw adapter installs to `~/.openclaw/workspace/skills/grokx/`
