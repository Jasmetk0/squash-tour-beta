"""Pure diagnostic contract tests; no season or server workload."""
import copy
import json
import sqlite3
import sys
from types import SimpleNamespace

import pytest

from scripts import profile_native_week_ab as driver
from scripts.profile_native_week_ab import (
    PLANS, SCHEMA, SEED, comparable, compare, copy_fixture, digest,
    expected_calls, file_sha, summarize_trials, trial_order, record_progress, summarize_cpu_samples,
)


pytestmark = pytest.mark.pr_critical  # Pure, short contract checks; no real benchmark in Fast CI.


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
                         request_sha256=digest(None if get else label.replace(":retry", ":execute")),
                         wall_s=1.0, cpu_s=.8, current_rss_kib=100, peak_rss_kib=123,
                         read_syscall_bytes=200, storage_read_bytes=64,
                         sql_calls=2, sql_cursor_wall_s=.01, fetch_rows=3,
                         fetch_text_blob_bytes=40, db_bytes=4096, wal_bytes=12))
    return dict(schema=SCHEMA, status="ok", scenario="w6", mode=mode, profile_cpu=False,
                seed=SEED, plan=json.loads(json.dumps(PLANS["w6"])),
                input_sha256="f" * 64, before=snapshot,
                after={**snapshot, "revisions": 13}, calls=rows,
                wall_s=len(rows), cpu_s=sum(row["cpu_s"] for row in rows),
                elapsed_wall_s=len(rows)+1, elapsed_cpu_s=len(rows),
                peak_rss_kib=123, check_wall_s=2,
                initial_evidence={**ev, "position": [0, 4], "match_count": 0, "head": "start"},
                evidence=ev, history=[
                    dict(id=ident, parent=parent, payload_sha256="a" * 64,
                         summary_sha256="b" * 64, content_hash="c" * 64)
                    for ident, parent in (("start", None), ("play", "start"),
                                          ("confirm", "play"), ("head", "confirm"))
                ],
                metadata=dict(commit=commit, source_tree="c" * 40,
                              runner_sha256="r", metrics_sha256="m", process_measurement_sha256="p", python="3.11",
                              platform="Linux", machine="x86_64", cpu_count=4,
                              hardware={"cpu_model": "fixture"}, cpu_affinity_count=4,
                              dependencies={}, pythonhashseed="0", new_run_storage="v1"))


def test_equal_commits_comparison_and_retry_cost():
    a, b = report(), report(commit="b" * 40)
    for row in b["calls"][:4]:
        row["wall_s"] -= .5
    b["wall_s"] -= 2
    result = compare(a, b)
    assert result["verdict"] == "equal"
    assert result["delta_b_minus_a"]["wall_s"] == -2
    assert result["a"]["http_calls"] == 16
    assert result["a"]["read_syscall_bytes"] == 3200
    assert result["a"]["storage_read_bytes"] == 1024
    assert result["a"]["mean_busy_logical_cpus"] == pytest.approx(16 / 17)
    assert result["a"]["max_sampled_db_plus_wal_bytes"] == 4108
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
    lambda b: b["calls"][1].update(request_sha256="0" * 64),
    lambda b: b.update(elapsed_wall_s=0),
    lambda b: b.update(cpu_s=0),
    lambda b: b["calls"][0].update(request_sha256="0" * 64),
    lambda b: b["after"].update(revisions=14),
    lambda b: b["history"].pop(1),
    lambda b: b["history"][1].update(parent="unknown"),
    lambda b: b["history"][1].update(id="start"),
    lambda b: b["initial_evidence"].update(head="unknown"),
    lambda b: b["evidence"].update(position=[0, 6]),
    lambda b: b["evidence"].update(match_count=2),
    lambda b: b["evidence"].update(players=7),
    lambda b: b.update(peak_rss_kib=122),
    lambda b: b["calls"][0].update(storage_read_bytes=-1),
    lambda b: b["calls"][0].update(current_rss_kib=124),
    lambda b: b["metadata"].update(cpu_affinity_count=2),
    lambda b: b.update(profile_cpu=True),
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


def test_profiled_timings_require_both_sides_to_own_the_same_instrumentation():
    a, b = report(), report()
    b["profile_cpu"] = True
    measurement = {"exclusive_total_cpu_s": .35, "exclusive_cpu_s": {"other": .34, "unattributed": .01},
                   "cpu_sample_count": 11, "replay_entry_cpu_s": {}}
    for row in b["calls"]:
        row["endpoint_cpu_profile"] = measurement
    assert compare(b, b)["verdict"] == "equal"
    assert "different profiling modes" in compare(a, b)["reasons"]
    measurement["exclusive_total_cpu_s"] = .5
    assert compare(b, b)["verdict"] == "not_comparable"


