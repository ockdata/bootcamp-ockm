#!/usr/bin/env python3
"""
PostToolUse hook for Claude Code: appends a changelog entry to README.md
whenever a file in the repo is edited or created.

Receives JSON on stdin with tool_name, tool_input, and tool_response.
Appends an entry under a '## Changelog' section at the end of README.md.

Exit codes:
  0 = success (always — post hooks should not block)
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
README_PATH = REPO_ROOT / "README.md"

CHANGELOG_HEADER = "## Changelog"


def _relative_path(file_path: str) -> str:
    """Return path relative to repo root, or the original if outside."""
    try:
        return str(Path(file_path).resolve().relative_to(REPO_ROOT))
    except ValueError:
        return file_path


def _detect_action(tool_name: str, tool_input: dict, rel_path: str) -> str:
    """Build a human-readable description of the change."""
    if tool_name == "Write":
        return f"Criado/sobrescrito `{rel_path}`"

    if tool_name == "Edit":
        old = tool_input.get("old_string", "")
        new = tool_input.get("new_string", "")
        replace_all = tool_input.get("replace_all", False)

        if not old and new:
            return f"Conteúdo adicionado em `{rel_path}`"
        if old and not new:
            return f"Conteúdo removido de `{rel_path}`"

        action = "Substituição global" if replace_all else "Edição"
        return f"{action} em `{rel_path}`"

    return f"Modificação em `{rel_path}`"


def _ensure_changelog_section(readme_text: str) -> str:
    """Ensure the README has a Changelog section at the end."""
    if CHANGELOG_HEADER not in readme_text:
        readme_text = readme_text.rstrip() + f"\n\n---\n\n{CHANGELOG_HEADER}\n\n"
    return readme_text


def main() -> int:
    try:
        payload = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, Exception):
        return 0  # post hooks should not block

    tool_input = payload.get("tool_input", {})
    tool_name = payload.get("tool_name", "")
    file_path = tool_input.get("file_path", "")

    if not file_path:
        return 0

    # Don't log changes to README.md itself (avoid infinite loop)
    rel_path = _relative_path(file_path)
    if rel_path == "README.md":
        return 0

    # Don't log changes to hidden/config files
    if rel_path.startswith("."):
        return 0

    description = _detect_action(tool_name, tool_input, rel_path)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    entry = f"- **[{timestamp}]** {description}"

    try:
        readme_text = README_PATH.read_text() if README_PATH.exists() else ""
        readme_text = _ensure_changelog_section(readme_text)

        # Insert the new entry right after the changelog header
        header_idx = readme_text.index(CHANGELOG_HEADER)
        insert_pos = header_idx + len(CHANGELOG_HEADER)

        # Skip any whitespace after the header
        while insert_pos < len(readme_text) and readme_text[insert_pos] in ("\n", " "):
            insert_pos += 1

        # Insert new entry at the top of the changelog (most recent first)
        readme_text = (
            readme_text[:header_idx]
            + CHANGELOG_HEADER
            + "\n\n"
            + entry
            + "\n"
            + readme_text[insert_pos:]
        )

        README_PATH.write_text(readme_text)
    except Exception:
        return 0  # post hooks should not block

    return 0


if __name__ == "__main__":
    sys.exit(main())
