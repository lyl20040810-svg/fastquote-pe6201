"""Price-list loading and exact product lookup."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class Catalog:
    def __init__(self, path: Path):
        self.path = path
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.metadata = payload["metadata"]
        self.rows = payload["rows"]
        self._index = {
            (row["standard"].upper(), row["diameter"].upper(), int(row["length_mm"])): row
            for row in self.rows
        }

    def find(self, standard: str, diameter: str, length_mm: int) -> dict[str, Any] | None:
        return self._index.get((standard.upper(), diameter.upper(), int(length_mm)))

    def allowed_skus(self) -> list[str]:
        return [row["sku"] for row in self.rows]

