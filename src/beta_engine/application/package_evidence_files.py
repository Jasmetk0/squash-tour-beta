"""Safe, semantic access to package-owned provenance files."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


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
    """Resolve a regular package-owned file and reject traversal and symlink tricks."""

    if not isinstance(relative_path, str) or not relative_path or "\\" in relative_path:
        raise ValueError("package evidence path must be a non-empty portable relative path")
    relative = Path(relative_path)
    if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
        raise ValueError(f"unsafe package evidence path {relative_path!r}")

    root_resolved = root.resolve()
    cursor = root
    for part in relative.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise ValueError(f"package evidence path uses symlink {relative_path!r}")

    try:
        resolved = (root / relative).resolve(strict=True)
    except OSError as exc:
        raise ValueError(f"package evidence file is unavailable: {relative_path}") from exc
    if not resolved.is_relative_to(root_resolved):
        raise ValueError(f"package evidence path escapes package root: {relative_path!r}")
    if not resolved.is_file():
        raise ValueError(f"package evidence path is not a regular file: {relative_path!r}")
    return resolved
