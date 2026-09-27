"""Write the OpenAPI schema to a file without starting the server or a database.

    uv run python -m app.scripts.export_openapi ../frontend/openapi.json

The frontend turns this into TypeScript types (`npm run gen:api`).
"""

import json
import sys
from pathlib import Path

from app.main import app


def main() -> None:
    target = Path(sys.argv[1] if len(sys.argv) > 1 else "openapi.json")
    # newline="\n": identical output on Windows and Linux, so CI's staleness check is stable.
    target.write_text(json.dumps(app.openapi(), indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"Wrote {target}")


if __name__ == "__main__":
    main()
