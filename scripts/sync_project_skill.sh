#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILL_ROOT="${ROOT}/skill-package"
SOURCE_DIR="${SKILL_ROOT}/adapters/codex/grokx"
TARGET_DIR="${ROOT}/.agents/skills/grokx"

if [[ ! -f "${SKILL_ROOT}/scripts/sync_from_core.py" ]]; then
  echo "Missing sync source: ${SKILL_ROOT}/scripts/sync_from_core.py" >&2
  exit 1
fi

if [[ ! -f "${SOURCE_DIR}/SKILL.md" ]]; then
  echo "Missing Codex adapter: ${SOURCE_DIR}/SKILL.md" >&2
  exit 1
fi

python3 "${SKILL_ROOT}/scripts/sync_from_core.py"

mkdir -p "$(dirname "${TARGET_DIR}")"
rm -rf "${TARGET_DIR}"
cp -R "${SOURCE_DIR}" "${TARGET_DIR}"

echo "Synced project skill to ${TARGET_DIR}"
