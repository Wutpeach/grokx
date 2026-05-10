from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "core" / "SKILL.md"

TARGETS = [
    ROOT / "adapters" / "hermes" / "grokx" / "SKILL.md",
    ROOT / "adapters" / "codex" / "grokx" / "SKILL.md",
    ROOT / "adapters" / "claude-plugin" / "skills" / "grokx" / "SKILL.md",
    ROOT / "adapters" / "openclaw" / "workspace" / "skills" / "grokx" / "SKILL.md",
]


def main() -> None:
    core_text = CORE.read_text(encoding="utf-8")
    banner = (
        "<!-- Synced from skill-package/core/SKILL.md. "
        "Platform-specific packaging details may be added below this banner. -->\n\n"
    )
    for target in TARGETS:
        existing = target.read_text(encoding="utf-8") if target.exists() else ""
        marker = "\n## Platform Notes\n"
        platform_notes = ""
        if marker in existing:
            platform_notes = existing.split(marker, 1)[1]
            platform_notes = f"{marker}{platform_notes}"
        target.write_text(f"{banner}{core_text}{platform_notes}", encoding="utf-8")
        print(f"synced {target}")


if __name__ == "__main__":
    main()
