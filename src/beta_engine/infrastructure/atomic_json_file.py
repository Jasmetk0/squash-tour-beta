"""Atomic replacement of the operator-configured legacy JSON files."""

import json
import os
import tempfile
from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager
from pathlib import Path


def require_regular_destination(path: Path) -> None:
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ValueError(f"{path} must be a regular file or a new destination")


@contextmanager
def stage_file_bytes(path: Path, payload: bytes) -> Iterator[Path]:
    require_regular_destination(path)
    try:
        mode = path.stat().st_mode & 0o777
    except FileNotFoundError:
        mode = None
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        # Exclusive creation avoids following any pre-existing link. Close the
        # staging handle before replacement, which Windows requires.
        with tempfile.NamedTemporaryFile(
            "wb", dir=path.parent, prefix=".squash-", delete=False
        ) as handle:
            temporary = Path(handle.name)
            if mode is not None and hasattr(os, "fchmod"):
                os.fchmod(handle.fileno(), mode)
            handle.write(payload)
        yield temporary
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def stage_json_file(path: Path, payload: object) -> AbstractContextManager[Path]:
    text = json.dumps(payload, indent=2) + "\n"
    return stage_file_bytes(path, text.replace("\n", os.linesep).encode("utf-8"))


def replace_json_file(path: Path, payload: object) -> None:
    with stage_json_file(path, payload) as temporary:
        temporary.replace(path)
