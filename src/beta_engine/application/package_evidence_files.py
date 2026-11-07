"""Safe, semantic access to package-owned provenance files."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from beta_engine.infrastructure.package_owned_paths import resolve_package_owned_file


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def canonical_json_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def load_json_object(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def safe_package_file(root: Path, relative_path: str) -> Path:
    return resolve_package_owned_file(root, relative_path, label="package evidence")
