"""PreToolUse hook: block edits that break repo rules.

- Real .env files hold secrets and are never edited by Claude (only *.env.example).
- Migrations that are already committed must never change: other databases
  (teammates, CI, client installs) have already applied them. Add a new one.

Exit code 2 blocks the tool call and shows the message to Claude.
"""

import json
import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    file_path = payload.get("tool_input", {}).get("file_path")
    if not file_path:
        return 0

    path = Path(file_path)
    name = path.name

    if (name == ".env" or name.startswith(".env.")) and name != ".env.example":
        print(
            f"Blocked: {name} holds secrets and must not be edited by Claude. "
            "Update the matching .env.example instead and tell the user what to set.",
            file=sys.stderr,
        )
        return 2

    parts = path.parts
    if "migrations" in parts and "versions" in parts and path.suffix == ".py":
        project = Path(os.environ.get("CLAUDE_PROJECT_DIR", "."))
        try:
            rel = path.resolve().relative_to(project.resolve()).as_posix()
        except ValueError:
            return 0
        committed = subprocess.run(  # noqa: S603
            ["git", "-C", str(project), "cat-file", "-e", f"HEAD:{rel}"],  # noqa: S607
            capture_output=True,
            check=False,
        )
        if committed.returncode == 0:
            print(
                f"Blocked: {rel} is already committed and may be applied on other databases. "
                "Create a new migration instead (see the db-migration skill).",
                file=sys.stderr,
            )
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