def test_replay_subtree_overlaps_sampled_categories_without_double_counting_intervals():
    replay = ("/beta_engine/infrastructure/db/calendar_native_competition.py", 3, "verify_competition_payload")
    play = ("/beta_engine/domain/matches/match_engine.py", 12, "play")
    decode = ("/lib/json/decoder.py", 8, "raw_decode")
    result = summarize_cpu_samples([(9, [play]), (20, [play, replay, replay]),
                                    (35, [decode, replay]), (45, [decode])], 10, 40)
    assert result["exclusive_cpu_s"] == {
        "match_domain": 10e-9, "json_pydantic": 15e-9, "unattributed": 5e-9,
    }
    assert sum(result["exclusive_cpu_s"].values()) == pytest.approx(result["exclusive_total_cpu_s"])
    assert result["cpu_sample_count"] == 2
    assert result["replay_entry_cpu_s"] == {
        "competition_replay": {"samples": 2, "inclusive_cpu_s": 25e-9},
    }
    assert result["top_exclusive_functions"][0]["function"] == "raw_decode"


def test_endpoint_without_samples_reports_its_cpu_as_unattributed():
    measured = summarize_cpu_samples([], 10, 40)
    assert measured["cpu_sample_count"] == 0
    assert measured["exclusive_cpu_s"] == {"unattributed": 30e-9}


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


def test_retry_requires_identical_request_body():
    a, b = report(), report("retry")
    next(row for row in b["calls"] if row["label"].endswith(":retry"))["request_sha256"] = "0" * 64
    assert compare(a, b, cross_mode=True)["verdict"] == "not_comparable"


def trial():
    return {label + "-" + mode: report(mode, commit)
            for label, commit in (("A", "a" * 40), ("B", "b" * 40))
            for mode in ("normal", "retry")}


def test_trial_order_balances_commits_and_modes():
    first, second = trial_order(0), trial_order(1)
    assert len(set(first)) == 4
    assert second == list(reversed(first))
    assert trial_order(2) == first


def test_repeated_trials_report_median_range_and_paired_delta():
    first, second = trial(), trial()
    for row in second["B-normal"]["calls"]:
        row["wall_s"] *= .5
    second["B-normal"]["wall_s"] = 8
    result = summarize_trials([first, second])
    assert result["verdict"] == "equal"
    assert result["aggregate"]["normal"]["b"]["wall_s"] == {"median": 12, "min": 8, "max": 16}
    assert result["aggregate"]["normal"]["delta_b_minus_a"]["wall_s"]["median"] == -4
    assert len(result["repeat_checks"]) == 4


def test_repeated_results_must_match_even_if_both_commits_drift_together():
    first, second = trial(), trial()
    for item in second.values():
        item["evidence"]["rankings_sha256"] = "7" * 64
    result = summarize_trials([first, second])
    assert result["verdict"] == "invalid_experiment"
    assert "aggregate" not in result
    assert all(row["result"]["verdict"] == "different_results" for row in result["repeat_checks"])


def test_repeated_commits_cannot_be_relabelled():
    first, second = trial(), trial()
    for mode in ("normal", "retry"):
        second["B-" + mode]["metadata"]["commit"] = "d" * 40
    result = summarize_trials([first, second])
    assert result["verdict"] == "invalid_experiment"
    assert "aggregate" not in result


def test_fixture_copy_rejects_dangling_symlink(tmp_path):
    source, target = tmp_path / "source.db", tmp_path / "copy.db"
    source.write_bytes(b"immutable")
    missing = tmp_path / "missing.db"
    try:
        target.symlink_to(missing)
    except OSError as exc:
        if sys.platform == "win32" and getattr(exc, "winerror", None) == 1314:
            pytest.skip("Windows account lacks symbolic link privilege")
        raise
    with pytest.raises(FileExistsError):
        copy_fixture(source, target, file_sha(source))
    assert not missing.exists()


def test_phase_progress_survives_without_final_report(tmp_path):
    path = tmp_path / "worker.phases.jsonl"
    record_progress(path, {"label": "initial_get", "wall_s": 1})
    record_progress(path, {"label": "play:preview", "wall_s": 2})
    assert [json.loads(line)["label"] for line in path.read_text().splitlines()] == [
        "initial_get", "play:preview"]
    assert not (tmp_path / "worker.json").exists()


def test_sampled_wal_peak_not_hidden_by_checkpoint():
    a, b = report(), report()
    b["calls"][3]["wal_bytes"] = 100000
    result = compare(a, b)
    assert result["verdict"] == "equal"
    assert result["b"]["wal_bytes"] == 0
    assert result["b"]["max_sampled_wal_bytes"] == 100000
    assert result["delta_b_minus_a"]["max_sampled_wal_bytes"] == 99988


