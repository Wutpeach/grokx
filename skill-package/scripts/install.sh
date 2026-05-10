#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

install_hermes() {
  local target="${HOME}/.hermes/skills/grokx"
  mkdir -p "$(dirname "$target")"
  rm -rf "$target"
  cp -R "${ROOT}/adapters/hermes/grokx" "$target"
  echo "Installed Hermes adapter to $target"
}

install_codex() {
  local target="${HOME}/.agents/skills/grokx"
  mkdir -p "$(dirname "$target")"
  rm -rf "$target"
  cp -R "${ROOT}/adapters/codex/grokx" "$target"
  echo "Installed Codex adapter to $target"
}

install_claude() {
  local target="${HOME}/.claude/plugins/local/grokx-skill"
  mkdir -p "$(dirname "$target")"
  rm -rf "$target"
  cp -R "${ROOT}/adapters/claude-plugin" "$target"
  echo "Installed Claude plugin adapter to $target"
}

install_openclaw() {
  local target="${HOME}/.openclaw/workspace/skills/grokx"
  mkdir -p "$(dirname "$target")"
  rm -rf "$target"
  cp -R "${ROOT}/adapters/openclaw/workspace/skills/grokx" "$target"
  echo "Installed OpenClaw adapter to $target"
}

usage() {
  cat <<'EOF'
Usage:
  install.sh hermes
  install.sh codex
  install.sh claude
  install.sh openclaw
  install.sh all
EOF
}

main() {
  local mode="${1:-}"
  case "$mode" in
    hermes) install_hermes ;;
    codex) install_codex ;;
    claude) install_claude ;;
    openclaw) install_openclaw ;;
    all)
      install_hermes
      install_codex
      install_claude
      install_openclaw
      ;;
    *)
      usage
      exit 1
      ;;
  esac
}

main "$@"
