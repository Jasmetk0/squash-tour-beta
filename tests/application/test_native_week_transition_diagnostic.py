from contextlib import closing
import json
from pathlib import Path
import sqlite3
from types import SimpleNamespace

import pytest

from scripts import profile_native_week_transition as diagnostic

pytestmark = pytest.mark.pr_critical


def test_backup_accepts_relative_paths_keeps_source_and_closes_copy(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    source, target = Path("source with spaces.db"), Path("copy.db")
    with closing(sqlite3.connect(source)) as connection, connection:
        connection.execute("CREATE TABLE example (value TEXT)")
        connection.execute("INSERT INTO example VALUES ('original')")
    original_sha = diagnostic.file_sha(source)

    diagnostic.backup(source, target)

    with closing(sqlite3.connect(target)) as connection:
        assert connection.execute("SELECT value FROM example").fetchall() == [("original",)]
    assert diagnostic.file_sha(source) == original_sha
    target.unlink()


def test_prepare_rejects_stop_outside_calendar_before_writing(tmp_path):
    out = tmp_path / "unreachable"
    with pytest.raises(ValueError, match="inside the Run calendar"):
        diagnostic.prepare(SimpleNamespace(out=out, seasons=1, width=6, stop_season=0, stop_week=7))
    assert not out.exists()


def _write_report(root, *, sha="a" * 64, evidence="{}", profile=False, quick_check="ok"):
    root.mkdir()
    metadata = {
        "git_sha": "b" * 40,
        "input_sha256": sha,
        "phases_instrumented": False,
        "profiled": profile,
        "sqlite_quick_check": "ok",
        "peak_rss_mib": 1.0,
        "peak_db_plus_wal_bytes": 1024,
        "saved_revisions": 3,
    }
    phases = [{"phase": phase, "seconds": 1.0, "process_cpu_s": 0.5}
              for phase in ("preview", "execute", "save", "first_saved_get")]
    (root / "timings.json").write_text(json.dumps({"metadata": metadata, "phases": phases}))
    restart_metadata = {**metadata, "sqlite_quick_check": quick_check}
    (root / "restart.json").write_text(json.dumps({"metadata": restart_metadata, "phases": []}))
    (root / "expected.json").write_text("{}")
    (root / "evidence.json").write_text(evidence)


@pytest.mark.parametrize("evidence, status", [("{}", 0), ('{"different":true}', 2)])
def test_report_returns_failure_for_different_evidence(tmp_path, capsys, evidence, status):
    a, b = tmp_path / "a", tmp_path / "b"
    _write_report(a)
    _write_report(b, evidence=evidence)

    assert diagnostic.report(SimpleNamespace(roots=[a, b])) == status
    assert json.loads(capsys.readouterr().out)["identical"] is (status == 0)


@pytest.mark.parametrize("settings", [{"sha": "c" * 64}, {"profile": True}, {"quick_check": "damaged"}])
def test_report_refuses_unmatched_inputs_and_bad_restart(tmp_path, settings):
    a, b = tmp_path / "a", tmp_path / "b"
    _write_report(a)
    _write_report(b, **settings)

    with pytest.raises(ValueError):
        diagnostic.report(SimpleNamespace(roots=[a, b]))


def test_every_phase_names_an_existing_production_callable():
    import importlib

    for module_name, attribute, label in diagnostic.PHASES:
        owner = importlib.import_module(module_name)
        for part in attribute.split("."):
            owner = getattr(owner, part)
        assert callable(owner), (module_name, attribute, label)


def test_v87_fixture_adds_only_the_explicit_lifecycle_policy(monkeypatch):
    from tests.api import test_calendar_initial_world_adoption as adoption
    from tests.api import test_calendar_population_sporting_checkpoint as population
    from tests.api.test_calendar_tour_turn_pro_v87_flow import V87

    seen = []
    monkeypatch.setattr(population, "population_request", population.population_request)
    monkeypatch.setattr(adoption, "request", lambda server, **changes: seen.append(changes) or changes)
    diagnostic._use_v87_population()
    population.population_request("server", generation={"seed": 1})
    assert seen == [{"generation": {"seed": 1}, "lifecycle_policy": V87}]
