"""Fail Fast CI if the pinned environment no longer covers the engine."""

import importlib.metadata
import tomllib
from pathlib import Path

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name


def main() -> None:
    lock_path = Path(".github/requirements/fast-ci-linux.lock.txt")
    locked = {}
    for line in lock_path.read_text(encoding="utf-8").splitlines():
        if not line or line[0].isspace() or line.startswith("#"):
            continue
        pinned = Requirement(line.removesuffix("\\").strip())
        name = canonicalize_name(pinned.name)
        locked[name] = pinned
        if not pinned.specifier.contains(importlib.metadata.version(name)):
            raise SystemExit(f"Fast CI did not install the locked version of {name}")

    with Path("pyproject.toml").open("rb") as stream:
        runtime = tomllib.load(stream)["project"]["dependencies"]
    for declaration in (*runtime, "pytest"):
        required = Requirement(declaration)
        if required.marker is not None and not required.marker.evaluate():
            continue
        name = canonicalize_name(required.name)
        pinned = locked.get(name)
        if (
            pinned is None
            or not required.extras <= pinned.extras
            or not required.specifier.contains(importlib.metadata.version(name))
        ):
            raise SystemExit(f"Update {lock_path} for engine requirement: {declaration}")


if __name__ == "__main__":
    main()
