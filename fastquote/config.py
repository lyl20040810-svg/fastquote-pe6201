"""Configuration loading without external dependencies."""

from __future__ import annotations

import os
from pathlib import Path


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def openrouter_settings(project_root: Path) -> tuple[str, str]:
    load_dotenv(project_root / ".env")
    return (
        os.getenv("OPENROUTER_API_KEY", "").strip(),
        os.getenv("OPENROUTER_MODEL", "").strip(),
    )

