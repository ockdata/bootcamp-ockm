#!/usr/bin/env python3
"""
PreToolUse hook for Claude Code: runs tfsec on proposed .tf edits.

Receives JSON on stdin with tool_name and tool_input.
Reconstructs the file after the proposed edit, scans with tfsec,
and exits 2 (block) if security issues are found.

Exit codes:
  0 = allow (not a .tf file, or no issues found)
  2 = block (tfsec found security issues)
  1 = hook error (fails closed — blocks on unexpected errors)
"""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> int:
    try:
        raw_input = sys.stdin.read()
        payload = json.loads(raw_input)
    except (json.JSONDecodeError, Exception) as e:
        print(f"BLOCKED: tfsec hook failed to parse input: {e}", file=sys.stderr)
        return 1

    tool_input = payload.get("tool_input", {})
    file_path = tool_input.get("file_path", "")

    if not file_path.endswith(".tf"):
        return 0

    file_path = Path(file_path)
    infra_dir = file_path.parent
    tool_name = payload.get("tool_name", "")

    scan_dir = Path(tempfile.mkdtemp(prefix="tfsec_hook_"))
    try:
        # Reconstruct the file content after the proposed edit
        if tool_name == "Write":
            content = tool_input.get("content", "")
            (scan_dir / file_path.name).write_text(content)

        elif tool_name == "Edit":
            old_string = tool_input.get("old_string", "")
            new_string = tool_input.get("new_string", "")

            if not file_path.exists():
                print(f"BLOCKED: tfsec hook cannot read {file_path}", file=sys.stderr)
                return 1

            original = file_path.read_text()

            if old_string not in original:
                print(
                    f"BLOCKED: tfsec hook — old_string not found in {file_path.name}. "
                    "Cannot reconstruct file for scanning.",
                    file=sys.stderr,
                )
                return 1

            if tool_input.get("replace_all", False):
                reconstructed = original.replace(old_string, new_string)
            else:
                reconstructed = original.replace(old_string, new_string, 1)

            (scan_dir / file_path.name).write_text(reconstructed)
        else:
            return 0

        # Copy other .tf files so tfsec can resolve references
        if infra_dir.is_dir():
            for tf_file in infra_dir.glob("*.tf"):
                if tf_file.name != file_path.name:
                    shutil.copy2(tf_file, scan_dir / tf_file.name)

        # Also copy modules directory if it exists (for module references)
        modules_dir = infra_dir / "modules"
        if modules_dir.is_dir():
            shutil.copytree(modules_dir, scan_dir / "modules")

        # Run tfsec
        tfsec_bin = shutil.which("tfsec")
        if not tfsec_bin:
            print(
                "BLOCKED: tfsec not found in PATH. "
                "Install it: brew install tfsec",
                file=sys.stderr,
            )
            return 1

        result = subprocess.run(
            [tfsec_bin, str(scan_dir), "--no-color", "--soft-fail"],
            capture_output=True,
            text=True,
            timeout=25,
        )

        output = result.stdout + result.stderr

        if "potential problem(s) detected" in output:
            print(
                "BLOCKED: tfsec found security issues in proposed Terraform changes:\n",
                file=sys.stderr,
            )
            print(output, file=sys.stderr)
            return 2

        return 0

    except subprocess.TimeoutExpired:
        print("BLOCKED: tfsec hook timed out after 25s", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"BLOCKED: tfsec hook unexpected error: {e}", file=sys.stderr)
        return 1
    finally:
        shutil.rmtree(scan_dir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
