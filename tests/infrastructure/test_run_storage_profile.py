import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.pr_critical

def run_profiler(db_path: Path, *args) -> dict:
    cmd = [sys.executable, "scripts/profile_run_storage.py", "--database", str(db_path)] + list(args)
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return json.loads(res.stdout)

def test_profiler_success_byte_counts(tmp_path):
    db_path = tmp_path / "test_db.sqlite"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE mock_table (run_id TEXT, data TEXT);")
    conn.execute("INSERT INTO mock_table VALUES ('run-1', 'ASCII_ONLY');")
    # Non-ASCII text (e.g. 5 bytes in UTF-8: a (1) + é (2) + o (1) + ñ (2) = wait, length(blob) in python)
    conn.execute("INSERT INTO mock_table VALUES ('run-1', 'aéñ');") # 1 + 2 + 2 = 5 bytes

    conn.execute("CREATE TABLE branch_saved_revisions (revision_id TEXT, run_id TEXT, branch_id TEXT, parent_revision_id TEXT, payload_json TEXT, change_summary_json TEXT);")
    conn.execute("CREATE TABLE branch_working_drafts (branch_id TEXT, run_id TEXT, based_on_revision_id TEXT);")

    # 2 branches sharing a parent
    conn.execute("INSERT INTO branch_saved_revisions VALUES ('rev1', 'run-1', 'b1', NULL, '{\"base\": 1}', '{}');")
    conn.execute("INSERT INTO branch_saved_revisions VALUES ('rev2', 'run-1', 'b1', 'rev1', '{\"base\": 2}', '{}');")

    # inherited fork HEAD
    conn.execute("INSERT INTO branch_saved_revisions VALUES ('rev3', 'run-1', 'b2', 'rev1', '{\"fork\": 3}', '{}');")

    conn.execute("INSERT INTO branch_working_drafts VALUES ('b1', 'run-1', 'rev2');")
    conn.execute("INSERT INTO branch_working_drafts VALUES ('b2', 'run-1', 'rev3');")
    conn.commit()
    conn.close()

    output = run_profiler(db_path, "--run-id", "run-1", "--label", "test-lbl")
    assert output["label"] == "test-lbl"
    assert output["run_id_scope"] == "run-1"

    # Test specific metrics
    assert "branch_saved_revisions" in output["tables"]
    assert output["tables"]["branch_saved_revisions"]["row_count"] == 3

    bsr = output["branch_saved_revisions"]
    assert "b1" in bsr
    assert bsr["b1"]["count"] == 2
    assert bsr["b1"]["payload_bytes_sum"] == len('{"base": 1}') + len('{"base": 2}')
    assert bsr["b1"]["head_payload_bytes"] == len('{"base": 2}')

    assert "b2" in bsr
    assert bsr["b2"]["count"] == 1
    assert bsr["b2"]["payload_bytes_sum"] == len('{"fork": 3}')
    assert bsr["b2"]["head_payload_bytes"] == len('{"fork": 3}')

def test_active_wal_not_failing(tmp_path):
    db_path = tmp_path / "test_wal.sqlite"
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("CREATE TABLE branch_working_drafts (id INT);")
    conn.execute("INSERT INTO branch_working_drafts VALUES (1);")
    conn.commit()

    # Keep the connection open while another connection profiles it
    conn.execute("BEGIN IMMEDIATE;")
    conn.execute("INSERT INTO branch_working_drafts VALUES (2);")

    # Run the profiler in read-only mode; should succeed and not block forever (if WAL logic handles it).
    # Since we are using subprocess, it will connect.
    output = run_profiler(db_path)

    # It might see 1 or 2 rows depending on isolation, but it shouldn't fail.
    assert "branch_working_drafts" in output["tables"]

    conn.commit()
    conn.close()

def test_invalid_missing_db(tmp_path):
    db_path = tmp_path / "missing.sqlite"
    cmd = [sys.executable, "scripts/profile_run_storage.py", "--database", str(db_path)]
    res = subprocess.run(cmd, capture_output=True, text=True, check=False)
    assert res.returncode != 0
    assert "does not exist" in res.stderr

def test_db_path_with_spaces_hash_query(tmp_path):
    db_path = tmp_path / "my # test ? db.sqlite"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE branch_working_drafts (a INT);")
    conn.commit()
    conn.close()

    output = run_profiler(db_path)
    assert "branch_working_drafts" in output["tables"]

def test_output_collision(tmp_path):
    db_path = tmp_path / "test_coll.sqlite"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE t1 (id INT);")
    conn.commit()
    conn.close()

    cmd = [sys.executable, "scripts/profile_run_storage.py", "--database", str(db_path), "--output", str(db_path)]
    res = subprocess.run(cmd, capture_output=True, text=True, check=False)
    assert res.returncode != 0
    assert "Output path cannot overwrite" in res.stderr

    # Write to a valid file
    out_path = tmp_path / "out.json"
    cmd = [sys.executable, "scripts/profile_run_storage.py", "--database", str(db_path), "--output", str(out_path)]
    subprocess.run(cmd, check=True)

    assert out_path.exists()
    data = json.loads(out_path.read_text())
    assert "branch_saved_revisions" not in data["tables"]
