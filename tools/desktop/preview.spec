# Windows-only one-folder build. Non-code resources are staged beside the exe.
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules

root = Path(SPECPATH).resolve().parents[1]
a = Analysis(
    [str(root / "tools/desktop/launcher.py")],
    pathex=[str(root / "src")],
    hiddenimports=collect_submodules("beta_engine") + [
        "uvicorn.loops.asyncio", "uvicorn.protocols.http.h11_impl", "uvicorn.lifespan.on",
    ],
    excludes=["pytest", "playwright", "tests"],
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="SquashEnginePreview",
          console=True, contents_directory="_internal")
coll = COLLECT(exe, a.binaries, a.datas, name="SquashEnginePreview")
