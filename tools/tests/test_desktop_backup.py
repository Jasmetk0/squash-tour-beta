"""Offline Windows preview backup contract tests; no real installed engine needed."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sqlite3
import zipfile
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "backup_launcher", Path(__file__).parents[1] / "desktop" / "launcher.py"
)
launcher = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(launcher)


@pytest.fixture
def running_data(tmp_path):
    program = tmp_path / "program"
    (program / "config").mkdir(parents=True)
    (program / "config" / "world.json").write_text('{"default":true}', encoding="utf-8")
    (program / "web" / "dist").mkdir(parents=True)
    (program / "web" / "dist" / "index.html").write_text("<html></html>", encoding="utf-8")
    build = {"format": "squash-desktop-preview.v1", "source_commit": "a" * 40}
    (program / "build-info.json").write_text(json.dumps(build), encoding="utf-8")
    data = tmp_path / "user data český"
    with launcher.DataLock(data):
        launcher.prepare_data(program, data, build)
    (data / "config" / "world.json").write_text('{"user":"custom"}', encoding="utf-8")
    with sqlite3.connect(data / "beta_engine.db") as connection:
        connection.execute("CREATE TABLE run_marker (id INTEGER PRIMARY KEY, name TEXT)")
        connection.execute("INSERT INTO run_marker VALUES (1, 'Saved run český')")
        connection.commit()
    (data / "launcher.log").write_text("startup complete", encoding="utf-8")
    return program, data, build


def test_offline_zip_preserves_saved_sqlite_config_and_owner(running_data, tmp_path):
    program, data, build = running_data
    before_db = hashlib.sha256((data / "beta_engine.db").read_bytes()).hexdigest()
    before_config = (data / "config" / "world.json").read_bytes()
    destination = tmp_path / "backups" / "Run český.zip"

    result = launcher.offline_backup(program, data, destination)
    assert result["verified"] is True
    assert result["source_commit"] == build["source_commit"]
    assert result["archive"] == str(destination)
    assert launcher.verify_offline_backup(destination)["verified"] is True
    assert (data / "config" / "world.json").read_bytes() == before_config
    assert hashlib.sha256((data / "beta_engine.db").read_bytes()).hexdigest() == before_db

    with zipfile.ZipFile(destination) as archive:
        entries = set(archive.namelist())
        assert entries == {
            "backup-manifest.json", "data/preview-owner.json",
            "data/config/world.json", "data/beta_engine.db", "data/launcher.log"
        }
        assert archive.read("data/config/world.json") == b'{"user":"custom"}'
        assert b"Saved run" in archive.read("data/beta_engine.db")
        extracted = tmp_path / "temporary extraction"
        extracted.mkdir()
        (extracted / "beta_engine.db").write_bytes(archive.read("data/beta_engine.db"))
        with sqlite3.connect(extracted / "beta_engine.db") as db:
            assert db.execute("SELECT name FROM run_marker").fetchone() == ("Saved run český",)


def test_cannot_back_up_a_running_engine_or_release_a_partial_file(running_data, tmp_path):
    program, data, _ = running_data
    output = tmp_path / "locked.zip"
    with launcher.DataLock(data), pytest.raises(launcher.LaunchError, match="already in use"):
        launcher.offline_backup(program, data, output)
    assert not output.exists()
    assert launcher.verify_offline_backup(
        launcher.offline_backup(program, data, tmp_path / "unlocked.zip")["archive"]
    )["verified"]


def test_foreign_identity_missing_database_and_invalid_sqlite_fail_closed(running_data, tmp_path):
    program, data, build = running_data
    destination = tmp_path / "backup.zip"
    owner = data / "preview-owner.json"
    owner.write_text(json.dumps({**build, "source_commit": "b" * 40}), encoding="utf-8")
    with pytest.raises(launcher.LaunchError, match="another build"):
        launcher.offline_backup(program, data, destination)
    assert not destination.exists()
    owner.write_text(json.dumps(build), encoding="utf-8")

    db = data / "beta_engine.db"
    original = db.read_bytes()
    db.write_bytes(b"not sqlite")
    with pytest.raises(launcher.LaunchError, match="SQLite"):
        launcher.offline_backup(program, data, destination)
    assert db.read_bytes() == b"not sqlite"
    assert not destination.exists()

    db.unlink()
    with pytest.raises(launcher.LaunchError, match="missing"):
        launcher.offline_backup(program, data, destination)
    assert not destination.exists()
    db.write_bytes(original)


def test_refuses_overwrite_inside_data_and_installed_program(running_data, tmp_path):
    program, data, _ = running_data
    output = tmp_path / "original.zip"
    output.write_bytes(b"KEEP ME")
    for destination in (output, data / "unsafe.zip", program / "unsafe.zip"):
        with pytest.raises(launcher.LaunchError):
            launcher.offline_backup(program, data, destination)
    assert output.read_bytes() == b"KEEP ME"
    assert not (data / "unsafe.zip").exists()
    assert not (program / "unsafe.zip").exists()


def test_symlink_in_data_is_rejected_without_reading_external_file(running_data, tmp_path):
    program, data, _ = running_data
    private = tmp_path / "outside-secret.txt"
    private.write_text("do not include", encoding="utf-8")
    try:
        (data / "outside").symlink_to(private)
    except (NotImplementedError, OSError):
        pytest.skip("Symlinks unavailable under the current user privileges")
    destination = tmp_path / "linked.zip"
    with pytest.raises(launcher.LaunchError, match="linked"):
        launcher.offline_backup(program, data, destination)
    assert not destination.exists()
    assert private.read_text() == "do not include"


def test_incomplete_or_corrupted_zip_manifest_is_not_trusted(running_data, tmp_path):
    program, data, _ = running_data
    clean = tmp_path / "clean.zip"
    launcher.offline_backup(program, data, clean)

    with zipfile.ZipFile(clean) as original:
        payloads = {name: original.read(name) for name in original.namelist()}
    corrupt = tmp_path / "corrupt.zip"
    with zipfile.ZipFile(corrupt, "w") as writer:
        for name, payload in payloads.items():
            writer.writestr(name, b"ALTERED" if name == "data/config/world.json" else payload)
    with pytest.raises(launcher.LaunchError, match="checksum"):
        launcher.verify_offline_backup(corrupt)

    for name in ("data/../escape.txt", "data/evil\\windows", "/absolute.txt"):
        forged = tmp_path / ("forged-" + str(len(name)) + "-" + name[-3:] + ".zip")
        with zipfile.ZipFile(forged, "w") as writer:
            writer.writestr("backup-manifest.json", payloads["backup-manifest.json"])
            writer.writestr(name, b"malicious")
        with pytest.raises(launcher.LaunchError):
            launcher.verify_offline_backup(forged)

    duplicate = tmp_path / "duplicate.zip"
    with zipfile.ZipFile(duplicate, "w") as writer:
        writer.writestr("backup-manifest.json", payloads["backup-manifest.json"])
        writer.writestr("backup-manifest.json", payloads["backup-manifest.json"])
    with pytest.raises(launcher.LaunchError, match="duplicate"):
        launcher.verify_offline_backup(duplicate)


def test_snapshot_includes_committed_wal_state_without_copying_wal_files(running_data, tmp_path):
    program, data, _ = running_data
    with sqlite3.connect(data / "beta_engine.db") as connection:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("INSERT INTO run_marker VALUES (2, 'WAL world')")
        connection.commit()
        result = launcher.offline_backup(program, data, tmp_path / "wal.zip")
    with zipfile.ZipFile(result["archive"]) as reader:
        assert "data/beta_engine.db-wal" not in reader.namelist()
        assert "data/beta_engine.db-shm" not in reader.namelist()
        snapshot = tmp_path / "restored-only-for-test.db"
        snapshot.write_bytes(reader.read("data/beta_engine.db"))
    with sqlite3.connect(snapshot) as connection:
        assert connection.execute("SELECT name FROM run_marker ORDER BY id").fetchall() == [
            ("Saved run český",), ("WAL world",)
        ]
