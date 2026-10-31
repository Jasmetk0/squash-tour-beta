"""Build a source-identified portable Windows candidate; not an official release."""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path


def tracked_copy(root: Path, destination: Path, prefix: str) -> None:
    paths = subprocess.check_output(["git", "ls-files", "-z", "--", prefix], cwd=root)
    for raw in paths.split(b"\0"):
        if not raw:
            continue
        path = Path(raw.decode("utf-8"))
        source = root / path
        if source.is_symlink() or source.suffix in (".db", ".sqlite", ".sqlite3"):
            raise ValueError("Do not distribute linked files or local databases: " + str(path))
        target = destination / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)


def main():
    root = Path(__file__).resolve().parents[2]
    if sys.platform != "win32":
        raise SystemExit("Build on Windows; PyInstaller does not cross-compile Windows executables.")
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    # Build outputs are ignored; a dirty source checkout is never labelled as HEAD.
    if subprocess.run(["git", "diff", "--quiet", "HEAD"], cwd=root, check=False).returncode:
        raise SystemExit("Commit source changes before building an identified package.")
    subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
                    str(root / "tools/desktop/preview.spec")], cwd=root, check=True)
    package = root / "dist/SquashEnginePreview"
    tracked_copy(root, package, "config")
    # Existing engine provenance inspects source bytes. Preserve the exact
    # tracked source alongside the frozen runtime rather than inventing a hash.
    tracked_copy(root, package, "src")
    shutil.copytree(root / "web/dist", package / "web/dist")
    shutil.copyfile(root / "Spustit_Squash_Engine.bat", package / "Spustit_Squash_Engine.bat")
    (package / "docs").mkdir()
    shutil.copyfile(root / "docs/WINDOWS_PREVIEW.md", package / "docs/WINDOWS_PREVIEW.md")
    shutil.copyfile(root / "docs/PRE_ALPHA_TEST_POLICY.md", package / "docs/PRE_ALPHA_TEST_POLICY.md")
    dependencies = subprocess.check_output([sys.executable, "-m", "pip", "freeze"], text=True)
    (package / "build-dependencies.txt").write_text(dependencies, encoding="utf-8")
    metadata = {
        "format": "squash-desktop-preview.v1", "source_commit": commit,
        "label": "Internal test build; not a certified pre-alpha release",
        "python": sys.version, "platform": sys.platform,
        "dependency_fingerprint": hashlib.sha256(dependencies.encode()).hexdigest(),
    }
    (package / "build-info.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print("Prepared " + str(package))


if __name__ == "__main__":
    main()
