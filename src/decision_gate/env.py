"""Load a local .env file into the environment, without a dependency.

Looks in the current directory and then the repository root. Lines are
KEY=VALUE; blank lines and # comments are ignored; surrounding quotes are
stripped. Existing environment variables are never overridden.
"""

from __future__ import annotations

import os
from pathlib import Path


def load_dotenv() -> Path | None:
    candidates = [Path.cwd() / ".env", Path(__file__).resolve().parents[2] / ".env"]
    for path in candidates:
        if not path.is_file():
            continue
        for raw in path.read_text(encoding="utf-8-sig").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip().removeprefix("export ").strip()
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            if key and key not in os.environ:
                os.environ[key] = value
        return path
    return None
