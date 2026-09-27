"""PostToolUse hook: auto-format the file Claude just edited.

Python -> ruff (fix + format), frontend files -> prettier.
Never fails the edit: formatting problems surface later in lint/CI.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

PRETTIER_EXTENSIONS = {".ts", ".tsx", ".js", ".jsx", ".css", ".json", ".html", ".md"}


def run(args: list[str], cwd: Path) -> None:
    try:
        subprocess.run(args, cwd=cwd, capture_output=True, timeout=60, check=False)  # noqa: S603
    except (OSError, subprocess.TimeoutExpired):
        pass


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    file_path = payload.get("tool_input", {}).get("file_path")
    if not file_path:
        return 0

    project = Path(os.environ.get("CLAUDE_PROJECT_DIR", ".")).resolve()
    path = Path(file_path).resolve()
    backend, frontend = project / "backend", project / "frontend"
    npx = "npx.cmd" if os.name == "nt" else "npx"

    if path.suffix == ".py" and backend in path.parents:
        run(["uv", "run", "ruff", "check", "--fix", "--quiet", str(path)], backend)
        run(["uv", "run", "ruff", "format", "--quiet", str(path)], backend)
    elif path.suffix in PRETTIER_EXTENSIONS and frontend in path.parents:
        if "node_modules" not in path.parts:
            run([npx, "prettier", "--write", "--log-level", "silent", str(path)], frontend)
    return 0


if __name__ == "__main__":
    sys.exit(main())
