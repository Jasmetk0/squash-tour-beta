"""Storage diagnostics against the real ORM schema, not an invented draft schema."""

import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import URL, create_engine

from beta_engine.infrastructure.db.models import Base

pytestmark = pytest.mark.pr_critical
SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "profile_run_storage.py"
PAYLOADS = ('{"name":"é"}', '{"name":"Ř😀"}', '{"other":9}')


def invoke(path, *args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--database", str(path), *args],
        capture_output=True, text=True, check=False, timeout=15,
    )


def report(path, *args):
    result = invoke(path, *args)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def make_database(path):
    engine = create_engine(URL.create("sqlite", database=str(path)))
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        for run in ("run-a", "run-b"):
            connection.execute(Base.metadata.tables["runs"].insert().values(
                run_id=run, display_name=run, timeline_start_season=0, timeline_end_season=49,
                storage_kind="custom_local",
            ))
        for branch, run, head, parent, source in (
            ("root", "run-a", "a2", None, None),
            ("fork", "run-a", "a1", "root", "a1"),
            ("other", "run-b", "b1", None, None),
        ):
            connection.execute(Base.metadata.tables["run_branches"].insert().values(
                branch_id=branch, run_id=run, display_name=branch,
                saved_head_revision_id=head, forked_from_branch_id=parent,
                forked_from_saved_revision_id=source,
            ))
        for revision, run, branch, sequence, parent, body in (
            ("a1", "run-a", "root", 1, None, PAYLOADS[0]),
            ("a2", "run-a", "root", 2, "a1", PAYLOADS[1]),
            ("b1", "run-b", "other", 1, None, PAYLOADS[2]),
        ):
            connection.execute(Base.metadata.tables["branch_saved_revisions"].insert().values(
                revision_id=revision, run_id=run, branch_id=branch, sequence=sequence,
                parent_revision_id=parent, kind="initial" if sequence == 1 else "save",
                payload_schema_version="run_saved_revision_v1", content_hash_algorithm="sha256",
                content_hash="0" * 64, payload_json=body, change_summary_json="{}",
            ))
        # Deliberately stale: a draft base is NOT the persisted Branch HEAD.
        connection.execute(Base.metadata.tables["branch_working_drafts"].insert().values(
            draft_id="draft", run_id="run-a", branch_id="root",
            base_revision_id="a1", draft_schema_version="test.v1",
        ))
    engine.dispose()
    return path


@pytest.fixture
def database(tmp_path):
    return make_database(tmp_path / "engine.sqlite")


def test_real_schema_utf8_totals_and_source_owned_fork_head(database):
    with sqlite3.connect(database) as connection:
        before = list(connection.iterdump())
    data = report(database, "--run-id", "run-a", "--label", "synthetic")
    assert data["schema_version"] == "run_storage_profile.v1"
    assert data["label"] == "synthetic"
    expected = sum(len(body.encode("utf-8")) for body in PAYLOADS[:2])
    assert data["saved_revision_totals"]["payload_bytes_sum"] == expected
    assert data["saved_revision_totals"]["change_summary_bytes_sum"] == 4
    assert data["saved_revision_totals"]["count"] == 2
    assert data["saved_revision_totals"]["payload_bytes_mean"] == expected / 2
    assert data["saved_revision_totals"]["payload_bytes_max"] == len(PAYLOADS[1].encode())
    assert set(data["branch_saved_revisions"]) == {"root"}
    assert data["branch_saved_revisions"]["root"]["count"] == 2
    assert data["branch_heads"]["root"]["revision_id"] == "a2"
    assert data["branch_heads"]["root"]["payload_bytes"] == len(PAYLOADS[1].encode())
    assert data["branch_heads"]["fork"]["revision_id"] == "a1"
    assert data["branch_heads"]["fork"]["original_owner_branch_id"] == "root"
    assert data["branch_heads"]["fork"]["payload_bytes"] == len(PAYLOADS[0].encode())
    assert data["tables"]["branch_saved_revisions"]["scope"] == "selected_run"
    assert data["page_metrics"]["scope"] == "whole_database"
    assert data["page_metrics"]["allocated_bytes"] == (
        data["page_metrics"]["page_count"] * data["page_metrics"]["page_size"]
    )
    assert data["dbstat"]["status"] == "not_collected"
    assert data["physical_sizes"]["db"]["bytes"] == database.stat().st_size
    with sqlite3.connect(database) as connection:
        assert list(connection.iterdump()) == before