def windows_report(mode="normal", commit="a" * 40):
    item = report(mode, commit)
    item["metadata"].update(platform="Windows-11", cpu_affinity_count=None,
                            hardware={"cpu_model": "fixture", "memory_metric": "Windows working set"})
    for row in item["calls"]:
        row.update(read_syscall_bytes=None, storage_read_bytes=None)
    return item


def test_windows_unavailable_metrics_are_not_zero_in_comparison_or_aggregate():
    a, b = windows_report(), windows_report(commit="b" * 40)
    result = compare(a, b)
    assert result["verdict"] == "equal"
    for key in driver.PHASE_COUNTERS:
        for group in ("a", "b", "delta_b_minus_a"):
            assert result[group][key] is None
    assert result["a"]["peak_rss_kib"] == 123
    assert result["a"]["http_calls"] == 16
    trial = {label + "-" + mode: windows_report(mode, commit)
             for label, commit in (("A", "a" * 40), ("B", "b" * 40))
             for mode in ("normal", "retry")}
    summary = summarize_trials([trial, copy.deepcopy(trial)])
    assert summary["verdict"] == "equal"
    for case in summary["aggregate"].values():
        for group in ("a", "b", "delta_b_minus_a"):
            for key in driver.PHASE_COUNTERS:
                assert case[group][key] is None
    assert summary["aggregate"]["normal"]["a"]["http_calls"]["median"] == 16


@pytest.mark.parametrize("change", [
    lambda b: b["calls"][0].update(read_syscall_bytes=0),
    lambda b: b["calls"][0].pop("storage_read_bytes"),
    lambda b: b["metadata"].update(cpu_affinity_count=4),
    lambda b: b.update(profile_cpu=True),
    lambda b: b["calls"][0].update(current_rss_kib=None),
    lambda b: b["calls"][0].update(peak_rss_kib=None),
])
def test_windows_rejects_missing_required_or_fabricated_unavailable_metrics(change):
    a, b = windows_report(), windows_report()
    change(b)
    result = compare(a, b)
    assert result["verdict"] == "not_comparable"
    assert "delta_b_minus_a" not in result


def test_linux_null_io_is_not_comparable_and_mixed_platforms_are_rejected():
    a, b = report(), report()
    b["calls"][0]["read_syscall_bytes"] = None
    assert compare(a, b)["verdict"] == "not_comparable"
    assert compare(a, windows_report())["verdict"] == "not_comparable"


def test_windows_does_not_probe_linux_and_rejects_profile_before_start(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Linux probe called on Windows")

    with monkeypatch.context() as patch:
        patch.setattr(driver.sys, "platform", "win32")
        patch.setattr(driver.Path, "read_text", forbidden)
        patch.setattr(driver.os, "sched_getaffinity", forbidden, raising=False)
        driver.require_measurement_platform()
        assert driver.cpu_affinity_count() is None
        assert driver.io_delta(driver.process_io(), driver.process_io()) == {
            "read_syscall_bytes": None, "storage_read_bytes": None}
        with pytest.raises(ValueError, match="--profile-cpu requires"):
            driver.require_measurement_platform(True)


def test_linux_io_delta_and_profile_stay_available(monkeypatch):
    with monkeypatch.context() as patch:
        patch.setattr(driver.sys, "platform", "linux")
        patch.setattr(driver.Path, "read_text", lambda self: "rchar: 120\nread_bytes: 64")
        patch.setattr(driver.os, "sched_getaffinity", lambda pid: {0, 1}, raising=False)
        driver.require_measurement_platform(True)
        assert driver.cpu_affinity_count() == 2
        assert driver.io_delta({"read_syscall_bytes": 100, "storage_read_bytes": 0},
                               driver.process_io()) == {
            "read_syscall_bytes": 20, "storage_read_bytes": 64}


def test_measurement_server_disposes_pool_only_after_server_exit():
    calls = []
    engine = SimpleNamespace(dispose=lambda: calls.append("dispose"))
    runtime = SimpleNamespace(repository=SimpleNamespace(_engine=engine))

    class Server:
        thread = SimpleNamespace(is_alive=lambda: "exit" not in calls)
        app = SimpleNamespace(state=SimpleNamespace(runtime=runtime))

        def __enter__(self):
            calls.append("enter")
            return self

        def __exit__(self, *args):
            calls.append("exit")

    server = Server()
    with driver.measurement_server(server) as running:
        assert running is server
        assert calls == ["enter"]
    assert calls == ["enter", "exit", "dispose"]


def test_real_process_memory_has_current_and_peak():
    if not (sys.platform.startswith("linux") or sys.platform == "win32"):
        pytest.skip("Native week driver supports Linux and Windows")
    measured = driver.process_measurement.memory_kib()
    assert 0 < measured["VmRSS"] <= measured["VmHWM"]
    assert driver.process_measurement.peak_rss_kib() >= measured["VmHWM"]
