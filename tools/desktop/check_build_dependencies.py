"""Verify the isolated Python environment for the portable Windows preview."""

import importlib.metadata
import re
import sys
import sysconfig
import tomllib
from pathlib import Path

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

ROOT = Path(__file__).resolve().parents[2]
LOCK = ROOT / ".github/requirements/windows-preview-win-amd64.lock.txt"
TOOLS = ("pytest", "playwright", "pyinstaller", "packaging")


def read_locked_requirements(path: Path) -> dict[str, Requirement]:
    result = {}
    text = path.read_text(encoding="utf-8").replace("\\\n", " ")
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        declaration, *hashes = line.split()
        requirement = Requirement(declaration)
        name = canonicalize_name(requirement.name)
        if (
            requirement.marker is not None
            or requirement.url is not None
            or not re.fullmatch(r"==[^,\s*]+", str(requirement.specifier))
            or not hashes
            or any(not re.fullmatch(r"--hash=sha256:[0-9a-f]{64}", value) for value in hashes)
            or name in result
        ):
            raise ValueError(f"Invalid pinned wheel declaration: {declaration}")
        result[name] = requirement
    return result


def verify_build_dependencies() -> None:
    if sys.version_info[:2] != (3, 12) or sysconfig.get_platform() != "win-amd64":
        raise SystemExit("Portable preview requires Windows x64 and CPython 3.12.")
    if sys.prefix == sys.base_prefix:
        raise SystemExit("Build the portable preview in a fresh virtual environment.")
    locked = read_locked_requirements(LOCK)
    installed = {
        canonicalize_name(distribution.metadata["Name"]): distribution.version
        for distribution in importlib.metadata.distributions()
    }
    # pip belongs to the interpreter's venv bootstrap, not the product closure.
    extras = set(installed) - locked.keys() - {"pip"}
    if extras:
        raise SystemExit(f"Unexpected Python packages in the build environment: {sorted(extras)}")
    for name, requirement in locked.items():
        if name not in installed or not requirement.specifier.contains(installed[name]):
            raise SystemExit(f"Build environment must install {requirement} from the Windows lock")

    with (ROOT / "pyproject.toml").open("rb") as stream:
        runtime = tomllib.load(stream)["project"]["dependencies"]

    def check(declaration: str, *, owner: str, active_extras: set[str]) -> None:
        required = Requirement(declaration)
        if required.marker is not None and not any(
            required.marker.evaluate({"extra": extra}) for extra in ("", *active_extras)
        ):
            return
        name = canonicalize_name(required.name)
        if (
            name not in locked
            or not required.extras <= locked[name].extras
            or not required.specifier.contains(installed[name])
        ):
            raise SystemExit(f"Update the Windows wheel lock: {owner} requires {declaration}")

    for declaration in (*runtime, *TOOLS):
        check(declaration, owner="portable preview", active_extras=set())
    for name, requirement in locked.items():
        for declaration in importlib.metadata.requires(name) or ():
            check(declaration, owner=name, active_extras=requirement.extras)


if __name__ == "__main__":
    verify_build_dependencies()