def test_whole_database_counts_each_persisted_revision_once(database):
    data = report(database)
    assert data["saved_revision_totals"]["count"] == 3
    assert data["saved_revision_totals"]["payload_bytes_sum"] == sum(len(p.encode()) for p in PAYLOADS)
    assert set(data["branch_heads"]) == {"root", "fork", "other"}
    assert data["tables"]["runs"]["row_count"] == 2


def test_active_wal_reads_committed_rows_not_uncommitted_head(database):
    writer = sqlite3.connect(database)
    try:
        writer.execute("PRAGMA journal_mode=WAL")
        writer.execute("UPDATE runs SET display_name='committed' WHERE run_id='run-a'")
        writer.commit()
        before = list(writer.iterdump())
        writer.execute("BEGIN IMMEDIATE")
        writer.execute("UPDATE run_branches SET saved_head_revision_id='uncommitted-invalid' WHERE branch_id='root'")
        data = report(database, "--run-id", "run-a")
        assert data["branch_heads"]["root"]["revision_id"] == "a2"
        assert data["saved_revision_totals"]["count"] == 2
        assert data["physical_sizes"]["wal"]["bytes"] > 0
        assert writer.in_transaction
        writer.rollback()
        assert list(writer.iterdump()) == before
        writer.execute("BEGIN IMMEDIATE")  # collector closed its read transaction
        writer.rollback()
    finally:
        writer.close()


@pytest.mark.parametrize("filename", ["my # test ? db.sqlite", "český % údaj.sqlite"])
def test_uri_reserved_characters_and_unicode(tmp_path, filename):
    path = make_database(tmp_path / filename)
    assert report(path)["saved_revision_totals"]["count"] == 3


@pytest.mark.parametrize("kind", ["missing", "zero", "corrupt", "unrelated", "malformed", "utf16", "view"])
def test_invalid_or_unsupported_database_never_produces_success(tmp_path, kind):
    path = tmp_path / f"{kind}.sqlite"
    if kind == "zero":
        path.touch()
    elif kind == "corrupt":
        path.write_bytes(b"this is not SQLite")
    elif kind not in ("missing",):
        with sqlite3.connect(path) as connection:
            if kind == "utf16":
                connection.execute("PRAGMA encoding='UTF-16'")
                connection.execute("CREATE TABLE runs(run_id TEXT)")
            elif kind == "view":
                connection.execute("CREATE VIEW runs AS SELECT 'x' AS run_id")
            elif kind == "malformed":
                connection.execute("CREATE TABLE branch_saved_revisions(wrong_column TEXT)")
            else:
                connection.execute("CREATE TABLE unknown_table(x INT)")
    output = tmp_path / "never.json"
    result = invoke(path, "--output", str(output))
    assert result.returncode != 0
    assert "Error:" in result.stderr
    assert result.stdout == ""
    assert not output.exists()
    if kind == "missing":
        assert not path.exists()


def test_missing_optional_tables_are_explicit_and_not_zero(tmp_path):
    path = tmp_path / "partial.sqlite"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE branch_working_drafts(legacy_id INT)")
        connection.execute("INSERT INTO branch_working_drafts VALUES(1)")
    data = report(path, "--run-id", "not-verifiable")
    assert data["tables"]["branch_working_drafts"]["row_count"] == 1
    assert data["tables"]["branch_working_drafts"]["scope"] == "whole_database"
    assert data["tables"]["branch_saved_revisions"]["reason"] == "table_absent"
    assert data["saved_revision_totals"] is None


def test_unknown_run_and_foreign_run_head_fail(database):
    assert invoke(database, "--run-id", "absent").returncode != 0
    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE run_branches SET saved_head_revision_id='b1' WHERE branch_id='root'")
    result = invoke(database, "--run-id", "run-a")
    assert result.returncode != 0
    assert "foreign-Run HEAD" in result.stderr


def test_output_collision_and_exclusive_create(database, tmp_path):
    existing = tmp_path / "existing.json"
    existing.write_text("keep this")
    hardlink = tmp_path / "hardlink"
    hardlink.hardlink_to(database)
    dangling = tmp_path / "dangling"
    dangling.symlink_to(tmp_path / "missing-target")
    for path in (
        database, Path(str(database) + "-wal"), Path(str(database) + "-shm"),
        existing, hardlink, dangling,
    ):
        assert invoke(database, "--output", str(path)).returncode != 0
    assert existing.read_text() == "keep this"
    assert dangling.is_symlink()
    output = tmp_path / "report.json"
    result = invoke(database, "--output", str(output))
    assert result.returncode == 0, result.stderr
    assert result.stdout == ""
    assert json.loads(output.read_text())["saved_revision_totals"]["count"] == 3
    original = output.read_bytes()
    assert invoke(database, "--output", str(output)).returncode != 0
    assert output.read_bytes() == original
