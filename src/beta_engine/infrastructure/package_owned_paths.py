"""Resolve package metadata paths with the same syntax on every host."""

import stat
from pathlib import Path

_WINDOWS_DEVICES = frozenset(
    {"CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$"}
    | {f"{kind}{digit}" for kind in ("COM", "LPT") for digit in "0123456789¹²³"}
)
_MOUNT_POINT = getattr(stat, "IO_REPARSE_TAG_MOUNT_POINT", -1)


def _portable_component(part: str) -> bool:
    return (
        bool(part)
        and part == part.strip(" ")
        and not part.endswith(".")
        and all(ord(char) >= 32 and char not in '<>:"\\|?*' for char in part)
        and part.split(".", 1)[0].rstrip(" ").upper() not in _WINDOWS_DEVICES
    )


def _redirects(path: Path) -> bool:
    info = path.lstat()
    return (
        stat.S_ISLNK(info.st_mode)
        or getattr(info, "st_reparse_tag", None) == _MOUNT_POINT
    )


def resolve_package_owned_file(root: Path, relative_path: str, *, label: str) -> Path:
    """Reject alternate spellings before looking up package-controlled names."""
    if not isinstance(relative_path, str) or not relative_path:
        raise ValueError(f"{label} path must be a non-empty portable relative path")
    # Path() normalizes repeated separators and dots, and drive syntax only has
    # meaning on Windows. Check raw components before invoking the host parser.
    parts = relative_path.split("/")
    if not all(_portable_component(part) for part in parts):
        raise ValueError(f"unsafe {label} path {relative_path!r}")

    try:
        if _redirects(root):
            raise ValueError(f"{label} root must not be a symlink or junction")
        owner = root.resolve(strict=True)
        cursor = owner
        for part in parts:
            cursor /= part
            if _redirects(cursor):
                raise ValueError(f"{label} path uses symlink or junction {relative_path!r}")
        resolved = cursor.resolve(strict=True)
    except OSError as exc:
        raise ValueError(f"{label} file is unavailable: {relative_path}") from exc
    if not resolved.is_relative_to(owner):
        raise ValueError(f"{label} path escapes package root: {relative_path!r}")
    if not resolved.is_file():
        raise ValueError(f"{label} path is not a regular file: {relative_path!r}")
    return resolved
