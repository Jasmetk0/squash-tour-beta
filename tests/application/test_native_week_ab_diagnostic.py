"""Pure diagnostic contract tests; no season or server workload."""
import copy
import json
import sqlite3

import pytest

from scripts.profile_native_week_ab import (
    PLANS, SCHEMA, SEED, comparable, compare, copy_fixture, digest,
    expected_calls, file_sha,
)


def report(mode="normal", commit="a" * 40):
    snapshot = dict(db_bytes=4096, wal_bytes=0, revisions=10,
                    stored_payload_column_bytes=1000)
    ev = {key: "e" * 64 for key in (
        "players_sha256", "editions_sha256", "matches_sha256",
        "edition_evidence_sha256", "rankings_sha256", "inspection_sha256")}
    ev.update(players=8, match_count=3, head="head", position=[0, 5])
    rows = []
    for label in expected_calls("w6", mode):
        get = label.endswith("get")
        rows.append(dict(label=label, method="GET" if get else "POST",
                         status=200 if get or label.endswith(":preview") else 201,
                         wall_s=1.0, cpu_s=.8, peak_rss_kib=123,
                         sql_calls=2, sql_cursor_wall_s=.01, fetch_rows=3,
                         fetch_text_blob_bytes=40, db_bytes=4096, wal_bytes=12))
    return dict(schema=SCHEMA, status="ok", scenario="w6", mode=mode,
                seed=SEED, plan=json.loads(json.dumps(PLANS["w6"])),
                input_sha256="f" * 64, before=snapshot,
                after={**snapshot, "revisions": 13}, calls=rows,
                wall_s=len(rows), cpu_s=12, peak_rss_kib=123, check_wall_s=2,
                initial_evidence={**ev, "position": [0, 4], "match_count": 0},
                evidence=ev, history=[dict(id="head", payload_sha256="a" * 64,
                                          summary_sha256="b" * 64, content_hash="c" * 64)],
                metadata=dict(commit=commit, source_tree="c" * 40,
                              runner_sha256="r", metrics_sha256="m", python="3.11",
                              platform="Linux", machine="x86_64", cpu_count=4,
                              dependencies={}, pythonhashseed="0", new_run_storage="v1"))


def test_equal_commits_comparison_and_retry_cost():
    a, b = report(), report(commit="b" * 40)
    b["wall_s"] -= 2
    result = compare(a, b)
    assert result["verdict"] == "equal"
    assert result["delta_b_minus_a"]["wall_s"] == -2
    assert result["a"]["http_calls"] == 16
    retry = compare(a, report("retry"), cross_mode=True)
    assert retry["verdict"] == "equal"
    assert retry["delta_b_minus_a"]["http_calls"] == 2
    assert retry["deliberate_retry_wall_s"] == 2
    assert compare(a, report("retry", "b" * 40), cross_mode=True)["verdict"] == "not_comparable"


@pytest.mark.parametrize("change", [
    lambda b: b.update(input_sha256="0" * 64),
    lambda b: b.update(seed=232),
    lambda b: b.update(plan=[["transition", None]]),
    lambda b: b["calls"].reverse(),
    lambda b: b["calls"][0].update(status=409),
    lambda b: b["calls"][0].update(wall_s=float("nan")),
    lambda b: b["metadata"].update(dependencies={"sqlalchemy": "different"}),
    lambda b: b.pop("history"),
    lambda b: b.pop("wall_s"),
    lambda b: b.update(status="failed"),
    lambda b: b["after"].update(revisions=14),
])
def test_incompatible_or_incomplete_report(change):
    a = report()
    b = copy.deepcopy(a)
    change(b)
    result = compare(a, b)
    assert result["verdict"] == "not_comparable"
    assert "delta_b_minus_a" not in result


@pytest.mark.parametrize("key", ["matches_sha256", "rankings_sha256", "players_sha256",
                                "edition_evidence_sha256", "inspection_sha256"])
def test_changed_sporting_results(key):
    a, b = report(), report()
    b["evidence"][key] = "9" * 64
    assert compare(a, b)["verdict"] == "different_results"


def test_changed_logical_history_and_order():
    a, b = report(), report()
    b["history"][0]["payload_sha256"] = "9" * 64
    assert compare(a, b)["verdict"] == "different_results"
    assert digest(["match1", "match2"]) != digest(["match2", "match1"])
    assert digest({"a": 1, "b": 2}) == digest({"b": 2, "a": 1})


def test_fixture_copy_never_overwrites_or_uses_wal(tmp_path):
    source, target = tmp_path / "source.db", tmp_path / "copy.db"
    with sqlite3.connect(source) as con:
        con.execute("create table example (id integer)")
        con.execute("insert into example values (1)")
    con.close()
    expected = file_sha(source)
    copy_fixture(source, target, expected)
    assert file_sha(target) == expected
    with sqlite3.connect(target) as con:
        con.execute("insert into example values (2)")
    con.close()
    assert file_sha(source) == expected
    with pytest.raises(ValueError):
        copy_fixture(source, target, expected)
    with pytest.raises(ValueError):
        copy_fixture(source, tmp_path / "wrong.db", "0" * 64)
    source.with_name("source.db-wal").touch()
    with pytest.raises(ValueError):
        copy_fixture(source, tmp_path / "wal.db", expected)


def test_modes_are_not_comparable_by_default():
    assert comparable(report(), report("retry"))
